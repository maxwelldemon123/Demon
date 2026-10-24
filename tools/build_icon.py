# -*- coding: utf-8 -*-
"""生成 Demon 图标（多尺寸 .ico），风格与托盘/界面一致：紫色渐变圆角方块 + 白色 D。"""

import os

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = r"E:\dshwork\Demon\dist"
SRC_DIR = r"E:\dshwork\Demon\src\assets"
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(SRC_DIR, exist_ok=True)

SIZE = 512
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# 竖向渐变（上浅紫 -> 下深紫）
top = (140, 108, 255)
bottom = (92, 60, 220)
for y in range(SIZE):
    t = y / (SIZE - 1)
    color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    draw.line([(0, y), (SIZE, y)], fill=color + (255,))

# 圆角遮罩
mask = Image.new("L", (SIZE, SIZE), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=int(SIZE * 0.22), fill=255)
img.putalpha(mask)

# 白色 D
font = None
for candidate in (
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\msyhbd.ttc",
):
    if os.path.exists(candidate):
        try:
            font = ImageFont.truetype(candidate, int(SIZE * 0.62))
            break
        except Exception:
            continue
if font is None:
    font = ImageFont.load_default()

bbox = draw.textbbox((0, 0), "D", font=font)
w = bbox[2] - bbox[0]
h = bbox[3] - bbox[1]
pos = ((SIZE - w) / 2 - bbox[0], (SIZE - h) / 2 - bbox[1] - SIZE * 0.01)
draw.text(pos, "D", font=font, fill=(255, 255, 255, 255))

sizes = [16, 24, 32, 48, 64, 128, 256]
ico_path = os.path.join(OUT_DIR, "demon.ico")
img.save(ico_path, format="ICO", sizes=[(s, s) for s in sizes])
img.save(os.path.join(OUT_DIR, "demon-icon.png"), format="PNG")

# 给 Qt 资源用的副本
copy_path = os.path.join(SRC_DIR, "demon.ico")
img.save(copy_path, format="ICO", sizes=[(s, s) for s in sizes])

print("[OK]", ico_path, os.path.getsize(ico_path), "bytes")
print("[OK]", copy_path)
for s in sizes:
    print("   size", s)
