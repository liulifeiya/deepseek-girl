// Quick OneBot 11 probe: prints get_login_info / get_status.
import fs from 'node:fs';

const TOKEN = fs.readFileSync('C:/Users/Administrator/qq-dsh-bot/onebot-token.txt', 'utf8').trim();
const WS = 'ws://127.0.0.1:3001';

function call(action, params = {}, timeout = 8000) {
  return new Promise((resolve) => {
    const ws = new WebSocket(WS, { headers: { Authorization: `Bearer ${TOKEN}` } });
    const timer = setTimeout(() => { try { ws.close(); } catch {} resolve({ ok: false, why: 'timeout' }); }, timeout);
    ws.onopen = () => ws.send(JSON.stringify({ action, params, echo: 'p' }));
    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(String(e.data));
        if (d.echo !== 'p') return;
        clearTimeout(timer);
        ws.close();
        resolve({ ok: d.retcode === 0, retcode: d.retcode, data: d.data });
      } catch {}
    };
    ws.onerror = () => { clearTimeout(timer); resolve({ ok: false, why: 'ws-error' }); };
    ws.onclose = () => { clearTimeout(timer); resolve({ ok: false, why: 'closed' }); };
  });
}

console.log('login_info:', JSON.stringify(await call('get_login_info')));
console.log('status    :', JSON.stringify(await call('get_status')));
console.log('version   :', JSON.stringify(await call('get_version_info')));
