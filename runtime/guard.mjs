// QQ 保活守卫
// 1) 每 30s 探一次在线状态，每 4min 发一次在线心跳
// 2) 连续 3 次探不到 -> 自动 systemctl --user restart napcat.service
// 3) 重启后仍不恢复 -> 按 5/10/20 分钟退避重试；30 分钟内满 3 次就停手
//    （这种情况通常要人工扫码，守卫不生成/不搬二维码，只等）
// 4) 恢复后给管理员发一条消息（23:00-08:00 静默，只记日志）
// 只重启 napcat.service，不改任何配置；日志写 guard.log
import fs from 'node:fs';
import net from 'node:net';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileP = promisify(execFile);

const HOME = process.env.BOT_HOME || process.env.USERPROFILE || process.env.HOME || process.cwd();
const BOT = `${HOME}/qq-dsh-bot`;
const TOKEN = fs.readFileSync(`${BOT}/onebot-token.txt`, 'utf8').trim();
const WS_URL = 'ws://127.0.0.1:3001';
const LOG = `${BOT}/guard.log`;
const STATE_FILE = `${BOT}/guard-state.json`;
const PID_FILE = `${BOT}/guard.pid`;
const QR_SRC = process.env.NAPCAT_QR_PNG || `${HOME}/Napcat/opt/QQ/resources/app/app_launcher/napcat/cache/qrcode.png`;
const ADMIN = Number(process.env.ADMIN_QQ || 2812108776);

const TICK = 30_000;              // 探活间隔
const FAIL_TO_RESTART = 3;        // 连续失败几次才重启
const HEARTBEAT = 4 * 60_000;     // 在线心跳间隔
const RECOVER_WAIT = 80_000;      // 重启后等它起来的观察期
const MAX_RESTARTS = 3;           // 窗口内最多重启次数
const WINDOW = 30 * 60_000;       // 重启计数窗口
const BACKOFF = [5 * 60_000, 10 * 60_000, 20 * 60_000]; // 第 1/2/3 次重启的冷却
const DRY = process.env.GUARD_DRY === '1';

// ---- 单实例锁 ----
try {
  const old = Number(fs.readFileSync(PID_FILE, 'utf8').trim());
  if (old && old !== process.pid) {
    try { process.kill(old, 0); console.error(`guard already running pid=${old}`); process.exit(0); } catch {}
  }
} catch {}
fs.writeFileSync(PID_FILE, String(process.pid));

// ---- 工具 ----
const ts = () => new Date(Date.now() + 8 * 3600e3).toISOString().replace('T', ' ').slice(0, 19) + ' +08';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function log(line) {
  try {
    // 超过 2MB 简单轮转一次
    const st = fs.statSync(LOG, { throwIfNoEntry: false });
    if (st && st.size > 2 * 1024 * 1024) fs.renameSync(LOG, LOG + '.1');
    fs.appendFileSync(LOG, `${ts()} ${line}\n`);
  } catch {}
}

function saveState(extra) {
  const data = { state, fails, needsQr, downSince: downSince || null, lastRestart: lastRestart || null, updatedAt: Date.now(), ...extra };
  try { fs.writeFileSync(STATE_FILE + '.tmp', JSON.stringify(data)); fs.renameSync(STATE_FILE + '.tmp', STATE_FILE); } catch {}
}

// ---- OneBot WS 调用 ----
function api(action, params = {}, timeout = 8000) {
  return new Promise((resolve) => {
    let done = false;
    let ws;
    const finish = (v) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      try { ws.close(); } catch {}
      resolve(v);
    };
    const timer = setTimeout(() => finish({ ok: false, why: 'timeout' }), timeout);
    try {
      ws = new WebSocket(WS_URL, { headers: { Authorization: `Bearer ${TOKEN}` } });
    } catch {
      return resolve({ ok: false, why: 'construct' });
    }
    ws.onopen = () => {
      try { ws.send(JSON.stringify({ action, params, echo: 'g' })); }
      catch { finish({ ok: false, why: 'send' }); }
    };
    ws.onmessage = (e) => {
      let d;
      try { d = JSON.parse(String(e.data)); } catch { return; }
      if (d.echo !== 'g') return;
      finish({ ok: d.retcode === 0, retcode: d.retcode, data: d.data });
    };
    ws.onerror = () => finish({ ok: false, why: 'ws-error' });
    ws.onclose = () => finish({ ok: false, why: 'closed' });
  });
}

// ---- 外网连通性（决定要不要重启）----
function netOk(timeout = 4000) {
  return new Promise((resolve) => {
    let done = false;
    const sock = net.connect({ host: '223.5.5.5', port: 443 });
    const finish = (v) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      try { sock.destroy(); } catch {}
      resolve(v);
    };
    const timer = setTimeout(() => finish(false), timeout);
    sock.once('connect', () => finish(true));
    sock.once('error', () => finish(false));
  });
}

// ---- 通知 ----
const inQuietHours = () => {
  const h = Number(new Date(Date.now() + 8 * 3600e3).toISOString().slice(11, 13));
  return h >= 23 || h < 8;
};

async function notify(text) {
  if (inQuietHours()) {
    log(`NOTIFY(跳过,夜间) ${text}`);
    return;
  }
  const r = await api('send_private_msg', { user_id: ADMIN, message: text }, 10_000);
  log(r.ok ? `NOTIFY 已发送: ${text}` : `NOTIFY 失败 ${JSON.stringify(r)}`);
}

// ---- 状态 ----
let state = 'unknown';        // unknown | online | offline | dead | needs_qr
let fails = 0;
let lastRestart = 0;
let restartTimes = [];
let needsQr = false;
let downSince = 0;
let hbAt = 0;
let lastNetLog = 0;
let lastQrWaitLog = 0;

// ---- 自动重启 ----
async function tryRecover() {
  const now = Date.now();
  restartTimes = restartTimes.filter((t) => now - t < WINDOW);

  // 等人工扫码阶段（NapCat 每 2 分钟刷新一次二维码）重启只会把码刷掉，先别动
  const qrSt = fs.statSync(QR_SRC, { throwIfNoEntry: false });
  if (qrSt && now - qrSt.mtimeMs < 3 * 60_000) {
    if (now - lastQrWaitLog > 5 * 60_000) {
      lastQrWaitLog = now;
      log('QRWAIT 二维码在刷新，判定为等待扫码，暂不重启');
    }
    return;
  }

  if (restartTimes.length >= MAX_RESTARTS) {
    needsQr = true;
    state = 'needs_qr';
    log(`GIVEUP 30 分钟内已重启 ${restartTimes.length} 次仍离线，停止自动重启，等人工扫码`);
    return;
  }

  const gap = BACKOFF[Math.min(restartTimes.length, BACKOFF.length - 1)];
  if (lastRestart && now - lastRestart < gap) return; // 冷却中

  // 网络本身不通时重启没用，别浪费重启次数
  if (!DRY && !(await netOk())) {
    if (now - lastNetLog > 5 * 60_000) {
      lastNetLog = now;
      log('NET 外网不通，暂不重启，等网络恢复');
    }
    return;
  }

  const downSec = Math.round((now - downSince) / 1000);
  if (DRY) {
    log(`RESTART(dry-run) 跳过重启，掉线 ${downSec}s`);
    fails = 0;
    return;
  }

  lastRestart = now;
  restartTimes.push(now);
  log(`RESTART 第 ${restartTimes.length} 次重启 napcat.service（已掉线 ${downSec}s）`);
  try {
    const restartCmd = process.env.NAPCAT_RESTART_CMD;
    if (restartCmd) {
      // Windows 移植：由 NAPCAT_RESTART_CMD 指定重启命令（默认 systemd）
      const parts = restartCmd.match(/(?:[^\s"]+|"[^"]*")+/g) || [];
      const [cmd, ...args] = parts.map((p) => p.replace(/^"|"$/g, ''));
      await execFileP(cmd, args, { timeout: 90_000 });
    } else {
      await execFileP('systemctl', ['--user', 'restart', 'napcat.service'], { timeout: 45_000 });
    }
    log('RESTART 命令已执行，等待恢复');
  } catch (e) {
    log(`RESTART 执行失败: ${e.message}`);
  }
  fails = 0;

  // 重启后每 10s 探一次，尽早确认恢复
  const t0 = Date.now();
  while (Date.now() - t0 < RECOVER_WAIT) {
    await sleep(10_000);
    const r = await api('get_status', {}, 6000);
    if (r.ok && r.data?.online === true) {
      log(`RESTART 后 ${Math.round((Date.now() - t0) / 1000)}s 已恢复上线`);
      return;
    }
  }
  log(`RESTART 后 ${Math.round(RECOVER_WAIT / 1000)}s 仍未上线，下轮继续判定`);
}

// ---- 主循环 ----
async function tick() {
  const now = Date.now();
  const r = await api('get_status');
  const online = r.ok && r.data?.online === true;

  if (online) {
    if (state === 'offline' || state === 'dead' || state === 'needs_qr') {
      const mins = Math.max(1, Math.round((now - downSince) / 60_000));
      log(`ONLINE 恢复${state === 'needs_qr' ? '（之前已放弃自动重启）' : ''}，掉线约 ${mins} 分钟`);
      if (downSince && now - downSince > 2 * 60_000) await notify(`刚掉线 ${mins} 分钟，已经自己连回来了。`);
      needsQr = false;
      restartTimes = [];
      lastRestart = 0;
      downSince = 0;
      fails = 0;
    } else if (state === 'unknown') {
      log(`ONLINE 守卫启动，当前在线 (${r.data?.good ? 'good' : 'not-good'})`);
    }
    state = 'online';
  } else {
    if (!needsQr && (state === 'online' || state === 'unknown')) {
      downSince = now;
      log(`OFFLINE 探测失败 ${JSON.stringify(r)}`);
    }
    state = needsQr ? 'needs_qr' : (r.ok ? 'offline' : 'dead');
    fails++;
    if (!needsQr && fails >= FAIL_TO_RESTART) await tryRecover();
  }

  if (state === 'online' && now - hbAt > HEARTBEAT) {
    hbAt = now;
    const h = await api('set_online_status', { status: 10, ext_status: 0, battery_status: 100 });
    if (!h.ok) log(`HEARTBEAT 失败 ${JSON.stringify(h)}`);
  }

  // 需要扫码时只定期记一笔，不生成也不搬二维码
  if (state === 'needs_qr' && Date.now() - lastQrWaitLog > 5 * 60_000) {
    lastQrWaitLog = Date.now();
    log('WAITQR 仍在等待人工扫码');
  }

  saveState();
}

log(`guard start pid=${process.pid}${DRY ? ' (dry-run)' : ''}`);

(async () => {
  for (;;) {
    try { await tick(); }
    catch (e) { log(`TICK 异常: ${e.stack || e.message}`); }
    await sleep(TICK);
  }
})();
