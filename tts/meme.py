import sys
from PIL import Image, ImageDraw, ImageFont
text = sys.argv[1] if len(sys.argv) > 1 else "行吧"
out = sys.argv[2] if len(sys.argv) > 2 else "/home/ubuntu/tts-out/meme.png"
W = 420
img = Image.new("RGB", (W, W), "#FFF1A8")
d = ImageDraw.Draw(img)
d.rectangle([8, 8, W-9, W-9], outline="#1A1A1A", width=6)
# 星星点点
for x, y in [(60,340),(120,80),(330,110),(360,330)]:
    d.ellipse([x, y, x+10, y+10], fill="#1A1A1A")
font = None
for p in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
          "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"]:
    try:
        font = ImageFont.truetype(p, 130); break
    except Exception: pass
lines = text.split("\n")
lh = 150
y = (W - lh*len(lines))//2
for ln in lines:
    bb = d.textbbox((0,0), ln, font=font)
    w = bb[2]-bb[0]
    d.text(((W-w)//2 - bb[0], y), ln, font=font, fill="#1A1A1A")
    y += lh
small = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc", 22)
d.text((W-110, W-46), "大肥鱼", font=small, fill="#5A5140")
img.save(out)
print(out)
