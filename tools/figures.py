# The report's figures, drawn from the runs and from research/results.json, so a figure cannot show something the
# data no longer says. Usage: py tools/figures.py  ->  research/img/*.jpg|png
import json
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'research', 'img')
FONT = os.path.join(ROOT, 'brands', 'meridian', 'fonts', 'InterTight.ttf')
SURFACE, INK, MUTED = (250, 250, 248), (28, 28, 26), (110, 108, 102)
VERDICT = {'publish': (46, 125, 50), 'review': (176, 110, 0), 'regenerate': (190, 40, 40)}
# sequential blue, light -> dark (dataviz reference palette, steps 100..650)
BLUES = ['#eeeeea', '#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#104281']


def font(size, weight='Regular'):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_name(weight)
    return f


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def on_grey(path, size):
    im = Image.open(path).convert('RGBA')
    bg = Image.new('RGBA', im.size, (200, 200, 198, 255))
    bg.alpha_composite(im)
    return bg.convert('RGB').resize(size, Image.LANCZOS)


def references():
    rows = [('vela', ['front', 'back'], ['graphite', 'paper']), ('lumen', ['front', 'right'], ['white', 'signal-orange']),
            ('field16', ['front', 'right'], ['white', 'signal-orange'])]
    S, T = 340, 34
    sheet = Image.new('RGB', (S * 4, (S + T) * 3), SURFACE)
    d = ImageDraw.Draw(sheet)
    for r, (p, views, cws) in enumerate(rows):
        i = 0
        for v in views:
            for cw in cws:
                x, y = i * S, r * (S + T)
                sheet.paste(on_grey(os.path.join(ROOT, 'runs', p, 'passes', v, f'beauty_{cw}.png'), (S, S)), (x, y + T))
                d.text((x + 8, y + 7), f'{p.upper()} · {v} · {cw}', font=font(18), fill=INK)
                i += 1
    sheet.save(os.path.join(OUT, 'references.jpg'), quality=86)


def variation():
    runs = {r['id']: r for r in map(json.loads, open(os.path.join(ROOT, 'research', 'runs.jsonl'), encoding='utf-8'))
            if r['id'].startswith('known-') and r['source'] == 'variation'}
    sel = [('lumen', 'front', 'signal-orange'), ('field16', 'right', 'white'), ('vela', 'front', 'graphite'), ('vela', 'back', 'paper')]
    lights = ['studio', 'courtyard', 'interior', 'sunset']
    S, L, T, B = 280, 190, 36, 50
    sheet = Image.new('RGB', (L + S * 4, T + (S + B) * len(sel)), SURFACE)
    d = ImageDraw.Draw(sheet)
    for j, l in enumerate(lights):
        d.text((L + j * S + 8, 8), l, font=font(20, 'Medium'), fill=INK)
    for i, (p, v, cw) in enumerate(sel):
        y = T + i * (S + B)
        d.text((10, y + S // 2 - 22), f'{p.upper()}\n{v} · {cw}', font=font(18), fill=INK)
        for j, l in enumerate(lights):
            r = runs[f'known-{p}-{v}-{cw}-light-{l}']
            sheet.paste(Image.open(os.path.join(ROOT, r['output'])).resize((S, S), Image.LANCZOS), (L + j * S, y))
            m = r['metrics']
            d.text((L + j * S + 8, y + S + 4), r['gate_verdict'], font=font(18, 'Medium'), fill=VERDICT[r['gate_verdict']])
            d.text((L + j * S + 8, y + S + 26), f"color {m['gate_colour']} · partes {m['gate_parts']}", font=font(15), fill=MUTED)
    sheet.save(os.path.join(OUT, 'variation.jpg'), quality=86)


def perturbations():
    names = ['none', 'invent', 'remove', 'erasetext', 'typo', 'warp10', 'hue10', 'whitebalance']
    rows = [('vela', 'front', 'graphite'), ('lumen', 'front', 'white'), ('field16', 'right', 'signal-orange')]
    S, T = 240, 30
    sheet = Image.new('RGB', (S * len(names), (S + T) * len(rows)), SURFACE)
    d = ImageDraw.Draw(sheet)
    for r, (p, v, cw) in enumerate(rows):
        for c, n in enumerate(names):
            path = os.path.join(ROOT, 'runs', p, 'perturb', f'{v}_{n}_{cw}.png')
            if not os.path.exists(path):
                continue
            im = Image.open(path)
            w, h = im.size
            sheet.paste(im.crop((int(w * .15), int(h * .1), int(w * .85), int(h * .9))).resize((S, S), Image.LANCZOS),
                        (c * S, r * (S + T) + T))
            d.text((c * S + 6, r * (S + T) + 6), f'{p.upper()} · {n}', font=font(16), fill=INK)
    sheet.save(os.path.join(OUT, 'perturbations.jpg'), quality=86)


def detection():
    res = json.load(open(os.path.join(ROOT, 'research', 'results.json'), encoding='utf-8'))['phase1']
    cols = ['gate_verdict', 'edge_precision', 'edge_recall', 'presence_min', 'presence_v2', 'colour_worst_p95',
            'colour_v1_median', 'colour_v2_drift', 'dreamsim', 'cer_worst', 'cer_primary_worst']
    groups = [('Debería fallar: más alto es mejor', [p for p in res['detection'] if res['expected'][p] == 'fail']),
              ('Borde', [p for p in res['detection'] if res['expected'][p] == 'border']),
              ('No debería fallar: más bajo es mejor', [p for p in res['detection'] if res['expected'][p] == 'pass'])]
    L, CW, RH, TOP, GAP = 230, 118, 42, 140, 44
    n_rows = sum(len(g) for _, g in groups)
    W, H = L + CW * len(cols) + 20, TOP + n_rows * RH + GAP * len(groups) + 70
    im = Image.new('RGB', (W, H), SURFACE)
    d = ImageDraw.Draw(im)
    d.text((20, 16), 'Qué ve cada juez: imágenes detectadas fuera de la envolvente de luz real', font=font(24, 'Medium'), fill=INK)
    d.text((20, 50), f"{res['n_perturb']} perturbaciones sobre 3 productos · detectada = peor que el peor valor del producto correcto bajo 4 luces",
           font=font(16), fill=MUTED)
    for j, c in enumerate(cols):
        label = res['labels'][c]
        words, line = label.split(' '), ''
        lines = []
        for w in words:
            if len(line + ' ' + w) > 12 and line:
                lines.append(line)
                line = w
            else:
                line = (line + ' ' + w).strip()
        lines.append(line)
        for k, t in enumerate(lines[-2:]):
            d.text((L + j * CW + CW / 2, TOP - 44 + k * 20), t, font=font(15, 'Medium'), fill=INK, anchor='mm')
    y = TOP
    for title, ps in groups:
        if not ps:
            continue
        y += 10
        d.text((20, y + 4), title, font=font(15, 'Medium'), fill=MUTED)
        y += GAP - 10
        for p in ps:
            d.text((20, y + RH / 2), res['names'][p], font=font(17), fill=INK, anchor='lm')
            for j, c in enumerate(cols):
                cell = res['detection'][p].get(c)
                x0, y0 = L + j * CW + 2, y + 2
                if not cell or not cell['of']:
                    d.rectangle((x0, y0, x0 + CW - 4, y0 + RH - 4), fill=SURFACE, outline=(225, 224, 220))
                    d.text((x0 + CW / 2 - 2, y0 + RH / 2 - 2), '—', font=font(16), fill=MUTED, anchor='mm')
                    continue
                k = min(int(round(cell['rate'] * (len(BLUES) - 1))), len(BLUES) - 1)
                d.rounded_rectangle((x0, y0, x0 + CW - 4, y0 + RH - 4), 4, fill=hexrgb(BLUES[k]))
                d.text((x0 + CW / 2 - 2, y0 + RH / 2 - 2), f"{cell['n']}/{cell['of']}", font=font(17, 'Medium'),
                       fill=(255, 255, 255) if k >= 4 else INK, anchor='mm')
            y += RH
    # legend: the ramp from 0 to 100 %
    lx, ly = L, H - 44
    d.text((20, ly + 4), 'Tasa detectada', font=font(15), fill=MUTED)
    for k, h in enumerate(BLUES):
        d.rounded_rectangle((lx + k * 44, ly, lx + k * 44 + 40, ly + 22), 3, fill=hexrgb(h))
    d.text((lx, ly + 26), '0 %', font=font(13), fill=MUTED)
    d.text((lx + len(BLUES) * 44 - 40, ly + 26), '100 %', font=font(13), fill=MUTED)
    im.save(os.path.join(OUT, 'detection.png'))


def auc_heatmap():
    res = json.load(open(os.path.join(ROOT, 'research', 'results.json'), encoding='utf-8'))['phase1']
    cols = ['gate_verdict', 'edge_precision', 'edge_recall', 'presence_min', 'presence_v2', 'colour_worst_p95',
            'colour_v1_median', 'colour_v2_drift', 'dreamsim', 'cer_primary_worst']
    exp = res['expected']
    groups = [('Debería fallar: cuanto más cerca de 1, mejor', [p for p in res['auc'] if exp[p] == 'fail']),
              ('Borde', [p for p in res['auc'] if exp[p] == 'border']),
              ('No debería fallar: 0,5 o menos es lo correcto; más alto = falsa alarma', [p for p in res['auc'] if exp[p] == 'pass'])]
    L, CW, RH, TOP, GAP = 230, 118, 42, 150, 44
    n_rows = sum(len(g) for _, g in groups)
    W, H = L + CW * len(cols) + 20, TOP + n_rows * RH + GAP * len(groups) + 70
    im = Image.new('RGB', (W, H), SURFACE)
    d = ImageDraw.Draw(im)
    d.text((20, 16), 'Qué ve cada juez: AUC por rango contra las imágenes correctas', font=font(24, 'Medium'), fill=INK)
    d.text((20, 50), 'Por imagen con falla: la parte de las imágenes correctas del mismo producto, vista y colorway '
           '(4 luces, otro fondo, balance, JPEG)', font=font(16), fill=MUTED)
    d.text((20, 72), 'que puntúan mejor que ella. 1 = siempre peor que todas las correctas · 0,5 = azar', font=font(16), fill=MUTED)
    for j, c in enumerate(cols):
        words, line, lines = res['labels'][c].split(' '), '', []
        for w in words:
            if len(line + ' ' + w) > 12 and line:
                lines.append(line)
                line = w
            else:
                line = (line + ' ' + w).strip()
        lines.append(line)
        for k, t in enumerate(lines[-2:]):
            d.text((L + j * CW + CW / 2, TOP - 40 + k * 19), t, font=font(14, 'Medium'), fill=INK, anchor='mm')
    y = TOP
    for title, ps in groups:
        if not ps:
            continue
        y += 10
        d.text((20, y + 4), title, font=font(15, 'Medium'), fill=MUTED)
        y += GAP - 10
        for p in ps:
            d.text((20, y + RH / 2), res['names'][p], font=font(16), fill=INK, anchor='lm')
            for j, c in enumerate(cols):
                cell = res['auc'][p].get(c)
                x0, y0 = L + j * CW + 2, y + 2
                if not cell:
                    d.rectangle((x0, y0, x0 + CW - 4, y0 + RH - 4), fill=SURFACE, outline=(225, 224, 220))
                    d.text((x0 + CW / 2 - 2, y0 + RH / 2 - 2), '—', font=font(15), fill=MUTED, anchor='mm')
                    continue
                v = cell['auc']
                k = 0 if v <= 0.5 else min(int(round((v - 0.5) / 0.5 * (len(BLUES) - 1))), len(BLUES) - 1)
                d.rounded_rectangle((x0, y0, x0 + CW - 4, y0 + RH - 4), 4, fill=hexrgb(BLUES[k]))
                d.text((x0 + CW / 2 - 2, y0 + RH / 2 - 2), f'{v:.2f}'.replace('.', ','), font=font(16, 'Medium'),
                       fill=(255, 255, 255) if k >= 4 else INK, anchor='mm')
            y += RH
    lx, ly = L, H - 44
    d.text((20, ly + 4), 'AUC', font=font(15), fill=MUTED)
    for k, h in enumerate(BLUES):
        d.rounded_rectangle((lx + k * 44, ly, lx + k * 44 + 40, ly + 22), 3, fill=hexrgb(h))
    d.text((lx, ly + 26), '≤ 0,5', font=font(13), fill=MUTED)
    d.text((lx + len(BLUES) * 44 - 30, ly + 26), '1,0', font=font(13), fill=MUTED)
    im.save(os.path.join(OUT, 'auc.png'))


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    references()
    variation()
    perturbations()
    detection()
    auc_heatmap()
    print('figures in', OUT)
