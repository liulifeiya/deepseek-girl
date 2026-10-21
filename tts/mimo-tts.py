#!/usr/bin/env python3
"""MiMo TTS: 用法 mimo-tts.py "文本" [输出文件] [音色] [风格指令]"""
import base64
import json
import os
import sys
import urllib.request

BASE = "https://api.xiaomimimo.com/v1/chat/completions"


def load_key():
    key = os.environ.get("MIMO_API_KEY", "").strip()
    if key:
        return key
    for p in ("/home/ubuntu/tts-out/mimo-key.txt", "/home/ubuntu/.mimo-key"):
        if os.path.exists(p):
            with open(p) as f:
                return f.read().strip()
    raise SystemExit("no MiMo API key")


def main():
    text = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "/home/ubuntu/tts-out/mimo.wav"
    voice = sys.argv[3] if len(sys.argv) > 3 else "冰糖"
    style = sys.argv[4] if len(sys.argv) > 4 else ""

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
