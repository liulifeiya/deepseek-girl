import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createAutoChat, buildReplyPrompt } from '../src/engine.js';

const ROOT = fileURLToPath(new URL('..', import.meta.url));
const NOON = new Date(2026, 9, 20, 12, 0, 0).getTime();
const QUIET = new Date(2026, 9, 20, 23, 45, 0).getTime();
const EARLY = new Date(2026, 9, 21, 7, 0, 0).getTime();
const MORNING = new Date(2026, 9, 21, 8, 0, 0).getTime();

function message(id, userId, text, at, extra = {}) {
  return {
    groupId: 'g',
    userId,
    nickname: userId,
    text,
    messageId: id,
    at,
    ...extra,
  };
}

function makeEngine(initialNow, overrides = {}) {
  let now = initialNow;
  const engine = createAutoChat({
    quietHours: null,
    cooldownMs: 0,
    ...overrides,
    now: () => now,
  });
  return {
    engine,
    setNow(value) { now = value; },
    now() { return now; },
  };
}

test('AC-1 empty group and cold window are silent', () => {
  const ctx = makeEngine(NOON, { interestKeywords: ['AI'] });
  assert.equal(ctx.engine.decide('g').reason, 'empty');

  ctx.engine.observe(message('m1', 'u1', 'AI 游戏？', NOON - 6 * 60 * 1000));
  const decision = ctx.engine.decide('g', NOON);
  assert.equal(decision.action, 'silent');
  assert.equal(decision.reason, 'cold');
});

test('AC-2 unrelated active chatter is low relevance', () => {
  const ctx = makeEngine(NOON, { interestKeywords: ['AI'] });
  ctx.engine.observe(message('m1', 'u1', '今天天气不错', NOON));
  const decision = ctx.engine.decide('g', NOON);
  assert.equal(decision.action, 'silent');
  assert.equal(decision.reason, 'low-relevance');
  assert.ok(decision.score < 0.55);
});

test('AC-3 relevant active topic replies with target and context', () => {
  const ctx = makeEngine(NOON, { interestKeywords: ['AI'] });
  ctx.engine.observe(message('m1', 'u1', 'AI 游戏？', NOON));
  const decision = ctx.engine.decide('g', NOON);
  assert.equal(decision.action, 'reply');
  assert.equal(decision.reason, 'relevant');
  assert.ok(decision.score >= 0.55);
  assert.equal(decision.replyToMessageId, 'm1');
  assert.equal(decision.context.length, 1);
  assert.equal(decision.context[0].messageId, 'm1');
});

test('AC-4 cooldown, bot-spoke-last, and recovery', () => {
  const ctx = makeEngine(NOON, { interestKeywords: ['AI'], cooldownMs: 180000 });
  ctx.engine.observe(message('m1', 'u1', 'AI 游戏？', NOON));
  assert.equal(ctx.engine.decide('g', NOON).action, 'reply');
  ctx.engine.recordReply('g', NOON);

  ctx.engine.observe(message('m2', 'u1', 'AI 游戏？', NOON + 1000));
  assert.equal(ctx.engine.decide('g', NOON + 1000).reason, 'cooldown');

  ctx.engine.observe(message('m3', 'u1', 'AI 游戏？', NOON + 181000));
  assert.equal(ctx.engine.decide('g', NOON + 181000).action, 'reply');

  ctx.engine.observe(message('m4', 'u1', 'AI 游戏？', NOON + 182000));
  ctx.engine.observe(message('m5', 'bot', '我先说', NOON + 183000, { isSelf: true }));
  assert.equal(ctx.engine.decide('g', NOON + 183000).reason, 'bot-spoke-last');
});

test('AC-5 hourly cap blocks and recovers after one hour', () => {
  const ctx = makeEngine(NOON, { interestKeywords: ['AI'], maxPerHour: 2, cooldownMs: 0 });
  for (let i = 0; i < 2; i += 1) {
    const at = NOON + i * 1000;
    ctx.engine.observe(message(`h${i}`, 'u1', 'AI 游戏？', at));
    assert.equal(ctx.engine.decide('g', at).action, 'reply');
    ctx.engine.recordReply('g', at);
  }

  const blockedAt = NOON + 2000;
  ctx.engine.observe(message('h2', 'u1', 'AI 游戏？', blockedAt));
  assert.equal(ctx.engine.decide('g', blockedAt).reason, 'hourly-cap');

  const later = NOON + 3600001;
  ctx.engine.observe(message('h3', 'u1', 'AI 游戏？', later));
  assert.equal(ctx.engine.decide('g', later).action, 'reply');
});

test('AC-6 mention replies without keywords but respects quiet/cooldown', () => {
  const normal = makeEngine(NOON);
  normal.engine.observe(message('m1', 'u1', '在吗', NOON, { mentionsSelf: true }));
  assert.equal(normal.engine.decide('g', NOON).reason, 'mentioned');

  const quiet = makeEngine(QUIET, {
    quietHours: { start: '23:30', end: '08:00' },
  });
  quiet.engine.observe(message('m2', 'u1', '在吗', QUIET, { mentionsSelf: true }));
  assert.equal(quiet.engine.decide('g', QUIET).reason, 'quiet-hours');

  const cooling = makeEngine(NOON, { cooldownMs: 180000 });
  cooling.engine.observe(message('m3', 'u1', 'AI', NOON));
  cooling.engine.recordReply('g', NOON);
  cooling.engine.observe(message('m4', 'u1', '在吗', NOON + 1000, { mentionsSelf: true }));
  assert.equal(cooling.engine.decide('g', NOON + 1000).reason, 'cooldown');
});

test('AC-7 rapid two-user exchange is silent unless mentioned', () => {
  const ctx = makeEngine(NOON, { interestKeywords: ['AI'], rapidWindowMs: 20000 });
  ctx.engine.observe(message('x1', 'u1', 'AI 游戏', NOON));
  ctx.engine.observe(message('x2', 'u2', 'AI 游戏？', NOON + 5000));
  ctx.engine.observe(message('x3', 'u1', 'AI 游戏？', NOON + 10000));
  assert.equal(ctx.engine.decide('g', NOON + 10000).reason, 'rapid-exchange');

  ctx.engine.observe(message('x4', 'u2', '在吗', NOON + 15000, { mentionsSelf: true }));
  assert.equal(ctx.engine.decide('g', NOON + 15000).reason, 'mentioned');
});

test('AC-8 reply-to-other is silent, reply-to-bot is scored', () => {
  const ctx = makeEngine(NOON, {
    interestKeywords: ['AI', '游戏', '电影'],
    rapidWindowMs: 1000,
  });
  ctx.engine.observe(message('r1', 'u1', 'AI 游戏', NOON));
  ctx.engine.observe(message('bot1', 'bot', '我先说', NOON + 1000, { isSelf: true }));
  ctx.engine.observe(message('r2', 'u2', 'AI 游戏？', NOON + 10000, {
    replyToMessageId: 'r1',
  }));
  assert.equal(ctx.engine.decide('g', NOON + 10000).reason, 'reply-to-other');

  ctx.engine.observe(message('r3', 'u2', 'AI 游戏电影？', NOON + 20000, {
    replyToMessageId: 'bot1',
  }));
  assert.equal(ctx.engine.decide('g', NOON + 20000).action, 'reply');
});

test('AC-9 quiet hours cover evening, cross-midnight, and end boundary', () => {
  const quietHours = { start: '23:30', end: '08:00' };
  const evening = makeEngine(QUIET, { interestKeywords: ['AI'], quietHours });
  evening.engine.observe(message('q1', 'u1', 'AI 游戏？', QUIET));
  assert.equal(evening.engine.decide('g', QUIET).reason, 'quiet-hours');

  const early = makeEngine(EARLY, { interestKeywords: ['AI'], quietHours });
  early.engine.observe(message('q2', 'u1', 'AI 游戏？', EARLY));
  assert.equal(early.engine.decide('g', EARLY).reason, 'quiet-hours');

  const morning = makeEngine(MORNING, { interestKeywords: ['AI'], quietHours });
  morning.engine.observe(message('q3', 'u1', 'AI 游戏？', MORNING));
  assert.equal(morning.engine.decide('g', MORNING).action, 'reply');
});

test('AC-10 history limit, context limit, and duplicate ids', () => {
  const history = makeEngine(NOON, { historyLimit: 5, contextLimit: 50, interestKeywords: ['AI'] });
  for (let i = 0; i < 8; i += 1) {
    assert.equal(history.engine.observe(message(`h${i}`, 'u1', 'AI 游戏？', NOON + i * 1000)), true);
  }
  const kept = history.engine.decide('g', NOON + 7000).context;
  assert.equal(kept.length, 5);
  assert.equal(kept[0].messageId, 'h3');
  assert.equal(kept.at(-1).messageId, 'h7');
  assert.equal(history.engine.observe(message('h7', 'u1', '重复', NOON + 7000)), false);

  const context = makeEngine(NOON, { historyLimit: 40, contextLimit: 3, interestKeywords: ['AI'] });
  for (let i = 0; i < 8; i += 1)
    context.engine.observe(message(`m${i}`, 'u1', 'AI 游戏？', NOON + i * 1000));
  const decision = context.engine.decide('g', NOON + 7000);
  assert.equal(decision.context.length, 3);
  assert.equal(decision.context.at(-1).messageId, 'm7');
});

test('AC-11 invalid config throws and reset clears state', () => {
  assert.throws(() => createAutoChat({ maxPerHour: 0 }), RangeError);
  assert.throws(() => createAutoChat({ cooldownMs: -1 }), RangeError);
  assert.throws(() => createAutoChat({ quietHours: { start: '25:00', end: '08:00' } }), TypeError);

  const ctx = makeEngine(NOON, { interestKeywords: ['AI'] });
  ctx.engine.observe(message('m1', 'u1', 'AI 游戏？', NOON));
  ctx.engine.reset();
  assert.equal(ctx.engine.decide('g').reason, 'empty');
});

test('AC-16 zero runtime dependencies and only node/local imports', () => {
  const pkg = JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf8'));
  assert.deepEqual(pkg.dependencies, {});

  const files = readdirSync(join(ROOT, 'src')).filter(name => name.endsWith('.js'));
  const importRe = /(?:from\s+|import\s*\()(['"])([^'"]+)\1/g;
  for (const file of files) {
    const source = readFileSync(join(ROOT, 'src', file), 'utf8');
    for (const match of source.matchAll(importRe)) {
      const specifier = match[2];
      assert.ok(
        specifier.startsWith('node:') || specifier.startsWith('./') || specifier.startsWith('../'),
        `${file} imports non-local module ${specifier}`,
      );
    }
  }
});

test('AC-17 buildReplyPrompt contains context, target, and skip contract', () => {
  const ctx = makeEngine(NOON, { interestKeywords: ['AI'] });
  ctx.engine.observe(message('p1', 'u1', 'AI 游戏？', NOON));
  const decision = ctx.engine.decide('g', NOON);
  const prompt = buildReplyPrompt(decision);

  assert.match(prompt, /\[\d{2}:\d{2} u1\] AI 游戏？/);
  assert.match(prompt, /消息 ID p1/);
  assert.match(prompt, /1–2 句/);
  assert.match(prompt, /\[\[skip\]\]/);
});
