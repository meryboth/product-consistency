# Phase 1: measure every image whose answer is known — the real-variation renders (always "pass") and the
# perturbations (labels.json) — with both the baseline gate (qa.check, unchanged) and the battery (metrics/battery.py).
# Usage: .venv/Scripts/python tools/measure_known.py [<product> ...]
# Appends one line per image to research/runs.jsonl. Old lines are never rewritten.
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
sys.path.insert(0, os.path.join(ROOT, 'metrics'))
import battery  # noqa: E402
import qa  # noqa: E402

VIEWS = {'lumen': ['front', 'right'], 'field16': ['front', 'right'], 'vela': ['front', 'back']}
VERSION = 'v1'  # v0 metrics + colour/presence v1 (light cast removed) + v2 (contrast ratios) + primary CER
COMMIT = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def images(product):
    """(file, view, colorway, source, condition, expected) for every known-answer image of a product."""
    judged = os.path.join(ROOT, 'runs', product, 'variation', '_judged')
    for f in sorted(os.listdir(judged)):
        view, light, cw = f[:-4].split('_', 2)
        yield os.path.join(judged, f), view, cw, 'variation', f'light/{light}', 'pass'
    pert = os.path.join(ROOT, 'runs', product, 'perturb')
    for f, lab in sorted(json.load(open(os.path.join(pert, 'labels.json'))).items()):
        yield os.path.join(pert, f), lab['view'], lab['colorway'], 'perturb', f"perturb/{lab['perturbation']}", lab['expected']


def run(product, log):
    spec = json.load(open(os.path.join(ROOT, 'products', product, 'product.json'), encoding='utf-8'))
    passes = os.path.join(ROOT, 'runs', product, 'passes')
    for path, view, cw, source, condition, expected in images(product):
        t0 = time.time()
        gate = qa.check(passes, path, cw, spec, path)
        scores, parts = battery.measure(product, view, cw, path, passes)
        row = {'id': f'known-{VERSION}-{product}-{view}-{cw}-{condition.replace("/", "-")}', 'study': 'A', 'source': source,
               'condition': condition, 'case': product, 'view': view, 'colorway': cw, 'seed': None,
               'expected': expected, 'gate_verdict': gate['verdict'],
               'metrics': {'gate_colour': gate['delta_e']['colour'], 'gate_parts': gate['delta_e']['parts'], **scores},
               'parts': parts, 'time_s': round(time.time() - t0, 2), 'cost_usd': 0.0, 'status': 'ok',
               'commit': COMMIT, 'judges': f'baseline-gate@64caef5 + battery-{VERSION}',
               'output': os.path.relpath(path, ROOT).replace(os.sep, '/'),
               'note': 'typo also shifts the two new letters ~2 px' if condition.endswith('typo') else ''}
        log.write(json.dumps(row) + '\n')
        log.flush()
        print(product, view, cw, condition, expected, gate['verdict'],
              {k: scores[k] for k in ('edge_precision', 'edge_recall', 'colour_worst_p95', 'dreamsim') if k in scores},
              scores.get('cer_primary_worst', ''), flush=True)


if __name__ == '__main__':
    with open(os.path.join(ROOT, 'research', 'runs.jsonl'), 'a', encoding='utf-8') as log:
        for p in sys.argv[1:] or list(VIEWS):
            run(p, log)
