import test from 'node:test';
import assert from 'node:assert/strict';
import { createAutoChat } from '../src/engine.js';
import { createSidecar } from '../src/server.js';

const NOW = new Date(2026, 9, 20, 12, 0, 0).getTime();

function event(id, text, at = NOW, extra = {}) {
  return {
    post_type: 'message',
    message_type: 'group',
    self_id: 10001,
    group_id: 123,
    user_id: 456,
    message_id: id,
    time: Math.floor(at / 1000),
    sender: { nickname: '小明' },
    message: [{ type: 'text', data: { text } }],
    ...extra,
  };
}

async function start({ engine = {}, sidecar = {} } = {}) {
  const engineInstance = createAutoChat({
    interestKeywords: ['AI', '游戏', '电影'],
    quietHours: null,
    cooldownMs: 0,
    now: () => NOW,
    ...engine,
  });
  const sidecarInstance = createSidecar({
    engine: engineInstance,
    apiBase: 'http://onebot.test',
    host: '127.0.0.1',
    port: 0,
    now: () => NOW,
    logger: () => {},
    ...sidecar,
  });
  const address = await sidecarInstance.start();
  return {
    engine: engineInstance,
    sidecar: sidecarInstance,
    base: `http://127.0.0.1:${address.port}`,
    close: () => sidecarInstance.stop(),
  };
}

async function post(base, body, headers = {}) {
  return fetch(`${base}/onebot/event`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', ...headers },
    body: typeof body === 'string' ? body : JSON.stringify(body),
  });
}

function fakeFetch(calls, { messageId = 'sent-1', ok = true, retcode = 0 } = {}) {
  return async (url, init) => {
    calls.push({ url, init, body: JSON.parse(init.body) });
    return {
      ok,
      status: ok ? 200 : 500,
      json: async () => ({ retcode, data: messageId === null ? {} : { message_id: messageId } }),
    };
  };
}

test('AC-14 HTTP sidecar sends once, dedups, and reports health', async () => {
  const calls = [];
  let generated = null;
  const app = await start({
    engine: { cooldownMs: 180000 },
    sidecar: {
      fetchImpl: fakeFetch(calls),
      replyGenerator: async args => {
        generated = args;
        return 'hi';
      },
    },
  });
  try {
    let response = await post(app.base, event('m1', 'AI 游戏？'));
    assert.equal(response.status, 204);
    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, 'http://onebot.test/send_group_msg');
    assert.equal(calls[0].body.group_id, '123');
    assert.deepEqual(calls[0].body.message[0], { type: 'reply', data: { id: 'm1' } });
    assert.deepEqual(calls[0].body.message[1], { type: 'text', data: { text: 'hi' } });
    assert.match(generated.prompt, /消息 ID m1/);
    assert.match(generated.prompt, /\[\[skip\]\]/);

    response = await post(app.base, event('m1', 'AI 游戏？'));
    assert.equal(response.status, 204);
    assert.equal(calls.length, 1);

    // A fresh human message inside cooldown proves recordReply ran after send.
    response = await post(app.base, event('m2', 'AI 游戏？', NOW + 1000));
    assert.equal(response.status, 204);
    assert.equal(calls.length, 1);

    const health = await fetch(`${app.base}/healthz`);
    assert.equal(health.status, 200);
    assert.deepEqual(await health.json(), { ok: true, dryRun: false, groups: 1 });
  }
  finally {
    await app.close();
  }
});

test('AC-8 sidecar registers its outbound id for reply-to-self', async () => {
  const calls = [];
  const app = await start({
    engine: { rapidWindowMs: 1000, cooldownMs: 0 },
    sidecar: {
      fetchImpl: fakeFetch(calls, { messageId: 'sent-42' }),
      replyGenerator: async () => 'hi',
    },
  });
  try {
    assert.equal((await post(app.base, event('r1', 'AI 游戏？'))).status, 204);
    assert.equal(calls.length, 1);

    const replyEvent = event('r2', 'AI 游戏电影？', NOW + 10000, {
      message: [
        { type: 'reply', data: { id: 'sent-42' } },
        { type: 'text', data: { text: 'AI 游戏电影？' } },
      ],
    });
    assert.equal((await post(app.base, replyEvent)).status, 204);
    assert.equal(calls.length, 2);
  }
  finally {
    await app.close();
  }
});

test('AC-15 webhook token, malformed JSON, and non-group events', async () => {
  const calls = [];
  const app = await start({
    sidecar: {
      webhookToken: 'secret',
      fetchImpl: fakeFetch(calls),
      replyGenerator: async () => 'hi',
    },
  });
  try {
    assert.equal((await post(app.base, event('a1', 'AI 游戏？'))).status, 401);
    assert.equal((await post(app.base, event('a2', 'AI 游戏？'), { authorization: 'Bearer wrong' })).status, 401);
    assert.equal((await post(app.base, event('a3', 'AI 游戏？'), { authorization: 'Bearer secret' })).status, 204);
    assert.equal(calls.length, 1);

    assert.equal((await post(app.base, '{', { authorization: 'Bearer secret' })).status, 400);
    assert.equal((await post(app.base, { ...event('a4', 'AI 游戏？'), message_type: 'private' }, { authorization: 'Bearer secret' })).status, 204);
    assert.equal(calls.length, 1);
  }
  finally {
    await app.close();
  }
});

test('AC-15 send failure does not record cooldown; dry-run does not call generator/fetch', async () => {
  let fail = true;
  const calls = [];
  const failingFetch = async (url, init) => {
    calls.push({ url, init });
    if (fail)
      return { ok: false, status: 500, json: async () => ({ retcode: 100 }) };
    return { ok: true, status: 200, json: async () => ({ retcode: 0, data: { message_id: 'ok-1' } }) };
  };
  const app = await start({
    engine: { cooldownMs: 180000 },
    sidecar: { fetchImpl: failingFetch, replyGenerator: async () => 'hi' },
  });
  try {
    assert.equal((await post(app.base, event('f1', 'AI 游戏？'))).status, 204);
    assert.equal(calls.length, 1);
    fail = false;
    assert.equal((await post(app.base, event('f2', 'AI 游戏？'))).status, 204);
    assert.equal(calls.length, 2);
  }
  finally {
    await app.close();
  }

  let generatorCalls = 0;
  let fetchCalls = 0;
  const dry = await start({
    sidecar: {
      dryRun: true,
      fetchImpl: async () => { fetchCalls += 1; return { ok: true, json: async () => ({ retcode: 0 }) }; },
      replyGenerator: async () => { generatorCalls += 1; return 'hi'; },
    },
  });
  try {
    assert.equal((await post(dry.base, event('d1', 'AI 游戏？'))).status, 204);
    assert.equal(generatorCalls, 0);
    assert.equal(fetchCalls, 0);
    const health = await (await fetch(`${dry.base}/healthz`)).json();
    assert.deepEqual(health, { ok: true, dryRun: true, groups: 1 });
  }
  finally {
    await dry.close();
  }
});

test('AC-17 [[skip]]/empty generator output does not send or record', async () => {
  for (const text of ['[[skip]]', '   ', null]) {
    let fetchCalls = 0;
    let sentPrompt = '';
    const app = await start({
      sidecar: {
        fetchImpl: async () => { fetchCalls += 1; return { ok: true, json: async () => ({ retcode: 0 }) }; },
        replyGenerator: async ({ prompt }) => {
          sentPrompt = prompt;
          return text;
        },
      },
    });
    try {
      assert.equal((await post(app.base, event(`s-${String(text)}`, 'AI 游戏？'))).status, 204);
      assert.equal(fetchCalls, 0);
      assert.match(sentPrompt, /AI 游戏？/);
    }
    finally {
      await app.close();
    }
  }
});
