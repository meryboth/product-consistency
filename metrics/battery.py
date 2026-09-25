# The per-region battery of Study A (research/PROTOCOL.md §5). Everything is measured inside the product, and every
# axis is measured from both sides: what went missing and what got invented.
#   edges      precision (photo edges that are not on the product: invented buttons, grilles, letters)
#              recall    (product edges missing from the photo)
#   colour     per part, hue and chroma against the spec (qa.chroma_delta, the same scale as the baseline gate),
#              per pixel: the median, the 95th percentile, and the share of pixels out of tolerance
#   identity   DINOv2 cosine and DreamSim distance between the product crops, both on the same grey
#   text       character error rate of an OCR reading against product.json -> text (only for products with text)
# The camera must match the passes (the local graph keeps it pixel for pixel; paid backends need registering first).
# Runs in the metrics environment: .venv/Scripts/python metrics/battery.py <product> <view> <colorway> <image>
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
from consistency import part_masks, targets  # noqa: E402
from qa import lab  # noqa: E402

GREY = (200, 200, 198)
EDGE_TOL_PX = 2          # an edge counts as matched within this many pixels (PROTOCOL.md §5)
COLOUR_TOL = 10.0        # hue-chroma delta above which a pixel is "out of tolerance"; calibrated in phase 3


# ---------- loading ----------
def load_mask(passes, view, name, size):
    return np.asarray(Image.open(os.path.join(passes, view, name)).convert('L').resize(size, Image.NEAREST)) > 127


def on_grey(path, size=None):
    im = Image.open(path).convert('RGBA')
    bg = Image.new('RGBA', im.size, (*GREY, 255))
    bg.alpha_composite(im)
    im = bg.convert('RGB')
    return im.resize(size, Image.LANCZOS) if size and im.size != size else im


# ---------- edges ----------
def reference_edges(passes, view, colorway, size):
    """Where the product has an edge: creases in the normals, steps in the depth, borders between parts,
    and the printed detail of the studio render (type, screen, grilles), which geometry alone does not have."""
    n = np.asarray(Image.open(os.path.join(passes, view, 'normal.png')).convert('RGB').resize(size, Image.NEAREST)).astype(float) / 127.5 - 1
    n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-6
    crease = np.zeros(size[::-1], bool)
    for dy, dx in ((0, 1), (1, 0)):
        dot = (n * np.roll(n, (dy, dx), (0, 1))).sum(-1)
        crease |= dot < np.cos(np.radians(30))
    depth = np.asarray(Image.open(os.path.join(passes, view, 'depth.png')).convert('L').resize(size, Image.NEAREST)).astype(float)
    step = (np.abs(np.gradient(depth)[0]) + np.abs(np.gradient(depth)[1])) > 6
    parts = np.asarray(Image.open(os.path.join(passes, view, 'mask_parts.png')).convert('RGB').resize(size, Image.NEAREST)).astype(int)
    border = (np.abs(np.diff(parts, axis=0, prepend=parts[:1])).sum(-1) > 30) | (np.abs(np.diff(parts, axis=1, prepend=parts[:, :1])).sum(-1) > 30)
    ref = np.asarray(on_grey(os.path.join(passes, view, f'beauty_{colorway}.png'), size).convert('L'))
    printed = cv2.Canny(cv2.GaussianBlur(ref, (0, 0), 1.2), 40, 110) > 0
    return crease | step | border | printed


def photo_edges(img):
    g = np.asarray(img.convert('L'))
    return cv2.Canny(cv2.GaussianBlur(g, (0, 0), 1.2), 40, 110) > 0


def edge_scores(passes, view, colorway, img):
    size = img.size
    mask = load_mask(passes, view, 'mask.png', size)
    inside = cv2.erode(mask.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0   # the silhouette itself is scored by IoU
    ref, pho = reference_edges(passes, view, colorway, size) & inside, photo_edges(img) & inside
    near = lambda e: cv2.distanceTransform((~e).astype(np.uint8), cv2.DIST_L2, 3) <= EDGE_TOL_PX
    precision = float((pho & near(ref)).sum() / max(pho.sum(), 1))
    recall = float((ref & near(pho)).sum() / max(ref.sum(), 1))
    return {'edge_precision': round(precision, 4), 'edge_recall': round(recall, 4),
            'edge_f1': round(2 * precision * recall / max(precision + recall, 1e-9), 4)}


# ---------- colour ----------
def chroma_delta_map(g, target):
    """qa.chroma_delta, per pixel: CIE94 without lightness, against one target colour."""
    c1, c2 = np.hypot(g[..., 1], g[..., 2]), np.hypot(target[1], target[2])
    dc = c1 - c2
    dh2 = np.maximum((g[..., 1] - target[1]) ** 2 + (g[..., 2] - target[2]) ** 2 - dc ** 2, 0)
    return np.sqrt((dc / (1 + 0.045 * c2)) ** 2 + dh2 / (1 + 0.015 * c2) ** 2)


def colour_scores(passes, view, colorway, spec, img):
    g = lab(img)
    parts, worst_p95, worst_out = {}, 0.0, 0.0
    for name, (target, mask) in targets(passes, view, colorway, spec, img.size).items():
        m = cv2.erode(mask.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0   # part borders mix two colours
        if m.sum() < 50:
            continue
        d = chroma_delta_map(g[m], target)
        row = {'median': round(float(np.median(d)), 2), 'p95': round(float(np.percentile(d, 95)), 2),
               'out': round(float((d > COLOUR_TOL).mean()), 4)}
        parts[name] = row
        worst_p95, worst_out = max(worst_p95, row['p95']), max(worst_out, row['out'])
    return {'colour_worst_p95': round(worst_p95, 2), 'colour_worst_out': round(worst_out, 4)}, parts


# ---------- identity ----------
_models = {}


def _crop(passes, view, img):
    mask = load_mask(passes, view, 'mask.png', img.size)
    ys, xs = np.where(mask)
    pad = 8
    box = (max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, img.size[0]), min(ys.max() + pad, img.size[1]))
    grey = Image.new('RGB', img.size, GREY)
    only = Image.composite(img, grey, Image.fromarray((mask * 255).astype(np.uint8)))
    return only.crop(box)


def identity_scores(passes, view, colorway, img):
    import torch
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    if 'dino' not in _models:
        from transformers import AutoImageProcessor, AutoModel
        _models['dino'] = (AutoImageProcessor.from_pretrained('facebook/dinov2-base'),
                           AutoModel.from_pretrained('facebook/dinov2-base').to(dev).eval())
        from dreamsim import dreamsim
        _models['dreamsim'] = dreamsim(pretrained=True, device=dev, cache_dir=os.path.join(ROOT, '.cache', 'dreamsim'))
    ref = on_grey(os.path.join(passes, view, f'beauty_{colorway}.png'), img.size)
    a, b = _crop(passes, view, img), _crop(passes, view, ref)
    proc, dino = _models['dino']
    with torch.no_grad():
        feats = dino(**proc(images=[a, b], return_tensors='pt').to(dev)).last_hidden_state[:, 0]
        cos = torch.nn.functional.cosine_similarity(feats[0:1], feats[1:2]).item()
        ds_model, ds_pre = _models['dreamsim']
        dist = ds_model(ds_pre(a).to(dev), ds_pre(b).to(dev)).item()
    return {'dino_cos': round(cos, 4), 'dreamsim': round(dist, 4)}


# ---------- text ----------
def cer(a, b):
    """Levenshtein distance / length of the reference b."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1] / max(len(b), 1)


def substring_cer(text, line):
    """How far `line` is from its best match anywhere inside `text` (edits / len(line)): the OCR may split a line
    into words or merge two lines, so the reference is searched for, not compared line to line."""
    prev = [0] * (len(text) + 1)                       # a match may start anywhere in the text for free
    for i, cl in enumerate(line, 1):
        cur = [i]
        for j, ct in enumerate(text, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (cl != ct)))
        prev = cur
    return min(prev) / max(len(line), 1)


def read_lines(img):
    if 'ocr' not in _models:
        from doctr.models import ocr_predictor
        _models['ocr'] = ocr_predictor(pretrained=True)
    page = _models['ocr']([np.asarray(img)]).pages[0]
    return [' '.join(w.value for w in line.words) for block in page.blocks for line in block.lines]


def _deskew(passes, view, img):
    """The product crop, turned so the printed lines run level. The angle comes from the part that carries the
    printed type in the parts map (`print`), measured on the render, never on the photo being judged."""
    crop = _crop(passes, view, img)
    size = img.size
    printed = part_masks(passes, view, size).get('print')
    if printed is None or printed.sum() < 30:
        return crop
    ys, xs = np.where(printed)
    (vx, vy), _ = np.polyfit(xs, ys, 1), None                     # slope of the line of print, in image space
    angle = np.degrees(np.arctan(vx))
    return crop.rotate(angle, resample=Image.BICUBIC, expand=True, fillcolor=GREY) if abs(angle) > 1 else crop


def text_scores(passes, view, spec, img):
    """Each line the spec prints on this side, matched to the OCR line that reads closest to it."""
    truth = spec.get('text', {}).get('screen' if view == 'front' else 'back', [])
    if not truth:
        return {}
    crop = _deskew(passes, view, img)
    crop = crop.resize((crop.size[0] * 2, crop.size[1] * 2), Image.LANCZOS)   # small type reads better upscaled
    found = ' '.join(read_lines(crop)).lower()
    # word by word, in any order: the OCR may split, merge or reorder lines, and that is not the product's fault
    per_line = []
    for t in truth:
        words = t.lower().split()
        per_line.append(sum(substring_cer(found, w) * len(w) for w in words) / max(sum(map(len, words)), 1))
    # invented text: words the OCR reads that are in no reference line (a precision-side check for type)
    vocab = {w for t in truth for w in t.lower().split()}
    extra = [w for w in found.split() if len(w) > 2 and min((cer(w, v) for v in vocab), default=1) > 0.34]
    return {'cer_mean': round(float(np.mean(per_line)), 4), 'cer_worst': round(float(np.max(per_line)), 4),
            'lines_read': int(sum(c <= 0.2 for c in per_line)), 'lines_total': len(truth), 'words_extra': len(extra),
            'ocr_text': found}


# ---------- all of it ----------
def measure(product, view, colorway, image, passes=None, identity=True, text=True):
    spec = json.load(open(os.path.join(ROOT, 'products', product, 'product.json'), encoding='utf-8'))
    passes = passes or os.path.join(ROOT, 'runs', product, 'passes')
    size = tuple(json.load(open(os.path.join(passes, 'manifest.json')))['size_px'])
    img = on_grey(image, size)
    out = {**edge_scores(passes, view, colorway, img)}
    colour, parts = colour_scores(passes, view, colorway, spec, img)
    out.update(colour)
    if identity:
        out.update(identity_scores(passes, view, colorway, img))
    if text:
        out.update(text_scores(passes, view, spec, img))
    return out, parts


if __name__ == '__main__':
    scores, parts = measure(*sys.argv[1:5])
    print(json.dumps({'scores': scores, 'parts': parts}, indent=2))
