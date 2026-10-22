// QQ 在线状态看门狗：每分钟探一次 OneBot，掉线/恢复都记时间。
// 只写 ~/qq-dsh-bot/watchdog.log，不动别的。
import fs from 'node:fs';

const TOKEN = fs.readFileSync('/home/ubuntu/qq-dsh-bot/onebot-token.txt', 'utf8').trim();
const LOG = '/home/ubuntu/qq-dsh-bot/watchdog.log';
const INTERVAL = 60_000;
let last = null;

function ts() {
  return new Date(Date.now() + 8 * 3600e3).toISOString().replace('T', ' ').slice(0, 19) + ' +08';
}
function log(line) {
  fs.appendFileSync(LOG, `${ts()} ${line}\n`);
}

function probe() {
  return new Promise((resolve) => {
    let done = false;
    const finish = (v) => { if (!done) { done = true; try { ws.close(); } catch {} resolve(v); } };
    let ws;
    try {
      ws = new WebSocket('ws://127.0.0.1:3001', { headers: { Authorization: `Bearer ${TOKEN}` } });
    } catch {
      return resolve({ ok: false, why: 'construct' });
    }
    const timer = setTimeout(() => finish({ ok: false, why: 'timeout' }), 10_000);
    ws.onopen = () => ws.send(JSON.stringify({ action: 'get_status', params: {}, echo: 'w' }));
    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(String(e.data));
        if (d.echo !== 'w') return;
        clearTimeout(timer);
        finish({ ok: true, online: d.data?.online === true, good: d.data?.good === true });
      } catch {}
    };
    ws.onerror = () => { clearTimeout(timer); finish({ ok: false, why: 'ws-error' }); };
    ws.onclose = () => { clearTimeout(timer); finish({ ok: false, why: 'closed' }); };
  });
}

async function tick() {
  const r = await probe();
  const state = r.ok ? (r.online ? 'online' : 'offline') : 'dead';
  if (state !== last) {
    log(`STATE ${last ?? 'start'} -> ${state} ${JSON.stringify(r)}`);
    last = state;
  } else if (state !== 'online') {
    log(`still ${state} ${JSON.stringify(r)}`);
  }
}

log('watchdog start');
await tick();
setInterval(tick, INTERVAL);
