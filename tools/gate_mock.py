# What the proposed gate node would show, on a real phase-2 photo: an overlay of where each fault is, a score per
# axis and a routed verdict. The thresholds are PROVISIONAL: each metric is compared with the real-variation
# envelope (the worst value the right product reaches under the four lights, phase 0-1). The gate that ships is
# the one frozen after human labels (phase 3).
# The example is fixed before looking: LUMEN, front, control 0.5 ("loose"), seed 1, raw and finished.
# Usage: py tools/gate_mock.py  ->  research/img/gate_example.png
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
sys.path.insert(0, os.path.join(ROOT, 'metrics'))
import battery  # noqa: E402
from consistency import part_masks  # noqa: E402

FONT = os.path.join(ROOT, 'brands', 'meridian', 'fonts', 'InterTight.ttf')
SURFACE, INK, MUTED = (250, 250, 248), (28, 28, 26), (110, 108, 102)
RED, BLUE, ORANGE, OK, BAD = (214, 48, 49), (37, 106, 191), (232, 126, 4), (46, 125, 50), (190, 40, 40)
AXES = [('edge_precision', 'Lo inventado', 'precisión de bordes', 'up'),
        ('edge_recall', 'Lo deformado o borrado', 'recall de bordes', 'up'),
        ('presence_min', 'Piezas presentes', 'presencia por pieza', 'up'),
        ('colour_v1_median', 'Color por parte', 'color v1, luz descontada', 'down')]


def font(size, weight='Regular'):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_name(weight)
    return f


def envelope(product, view, cw):
    """Worst value of each metric over the four lights, for the right product (known-v1 rows)."""
    env = {}
    for l in open(os.path.join(ROOT, 'research', 'runs.jsonl'), encoding='utf-8'):
        r = json.loads(l)
        if not (r['id'].startswith('known-v1-') and r['source'] == 'variation' and r['case'] == product
                and r['view'] == view and r['colorway'] == cw):
            continue
        for m, _, _, d in AXES:
            v = r['metrics'][m]
            env[m] = v if m not in env else (min(env[m], v) if d == 'up' else max(env[m], v))
    return env


def overlay(product, view, cw, path):
    passes = os.path.join(ROOT, 'runs', product, 'passes')
    img = battery.on_grey(path, (1024, 1024))
    size = img.size
    mask = battery.load_mask(passes, view, 'mask.png', size)
    inside = cv2.erode(mask.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    ref_e = battery.reference_edges(passes, view, cw, size) & inside
    pho_e = battery.photo_edges(img) & inside
    near = lambda e: cv2.distanceTransform((~e).astype(np.uint8), cv2.DIST_L2, 3) <= battery.EDGE_TOL_PX
    invented, missing = pho_e & ~near(ref_e), ref_e & ~near(pho_e)
    base = np.asarray(img).astype(float) * 0.45 + 255 * 0.55              # the photo, faded, as a backdrop
    out = base.copy()
    out[cv2.dilate(missing.astype(np.uint8), np.ones((2, 2), np.uint8)) > 0] = BLUE
    out[cv2.dilate(invented.astype(np.uint8), np.ones((2, 2), np.uint8)) > 0] = RED
    ov = Image.fromarray(out.astype(np.uint8))
    d = ImageDraw.Draw(ov)
    scores, parts = battery.colour_presence_scores(passes, view, cw, img)
    for name, m in part_masks(passes, view, size).items():
        for piece in battery._components(m, battery.PIECE_MIN_PX):
            row = parts.get(name, {})
            if row.get('presence_min', 1) < 0.5:
                ys, xs = np.where(piece)
                d.rectangle((xs.min() - 6, ys.min() - 6, xs.max() + 6, ys.max() + 6), outline=ORANGE, width=4)
    edges = battery.edge_scores(passes, view, cw, img)
    return img, ov, {**edges, **scores}, parts


def verdict(scores, env):
    flags = {m: (scores[m] < env[m]) if d == 'up' else (scores[m] > env[m]) for m, _, _, d in AXES}
    if not any(flags.values()):
        return 'publicar', flags
    if flags['edge_precision'] or flags['edge_recall']:
        return 'regenerar (nueva semilla, más control)', flags
    return 'aplicar guardas y volver a medir', flags


PART_NAMES = {'dark': 'agujeros del parlante', 'ab': 'botones A/B', 'dpad': 'cruceta', 'pills': 'Start/Select',
              'cart': 'cartucho', 'screen': 'pantalla', 'bezel': 'marco', 'body': 'cuerpo', 'led': 'LED', 'well': 'hueco'}


def card(d, x, y, title, scores, env, flags, v, parts):
    d.text((x, y), title, font=font(22, 'Medium'), fill=INK)
    y += 40
    worst = {'colour_v1_median': max(parts, key=lambda n: parts[n].get('median', 0)),
             'presence_min': min(parts, key=lambda n: parts[n].get('presence_min', 9))}
    for m, label, sub, dirn in AXES:
        bad = flags[m]
        d.text((x, y), ('FALLA · ' if bad else 'OK · ') + label, font=font(19, 'Medium'), fill=BAD if bad else OK)
        extra = f"  · peor: {PART_NAMES.get(worst[m], worst[m])}" if m in worst else ''
        d.text((x, y + 26), f"{sub}: {scores[m]:.3g}   (correcto: {'≥' if dirn == 'up' else '≤'} {env[m]:.3g}){extra}",
               font=font(15), fill=MUTED)
        y += 60
    d.text((x, y + 6), 'Veredicto (umbrales provisorios)', font=font(15), fill=MUTED)
    d.text((x, y + 28), v, font=font(21, 'Medium'), fill=BAD if v != 'publicar' else OK)


def main():
    product, view = 'lumen', 'front'
    ledger = [json.loads(l) for l in open(os.path.join(ROOT, 'runs', product, 'gen', 'ledger.jsonl'), encoding='utf-8')]
    g = {(x['view'], x['condition'], x['seed']): x for x in ledger}[(view, 'loose', 1)]
    env = envelope(product, view, g['colorway'])
    S, CARD, T = 430, 640, 44
    W, H = 2 * S + CARD + 60, 2 * (S + T) + 150
    sheet = Image.new('RGB', (W, H), SURFACE)
    d = ImageDraw.Draw(sheet)
    example = {'product': product, 'view': view, 'colorway': g['colorway'], 'condition': 'loose', 'seed': 1,
               'scene': g['scene'], 'envelope': env}
    runs = {r['id']: r for r in map(json.loads, open(os.path.join(ROOT, 'research', 'runs.jsonl'), encoding='utf-8'))}
    for i, (kind, title) in enumerate((('raw', 'Salida cruda del modelo'), ('final', 'Después de las guardas'))):
        img, ov, scores, parts = overlay(product, view, g['colorway'], os.path.join(ROOT, g[kind]))
        v, flags = verdict(scores, env)
        base = runs.get(f'gen-v1-{product}-{view}-loose-{kind}-s1', {})
        example[kind] = {'scores': {m: round(scores[m], 3) for m, *_ in AXES}, 'fails': sum(flags.values()),
                         'flags': flags, 'verdict': v, 'baseline_gate': base.get('gate_verdict'),
                         'worst_colour_part': max(parts, key=lambda n: parts[n].get('median', 0))}
        y = 20 + i * (S + T)
        crop = lambda im: im.crop((110, 80, 914, 944)).resize((S, int(S * 864 / 804)), Image.LANCZOS).crop((0, 0, S, S))
        sheet.paste(crop(img), (20, y + T))
        sheet.paste(crop(ov), (40 + S, y + T))
        d.text((20, y + 10), 'Foto', font=font(17, 'Medium'), fill=INK)
        d.text((40 + S, y + 10), 'Lo que marca el gate', font=font(17, 'Medium'), fill=INK)
        card(d, 60 + 2 * S, y + T, title, scores, env, flags, v, parts)
    ly = H - 100
    for k, (c, t) in enumerate(((RED, 'borde que no existe en el producto (inventado)'), (BLUE, 'borde del producto que falta'),
                                (ORANGE, 'pieza ausente'))):
        d.rectangle((20 + k * 470, ly, 44 + k * 470, ly + 18), fill=c)
        d.text((54 + k * 470, ly - 2), t, font=font(16), fill=INK)
    d.text((20, ly + 36), f"LUMEN · front · {g['colorway']} · control 0,5 · semilla 1 · escena {g['scene']}. Ejemplo fijado antes de mirar. "
           "Umbrales provisorios: el peor valor del producto correcto bajo 4 luces.", font=font(15), fill=MUTED)
    sheet.save(os.path.join(ROOT, 'research', 'img', 'gate_example.png'))
    path = os.path.join(ROOT, 'research', 'results.json')
    res = json.load(open(path, encoding='utf-8'))
    res['gate_example'] = example
    json.dump(res, open(path, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print('research/img/gate_example.png')


if __name__ == '__main__':
    main()
