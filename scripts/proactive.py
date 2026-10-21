#!/usr/bin/env python3
"""主动搭话：从白名单里挑一个今天还没聊过的人，生成一句开场白并发送。

小号好友很少，默认走「群里 @ 对方」；行尾加 dm 才走私聊（需互为好友）。

目标文件 ~/qq-dsh-bot/proactive-targets.txt 每行：
  QQ号 昵称 [group:群号] [dm]

用法:
  proactive.py                # 干跑：只生成，不发送
  proactive.py --send         # 真发（受频率/时段限制）
  proactive.py --send --to QQ # 指定对象
"""
import argparse
import asyncio
import json
import os
import random
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path.home() / "qq-dsh-bot"
TOKEN = (BASE / "onebot-token.txt").read_text().strip()
TARGETS = BASE / "proactive-targets.txt"
STATE = BASE / "proactive-state.json"
LOG = BASE / "proactive.log"
API = "https://api.deepseek.com/chat/completions"
DEFAULT_GROUP = "1003871222"

MIN_GAP_HOURS = 20
MAX_PER_DAY = 3
QUIET_START, QUIET_END = 23, 8


def log(msg: str) -> None:
    line = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
    print(line)
    with LOG.open("a") as f:
        f.write(line + "\n")


def load_targets():
    out = []
    if not TARGETS.exists():
        return out
    for line in TARGETS.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if not parts[0].isdigit():
            continue
        qq, nick = parts[0], parts[1] if len(parts) > 1 else parts[0]
        mode, gid = "group", DEFAULT_GROUP
        for p in parts[2:]:
            if p == "dm":
                mode = "dm"
            elif p.startswith("group:"):
                gid = p.split(":", 1)[1]
        out.append((qq, nick, mode, gid))
    return out


def load_state():
    try:
        st = json.loads(STATE.read_text())
    except Exception:
        st = {}
    st.setdefault("last_sent", {})
    st.setdefault("recent", [])
    st.setdefault("day", "")
    st.setdefault("count", 0)
    return st


def save_state(st) -> None:
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1))
    os.chmod(STATE, 0o600)


def gen_text(nick: str, recent, mode: str) -> str:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY 未设置")
    now = datetime.now()
    wd = "一二三四五六日"[now.weekday()]
    recent_txt = "；".join(recent[-6:]) if recent else "（无）"
    where = "你在 QQ 群里 @ 一个群友随口搭话，群里还有其他人" if mode == "group" \
        else "你在 QQ 上给一个朋友发私聊"
    prompt = (
        f"{where}。对方昵称：{nick}。现在是周{wd} {now:%H:%M}。"
        "写一句自然、口语化的开场白，15~40 字：可以是问候、分享一个小观察、或问一个轻松的问题。"
        "不要用“在吗”，不要说“想起你/想你/惦记”这类暧昧话，不要装熟，"
        "不要提 AI、机器人、服务器，不要列点，不要用引号，只输出这一句话。"
        f"最近已经发过：{recent_txt}，不要重复。"
    )
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 1.15,
        "max_tokens": 120,
    }).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    text = data["choices"][0]["message"]["content"].strip().strip('"“”')
    text = text.split("\n")[0].strip()
    return text[:80]


async def _call(action: str, params: dict):
    import websockets
    async with websockets.connect(
        "ws://127.0.0.1:3001",
        additional_headers={"Authorization": f"Bearer {TOKEN}"},
        max_size=2 ** 22,
        open_timeout=10,
    ) as ws:
        await ws.send(json.dumps({"action": action, "params": params, "echo": "call1"}))
        for _ in range(30):
            m = json.loads(await asyncio.wait_for(ws.recv(), 10))
            if m.get("echo") == "call1":
                ok = m.get("status") == "ok" or m.get("retcode") == 0
                return ok, m.get("message") or m.get("wording") or ""


def send(qq: str, nick: str, text: str, mode: str, gid: str):
    if mode == "dm":
        return asyncio.run(_call("send_private_msg", {"user_id": int(qq), "message": text}))
    msg = [
        {"type": "at", "data": {"qq": str(qq)}},
        {"type": "text", "data": {"text": f" {text}"}},
    ]
    return asyncio.run(_call("send_group_msg", {"group_id": int(gid), "message": msg}))


def pick(st, targets, forced=None):
    now = datetime.now()
    gap = timedelta(hours=MIN_GAP_HOURS)
    if forced:
        for t in targets:
            if t[0] == forced:
                return t
        return None
    pool = []
    for t in targets:
        last = st["last_sent"].get(t[0], 0)
        if now.timestamp() - last >= gap.total_seconds():
            pool.append(t)
    if not pool:
        return None
    return random.choice(pool)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true", help="真正发送")
    ap.add_argument("--to", help="指定 QQ 号")
    args = ap.parse_args()

    now = datetime.now()
    if now.hour >= QUIET_START or now.hour < QUIET_END:
        log("skip: quiet hours")
        return 0

    targets = load_targets()
    if not targets:
        log("skip: no targets")
        return 0

    st = load_state()
    today = now.strftime("%Y-%m-%d")
    if st.get("day") != today:
        st["day"] = today
        st["count"] = 0
    if st["count"] >= MAX_PER_DAY:
        log(f"skip: daily cap {MAX_PER_DAY} reached")
        return 0

    chosen = pick(st, targets, args.to)
    if not chosen:
        log("skip: no eligible target (all contacted within 20h)")
        return 0
    qq, nick, mode, gid = chosen
    text = gen_text(nick, st["recent"], mode)
    log(f"{'SEND' if args.send else 'DRY'} [{mode}] -> {nick}({qq}): {text}")

    if not args.send:
        return 0

    try:
        ok, err = send(qq, nick, text, mode, gid)
    except Exception as e:
        log(f"error: send failed: {type(e).__name__}: {e}")
        return 1
    if not ok:
        log(f"error: OneBot rejected: {err}")
        return 1

    st["last_sent"][qq] = now.timestamp()
    st["count"] += 1
    st["recent"] = (st["recent"] + [text])[-12:]
    save_state(st)
    log(f"ok: sent to {nick}({qq}); today={st['count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
