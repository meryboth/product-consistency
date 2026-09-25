# Phase 3 without human labels (PROTOCOL.md, change of 2026-09-25): two VLM judges from different families label
# every phase-2 photo with the same brief the labelling page gave. Each call sees one image: the reference render of
# the right product on the left and the photo on the right, nothing about the condition, seed or metrics.
# Paid, through the Comfy API partner nodes: runs only with --spend and a COMFY_API_KEY, like pipeline/generate.py.
# Usage: py tools/vlm_judge.py [--judges gemini,gpt] [--limit N] [--spend]
#   without --spend it prints the plan and the prompt, and sends nothing
# Answers go to research/labels/vlm.jsonl, one line per (image, judge); already judged pairs are skipped.
import hashlib
import json
import os
import random
import re
import sys
import time
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
import generate  # noqa: E402  (the ComfyUI client and the Comfy key handling)

OUT = os.path.join(ROOT, 'research', 'labels', 'vlm.jsonl')
FONT = os.path.join(ROOT, 'brands', 'meridian', 'fonts', 'InterTight.ttf')
JUDGES = {'gemini': ('GeminiNode', {'model': 'gemini-3-1-pro', 'seed': 7}),
          'gpt': ('OpenAIChatNode', {'model': 'gpt-5.5', 'persist_context': False})}

BRIEF = """You are a product designer checking generated product photos for a campaign.
The image has two panels. LEFT: the reference render, which shows the product exactly as designed.
RIGHT: a generated photo that is supposed to show that same product.
Judge ONLY the product in the RIGHT panel against the LEFT one. Ignore the background, the scene, the lighting,
shadows, reflections and photographic style: a different light is fine. Small rendering differences are fine.

The product: {name}, a {category}. Colorway: {colorway}.
Designed facts: {facts}
{text_block}
Answer these questions about the RIGHT panel:
- shape: is any part invented, missing, duplicated or deformed (buttons, keys, grilles, dials, lenses, holes, outline)?
- colour: does any part have the wrong colour (after allowing for the scene light)?
- text: is any printed text, screen content or logo wrong, garbled, missing or invented?
- other: any other problem with the product itself?
- publish: would you publish this photo in the product's campaign as it is?

Reply with JSON only, no other text:
{{"shape": true|false, "colour": true|false, "text": true|false, "other": true|false, "publish": true|false, "reason": "<one short sentence>"}}
where true means the problem IS present (for publish, true means yes, publish it)."""


def items():
    rows = []
    for product in ('lumen', 'field16', 'vela'):
        spec = json.load(open(os.path.join(ROOT, 'products', product, 'product.json'), encoding='utf-8'))
        ledger = {}
        for g in map(json.loads, open(os.path.join(ROOT, 'runs', product, 'gen', 'ledger.jsonl'), encoding='utf-8')):
            ledger[(g['view'], g['condition'], g['seed'])] = g
        for g in ledger.values():
            for kind in ('raw', 'final'):
                rows.append({'id': hashlib.sha1(g[kind].encode()).hexdigest()[:12], 'product': product, 'spec': spec,
                             'path': g[kind], 'view': g['view'], 'colorway': g['colorway'],
                             'ref': f"runs/{product}/passes/{g['view']}/beauty_{g['colorway']}.png"})
    random.Random(11).shuffle(rows)
    return rows


def panel(item, size=768):
    """Reference left, photo right, on one canvas; both on the same grey, labelled."""
    ref = Image.open(os.path.join(ROOT, item['ref'])).convert('RGBA')
    bg = Image.new('RGBA', ref.size, (200, 200, 198, 255))
    bg.alpha_composite(ref)
    left, right = bg.convert('RGB').resize((size, size)), Image.open(os.path.join(ROOT, item['path'])).convert('RGB').resize((size, size))
    im = Image.new('RGB', (2 * size + 24, size + 44), (255, 255, 255))
    im.paste(left, (0, 44))
    im.paste(right, (size + 24, 44))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, 26)
    d.text((10, 8), 'LEFT: reference (correct product)', font=f, fill=(0, 0, 0))
    d.text((size + 34, 8), 'RIGHT: photo to judge', font=f, fill=(0, 0, 0))
    return im


def prompt(item):
    spec = item['spec']
    side = 'screen' if item['view'] == 'front' else 'back'
    lines = spec.get('text_primary', {}).get(side) or []
    text_block = ('The large text that must read exactly, visible in this view: ' + ' | '.join(lines) + '\n') if lines else ''
    return BRIEF.format(name=spec['name'], category=spec.get('category', 'product'), colorway=item['colorway'].replace('-', ' '),
                        facts='; '.join(spec.get('facts', [])), text_block=text_block)


def ask(judge, item):
    node, params = JUDGES[judge]
    name = generate.upload(panel(item), f"judge_{item['id']}.png")
    g = {'img': {'class_type': 'LoadImage', 'inputs': {'image': name}},
         'ask': {'class_type': node, 'inputs': {'prompt': prompt(item), 'images': ['img', 0], **params}},
         'show': {'class_type': 'PreviewAny', 'inputs': {'source': ['ask', 0]}}}
    body = {'prompt': g, 'client_id': 'product-consistency'}
    if os.environ.get('COMFY_API_KEY'):
        body['extra_data'] = {'api_key_comfy_org': os.environ['COMFY_API_KEY']}
    req = urllib.request.Request(f'{generate.COMFY}/prompt', json.dumps(body).encode(), {'Content-Type': 'application/json'})
    pid = json.load(urllib.request.urlopen(req))['prompt_id']
    while True:
        time.sleep(2)
        h = json.load(urllib.request.urlopen(f'{generate.COMFY}/history/{pid}'))
        if pid in h:
            st = h[pid].get('status', {})
            if st.get('status_str') == 'error':
                return None, json.dumps(st.get('messages', []))[:800]
            out = h[pid]['outputs'].get('show', {})
            text = out.get('text') or out.get('string') or []
            return (text[0] if isinstance(text, list) and text else str(text)), None


def parse(text):
    m = re.search(r'\{.*\}', text or '', re.S)
    try:
        d = json.loads(m.group(0)) if m else None
        return {k: bool(d[k]) for k in ('shape', 'colour', 'text', 'other', 'publish')} | {'reason': str(d.get('reason', ''))[:300]} if d else None
    except (ValueError, KeyError, TypeError):
        return None


def main():
    args = sys.argv[1:]
    judges = (args[args.index('--judges') + 1] if '--judges' in args else 'gemini,gpt').split(',')
    limit = int(args[args.index('--limit') + 1]) if '--limit' in args else None
    todo = items()[:limit] if limit else items()
    done = set()
    if os.path.exists(OUT):
        done = {(r['id'], r['judge']) for r in map(json.loads, open(OUT, encoding='utf-8')) if r.get('parsed')}
    plan = [(i, j) for i in todo for j in judges if (i['id'], j) not in done]
    print(f'{len(plan)} calls planned ({len(todo)} images x {judges}); {len(done)} already done')
    if '--spend' not in args:
        print('\n--- prompt for the first image ---\n' + prompt(todo[0]))
        panel(todo[0]).save(os.path.join(ROOT, 'runs', '_judge_panel_example.png'))
        print('\nexample panel: runs/_judge_panel_example.png\nnothing sent; add --spend to run (paid).')
        return
    if not os.environ.get('COMFY_API_KEY'):
        raise SystemExit('Paid nodes need COMFY_API_KEY (or ~/.comfy_api_key).')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'a', encoding='utf-8') as f:
        for item, judge in plan:
            t0 = time.time()
            text, err = ask(judge, item)
            row = {'id': item['id'], 'path': item['path'], 'product': item['product'], 'judge': judge,
                   'model': JUDGES[judge][1]['model'], 'raw': text, 'error': err, 'parsed': parse(text),
                   'seconds': round(time.time() - t0, 1), 'at': time.strftime('%Y-%m-%d %H:%M:%S')}
            f.write(json.dumps(row) + '\n')
            f.flush()
            print(judge, item['id'], item['path'].split('/')[-1], row['parsed'] or err or text, flush=True)


if __name__ == '__main__':
    main()
