"""crop.py IMG x0 y0 x1 y1 OUT [grid_step] [marks]
Crops a region, upscales to ~1100px wide and draws a labelled pixel grid (original coordinates).
marks: optional 'x,y;x,y' points drawn as red crosses (original coords)."""
import sys
from PIL import Image, ImageDraw, ImageFont
img, x0, y0, x1, y1, out = sys.argv[1], *map(int, sys.argv[2:6]), sys.argv[6]
step = int(sys.argv[7]) if len(sys.argv) > 7 else 50
marks = [tuple(map(float, p.split(','))) for p in sys.argv[8].split(';')] if len(sys.argv) > 8 and sys.argv[8] else []
im = Image.open(img).convert('RGB').crop((x0, y0, x1, y1))
s = 1100 / (x1 - x0)
im = im.resize((int((x1 - x0) * s), int((y1 - y0) * s)), Image.LANCZOS)
d = ImageDraw.Draw(im)
try:
    f = ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', 14)
except Exception:
    f = ImageFont.load_default()
for gx in range((x0 // step + 1) * step, x1, step):
    X = (gx - x0) * s
    d.line([(X, 0), (X, im.height)], fill=(255, 0, 255) if gx % (step * 2) == 0 else (0, 200, 255), width=1)
    d.text((X + 2, 2), str(gx), fill=(255, 0, 255), font=f)
for gy in range((y0 // step + 1) * step, y1, step):
    Y = (gy - y0) * s
    d.line([(0, Y), (im.width, Y)], fill=(255, 0, 255) if gy % (step * 2) == 0 else (0, 200, 255), width=1)
    d.text((2, Y + 2), str(gy), fill=(255, 0, 255), font=f)
for (mx, my) in marks:
    X, Y = (mx - x0) * s, (my - y0) * s
    d.line([(X - 10, Y), (X + 10, Y)], fill=(255, 0, 0), width=2)
    d.line([(X, Y - 10), (X, Y + 10)], fill=(255, 0, 0), width=2)
im.save(out)
print(out, im.size)
