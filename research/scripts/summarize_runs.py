"""Summarise research runs: n, median and range per condition, and paired comparisons against a baseline.

One run per line in a JSONL file (research/runs.jsonl):

    {"id": "r0042", "condition": "triptych", "case": "mascot", "seed": 3, "view": "front",
     "metrics": {"drift": 0.0109, "edge_f1": 0.81}, "time_s": 212.4, "cost_usd": 0.0,
     "status": "ok", "commit": "a1b2c3d", "config": "configs/triptych.yaml",
     "output": "out/triptych_mascot_s3_front.png", "note": ""}

Only "condition" and "metrics" are required. Runs whose status is not "ok" are counted and kept out of the statistics.
Pairs for the comparison are matched on (case, seed, view), so every condition must use the same seeds.

    python summarize_runs.py research/runs.jsonl --baseline separate-views \
        --direction drift:down --direction edge_f1:up --out research/results.json

Metric direction defaults to "up" (higher is better); say --direction name:down for errors, distances and costs.
A comparison is only called when there are at least 5 pairs and the bootstrap 95 % interval of the median
difference does not cross zero; otherwise the verdict says so.
"""
import argparse
import json
import random
import statistics
import sys
from collections import defaultdict

MIN_PAIRS = 5


def quantiles(xs):
    xs = sorted(xs)
    if len(xs) == 1:
        return xs[0], xs[0]
    q = statistics.quantiles(xs, n=4, method='inclusive')
    return q[0], q[2]


def describe(xs):
    q1, q3 = quantiles(xs)
    return {'n': len(xs), 'median': statistics.median(xs), 'min': min(xs), 'max': max(xs), 'q1': q1, 'q3': q3,
            'mean': statistics.fmean(xs)}


def bootstrap_median_ci(diffs, reps, rng):
    meds = []
    for _ in range(reps):
        sample = [diffs[rng.randrange(len(diffs))] for _ in diffs]
        meds.append(statistics.median(sample))
    meds.sort()
    return meds[int(0.025 * reps)], meds[min(reps - 1, int(0.975 * reps))]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # Windows consoles default to cp1252
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('runs')
    ap.add_argument('--baseline', help='condition every other condition is compared against')
    ap.add_argument('--direction', action='append', default=[], help='metric:up or metric:down (default up)')
    ap.add_argument('--out', help='write the summary as JSON (the only source of numbers for the report)')
    ap.add_argument('--reps', type=int, default=4000, help='bootstrap resamples')
    ap.add_argument('--seed', type=int, default=0, help='seed for the bootstrap, so the summary is reproducible')
    args = ap.parse_args()

    direction = defaultdict(lambda: 'up')
    for d in args.direction:
        name, _, way = d.partition(':')
        if way not in ('up', 'down'):
            sys.exit(f'--direction {d}: use name:up or name:down')
        direction[name] = way

    runs, bad = [], []
    with open(args.runs, encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError as e:
                sys.exit(f'{args.runs}:{i}: not valid JSON ({e})')
            if 'condition' not in r or 'metrics' not in r:
                sys.exit(f'{args.runs}:{i}: every run needs "condition" and "metrics"')
            (runs if r.get('status', 'ok') == 'ok' else bad).append(r)

    by_cond = defaultdict(list)
    for r in runs:
        by_cond[r['condition']].append(r)
    metrics = sorted({m for r in runs for m in r['metrics']})

    out = {'n_runs': len(runs) + len(bad), 'n_ok': len(runs), 'n_not_ok': len(bad),
           'not_ok': [{'id': r.get('id'), 'condition': r['condition'], 'status': r.get('status'), 'note': r.get('note', '')} for r in bad],
           'directions': {m: direction[m] for m in metrics}, 'conditions': {}, 'vs_baseline': {}, 'cost': {}}

    for cond, rs in sorted(by_cond.items()):
        c = {'n': len(rs), 'summary': {}, 'by_case': {}}
        for m in metrics:
            xs = [r['metrics'][m] for r in rs if r['metrics'].get(m) is not None]
            if xs:
                c['summary'][m] = describe(xs)
        cases = defaultdict(list)
        for r in rs:
            cases[r.get('case', '-')].append(r)
        for case, crs in sorted(cases.items()):
            c['by_case'][case] = {m: describe(xs) for m in metrics
                                  if (xs := [r['metrics'][m] for r in crs if r['metrics'].get(m) is not None])}
        times = [r['time_s'] for r in rs if r.get('time_s') is not None]
        if times:
            c['time_s'] = describe(times)
        c['cost_usd'] = round(sum(r.get('cost_usd') or 0 for r in rs), 6)
        out['conditions'][cond] = c

    all_runs = runs + bad
    out['cost'] = {'total_usd': round(sum(r.get('cost_usd') or 0 for r in all_runs), 6),
                   'including_not_ok_usd': round(sum(r.get('cost_usd') or 0 for r in bad), 6),
                   'time_s_total': round(sum(r.get('time_s') or 0 for r in all_runs), 1)}

    if args.baseline:
        if args.baseline not in by_cond:
            sys.exit(f'baseline "{args.baseline}" has no ok runs; conditions: {", ".join(sorted(by_cond))}')
        rng = random.Random(args.seed)
        key = lambda r: (r.get('case', '-'), r.get('seed'), r.get('view'))
        base = {key(r): r for r in by_cond[args.baseline]}
        for cond, rs in sorted(by_cond.items()):
            if cond == args.baseline:
                continue
            comp = {}
            for m in metrics:
                pairs = [(r['metrics'][m], base[key(r)]['metrics'][m]) for r in rs
                         if key(r) in base and r['metrics'].get(m) is not None and base[key(r)]['metrics'].get(m) is not None]
                if not pairs:
                    continue
                diffs = [a - b for a, b in pairs]
                good = (lambda d: d > 0) if direction[m] == 'up' else (lambda d: d < 0)
                res = {'pairs': len(pairs), 'median_diff': statistics.median(diffs),
                       'win_rate': sum(good(d) for d in diffs) / len(diffs), 'direction': direction[m]}
                if len(pairs) < MIN_PAIRS:
                    res['verdict'] = f'insufficient: {len(pairs)} pairs, need {MIN_PAIRS}'
                else:
                    lo, hi = bootstrap_median_ci(diffs, args.reps, rng)
                    res['ci95'] = [lo, hi]
                    if lo <= 0 <= hi:
                        res['verdict'] = 'no winner: the interval crosses zero'
                    elif good(lo) and good(hi):
                        res['verdict'] = 'better than baseline'
                    else:
                        res['verdict'] = 'worse than baseline'
                comp[m] = res
            out['vs_baseline'][cond] = comp
        out['baseline'] = args.baseline

    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(out, f, indent=2, ensure_ascii=False)

    # a readable summary on stdout
    print(f"{out['n_ok']} ok runs, {out['n_not_ok']} not ok · total cost ${out['cost']['total_usd']}")
    for m in metrics:
        print(f"\n{m} ({'higher' if direction[m] == 'up' else 'lower'} is better)")
        print('| condition | n | median | min–max |')
        print('|---|---|---|---|')
        for cond, c in out['conditions'].items():
            s = c['summary'].get(m)
            if s:
                print(f"| {cond} | {s['n']} | {s['median']:.4g} | {s['min']:.4g}–{s['max']:.4g} |")
        for cond, comp in out['vs_baseline'].items():
            if m in comp:
                v = comp[m]
                ci = f" · 95 % CI [{v['ci95'][0]:.4g}, {v['ci95'][1]:.4g}]" if 'ci95' in v else ''
                print(f"  {cond} vs {args.baseline}: median diff {v['median_diff']:.4g}{ci} · wins {v['win_rate']:.0%} of {v['pairs']} → {v['verdict']}")


if __name__ == '__main__':
    main()
