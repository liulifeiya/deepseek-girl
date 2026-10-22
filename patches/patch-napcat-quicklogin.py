#!/usr/bin/env python3
"""NapCat 快速登录补丁：Worker 重启时保留 -q <uin>。

背景见 NAPCAT-QUICK-LOGIN.md。NapCat 升级会覆盖 napcat.mjs，升级后重跑本脚本。

用法：
    python3 patch-napcat-quicklogin.py [napcat.mjs 路径]

默认路径：~/Napcat/opt/QQ/resources/app/app_launcher/napcat/napcat.mjs
退出码：0 已打/本来就打了；1 锚点找不到（版本变了，需要人工看）。
"""
import os
import sys

DEFAULT = os.path.expanduser(
    "~/Napcat/opt/QQ/resources/app/app_launcher/napcat/napcat.mjs"
)
ANCHOR = "async function c2e(t, e)"
WINDOW = 4000


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    if not os.path.isfile(path):
        print(f"找不到 {path}")
        return 1

    with open(path, encoding="utf-8", errors="surrogateescape") as f:
        src = f.read()

    i = src.find(ANCHOR)
    if i < 0:
        print("锚点 async function c2e 没找到：NapCat 版本变了，请按文档人工确认")
        return 1

    head, body, tail = src[:i], src[i:i + WINDOW], src[i + WINDOW:]
    if "await Bg(!1, t, e)" not in body:
        if "await Bg(!0, t, e)" in body:
            print("快速登录补丁已经打过了")
            return 0
        print("c2e 里没找到 Bg(!1, t, e)，版本可能变了，请人工确认")
        return 1

    body = body.replace("await Bg(!1, t, e)", "await Bg(!0, t, e)", 1)
    with open(path, "w", encoding="utf-8", errors="surrogateescape") as f:
        f.write(head + body + tail)
    print("已打快速登录补丁：c2e 重启 Worker 时保留 -q")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
