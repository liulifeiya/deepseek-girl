#!/usr/bin/env node
/**
 * 插件自检：不依赖 QQ 消息，直接调用运行库里的模块并断言行为。
 *
 *   node scripts/selftest.mjs
 *
 * 需要环境变量 DSH_HOME / BOT_HOME（deploy/selftest.ps1 会设置）。
 * 输出每项 PASS/FAIL，退出码 = 失败项数（0 表示全过）。
 */
import fs from 'node:fs';
import path from 'node:path';

const HOME = process.env.BOT_HOME || process.env.USERPROFILE || process.env.HOME || '.';
const DSH_HOME = process.env.DSH_HOME || path.join(HOME, '.dsh-qq');
const LIB = path.join(DSH_HOME, 'profiles', 'qq', 'node_modules', 'dsh-onebot-qq', 'lib');
const API = process.env.BOT_DSH_API || 'http://127.0.0.1:3081';

let failed = 0;
function pass(name, detail) { console.log('PASS  ' + name.padEnd(20) + String(detail ?? '').slice(0, 110)); }
function fail(name, detail) { failed++; console.log('FAIL  ' + name.padEnd(20) + String(detail ?? '').slice(0, 160)); }
function check(name, cond, detail) { cond ? pass(name, detail) : fail(name, detail); }

const imp = async (file) => import('file:///' + path.join(LIB, file).replace(/\\/g, '/'));

// ---- 模块级行为 ----
try {
  const p = path.join(HOME, 'qq-dsh-bot', 'sleep-selftest.json');
  fs.writeFileSync(p, JSON.stringify({ enabled: true, workdays: [0, 1, 2, 3, 4, 5, 6], ranges: [['00:00', '23:59']], holidays: [], workdayOverrides: [] }));
  process.env.SLEEP_WINDOW_CONFIG = p;
  const m = await imp('sleep-window.js');
  const inWindow = m.isSleeping();
  fs.writeFileSync(p, JSON.stringify({ enabled: true, workdays: [0, 1, 2, 3, 4, 5, 6], ranges: [['03:00', '03:01']], holidays: [], workdayOverrides: [] }));
  const outWindow = m.isSleeping();
  fs.unlinkSync(p);
  check('sleep-window', inWindow === true && outWindow === false, `in=${inWindow} out=${outWindow}`);
} catch (e) { fail('sleep-window', e.message); }

try {
  const m = await imp('persona-lock.js');
  const admin = m.buildPersonaLock('2812108776');
  const other = m.buildPersonaLock('10000');
  check('persona-lock', admin.length > 100 && other === '', `admin=${admin.length}字 other=${other === '' ? '空' : other}`);
} catch (e) { fail('persona-lock', e.message); }

try {
  const m = await imp('mention-context.js');
  m.recordGroupMessage({ kind: 'group', chatId: 'selftest', userId: '1', nickname: 'n', text: '前文一句', media: [] });
  const ctx = m.buildMentionContext('selftest', '1', 'n');
  check('mention-context', ctx.includes('前文一句'), ctx.includes('前文一句') ? '上下文含前文' : ctx);
} catch (e) { fail('mention-context', e.message); }

try {
  const m = await imp('image-hash.js');
  const src = path.join(HOME, 'tts-out', 'meme.png');
  const tmp = path.join(HOME, 'qq-dsh-bot', 'image-lib', '_prep', 'selftest-' + Date.now() + '.png');
  // 追加随机字节，保证每次内容不同（PNG 尾部多余字节不影响解析）
  fs.copyFileSync(src, tmp);
  fs.appendFileSync(tmp, Buffer.from(String(Math.random())));
  const a = m.ingestImage(tmp);
  const b = m.ingestImage(tmp);
  // 清理：临时文件、入库副本、索引行
  fs.unlinkSync(tmp);
  if (a?.file && fs.existsSync(a.file)) fs.unlinkSync(a.file);
  const indexPath = path.join(HOME, 'qq-dsh-bot', 'image-lib', 'index.jsonl');
  if (a?.short && fs.existsSync(indexPath)) {
    const keep = fs.readFileSync(indexPath, 'utf8').split('\n').filter((l) => l.trim() && !l.includes(a.short));
    fs.writeFileSync(indexPath, keep.join('\n') + (keep.length ? '\n' : ''));
  }
  check('image-hash', a?.dup === false && b?.dup === true, a && b ? a.short + ' 新→DUP' : 'undefined');
} catch (e) { fail('image-hash', e.message); }

try {
  const cfgPath = path.join(HOME, 'qq-dsh-bot', 'group-wake-selftest.json');
  // 必须在 import 之前设置：模块在加载时就算好了 CONFIG_PATH
  process.env.GROUP_WAKE_CONFIG = cfgPath;
  const m = await imp('group-wake.js');

  async function wakeCase(cfg, notes, hour) {
    fs.writeFileSync(cfgPath, JSON.stringify(cfg));
    const gw = new m.GroupWake();
    let dispatched = 0;
    const ctx = { log: () => { }, getChat: () => undefined, dispatchFollowup: async () => { dispatched++; } };
    for (const n of notes) {
      gw.note(ctx, { kind: 'group', chatId: 'selftest', userId: '1', nickname: 'n', text: n, media: [] });
    }
    // 抽签是随机的：固定成 0 让“该醒”的用例确定命中
    const origRandom = Math.random;
    Math.random = () => 0;
    try {
      gw.tick(new Date(2026, 9, 24, hour, 0, 0).getTime());
      await new Promise((r) => setTimeout(r, 40));
    } finally {
      Math.random = origRandom;
    }
    return dispatched;
  }

  const base = {
    enabled: true, idleMs: 0, cooldownMs: 0, minMessages: 1,
    fallbackProb: 1, maxTurnsPerHour: 10, quietStart: '00:00', quietEnd: '00:00', keywords: [],
  };
  const hit = await wakeCase(base, ['在吗'], 12);
  const few = await wakeCase({ ...base, minMessages: 3 }, ['在吗'], 12);
  const quiet = await wakeCase({ ...base, quietStart: '00:00', quietEnd: '23:59' }, ['在吗'], 12);
  const off = await wakeCase({ ...base, enabled: false }, ['在吗'], 12);
  fs.unlinkSync(cfgPath);
  check('group-wake', hit === 1 && few === 0 && quiet === 0 && off === 0,
    `命中=${hit} 不足阈值=${few} 静默时段=${quiet} 已关闭=${off}`);
} catch (e) { fail('group-wake', e.message); }

// ---- HTTP 接口 ----
async function getJson(url) {
  const r = await fetch(url, { signal: AbortSignal.timeout(5000) });
  return { status: r.status, body: await r.json() };
}

try {
  const { status, body } = await getJson(API + '/api/dsh-persona-dafeiyu/status');
  const v = body.value || {};
  check('persona-api', status === 200 && Array.isArray(v.personas) && v.personas.length >= 3,
    `cards=${v.personas?.length} sessions=${v.sessionCount}`);
} catch (e) { fail('persona-api', e.message); }

try {
  const { status, body } = await getJson(API + '/api/dsh-proactive/state');
  check('proactive-api', status === 200 && body.config?.enabled === true,
    `enabled=${body.config?.enabled} quiet=${body.config?.quietHours?.start}-${body.config?.quietHours?.end}`);
} catch (e) { fail('proactive-api', e.message); }

// ---- OneBot ----
try {
  const token = fs.readFileSync(path.join(HOME, 'qq-dsh-bot', 'onebot-token.txt'), 'utf8').trim();
  const res = await new Promise((resolve) => {
    const ws = new WebSocket('ws://127.0.0.1:3001', { headers: { Authorization: `Bearer ${token}` } });
    const t = setTimeout(() => { try { ws.close(); } catch { } resolve(undefined); }, 6000);
    ws.onopen = () => ws.send(JSON.stringify({ action: 'get_status', params: {}, echo: 'st' }));
    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(String(e.data));
        if (d.echo !== 'st') return;
        clearTimeout(t); ws.close();
        resolve(d.data);
      } catch { }
    };
    ws.onerror = () => { clearTimeout(t); resolve(undefined); };
  });
  check('onebot-status', res?.online === true, res ? `online=${res.online} good=${res.good}` : 'no response');
} catch (e) { fail('onebot-status', e.message); }

console.log('\n' + (failed === 0 ? '全部通过' : `失败 ${failed} 项`));
process.exit(failed);
