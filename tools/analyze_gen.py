# Phase 2 analysis, before any human label: how each metric moves with the control strength and with the guards,
# on the 180 real generations. Paired by (product, view, seed) with research/scripts/summarize_runs.py against the
# pipeline as it ships (full control, with guards). Writes the "phase2" key of research/results.json.
# Usage: py tools/analyze_gen.py
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, 'research', 'results.json')
METRICS = {'edge_precision': 'up', 'edge_recall': 'up', 'presence_min': 'up', 'colour_v1_median': 'down',
           'cer_primary_worst': 'down', 'gate_colour': 'down', 'gate_parts': 'down'}
CONDS = ['full/final', 'mid/final', 'loose/final', 'full/raw', 'mid/raw', 'loose/raw']
NAMES = {'full': 'control 1,0', 'mid': 'control 0,75', 'loose': 'control 0,5', 'raw': 'crudo', 'final': 'con guardas'}


def main():
    rows = [json.loads(l) for l in open(os.path.join(ROOT, 'research', 'runs.jsonl'), encoding='utf-8')]
    gen = [r for r in rows if r['id'].startswith('gen-v1-')]
    tmp = os.path.join(ROOT, 'runs', '_gen_runs.jsonl')
    with open(tmp, 'w', encoding='utf-8') as f:
        for r in gen:
            f.write(json.dumps({'condition': r['condition'], 'case': r['case'], 'seed': r['seed'], 'view': r['view'],
                                'metrics': {m: r['metrics'][m] for m in METRICS if m in r['metrics']},
                                'status': 'ok', 'cost_usd': 0.0}) + '\n')
    out = os.path.join(ROOT, 'runs', '_gen_summary.json')
    cmd = [sys.executable, os.path.join(ROOT, 'research', 'scripts', 'summarize_runs.py'), tmp, '--baseline', 'full/final',
           '--out', out] + [a for m, d in METRICS.items() for a in ('--direction', f'{m}:{d}')]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    summary = json.load(open(out, encoding='utf-8'))

    # the baseline gate's verdicts: From CAD to Shelf judges colour on the raw photo and parts on the finished one,
    # so its verdict belongs to the pair; it is reported once per generation (the final rows)
    verdicts = {c: Counter(r['gate_verdict'] for r in gen if r['condition'] == c) for c in CONDS}
    per_case = defaultdict(dict)
    for case in ('lumen', 'field16', 'vela'):
        for c in CONDS:
            rs = [r for r in gen if r['case'] == case and r['condition'] == c]
            if rs:
                med = lambda m: sorted(r['metrics'][m] for r in rs if m in r['metrics'])
                vals = {m: med(m) for m in METRICS}
                per_case[case][c] = {m: (v[len(v) // 2] if v else None) for m, v in vals.items()} | {'n': len(rs)}
    secs = [r['gen_seconds'] for r in gen if r['condition'].endswith('/final') and not r['note']]
    secs_dup = [r['gen_seconds'] for r in gen if r['condition'].endswith('/final') and r['note']]

    def table():
        cols = ['edge_precision', 'edge_recall', 'presence_min', 'colour_v1_median', 'cer_primary_worst']
        head = ['Precisión de bordes ↑', 'Recall de bordes ↑', 'Presencia ↑', 'Color v1 ↓', 'CER principal ↓ (VELA)']
        md = ['| Condición | n | ' + ' | '.join(head) + ' | Gate actual: publica |', '|---|---|' + '---|' * (len(cols) + 1)]
        for c in CONDS:
            s = summary['conditions'].get(c, {}).get('summary', {})
            cells = []
            for m in cols:
                x = s.get(m)
                cells.append(f"{x['median']:.3g} ({x['min']:.3g}–{x['max']:.3g})" if x else '—')
            v = verdicts[c]
            strength, kind = c.split('/')
            md.append(f"| {NAMES[strength]}, {NAMES[kind]} | {summary['conditions'][c]['n']} | " + ' | '.join(cells) +
                      f" | {v['publish']}/{sum(v.values())} |")
        return '\n'.join(md)

    def comparisons():
        md = ['| Contra "control 1,0 con guardas" | Métrica | Mediana de la diferencia | IC 95 % | Pares | Veredicto |',
              '|---|---|---|---|---|---|']
        verdict_es = {'better than baseline': 'mejor', 'worse than baseline': 'peor',
                      'no winner: the interval crosses zero': 'sin ganador (el IC cruza el 0)'}
        for c in CONDS[1:]:
            for m in ('edge_precision', 'presence_min', 'colour_v1_median', 'cer_primary_worst'):
                v = summary.get('vs_baseline', {}).get(c, {}).get(m)
                if not v:
                    continue
                ci = v.get('ci95')
                strength, kind = c.split('/')
                md.append(f"| {NAMES[strength]}, {NAMES[kind]} | {m} | {v['median_diff']:.3g} | "
                          f"{f'{ci[0]:.3g} a {ci[1]:.3g}' if ci else '—'} | {v['pairs']} | "
                          f"{verdict_es.get(v['verdict'], v['verdict'])} |")
        return '\n'.join(md)

    phase2 = {'n_images': len(gen), 'n_generations': len(gen) // 2,
              'gate_verdicts': {c: dict(v) for c, v in verdicts.items()},
              'gate_publish': {c.replace('/', '_'): {'n': verdicts[c]['publish'], 'of': sum(verdicts[c].values())} for c in CONDS},
              'per_case': per_case, 'summary': summary,
              'seconds': {'median': sorted(secs)[len(secs) // 2] if secs else None, 'n': len(secs),
                          'min': min(secs) if secs else None, 'max': max(secs) if secs else None,
                          'n_contaminated': len(secs_dup)},
              'tables': {'conditions_md': table(), 'comparisons_md': comparisons()}}
    res = json.load(open(RESULTS, encoding='utf-8')) if os.path.exists(RESULTS) else {}
    res['phase2'] = phase2
    json.dump(res, open(RESULTS, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print('phase2 written:', len(gen), 'images')


if __name__ == '__main__':
    main()
