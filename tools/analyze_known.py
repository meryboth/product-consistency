# Phase 1 analysis: which metric sees which fault, without picking a threshold by eye.
# For every (product, view, colorway), the four real-variation lights give each metric an envelope: the worst value
# the right product reaches when only the light changes. A perturbed image counts as "detected" by a metric when its
# value falls outside that envelope in the bad direction. The baseline gate is scored by its own verdict (not publish).
# Usage: py tools/analyze_known.py  ->  research/results_known.json, and a table on stdout
import json
import os
import statistics
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = {'edge_precision', 'edge_recall', 'edge_f1', 'dino_cos'}
METRICS = ['gate_colour', 'gate_parts', 'edge_precision', 'edge_recall', 'colour_worst_p95', 'colour_worst_out',
           'dino_cos', 'dreamsim', 'cer_worst', 'words_extra']
ORDER = ['hue2', 'hue5', 'hue10', 'invent', 'remove', 'erasetext', 'typo', 'warp10', 'warp25',
         'background', 'whitebalance', 'jpeg']


def worse(m, a, b):
    """True when a is worse than b for metric m."""
    return a < b if m in UP else a > b


def main():
    rows = [json.loads(l) for l in open(os.path.join(ROOT, 'research', 'runs.jsonl'), encoding='utf-8')]
    rows = [r for r in rows if r.get('id', '').startswith('known-')]
    key = lambda r: (r['case'], r['view'], r['colorway'])
    envelope = defaultdict(dict)
    for r in rows:
        if r['source'] != 'variation':
            continue
        for m in METRICS:
            v = r['metrics'].get(m)
            if v is None:
                continue
            cur = envelope[key(r)].get(m)
            envelope[key(r)][m] = v if cur is None or worse(m, v, cur) else cur
    # the gate's false rejections on images that are right (variation and the "pass" perturbations)
    right = [r for r in rows if r['expected'] == 'pass']
    gate_false = sum(r['gate_verdict'] != 'publish' for r in right)
    # detection per perturbation x metric
    table = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r['source'] != 'perturb':
            continue
        p = r['condition'].split('/')[1]
        if p == 'none':
            continue
        table[p]['gate_verdict'].append(r['gate_verdict'] != 'publish')
        for m in METRICS:
            v, e = r['metrics'].get(m), envelope[key(r)].get(m)
            if v is not None and e is not None:
                table[p][m].append(worse(m, v, e))
    result = {'n_rows': len(rows), 'n_right': len(right),
              'gate_false_rejections': {'n': gate_false, 'of': len(right)},
              'envelope_note': 'worst value over 4 studio lights of the correct render, per product/view/colorway',
              'detection': {p: {m: {'detected': sum(v), 'n': len(v)} for m, v in table[p].items()} for p in ORDER if p in table},
              'expected': {p: next(r['expected'] for r in rows if r['condition'] == f'perturb/{p}') for p in ORDER if p in table}}
    json.dump(result, open(os.path.join(ROOT, 'research', 'results_known.json'), 'w'), indent=2)
    cols = ['gate_verdict'] + METRICS
    print(f"gate false rejections on right images: {gate_false}/{len(right)}")
    print('perturbation'.ljust(14), 'exp'.ljust(7), ' '.join(c[:11].rjust(11) for c in cols))
    for p in ORDER:
        if p not in table:
            continue
        cells = []
        for c in cols:
            v = table[p].get(c, [])
            cells.append(f'{sum(v)}/{len(v)}'.rjust(11) if v else '—'.rjust(11))
        print(p.ljust(14), result['expected'][p].ljust(7), ' '.join(cells))


if __name__ == '__main__':
    main()
