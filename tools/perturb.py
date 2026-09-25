# Images whose right answer is known, because the fault is put in on purpose (research/PROTOCOL.md §7).
# Each one starts from the studio reference render of a product, view and colorway, and changes one thing.
# Some changes should fail a gate (an invented part, a missing part, a shifted colour, a typo, a warped shape);
# others should not (another background, another white balance, compression). A metric is sensitive if it moves
# with the first kind and robust if it stays still with the second.
# Usage: .venv/Scripts/python tools/perturb.py [<product> ...]
# Writes runs/<product>/perturb/<view>_<perturbation>_<colorway>.png and runs/<product>/perturb/labels.json
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
sys.path.insert(0, os.path.join(ROOT, 'metrics'))
from battery import on_grey  # noqa: E402
from consistency import part_masks  # noqa: E402
from qa import lab, rgb  # noqa: E402

VIEWS = {'lumen': ['front', 'right'], 'field16': ['front', 'right'], 'vela': ['front', 'back']}
HERO = {'lumen': 'body', 'field16': 'body', 'vela': 'body'}
# the part copied somewhere it does not belong (an invented button), and the part taken away (a missing one)
INVENT = {'lumen': 'ab', 'field16': 'dark', 'vela': 'keys'}
REMOVE = {'lumen': 'ab', 'field16': 'cap', 'vela': 'keys'}
rng = np.random.default_rng(0)


def mask_of(passes, view, size, name):
    return part_masks(passes, view, size).get(name)


def hue_shift(img, region, delta_e):
    """Rotate hue and push chroma inside the region until the median moves by about delta_e (CIE94-like units)."""
    g = lab(img)
    ab = g[..., 1:]
    chroma = np.hypot(ab[region][:, 0], ab[region][:, 1]).mean()
    if chroma < 4:  # a near-neutral part: tint it instead of rotating it
        g[..., 2] = np.where(region, g[..., 2] + delta_e, g[..., 2])
    else:
        ang = np.radians(delta_e / max(chroma, 1) * 57.3)
        a, b = ab[..., 0].copy(), ab[..., 1].copy()
        g[..., 1] = np.where(region, a * np.cos(ang) - b * np.sin(ang), a)
        g[..., 2] = np.where(region, a * np.sin(ang) + b * np.cos(ang), b)
    return rgb(g)


def invent_part(img, part, body):
    """Copy one instance of a part onto an empty stretch of the body: a button that was never designed."""
    arr = np.asarray(img).copy()
    n, lab_img, stats, _ = cv2.connectedComponentsWithStats(part.astype(np.uint8))
    if n < 2:
        return None
    k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, w, h = stats[k, :4]
    pad = 3
    patch = arr[y - pad:y + h + pad, x - pad:x + w + pad]
    pmask = (lab_img[y - pad:y + h + pad, x - pad:x + w + pad] == k)
    free = cv2.erode((body & ~part).astype(np.uint8), np.ones((h + 2 * pad + 20, w + 2 * pad + 20), np.uint8)) > 0
    ys, xs = np.where(free)
    if not len(ys):
        return None
    i = rng.integers(len(ys))
    cy, cx = ys[i] - (h + 2 * pad) // 2, xs[i] - (w + 2 * pad) // 2
    soft = cv2.GaussianBlur(cv2.dilate(pmask.astype(np.uint8) * 255, np.ones((3, 3), np.uint8)), (0, 0), 1.0)[..., None] / 255
    region = arr[cy:cy + patch.shape[0], cx:cx + patch.shape[1]]
    arr[cy:cy + patch.shape[0], cx:cx + patch.shape[1]] = (patch * soft + region * (1 - soft)).astype(np.uint8)
    return Image.fromarray(arr)


def remove_part(img, part):
    """Paint a part out with its surroundings, as if the model had forgotten it."""
    n, lab_img, stats, _ = cv2.connectedComponentsWithStats(part.astype(np.uint8))
    if n < 2:
        return None
    k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    hole = cv2.dilate((lab_img == k).astype(np.uint8) * 255, np.ones((7, 7), np.uint8))
    return Image.fromarray(cv2.inpaint(np.asarray(img), hole, 9, cv2.INPAINT_TELEA))


def warp(img, region, strength):
    """A smooth local bulge centred on the product: the silhouette mostly holds, the shape inside does not."""
    arr = np.asarray(img)
    h, w = arr.shape[:2]
    ys, xs = np.where(region)
    cy, cx = ys.mean(), xs.mean()
    rad = 0.35 * max(np.ptp(ys), np.ptp(xs))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dy, dx = yy - cy, xx - cx
    r = np.sqrt(dx ** 2 + dy ** 2)
    f = 1 - strength * np.exp(-(r / rad) ** 2)
    return Image.fromarray(cv2.remap(arr, (cx + dx * f).astype(np.float32), (cy + dy * f).astype(np.float32), cv2.INTER_LINEAR,
                                     borderMode=cv2.BORDER_REPLICATE))


def erase_text(img, passes, view, size):
    """Blank out the wordmark (or, on VELA's front, one line of the screen): text that went missing."""
    arr = np.asarray(img).copy()
    exact = np.asarray(Image.open(os.path.join(passes, view, 'mask_exact.png')).convert('L').resize(size)) > 127
    if not exact.any():
        return None
    ys, xs = np.where(exact)
    y0, y1 = ys.min(), ys.max()
    band = slice(int(y0 + (y1 - y0) * 0.45), int(y0 + (y1 - y0) * 0.52))   # one horizontal band through the text
    sel = np.zeros_like(exact)
    sel[band] = exact[band]
    hole = cv2.dilate(sel.astype(np.uint8) * 255, np.ones((3, 3), np.uint8))
    return Image.fromarray(cv2.inpaint(arr, hole, 5, cv2.INPAINT_TELEA))


def typo_screen(img, passes, view, size):
    """VELA only: redraw the screen with one letter changed ("Messages" -> "Messagas") and put it back in place."""
    here = os.path.join(ROOT, 'fixtures', 'vela')
    sys.path.insert(0, here)
    import screen as sc
    orig = sc.draw()
    items = sc.ITEMS
    sc.ITEMS = [(('Messagas' if l == 'Messages' else l), v) for l, v in items]
    bad = sc.draw()
    sc.ITEMS = items
    part = mask_of(passes, view, size, 'screen')
    if part is None:
        return None
    cnts, _ = cv2.findContours(part.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    quad = cv2.boxPoints(cv2.minAreaRect(max(cnts, key=cv2.contourArea)))
    quad = quad[np.lexsort((quad[:, 0], quad[:, 1]))]            # top two, then bottom two
    tl, tr = sorted(quad[:2], key=lambda p: p[0])
    bl, br = sorted(quad[2:], key=lambda p: p[0])
    src = np.float32([[0, 0], [bad.size[0], 0], [bad.size[0], bad.size[1]], [0, bad.size[1]]])
    M = cv2.getPerspectiveTransform(src, np.float32([tl, tr, br, bl]))
    # only the letters the typo changes are rewritten, in the paper and ink tones the render itself has there
    changed = np.any(np.asarray(bad) != np.asarray(orig), -1).astype(np.uint8) * 255
    changed = cv2.dilate(changed, np.ones((25, 25), np.uint8))
    scale = bad.size[0] / max(np.linalg.norm(tr - tl), 1)            # texture pixels per image pixel
    ink = (float(sc.PAPER[0]) - np.asarray(bad.convert('L')).astype(np.float32)) / (sc.PAPER[0] - sc.INK[0])
    ink = cv2.GaussianBlur(np.clip(ink, 0, 1), (0, 0), 0.5 * scale)   # as soft as the render draws it
    alpha = cv2.warpPerspective(ink, M, size, flags=cv2.INTER_LINEAR)[..., None]
    where = ((cv2.warpPerspective(changed, M, size) > 0) & part)
    arr = np.asarray(img).astype(float)
    lum = arr.mean(-1)[where]
    paper_c = arr[where][lum >= np.percentile(lum, 90)].mean(0)
    ink_c = arr[where][lum <= np.percentile(lum, 3)].mean(0)
    redrawn = paper_c + (ink_c - paper_c) * alpha
    out = np.where(where[..., None], redrawn, arr)
    return Image.fromarray(out.astype(np.uint8))


def background(img, mask):
    arr = np.asarray(img).copy()
    arr[~mask] = (96, 110, 124)
    return Image.fromarray(arr)


def white_balance(img):
    arr = np.asarray(img).astype(float) * np.array([1.06, 1.0, 0.9])
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def jpeg(img, path):
    img.save(path, quality=35)
    return Image.open(path).convert('RGB')


def run(product):
    spec = json.load(open(os.path.join(ROOT, 'products', product, 'product.json'), encoding='utf-8'))
    passes = os.path.join(ROOT, 'runs', product, 'passes')
    size = tuple(json.load(open(os.path.join(passes, 'manifest.json')))['size_px'])
    out = os.path.join(ROOT, 'runs', product, 'perturb')
    os.makedirs(out, exist_ok=True)
    labels = {}
    for view in VIEWS[product]:
        mask = np.asarray(Image.open(os.path.join(passes, view, 'mask.png')).convert('L').resize(size)) > 127
        body = mask_of(passes, view, size, HERO[product])
        for cw in spec['colorways']:
            ref = on_grey(os.path.join(passes, view, f'beauty_{cw}.png'), size)
            made = {
                'hue2': ('pass', hue_shift(ref, body, 2)), 'hue5': ('border', hue_shift(ref, body, 5)),
                'hue10': ('fail', hue_shift(ref, body, 10)),
                'invent': ('fail', invent_part(ref, mask_of(passes, view, size, INVENT[product]), body)),
                'remove': ('fail', remove_part(ref, mask_of(passes, view, size, REMOVE[product]))),
                'erasetext': ('fail', erase_text(ref, passes, view, size)),
                'warp10': ('fail', warp(ref, mask, 0.10)), 'warp25': ('fail', warp(ref, mask, 0.25)),
                'background': ('pass', background(ref, mask)), 'whitebalance': ('pass', white_balance(ref)),
                'jpeg': ('pass', jpeg(ref, os.path.join(out, '_tmp.jpg'))),
            }
            if product == 'vela' and view == 'front':
                made['typo'] = ('fail', typo_screen(ref, passes, view, size))
            for name, (expected, im) in made.items():
                if im is None:
                    print('skipped', product, view, cw, name)
                    continue
                path = os.path.join(out, f'{view}_{name}_{cw}.png')
                im.save(path)
                labels[os.path.basename(path)] = {'view': view, 'colorway': cw, 'perturbation': name, 'expected': expected}
            ref.save(os.path.join(out, f'{view}_none_{cw}.png'))
            labels[f'{view}_none_{cw}.png'] = {'view': view, 'colorway': cw, 'perturbation': 'none', 'expected': 'pass'}
    if os.path.exists(os.path.join(out, '_tmp.jpg')):
        os.remove(os.path.join(out, '_tmp.jpg'))
    json.dump(labels, open(os.path.join(out, 'labels.json'), 'w'), indent=2)
    print(product, len(labels), 'images')


if __name__ == '__main__':
    for p in sys.argv[1:] or list(VIEWS):
        run(p)
