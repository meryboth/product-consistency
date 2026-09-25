# Phase 2: real generations with natural faults, from From CAD to Shelf's local graph (RealVisXL + ControlNet Union,
# SDXL Lightning 8 steps), unchanged. The control is loosened on purpose, so the set holds good photos and bad ones:
#   full   the scene as it ships (depth 0.95, normal 0.60, denoise 0.62)
#   mid    halfway (depth 0.75, normal 0.42, denoise 0.74)
#   loose  the published ablation's "ControlNet at half strength" (depth 0.55, normal 0.25, denoise 0.85)
# Each generation is saved twice: raw, and finished by generate.finish (the guards: colour, detail, locked parts).
# Seeds 1-5; the colorway and the scene rotate with the seed, the same way in every condition, so runs pair by
# (product, view, seed). Resumable: files already there are skipped.
# Usage: py tools/generate_local.py [<product> ...] [--only-seed N]    (ComfyUI must be running)
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
import generate  # noqa: E402

VIEWS = {'lumen': ['front', 'right'], 'field16': ['front', 'right'], 'vela': ['front', 'back']}
STRENGTH = {'full': {}, 'mid': {'depth': 0.75, 'normal': 0.42, 'denoise': 0.74},
            'loose': {'depth': 0.55, 'normal': 0.25, 'denoise': 0.85}}
SEEDS = [1, 2, 3, 4, 5]
SCENES = ['studio-paper', 'concrete-desk']


def plan(seed, colorways):
    return colorways[seed % 2], SCENES[(seed // 2) % 2]


def run(product, only_seed=None):
    spec = json.load(open(os.path.join(ROOT, 'products', product, 'product.json'), encoding='utf-8'))
    scenes = json.load(open(os.path.join(ROOT, 'brands', 'meridian', 'scenes.json'), encoding='utf-8'))
    passes = os.path.join(ROOT, 'runs', product, 'passes')
    out = os.path.join(ROOT, 'runs', product, 'gen')
    os.makedirs(out, exist_ok=True)
    ledger = open(os.path.join(out, 'ledger.jsonl'), 'a', encoding='utf-8')
    cws = list(spec['colorways'])
    for seed in SEEDS:
        if only_seed and seed != only_seed:
            continue
        cw, scene_id = plan(seed, cws)
        for view in VIEWS[product]:
            for cond, tweak in STRENGTH.items():
                name = f'{view}_{cond}_{cw}_{scene_id}_s{seed}'
                raw_path, fin_path = os.path.join(out, name + '_raw.png'), os.path.join(out, name + '_final.png')
                if os.path.exists(raw_path) and os.path.exists(fin_path):
                    continue
                scene = {**scenes[scene_id], **tweak}
                t0 = time.time()
                raw, prompt = generate.local_sdxl(passes, view, cw, scene, spec, seed)
                seconds = round(time.time() - t0, 1)
                raw.save(raw_path)
                generate.finish(raw, passes, view, cw, spec).save(fin_path)
                row = {'product': product, 'view': view, 'condition': cond, 'colorway': cw, 'scene': scene_id,
                       'seed': seed, 'seconds': seconds, 'usd': 0.0, 'prompt': prompt,
                       'control': {k: scene.get(k) for k in ('depth', 'depth_end', 'normal', 'denoise')},
                       'raw': os.path.relpath(raw_path, ROOT).replace(os.sep, '/'),
                       'final': os.path.relpath(fin_path, ROOT).replace(os.sep, '/'), 'at': time.strftime('%Y-%m-%d %H:%M:%S')}
                ledger.write(json.dumps(row) + '\n')
                ledger.flush()
                print(product, name, seconds, 's', flush=True)


if __name__ == '__main__':
    args = sys.argv[1:]
    only = int(args[args.index('--only-seed') + 1]) if '--only-seed' in args else None
    products = [a for a in args if a in VIEWS] or list(VIEWS)
    for p in products:
        run(p, only)
