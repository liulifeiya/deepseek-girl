/**
 * HTTP sidecar for group-autochat.
 *
 * Endpoints:
 *   POST /onebot/event  receive OneBot 11 group events
 *   GET  /healthz       health JSON
 *
 * The sidecar normalizes an event, feeds the decision engine, optionally calls
 * an injected reply generator, sends via OneBot's HTTP API, and records the
 * reply only after the send succeeds. No plugin files are read or modified.
 */

import http from 'node:http';
import { normalizeOneBot11, toSendGroupMsg } from './onebot.js';
import { buildReplyPrompt } from './prompt.js';

const MAX_BODY_BYTES = 1_000_000;

function defaultLogger(level, event, fields = {}) {
  const record = {
    ts: new Date().toISOString(),
    level,
    event,
    ...fields,
  };
  const line = JSON.stringify(record);
  if (level === 'error')
    console.error(line);
  else
    console.log(line);
}

function sendJson(res, status, body) {
  if (res.headersSent)
    return;
  const text = JSON.stringify(body);
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': Buffer.byteLength(text),
  });
  res.end(text);
}

function sendEmpty(res, status) {
  if (res.headersSent)
    return;
  res.writeHead(status);
  res.end();
}

async function readBody(req) {
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    size += buffer.length;
    if (size > MAX_BODY_BYTES) {
      const error = new Error('request body too large');
      error.statusCode = 413;
      throw error;
    }
    chunks.push(buffer);
  }
  return Buffer.concat(chunks).toString('utf8');
}

/**
 * Create an HTTP sidecar instance (does not listen until start()).
 *
 * @param {object} options
 * @param {object} options.engine createAutoChat() instance (required)
 * @param {string} [options.apiBase] OneBot HTTP API base, e.g. http://127.0.0.1:3000
 * @param {string} [options.accessToken] OneBot API access token
 * @param {string} [options.webhookToken] expected inbound webhook token
 * @param {Function|null} [options.replyGenerator] async ({decision,prompt,groupId,context}) => string|null
 * @param {boolean} [options.dryRun]
 * @param {string} [options.host]
 * @param {number} [options.port]
 * @param {string} [options.selfId]
 * @param {Function} [options.logger] (level,event,fields)=>void
 * @param {Function} [options.fetchImpl]
 * @param {Function} [options.now]
 * @returns {{server: import('node:http').Server, start: Function, stop: Function, handleEvent: Function}}
 */
export function createSidecar(options = {}) {
  const {
    engine,
    apiBase = '',
    accessToken = '',
    webhookToken = '',
    replyGenerator = null,
    dryRun = false,
    host = '127.0.0.1',
    port = 8787,
    selfId = '',
    logger = defaultLogger,
    fetchImpl = globalThis.fetch,
    now = Date.now,
  } = options;

  if (engine === null || typeof engine !== 'object'
      || typeof engine.observe !== 'function'
      || typeof engine.decide !== 'function'
      || typeof engine.recordReply !== 'function') {
    throw new TypeError('engine must be a createAutoChat() instance');
  }
  if (replyGenerator !== null && typeof replyGenerator !== 'function')
    throw new TypeError('replyGenerator must be a function or null');
  if (typeof now !== 'function')
    throw new TypeError('now must be a function');
  if (fetchImpl !== undefined && typeof fetchImpl !== 'function')
    throw new TypeError('fetchImpl must be a function');

  const log = typeof logger === 'function' ? logger : defaultLogger;
  const groups = new Set();
  let outboundSeq = 0;
  const apiBaseUrl = String(apiBase ?? '').replace(/\/+$/, '');
  const incomingToken = String(webhookToken ?? '');
  const effectiveDryRun = Boolean(dryRun) || replyGenerator === null;

  if ((host === '0.0.0.0' || host === '::') && incomingToken === '')
    log('warn', 'insecure-bind', { host, reason: 'no AUTOCHAT_WEBHOOK_TOKEN' });

  function authorized(req) {
    if (incomingToken === '')
      return true;
    const auth = req.headers.authorization;
    const custom = req.headers['x-autochat-token'];
    return auth === `Bearer ${incomingToken}` || custom === incomingToken;
  }

  async function sendGroupMessage(groupId, text, replyToMessageId) {
    if (apiBaseUrl === '') {
      log('error', 'send-failed', { groupId, reason: 'ONEBOT_API_BASE is empty' });
      return { ok: false };
    }
    if (typeof fetchImpl !== 'function') {
      log('error', 'send-failed', { groupId, reason: 'fetch is unavailable' });
      return { ok: false };
    }

    const payload = toSendGroupMsg(groupId, text, replyToMessageId);
    const headers = { 'content-type': 'application/json' };
    if (accessToken)
      headers.authorization = `Bearer ${accessToken}`;

    try {
      const response = await fetchImpl(`${apiBaseUrl}/send_group_msg`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload.params),
      });
      if (!response || response.ok === false) {
        log('warn', 'send-failed', {
          groupId,
          reason: `HTTP ${response?.status ?? 'no response'}`,
        });
        return { ok: false };
      }

      let data = null;
      if (typeof response.json === 'function') {
        try {
          data = await response.json();
        }
        catch {
          log('warn', 'send-failed', { groupId, reason: 'OneBot response is not JSON' });
          return { ok: false };
        }
      }
      if (data !== null && data !== undefined && data.retcode !== undefined
          && Number(data.retcode) !== 0) {
        log('warn', 'send-failed', { groupId, reason: `retcode ${data.retcode}` });
        return { ok: false };
      }

      const messageId = data?.data?.message_id ?? data?.message_id;
      return {
        ok: true,
        messageId: messageId === undefined || messageId === null
          ? null
          : String(messageId),
      };
    }
    catch (error) {
      log('warn', 'send-failed', { groupId, reason: String(error) });
      return { ok: false };
    }
  }

  async function handleEvent(event) {
    const started = Date.now();
    try {
      const message = normalizeOneBot11(event, {
        selfId: selfId === '' ? undefined : selfId,
        now,
      });
      if (message === null) {
        log('debug', 'event-ignored', { reason: 'not a group message' });
        return { status: 204, action: 'ignore' };
      }

      groups.add(message.groupId);
      if (!engine.observe(message)) {
        log('debug', 'event-ignored', { groupId: message.groupId, reason: 'duplicate or empty' });
        return { status: 204, action: 'ignore' };
      }

      const decision = engine.decide(message.groupId);
      const fields = {
        groupId: message.groupId,
        action: decision.action,
        reason: decision.reason,
        score: decision.score,
      };

      if (decision.action !== 'reply') {
        log('debug', 'decision', fields);
        return { status: 204, action: 'silent', decision };
      }

      if (effectiveDryRun) {
        log('info', 'would-reply', fields);
        return { status: 204, action: 'dry-run', decision };
      }

      let text;
      try {
        const prompt = buildReplyPrompt(decision);
        text = await replyGenerator({
          decision,
          prompt,
          groupId: message.groupId,
          context: decision.context,
        });
      }
      catch (error) {
        log('warn', 'generator-failed', { ...fields, error: String(error) });
        return { status: 204, action: 'generator-failed', decision };
      }

      if (typeof text !== 'string' || text.trim() === '' || text.trim() === '[[skip]]') {
        log('debug', 'generator-skip', fields);
        return { status: 204, action: 'skip', decision };
      }

      const sent = await sendGroupMessage(
        message.groupId,
        text.trim(),
        decision.replyToMessageId,
      );
      if (!sent.ok) {
        log('warn', 'reply-not-recorded', { groupId: message.groupId });
        return { status: 204, action: 'send-failed', decision };
      }

      engine.recordReply(message.groupId);
      // Register our own outbound message so a later human reply to it is not
      // mistaken for "replying to another human" by the reply-to-other gate.
      const botId = String(selfId || event.self_id || 'bot');
      const outboundId = sent.messageId || `local-out-${++outboundSeq}`;
      try {
        engine.observe({
          groupId: message.groupId,
          userId: botId,
          nickname: botId,
          text: text.trim(),
          messageId: outboundId,
          at: now(),
          isSelf: true,
        });
      }
      catch (error) {
        log('warn', 'self-observe-failed', { groupId: message.groupId, error: String(error) });
      }

      log('info', 'replied', {
        ...fields,
        durationMs: Date.now() - started,
      });
      return { status: 204, action: 'reply', decision };
    }
    catch (error) {
      // A malformed event or engine error must never take the sidecar down.
      log('error', 'event-error', { error: String(error) });
      return { status: 204, action: 'error' };
    }
  }

  async function handleRequest(req, res) {
    try {
      const url = new URL(req.url ?? '/', 'http://localhost');

      if (url.pathname === '/healthz') {
        if (req.method !== 'GET') {
          sendJson(res, 405, { ok: false, error: 'method not allowed' });
          return;
        }
        sendJson(res, 200, { ok: true, dryRun: effectiveDryRun, groups: groups.size });
        return;
      }

      if (url.pathname === '/onebot/event') {
        if (req.method !== 'POST') {
          sendJson(res, 405, { ok: false, error: 'method not allowed' });
          return;
        }
        if (!authorized(req)) {
          sendJson(res, 401, { ok: false, error: 'unauthorized' });
          return;
        }

        let body;
        try {
          body = await readBody(req);
        }
        catch (error) {
          const status = error.statusCode ?? 400;
          sendJson(res, status, { ok: false, error: error.message });
          return;
        }

        let event;
        try {
          event = JSON.parse(body);
        }
        catch {
          sendJson(res, 400, { ok: false, error: 'invalid JSON' });
          return;
        }
        if (event === null || typeof event !== 'object' || Array.isArray(event)) {
          sendJson(res, 400, { ok: false, error: 'event must be a JSON object' });
          return;
        }

        await handleEvent(event);
        sendEmpty(res, 204);
        return;
      }

      sendJson(res, 404, { ok: false, error: 'not found' });
    }
    catch (error) {
      log('error', 'http-error', { error: String(error) });
      if (!res.headersSent)
        sendJson(res, 400, { ok: false, error: 'bad request' });
      else
        res.end();
    }
  }

  const server = http.createServer((req, res) => {
    void handleRequest(req, res);
  });

  function start() {
    if (server.listening)
      return Promise.resolve(server.address());
    return new Promise((resolve, reject) => {
      const onError = error => {
        server.off('listening', onListening);
        reject(error);
      };
      const onListening = () => {
        server.off('error', onError);
        resolve(server.address());
      };
      server.once('error', onError);
      server.once('listening', onListening);
      server.listen(port, host);
    });
  }

  function stop() {
    return new Promise(resolve => {
      if (!server.listening) {
        resolve();
        return;
      }
      server.close(() => resolve());
      if (typeof server.closeAllConnections === 'function')
        server.closeAllConnections();
    });
  }

  return { server, start, stop, handleEvent };
}
