"""表情包：白底黄框 + 一行大字（跨平台，自动找中文字体）。

用法: meme.py "文字" [输出文件]
"""
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HOME = Path(os.environ.get("BOT_HOME") or Path.home())
OUT_DIR = Path(os.environ.get("TTS_OUT_DIR") or (HOME / "tts-out"))

FONT_CANDIDATES = [
    # Linux (Noto CJK)
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    # Windows
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
]


def load_font(size):
    for p in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default(size=size)


text = sys.argv[1] if len(sys.argv) > 1 else "行吧"
out = sys.argv[2] if len(sys.argv) > 2 else str(OUT_DIR / "meme.png")
OUT_DIR.mkdir(parents=True, exist_ok=True)
Path(out).parent.mkdir(parents=True, exist_ok=True)

W = 420
img = Image.new("RGB", (W, W), "#FFF1A8")
d = ImageDraw.Draw(img)
d.rectangle([8, 8, W - 9, W - 9], outline="#1A1A1A", width=6)
# 星星点点
for x, y in [(60, 340), (120, 80), (330, 110), (360, 330)]:
    d.ellipse([x, y, x + 10, y + 10], fill="#1A1A1A")

font = load_font(130)
lines = text.split("\n")
lh = 150
y = (W - lh * len(lines)) // 2
for ln in lines:
    bb = d.textbbox((0, 0), ln, font=font)
    w = bb[2] - bb[0]
    d.text(((W - w) // 2 - bb[0], y), ln, font=font, fill="#1A1A1A")
    y += lh

small = load_font(22)
d.text((W - 110, W - 46), "大肥鱼", font=small, fill="#5A5140")
img.save(out)
print(out)
