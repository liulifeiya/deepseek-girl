"""画一只熬夜的鲸鱼娘（跨平台，自动找中文字体）。

用法: draw2.py [输出文件]
"""
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HOME = Path(os.environ.get("BOT_HOME") or Path.home())
OUT_DIR = Path(os.environ.get("TTS_OUT_DIR") or (HOME / "tts-out"))

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
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


OUT_DIR.mkdir(parents=True, exist_ok=True)

W, H = 720, 560
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)
BLUE = (58, 78, 150)
SKIN = (255, 226, 210)
f_big = load_font(30)


def bubble(xy, text, lines=2):
    x0, y0, x1, y1 = xy
    d.rounded_rectangle(xy, radius=18, fill="white", outline="black", width=3)
    d.polygon([(x1 - 40, y1), (x1, y1 + 34), (x1 - 78, y1)], fill="white", outline="black")
    d.line([(x1 - 40, y1), (x1 - 78, y1)], fill="white", width=4)
    yy = y0 + 22
    for ln in text.split("\n"):
        d.text((x0 + 22, yy), ln, font=f_big, fill=(20, 20, 20))
        yy += 40


# 鲸鱼娘：头
d.ellipse([300, 150, 500, 350], fill=SKIN, outline="black", width=3)
# 头发
d.chord([280, 120, 520, 400], 180, 360, fill=BLUE, outline="black", width=3)
d.ellipse([270, 150, 340, 330], fill=BLUE, outline="black", width=3)
d.ellipse([460, 150, 530, 330], fill=BLUE, outline="black", width=3)
# 眼睛
d.ellipse([340, 250, 372, 300], fill=(40, 40, 60))
d.ellipse([428, 250, 460, 300], fill=(40, 40, 60))
d.ellipse([350, 258, 362, 272], fill="white")
d.ellipse([438, 258, 450, 272], fill="white")
# 嘴
d.arc([372, 300, 428, 335], 0, 180, fill="black", width=3)
# 身体
d.rounded_rectangle([330, 340, 470, 470], radius=30, fill=BLUE, outline="black", width=3)
d.rectangle([350, 350, 450, 420], fill="white")
# 尾巴
d.polygon([(470, 420), (540, 380), (540, 460)], fill=BLUE, outline="black")
# 耳朵/鳍
d.polygon([(300, 230), (250, 210), (300, 280)], fill=BLUE, outline="black")
d.polygon([(500, 230), (550, 210), (500, 280)], fill=BLUE, outline="black")
# 咖啡杯 + 热气
d.rounded_rectangle([90, 430, 190, 500], radius=10, fill="white", outline="black", width=3)
d.arc([180, 445, 215, 485], 270, 90, fill="black", width=3)
for x in (115, 140, 165):
    d.arc([x, 380, x + 24, 420], 200, 340, fill=(160, 160, 160), width=3)
d.text((100, 505), "凌晨三点", font=load_font(22), fill=(90, 90, 90))
# 对话框
bubble((40, 60, 330, 190), "还睡不睡了\n你这熬夜大肥鱼")

out = sys.argv[1] if len(sys.argv) > 1 else str(OUT_DIR / "meme3.png")
img.save(out)
print(out)
