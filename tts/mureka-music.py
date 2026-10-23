#!/usr/bin/env python3
"""Mureka 音乐生成
用法：mureka-music.py "<风格prompt>" [输出文件] [歌词文件]
不给歌词就用 easy-generate（它自己写词，贵约10倍）

跨平台：BOT_HOME（默认用户家目录）+ tts-out/。
"""
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://api.mureka.ai"

HOME = Path(os.environ.get("BOT_HOME") or Path.home())
OUT_DIR = Path(os.environ.get("TTS_OUT_DIR") or (HOME / "tts-out"))


def load_key():
    k = os.environ.get("MUREKA_API_KEY", "").strip()
    if k:
        return k
    for p in (OUT_DIR / "mureka-key.txt", HOME / ".mureka-key"):
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
    raise SystemExit("no Mureka API key")


def call(path, payload=None, method=None):
    url = BASE + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method or ("POST" if data else "GET"),
                                 headers={"Authorization": "Bearer " + load_key(),
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def find_audio(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and v.startswith("http") and (".mp3" in v or ".wav" in v or "audio" in v.lower()):
                out.append(v)
            else:
                find_audio(v, out)
    elif isinstance(obj, list):
        for v in obj:
            find_audio(v, out)
    return out


def main():
    prompt = sys.argv[1] if len(sys.argv) > 1 else "流行, 轻快, 女声"
    out = sys.argv[2] if len(sys.argv) > 2 else str(OUT_DIR / "song.mp3")
    lyr_path = sys.argv[3] if len(sys.argv) > 3 else None

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    Path(out).parent.mkdir(parents=True, exist_ok=True)

    payload = {"model": "auto", "prompt": prompt, "n": 1}
    if lyr_path and os.path.exists(lyr_path):
        payload["lyrics"] = Path(lyr_path).read_text(encoding="utf-8")
        path = "/v1/song/generate"
    else:
        path = "/v1/song/easy-generate"

    task = call(path, payload)
    tid = task.get("id") or task.get("task_id")
    if not tid:
        raise SystemExit("submit failed: " + json.dumps(task, ensure_ascii=False)[:500])
    print("task", tid, file=sys.stderr)

    for _ in range(120):
        time.sleep(6)
        t = call(f"/v1/song/query/{tid}")
        st = t.get("status")
        print("status", st, file=sys.stderr)
        if st in ("succeeded", "failed", "timeouted", "cancelled"):
            if st != "succeeded":
                raise SystemExit("task " + str(st) + ": " + json.dumps(t, ensure_ascii=False)[:500])
            urls = find_audio(t, [])
            if not urls:
                raise SystemExit("no audio url: " + json.dumps(t, ensure_ascii=False)[:800])
            with urllib.request.urlopen(urls[0], timeout=180) as r, open(out, "wb") as f:
                f.write(r.read())
            print(out)
            return
    raise SystemExit("timeout waiting for task")


if __name__ == "__main__":
    main()
