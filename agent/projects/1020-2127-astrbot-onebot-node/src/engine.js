/**
 * Core decision engine for group-autochat.
 *
 * Scope: history buffer, observe/decide/recordReply/reset; gates for empty /
 * bot-spoke-last / cold / quiet-hours / cooldown / hourly-cap /
 * reply-to-other / rapid-exchange; relevance scoring; mention bypass.
 * Prompt building lives in prompt.js and is re-exported here.
 */

const QUESTION_RE = /[\?？]|怎么|如何|为什么|是不是|能不能|有没有|吗|呢/;
const HOUR_MS = 60 * 60 * 1000;

export const DEFAULT_OPTIONS = Object.freeze({
  historyLimit: 40,
  contextLimit: 12,
  activeWindowMs: 5 * 60 * 1000,
  cooldownMs: 3 * 60 * 1000,
  maxPerHour: 6,
  minScore: 0.55,
  quietHours: Object.freeze({ start: '23:30', end: '08:00' }),
  interestKeywords: Object.freeze([]),
  rapidWindowMs: 20 * 1000,
  now: Date.now,
});

function assertInteger(name, value, min, max) {
  if (typeof value !== 'number' || !Number.isInteger(value)) {
    throw new TypeError(`${name} must be an integer`);
  }
  if (value < min || value > max) {
    throw new RangeError(`${name} must be between ${min} and ${max}`);
  }
}

function assertNumber(name, value, min, max) {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new TypeError(`${name} must be a finite number`);
  }
  if (value < min || value > max) {
    throw new RangeError(`${name} must be between ${min} and ${max}`);
  }
}

function assertTime(name, value) {
  if (typeof value !== 'string' || !/^([01]\d|2[0-3]):[0-5]\d$/.test(value)) {
    throw new TypeError(`${name} must be HH:MM`);
  }
}

function validateOptions(options) {
  assertInteger('historyLimit', options.historyLimit, 5, 200);
  assertInteger('contextLimit', options.contextLimit, 1, 50);
  assertInteger('activeWindowMs', options.activeWindowMs, 1, Number.MAX_SAFE_INTEGER);
  assertInteger('cooldownMs', options.cooldownMs, 0, Number.MAX_SAFE_INTEGER);
  assertInteger('maxPerHour', options.maxPerHour, 1, 1000);
  assertNumber('minScore', options.minScore, 0, 1);
  assertInteger('rapidWindowMs', options.rapidWindowMs, 1, Number.MAX_SAFE_INTEGER);
  if (typeof options.now !== 'function')
    throw new TypeError('now must be a function');
  if (options.quietHours !== null) {
    if (typeof options.quietHours !== 'object' || Array.isArray(options.quietHours)) {
      throw new TypeError('quietHours must be null or {start,end}');
    }
    assertTime('quietHours.start', options.quietHours.start);
    assertTime('quietHours.end', options.quietHours.end);
  }
  if (!Array.isArray(options.interestKeywords))
    throw new TypeError('interestKeywords must be an array of strings');
  for (const keyword of options.interestKeywords) {
    if (typeof keyword !== 'string')
      throw new TypeError('interestKeywords must be an array of strings');
  }
}

function textOf(value) {
  return typeof value === 'string' ? value.trim() : '';
}

function idOf(value, field) {
  const id = String(value ?? '').trim();
  if (id === '')
    throw new TypeError(`${field} is required`);
  return id;
}

function cloneContext(messages, limit) {
  return messages.slice(-limit).map(message => ({ ...message }));
}

function silent(reason, score, context) {
  return {
    action: 'silent',
    reason,
    score,
    replyToMessageId: null,
    context,
  };
}

function questionScore(text) {
  return QUESTION_RE.test(text) ? 0.15 : 0;
}

function minutesOf(hhmm) {
  const [hours, minutes] = hhmm.split(':').map(Number);
  return hours * 60 + minutes;
}

function inQuietHours(quietHours, at) {
  if (quietHours === null)
    return false;
  const start = minutesOf(quietHours.start);
  const end = minutesOf(quietHours.end);
  if (start === end)
    return false;
  const date = new Date(at);
  const current = date.getHours() * 60 + date.getMinutes();
  return start < end
    ? current >= start && current < end
    : current >= start || current < end;
}

function isRapidExchange(messages, at, windowMs) {
  const humans = messages.filter(message => !message.isSelf).slice(-3);
  if (humans.length < 3)
    return false;
  if (at - humans[0].at > windowMs)
    return false;
  return new Set(humans.map(message => message.userId)).size >= 2;
}

function isReplyToOther(state, last) {
  const target = last.replyToMessageId;
  return target !== null && !state.selfIds.has(target);
}

function recentReplyCount(replyTimes, at) {
  return replyTimes.filter(replyAt => at - replyAt < HOUR_MS).length;
}

function relevanceScore(text, messages, options, now) {
  let score = 0.1; // a recent human message, still below threshold on its own

  const lower = text.toLowerCase();
  const hits = new Set();
  for (const keyword of options.interestKeywords) {
    const key = keyword.trim().toLowerCase();
    if (key !== '' && lower.includes(key))
      hits.add(key);
  }
  score += Math.min(hits.size * 0.35, 0.70);
  score += questionScore(text);

  const recentUsers = new Set();
  for (const message of messages) {
    if (!message.isSelf && now - message.at <= 60 * 1000)
      recentUsers.add(message.userId);
  }
  if (recentUsers.size >= 2)
    score += 0.10;

  if (messages.slice(-3).some(message => message.isSelf))
    score -= 0.20;

  return Math.round(Math.max(0, Math.min(1, score)) * 1000) / 1000;
}

/**
 * Create an in-memory autonomous-reply decision engine.
 *
 * @param {object} overrides partial DEFAULT_OPTIONS
 * @returns {{
 *   observe: (message: object) => boolean,
 *   decide: (groupId: string, now?: number) => object,
 *   recordReply: (groupId: string, now?: number) => void,
 *   reset: (groupId?: string) => void
 * }}
 */
export function createAutoChat(overrides = {}) {
  if (overrides === null || typeof overrides !== 'object' || Array.isArray(overrides))
    throw new TypeError('options must be an object');

  const options = { ...DEFAULT_OPTIONS, ...overrides };
  const rawKeywords = overrides.interestKeywords === undefined
    ? DEFAULT_OPTIONS.interestKeywords
    : overrides.interestKeywords;
  if (!Array.isArray(rawKeywords))
    throw new TypeError('interestKeywords must be an array of strings');
  for (const keyword of rawKeywords) {
    if (typeof keyword !== 'string')
      throw new TypeError('interestKeywords must be an array of strings');
  }
  options.interestKeywords = rawKeywords
    .map(keyword => keyword.trim())
    .filter(keyword => keyword !== '');
  validateOptions(options);

  const groups = new Map();

  function group(groupId) {
    const key = String(groupId);
    let state = groups.get(key);
    if (state === undefined) {
      state = {
        messages: [],
        seenIds: new Set(),
        selfIds: new Set(),
        lastReplyAt: 0,
        replyTimes: [],
      };
      groups.set(key, state);
    }
    return state;
  }

  function observe(message) {
    if (message === null || typeof message !== 'object' || Array.isArray(message))
      throw new TypeError('message must be an object');

    const groupId = idOf(message.groupId, 'groupId');
    const userId = idOf(message.userId, 'userId');
    const messageId = idOf(message.messageId, 'messageId');
    const text = textOf(message.text);
    if (text === '' || text.startsWith('/'))
      return false;

    const state = group(groupId);
    if (state.seenIds.has(messageId))
      return false;

    const at = message.at ?? options.now();
    if (typeof at !== 'number' || !Number.isFinite(at))
      throw new TypeError('message.at must be a finite epoch-ms number');

    const replyTo = message.replyToMessageId == null
      ? ''
      : String(message.replyToMessageId).trim();
    const isSelf = Boolean(message.isSelf);

    state.seenIds.add(messageId);
    if (isSelf)
      state.selfIds.add(messageId);
    state.messages.push({
      groupId,
      userId,
      nickname: textOf(message.nickname) || userId,
      text: text.slice(0, 500),
      messageId,
      at,
      isSelf,
      mentionsSelf: Boolean(message.mentionsSelf),
      replyToMessageId: replyTo === '' ? null : replyTo,
    });

    if (state.messages.length > options.historyLimit)
      state.messages.splice(0, state.messages.length - options.historyLimit);

    // Keep dedup memory bounded. This is intentionally larger than the
    // visible history so delayed OneBot retries still hit the duplicate check.
    const seenLimit = Math.max(200, options.historyLimit * 5);
    while (state.seenIds.size > seenLimit) {
      const oldest = state.seenIds.values().next().value;
      state.seenIds.delete(oldest);
    }
    const selfLimit = Math.max(100, options.historyLimit * 2);
    while (state.selfIds.size > selfLimit) {
      const oldest = state.selfIds.values().next().value;
      state.selfIds.delete(oldest);
    }
    return true;
  }

  function decide(groupId, at = options.now()) {
    if (typeof at !== 'number' || !Number.isFinite(at))
      throw new TypeError('decide now must be a finite epoch-ms number');

    const state = groups.get(String(groupId));
    if (state === undefined || state.messages.length === 0)
      return silent('empty', 0, []);

    const context = cloneContext(state.messages, options.contextLimit);
    const last = state.messages[state.messages.length - 1];

    if (last.isSelf)
      return silent('bot-spoke-last', 0, context);

    if (at - last.at > options.activeWindowMs)
      return silent('cold', 0, context);

    if (inQuietHours(options.quietHours, at))
      return silent('quiet-hours', 0, context);

    if (state.lastReplyAt !== 0 && at - state.lastReplyAt < options.cooldownMs)
      return silent('cooldown', 0, context);

    if (recentReplyCount(state.replyTimes, at) >= options.maxPerHour)
      return silent('hourly-cap', 0, context);

    if (!last.mentionsSelf) {
      if (isReplyToOther(state, last))
        return silent('reply-to-other', 0, context);
      if (isRapidExchange(state.messages, at, options.rapidWindowMs))
        return silent('rapid-exchange', 0, context);
    }

    if (last.mentionsSelf) {
      return {
        action: 'reply',
        reason: 'mentioned',
        score: 1,
        replyToMessageId: last.messageId,
        context,
      };
    }

    const score = relevanceScore(last.text, state.messages, options, at);
    if (score < options.minScore)
      return silent('low-relevance', score, context);

    return {
      action: 'reply',
      reason: 'relevant',
      score,
      replyToMessageId: last.messageId,
      context,
    };
  }

  function recordReply(groupId, at = options.now()) {
    if (typeof at !== 'number' || !Number.isFinite(at))
      throw new TypeError('recordReply now must be a finite epoch-ms number');

    const state = group(groupId);
    state.lastReplyAt = at;
    state.replyTimes.push(at);
    state.replyTimes = state.replyTimes.filter(replyAt => at - replyAt < HOUR_MS);
  }

  function reset(groupId) {
    if (groupId === undefined)
      groups.clear();
    else
      groups.delete(String(groupId));
  }

  return { observe, decide, recordReply, reset };
}

export { buildReplyPrompt } from './prompt.js';
