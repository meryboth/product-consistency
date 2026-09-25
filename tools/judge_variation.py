# Judge the real-variation images (tools/variation.py) with the baseline gate, qa.check from From CAD to Shelf,
# unchanged. Every image is the right product under another light, so the right answer is always "publish":
# anything else is a false rejection, and tells us how much of the gate's scale the light alone uses up.
# Usage: py tools/judge_variation.py [<product> ...]
# Appends one line per image to research/runs.jsonl (the research-rigor format) and never rewrites old lines.
import json
import os
import subprocess
import sys
import time

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
import consistency  # noqa: E402
import qa  # noqa: E402

VIEWS = {'lumen': ['front', 'right'], 'field16': ['front', 'right'], 'vela': ['front', 'back']}
COMMIT = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def on_grey(path, grey=(200, 200, 198)):
    im = Image.open(path).convert('RGBA')
    bg = Image.new('RGBA', im.size, (*grey, 255))
    bg.alpha_composite(im)
    return bg.convert('RGB')


def judge(product, log):
    spec = json.load(open(os.path.join(ROOT, 'products', product, 'product.json'), encoding='utf-8'))
    passes = os.path.join(ROOT, 'runs', product, 'passes')             # the reference: the studio light
    var = os.path.join(ROOT, 'runs', product, 'variation')
    out = os.path.join(var, '_judged')
    os.makedirs(out, exist_ok=True)
    for light in sorted(os.listdir(var)):
        if light.startswith('_'):
            continue
        for view in VIEWS[product]:
            for cw in spec['colorways']:
                src = os.path.join(var, light, view, f'beauty_{cw}.png')
                if not os.path.exists(src):
                    continue
                # qa reads the view from the start of the file name, so it leads
                img = os.path.join(out, f'{view}_{light}_{cw}.png')
                on_grey(src).save(img)
                t0 = time.time()
                v = qa.check(passes, img, cw, spec, img)
                parts = consistency.measure(passes, cw, spec, [img])
                row = {'id': f'var-{product}-{view}-{cw}-{light}', 'study': 'A', 'condition': f'real-variation/{light}',
                       'judge': 'baseline-gate (qa.check @64caef5)', 'case': product, 'view': view, 'colorway': cw,
                       'seed': None, 'expected': 'publish', 'verdict': v['verdict'],
                       'metrics': {'colour_delta_e': v['delta_e']['colour'], 'parts_delta_e': v['delta_e']['parts'],
                                   'worst_part_to_spec': max((p['to_spec'] for p in parts['parts'].values()), default=0.0)},
                       'time_s': round(time.time() - t0, 2), 'cost_usd': 0.0, 'status': 'ok', 'commit': COMMIT,
                       'output': os.path.relpath(img, ROOT).replace(os.sep, '/'), 'note': ''}
                log.write(json.dumps(row) + '\n')
                print(product, view, cw, light, v['verdict'], v['delta_e'])


if __name__ == '__main__':
    with open(os.path.join(ROOT, 'research', 'runs.jsonl'), 'a', encoding='utf-8') as log:
        for p in sys.argv[1:] or list(VIEWS):
            judge(p, log)
