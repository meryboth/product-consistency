"""Fill a report template with numbers from results.json, so no number in the report is typed by hand.

    python render_report.py research/report.template.md research/results.json research/report.md

Markers: {{path.to.value}} or {{path.to.value|format}}, where the path walks results.json by keys
(list items by index, e.g. {{vs_baseline.method.drift.ci95.0|.3f}}). Formats:
    .2f, .3g, ,d …   any Python format spec
    pct             0.873 → 87.3 %
    int             rounds and adds thousands separators
The render fails, listing every marker it could not resolve, instead of leaving a gap in the report.
"""
import json
import re
import sys

MARK = re.compile(r'\{\{\s*([^}|]+?)\s*(?:\|\s*([^}]+?)\s*)?\}\}')


def walk(data, path):
    cur = data
    for part in path.split('.'):
        if isinstance(cur, list):
            if not part.isdigit() or int(part) >= len(cur):
                raise KeyError(path)
            cur = cur[int(part)]
        elif isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise KeyError(path)
    return cur


def fmt(value, spec):
    if spec is None:
        return str(value)
    if spec == 'pct':
        return f'{value * 100:.1f} %'
    if spec == 'int':
        return f'{round(value):,}'
    return format(value, spec)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # Windows consoles default to cp1252
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    template, results, out = sys.argv[1:]
    text = open(template, encoding='utf-8').read()
    data = json.load(open(results, encoding='utf-8'))
    missing = []

    def sub(m):
        path, spec = m.group(1), m.group(2)
        try:
            return fmt(walk(data, path), spec)
        except KeyError:
            missing.append(path)
        except (TypeError, ValueError) as e:
            missing.append(f'{path} (format "{spec}": {e})')
        return m.group(0)

    rendered = MARK.sub(sub, text)
    if missing:
        sys.exit('could not fill from results.json (missing, or the wrong format):\n  ' + '\n  '.join(sorted(set(missing))))
    open(out, 'w', encoding='utf-8').write(rendered)
    print(f'{out}: {len(MARK.findall(text))} numbers filled from {results}')


if __name__ == '__main__':
    main()
