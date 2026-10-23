#!/usr/bin/env python3
"""MiMo TTS: 用法 mimo-tts.py "文本" [输出文件] [音色] [风格指令]

跨平台：BOT_HOME（默认用户家目录）+ tts-out/。
"""
import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

BASE = "https://api.xiaomimimo.com/v1/chat/completions"

HOME = Path(os.environ.get("BOT_HOME") or Path.home())
OUT_DIR = Path(os.environ.get("TTS_OUT_DIR") or (HOME / "tts-out"))


def load_key():
    key = os.environ.get("MIMO_API_KEY", "").strip()
    if key:
        return key
    for p in (OUT_DIR / "mimo-key.txt", HOME / ".mimo-key"):
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
    raise SystemExit("no MiMo API key")


def main():
    text = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else str(OUT_DIR / "mimo.wav")
    voice = sys.argv[3] if len(sys.argv) > 3 else "冰糖"
    style = sys.argv[4] if len(sys.argv) > 4 else ""

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    Path(out).parent.mkdir(parents=True, exist_ok=True)

    msgs = []
    if style:
        msgs.append({"role": "user", "content": style})
    msgs.append({"role": "assistant", "content": text})

    body = json.dumps({
        "model": "mimo-v2.5-tts",
        "messages": msgs,
        "audio": {"format": "wav", "voice": voice},
    }).encode()

    req = urllib.request.Request(BASE, data=body, headers={
        "Authorization": "Bearer " + load_key(),
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    audio = data["choices"][0]["message"]["audio"]["data"]
    with open(out, "wb") as f:
        f.write(base64.b64decode(audio))
    print(out)


if __name__ == "__main__":
    main()
