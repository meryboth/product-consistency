# Phase 2 measurement: every generated photo (raw and finished) judged by the baseline gate and by the battery.
# The baseline gate is used the way From CAD to Shelf uses it: colour on the raw photo, parts on the finished one.
# Usage: .venv/Scripts/python tools/measure_gen.py [<product> ...]
# Appends one line per image to research/runs.jsonl; images already measured (same id) are skipped.
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

VERSION = 'v1'
COMMIT = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
LOG = os.path.join(ROOT, 'research', 'runs.jsonl')


def main(products):
    seen = {json.loads(l)['id'] for l in open(LOG, encoding='utf-8')} if os.path.exists(LOG) else set()
    with open(LOG, 'a', encoding='utf-8') as log:
        for product in products:
            spec = json.load(open(os.path.join(ROOT, 'products', product, 'product.json'), encoding='utf-8'))
            passes = os.path.join(ROOT, 'runs', product, 'passes')
            ledger = os.path.join(ROOT, 'runs', product, 'gen', 'ledger.jsonl')
            # a duplicate generator ran in parallel for a while (2026-09-25): the same image was generated twice and the
            # later entry wins; those rows keep a note, since their time was measured on a shared GPU
            entries = {}
            for g in map(json.loads, open(ledger, encoding='utf-8')):
                k = (g['view'], g['condition'], g['seed'])
                g['dup'] = k in entries
                entries[k] = g
            for g in entries.values():
                raw, final = os.path.join(ROOT, g['raw']), os.path.join(ROOT, g['final'])
                gate = qa.check(passes, raw, g['colorway'], spec, final)          # as the pipeline runs it
                for kind, path in (('raw', raw), ('final', final)):
                    rid = f"gen-{VERSION}-{product}-{g['view']}-{g['condition']}-{kind}-s{g['seed']}"
                    if rid in seen:
                        continue
                    t0 = time.time()
                    scores, parts = battery.measure(product, g['view'], g['colorway'], path, passes)
                    ocr = scores.pop('ocr_text', None)
                    row = {'id': rid, 'study': 'A', 'source': 'generated', 'condition': f"{g['condition']}/{kind}",
                           'case': product, 'view': g['view'], 'colorway': g['colorway'], 'scene': g['scene'],
                           'seed': g['seed'], 'gate_verdict': gate['verdict'],
                           'metrics': {'gate_colour': gate['delta_e']['colour'], 'gate_parts': gate['delta_e']['parts'], **scores},
                           'parts': parts, 'ocr_text': ocr, 'time_s': round(time.time() - t0, 2),
                           'gen_seconds': g['seconds'], 'cost_usd': 0.0, 'status': 'ok', 'commit': COMMIT,
                           'judges': f'baseline-gate@64caef5 + battery-{VERSION}',
                           'output': os.path.relpath(path, ROOT).replace(os.sep, '/'),
                           'note': 'generated twice by a duplicate process; gen_seconds taken on a shared GPU' if g['dup'] else ''}
                    log.write(json.dumps(row) + '\n')
                    log.flush()
                    print(rid, gate['verdict'], scores.get('edge_precision'), scores.get('presence_min'),
                          scores.get('colour_v1_median'), scores.get('cer_primary_worst', ''), flush=True)


if __name__ == '__main__':
    main(sys.argv[1:] or ['vela', 'lumen', 'field16'])
