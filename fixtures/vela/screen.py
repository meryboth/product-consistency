# VELA's e-ink screen, drawn from code: the UI is almost only text, on purpose. Every line here is also written to
# screen.json, which is the ground truth the OCR metric reads (research/PROTOCOL.md, CER).
# Runs with the normal Python (Pillow), not Blender:  py fixtures/vela/screen.py
# Writes fixtures/vela/screen.png (960 x 1600, portrait, the aspect of the 56 x 94 mm display) and screen.json.
import json
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, '..', '..', 'brands', 'meridian', 'fonts', 'InterTight.ttf')
W, H, M = 960, 1600, 72                                # pixels, and the side margin
PAPER, INK = (237, 235, 230), (26, 26, 26)             # e-ink: warm light grey and near black

# the screen, top to bottom: (text, size in px, weight, align, gap after)
CLOCK = '09:41'
BATTERY = '82%'
DATE = 'Thursday, September 25'
ITEMS = [('Calls', None), ('Messages', '2'), ('Notes', None), ('Calendar', None), ('Alarm', '07:30'), ('Settings', None)]
FOOTER = 'Focus mode · 3h 20m'


def font(size, weight='Regular'):
    f = ImageFont.truetype(FONT, size)
    try:
        f.set_variation_by_name(weight)
    except (OSError, ValueError):
        pass
    return f


def draw():
    img = Image.new('RGB', (W, H), PAPER)
    d = ImageDraw.Draw(img)
    y = 56
    # status: battery on the right, a small battery glyph before it
    small = font(40, 'Medium')
    bw = d.textlength(BATTERY, font=small)
    d.text((W - M - bw, y), BATTERY, font=small, fill=INK)
    bx = W - M - bw - 76
    d.rectangle((bx, y + 10, bx + 52, y + 38), outline=INK, width=4)
    d.rectangle((bx + 52, y + 18, bx + 58, y + 30), fill=INK)
    d.rectangle((bx + 8, y + 18, bx + 8 + int(36 * 0.82), y + 30), fill=INK)
    y += 70
    d.text((M, y), CLOCK, font=font(210, 'Bold'), fill=INK)
    y += 250
    d.text((M, y), DATE, font=font(52, 'Regular'), fill=INK)
    y += 100
    d.line((M, y, W - M, y), fill=INK, width=4)
    y += 44
    item = font(72, 'Medium')
    for label, value in ITEMS:
        d.text((M, y), label, font=item, fill=INK)
        if value:
            vw = d.textlength(value, font=item)
            d.text((W - M - vw, y), value, font=item, fill=INK)
        y += 124
    y += 10
    d.line((M, y, W - M, y), fill=INK, width=4)
    y += 44
    d.text((M, y), FOOTER, font=font(46, 'Regular'), fill=INK)
    return img


if __name__ == '__main__':
    draw().save(os.path.join(HERE, 'screen.png'))
    lines = [f'{BATTERY}', CLOCK, DATE] + [f'{l} {v}' if v else l for l, v in ITEMS] + [FOOTER]
    json.dump({'lines': lines, 'note': 'reading order, top to bottom; the battery sits on the first row, right'},
              open(os.path.join(HERE, 'screen.json'), 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print('screen.png', len(lines), 'lines')
