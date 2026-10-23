#!/usr/bin/env python3
"""看图前预处理：不管原始后缀是什么，转成能读的 PNG 并打印路径。

用法：python img-prep.py <图片路径>
输出：可读 PNG 的绝对路径（同一张图复用缓存）
"""
import hashlib
import os
import sys

from PIL import Image

HOME = os.environ.get("BOT_HOME") or os.path.expanduser("~")
OUT_DIR = os.path.join(HOME, "qq-dsh-bot", "image-lib", "_prep")


def main():
    if len(sys.argv) < 2:
        print('usage: img-prep.py <path>')
        return 1
    src = sys.argv[1]
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(src, 'rb') as f:
        digest = hashlib.sha256(f.read()).hexdigest()[:16]
    dest = os.path.join(OUT_DIR, digest + '.png')
    if os.path.exists(dest):
        print(dest)
        return 0
    im = Image.open(src)
    fmt = (im.format or '').upper()
    im.seek(0)
    im.convert('RGB').save(dest, 'PNG')
    print(dest)
    print('source_format=' + fmt, file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
