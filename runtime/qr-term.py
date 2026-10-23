#!/usr/bin/env python3
"""把 NapCat 的 qrcode.png 打成终端二维码（半块字符，白底黑块）。

用法: <venv>/python qr-term.py [png路径]

默认读 NapCat 的登录二维码缓存，路径按平台自动判断：
  Windows: %BOT_HOME%\\Napcat\\cache\\qrcode.png
  Linux  : $BOT_HOME/Napcat/opt/QQ/resources/app/app_launcher/napcat/cache/qrcode.png
也可以用 NAPCAT_QR_PNG 直接指定。
"""
import os
import sys
from math import gcd

from PIL import Image

HOME = os.environ.get("BOT_HOME") or os.path.expanduser("~")

_DEFAULT_CANDIDATES = [
    os.path.join(HOME, "Napcat", "cache", "qrcode.png"),
    os.path.join(HOME, "Napcat", "opt", "QQ", "resources", "app", "app_launcher", "napcat", "cache", "qrcode.png"),
]

PATH = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("NAPCAT_QR_PNG")
if not PATH:
    PATH = next((p for p in _DEFAULT_CANDIDATES if os.path.exists(p)), _DEFAULT_CANDIDATES[0])


def module_size(px, w, h):
    """用所有行/列游程长度的最大公约数估算模块边长。"""
    g = 0
    for y in range(h):
        run = 1
        for x in range(1, w):
            if px[x, y] == px[x - 1, y]:
                run += 1
            else:
                g = gcd(g, run)
                run = 1
        g = gcd(g, run)
    return g or 1


im = Image.open(PATH).convert("L")
w, h = im.size
px = im.load()
scale = module_size(px, w, h)
n = min(w, h) // scale
mat = [[px[x * scale + scale // 2, y * scale + scale // 2] < 128 for x in range(n)]
       for y in range(n)]

WHITE_BG = "\x1b[48;2;255;255;255m"
BLACK_FG = "\x1b[38;2;0;0;0m"
RESET = "\x1b[0m"
for y in range(0, n, 2):
    top = mat[y]
    bot = mat[y + 1] if y + 1 < n else [False] * n
    line = []
    for x in range(n):
        t, b = top[x], bot[x]
        if t and b:
            line.append("█")
        elif t:
            line.append("▀")
        elif b:
            line.append("▄")
        else:
            line.append(" ")
    print(WHITE_BG + BLACK_FG + "".join(line) + RESET)
