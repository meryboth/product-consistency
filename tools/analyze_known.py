# Phases 0-1 analysis: everything measured on images whose answer is known, written to research/results.json,
# the only source of numbers for the report (research/INFORME.template.md -> INFORME.md).
#   phase0  the baseline gate on the real-variation renders (the right product under four lights)
#   phase1  which metric sees which fault, without a threshold picked by eye: for every (product, view, colorway),
#           the four lights give each metric an envelope, the worst value the right product reaches when only the
#           light changes; a perturbed image is "detected" when it falls outside it in the bad direction.
# Usage: py tools/analyze_known.py
import json
import os
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = {'edge_precision', 'edge_recall', 'edge_f1', 'dino_cos', 'presence_min', 'presence_v2'}
METRICS = ['gate_colour', 'gate_parts', 'edge_precision', 'edge_recall', 'colour_worst_p95', 'colour_worst_out',
           'dino_cos', 'dreamsim', 'cer_worst', 'cer_primary_worst', 'colour_v1_p95', 'colour_v1_median', 'presence_min',
           'presence_v2', 'colour_v2_drift']
VERSION = 'v1'   # which measurement rows to read: known-v1-*
LABELS = {'gate_verdict': 'Gate actual (veredicto)', 'gate_colour': 'Gate: color', 'gate_parts': 'Gate: partes',
          'edge_precision': 'Precisión de bordes', 'edge_recall': 'Recall de bordes', 'colour_worst_p95': 'Color p95',
          'colour_worst_out': 'Color fuera de tol.', 'dino_cos': 'DINOv2', 'dreamsim': 'DreamSim', 'cer_worst': 'CER (todo el texto)',
          'cer_primary_worst': 'CER principal', 'colour_v1_p95': 'Color v1 p95', 'colour_v1_median': 'Color v1 mediana',
          'presence_min': 'Presencia v1', 'presence_v2': 'Presencia v2', 'colour_v2_drift': 'Color v2 (contraste)'}
ORDER = ['invent', 'remove', 'erasetext', 'typo', 'warp10', 'warp25', 'hue10', 'hue5', 'hue2',
         'background', 'whitebalance', 'jpeg']
NAMES = {'invent': 'Parte inventada', 'remove': 'Parte faltante', 'erasetext': 'Texto borrado', 'typo': 'Typo ("Messagas")',
         'warp10': 'Warp 10 %', 'warp25': 'Warp 25 %', 'hue10': 'Color +10', 'hue5': 'Color +5', 'hue2': 'Color +2',
         'background': 'Otro fondo', 'whitebalance': 'Balance de blancos', 'jpeg': 'JPEG calidad 35'}
EXPECTED = {'pass': 'no', 'fail': 'sí', 'border': 'borde'}


def worse(m, a, b):
    return a < b if m in UP else a > b


def rate(ok, n):
    return {'n': ok, 'of': n, 'rate': round(ok / n, 3) if n else None}


def main():
    rows = [json.loads(l) for l in open(os.path.join(ROOT, 'research', 'runs.jsonl'), encoding='utf-8')]
    rows = [r for r in rows if r.get('id', '').startswith(f'known-{VERSION}-')]
    key = lambda r: (r['case'], r['view'], r['colorway'])
    var = [r for r in rows if r['source'] == 'variation']
    pert = [r for r in rows if r['source'] == 'perturb']

    # ---------- phase 0: the baseline gate on the right product under four lights ----------
    verdicts = Counter(r['gate_verdict'] for r in var)
    orange = [r for r in var if r['colorway'] == 'signal-orange']
    rest = [r for r in var if r['colorway'] != 'signal-orange']
    by_light = {}
    for light in sorted({r['condition'].split('/')[1] for r in var}):
        rs = [r for r in var if r['condition'] == f'light/{light}']
        by_light[light] = rate(sum(r['gate_verdict'] == 'publish' for r in rs), len(rs))
    studio_orange = [r['metrics']['gate_colour'] for r in orange if r['condition'] == 'light/studio']
    phase0 = {'n': len(var), 'publish': verdicts['publish'], 'review': verdicts['review'], 'regenerate': verdicts['regenerate'],
              'not_publish': len(var) - verdicts['publish'],
              'orange': rate(sum(r['gate_verdict'] == 'publish' for r in orange), len(orange)),
              'other_colorways': rate(sum(r['gate_verdict'] == 'publish' for r in rest), len(rest)),
              'by_light': by_light,
              'studio_orange_colour': {'min': min(studio_orange), 'max': max(studio_orange), 'n': len(studio_orange)},
              'parts_max': max(r['metrics']['gate_parts'] for r in var),
              'parts_studio_max': max(r['metrics']['gate_parts'] for r in var if r['condition'] == 'light/studio')}

    # ---------- phase 1: detection against the real-variation envelope ----------
    envelope = defaultdict(dict)
    for r in var:
        for m in METRICS:
            v = r['metrics'].get(m)
            if v is not None:
                cur = envelope[key(r)].get(m)
                envelope[key(r)][m] = v if cur is None or worse(m, v, cur) else cur
    table = defaultdict(lambda: defaultdict(list))
    for r in pert:
        p = r['condition'].split('/')[1]
        if p == 'none':
            continue
        table[p]['gate_verdict'].append(r['gate_verdict'] != 'publish')
        for m in METRICS:
            v, e = r['metrics'].get(m), envelope[key(r)].get(m)
            if v is not None and e is not None:
                table[p][m].append(worse(m, v, e))
    detection = {p: {m: rate(sum(v), len(v)) for m, v in table[p].items()} for p in ORDER if p in table}
    # threshold-free: for each faulty image, the share of the right images of the same product, view and colorway
    # (four lights + the three legitimate changes) that score better than it; averaged, a rank AUC (1 = always
    # worse than every right image, 0.5 = chance). Ties count half.
    right_by = defaultdict(list)
    for r in rows:
        if r['expected'] == 'pass' and r['condition'] != 'perturb/none':
            right_by[key(r)].append(r)
    auc = defaultdict(dict)
    for p in ORDER:
        faulty = [r for r in pert if r['condition'] == f'perturb/{p}']
        for m in ['gate_verdict'] + METRICS:
            scores = []
            for r in faulty:
                pool = [q for q in right_by[key(r)] if q is not r]
                if m == 'gate_verdict':
                    bad = lambda x: x['gate_verdict'] != 'publish'
                    v = bad(r)
                    s_ = [1.0 if v and not bad(q) else 0.5 if v == bad(q) else 0.0 for q in pool]
                else:
                    v = r['metrics'].get(m)
                    if v is None:
                        continue
                    s_ = [1.0 if worse(m, v, q['metrics'][m]) else 0.5 if v == q['metrics'][m] else 0.0 for q in pool if m in q['metrics']]
                if s_:
                    scores.append(sum(s_) / len(s_))
            if scores:
                auc[p][m] = {'auc': round(sum(scores) / len(scores), 3), 'n': len(scores)}
    expected = {p: next(r['expected'] for r in pert if r['condition'] == f'perturb/{p}') for p in detection}
    # the gate's rejections on faults it should not care about, outside the orange colorway
    quiet = [r for r in pert if r['condition'].split('/')[1] in ('invent', 'remove', 'background', 'jpeg', 'hue2')]
    right = [r for r in rows if r['expected'] == 'pass']
    cols = ['gate_verdict', 'edge_precision', 'presence_min', 'presence_v2', 'colour_worst_p95', 'colour_v1_median',
            'colour_v2_drift', 'dreamsim', 'cer_primary_worst']
    md = ['| Perturbación | ¿Debería fallar? | ' + ' | '.join(LABELS[c] for c in cols) + ' |',
          '|---|---|' + '---|' * len(cols)]
    for p in detection:
        cells = [f"{detection[p][c]['n']}/{detection[p][c]['of']}" if c in detection[p] else '—' for c in cols]
        md.append(f'| {NAMES[p]} | {EXPECTED[expected[p]]} | ' + ' | '.join(cells) + ' |')
    auc_cols = ['gate_verdict', 'edge_precision', 'edge_recall', 'presence_min', 'presence_v2', 'colour_worst_p95',
                'colour_v1_median', 'colour_v2_drift', 'dreamsim', 'cer_primary_worst']
    md2 = ['| Perturbación | ¿Debería fallar? | ' + ' | '.join(LABELS[c] for c in auc_cols) + ' |',
           '|---|---|' + '---|' * len(auc_cols)]
    for p in ORDER:
        if p in auc:
            md2.append(f'| {NAMES[p]} | {EXPECTED[expected[p]]} | ' +
                       ' | '.join(f"{auc[p][c]['auc']:.2f}" if c in auc[p] else '—' for c in auc_cols) + ' |')
    phase1 = {'n_known': len(rows), 'n_perturb': len(pert), 'n_right': len(right),
              'gate_false_rejections': rate(sum(r['gate_verdict'] != 'publish' for r in right), len(right)),
              'gate_quiet': {'orange': rate(sum(r['gate_verdict'] != 'publish' for r in quiet if r['colorway'] == 'signal-orange'),
                                            sum(r['colorway'] == 'signal-orange' for r in quiet)),
                             'other': rate(sum(r['gate_verdict'] != 'publish' for r in quiet if r['colorway'] != 'signal-orange'),
                                           sum(r['colorway'] != 'signal-orange' for r in quiet))},
              'remove_presence_zero': rate(sum(r['metrics'].get('presence_min', 1) == 0 for r in pert
                                                if r['condition'] == 'perturb/remove' and r['case'] != 'vela'),
                                            sum(r['condition'] == 'perturb/remove' and r['case'] != 'vela' for r in pert)),
              'detection': detection, 'auc': auc, 'expected': expected, 'labels': LABELS, 'names': NAMES,
              'tables': {'detection_md': '\n'.join(md), 'auc_md': '\n'.join(md2)}}
    out = {'generated_from': f'research/runs.jsonl (rows known-{VERSION}-*)', 'phase0': phase0, 'phase1': phase1}
    json.dump(out, open(os.path.join(ROOT, 'research', 'results.json'), 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print(phase1['tables']['detection_md'])
    print(json.dumps({k: phase0[k] for k in ('n', 'publish', 'review', 'regenerate', 'orange', 'other_colorways')}))


if __name__ == '__main__':
    main()
