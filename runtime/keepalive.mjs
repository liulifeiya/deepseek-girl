// 保活钩子：每 5 分钟给 OneBot 发一次在线状态，防止长时间无动作。
// 默认不发聊天消息（发给自己可能被推到「我的设备」，每 5 分钟一条会烦）。
// 真要改成发消息：KEEPALIVE_MODE=message 启动即可。
import fs from 'node:fs';

const HOME = process.env.BOT_HOME || '/home/ubuntu';
const TOKEN = fs.readFileSync(`${HOME}/qq-dsh-bot/onebot-token.txt`, 'utf8').trim();
const SELF = process.env.BOT_QQ || '2836148023';
const LOG = `${HOME}/qq-dsh-bot/keepalive.log`;
const INTERVAL = 5 * 60_000;
const MODE = process.env.KEEPALIVE_MODE === 'message' ? 'message' : 'status';
let last = '';

function ts() {
    return new Date(Date.now() + 8 * 3600e3).toISOString().replace('T', ' ').slice(0, 19) + ' +08';
}
function log(line) {
    try { fs.appendFileSync(LOG, `${ts()} ${line}\n`); } catch {}
}

function ping() {
    return new Promise((resolve) => {
        let done = false;
        let ws;
        const pending = new Set(MODE === 'message' ? ['s', 'm'] : ['s']);
        const finish = (v) => {
            if (done) return;
            done = true;
            clearTimeout(timer);
            try { ws.close(); } catch {}
            resolve(v);
        };
        const timer = setTimeout(() => finish({ ok: false, why: 'timeout' }), 10_000);
        try {
            ws = new WebSocket('ws://127.0.0.1:3001', { headers: { Authorization: `Bearer ${TOKEN}` } });
        } catch {
            return resolve({ ok: false, why: 'construct' });
        }
        ws.onopen = () => {
            try {
                ws.send(JSON.stringify({ action: 'set_online_status', params: { status: 10, ext_status: 0, battery_status: 100 }, echo: 's' }));
                if (MODE === 'message') {
                    ws.send(JSON.stringify({ action: 'send_private_msg', params: { user_id: Number(SELF), message: '.' }, echo: 'm' }));
                }
            } catch {}
        };
        ws.onmessage = (e) => {
            let d;
            try { d = JSON.parse(String(e.data)); } catch { return; }
            if (!pending.has(d.echo)) return;
            pending.delete(d.echo);
            if (d.retcode !== 0 && d.retcode !== undefined) {
                return finish({ ok: false, why: 'api', echo: d.echo, retcode: d.retcode });
            }
            if (pending.size === 0) finish({ ok: true });
        };
        ws.onerror = () => finish({ ok: false, why: 'ws-error' });
        ws.onclose = () => finish({ ok: false, why: 'closed' });
    });
}

async function loop() {
    const r = await ping();
    const state = r.ok ? 'ok' : 'fail';
    if (state !== last) {
        log(`STATE ${last || 'start'} -> ${state} ${JSON.stringify(r)}`);
        last = state;
    }
    setTimeout(loop, INTERVAL);
}

log(`keepalive start mode=${MODE}`);
loop();
