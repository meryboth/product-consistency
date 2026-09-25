# The real-variation baseline (research/PROTOCOL.md §5 and §7): the same product, the same camera, rendered under
# different studio lights. Every one of these images is, by construction, the right product, so any metric that
# rejects one of them is miscalibrated. The light is the only thing that changes.
# Usage: py tools/variation.py <product> [<product> ...]      e.g. py tools/variation.py vela lumen field16
# Writes runs/<product>/variation/<light>/<view>/beauty_<colorway>.png plus the usual passes, and a manifest.
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLENDER = os.environ.get('BLENDER', r'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe')
# the views each product is studied in (PROTOCOL.md §4)
VIEWS = {'lumen': ['front', 'right'], 'field16': ['front', 'right'], 'vela': ['front', 'back']}
# four lights: the pipeline's own studio, two neutral alternatives, and a warm one that a colour check should forgive
LIGHTS = {
    'studio': {'hdri': 'studio.exr', 'light': 2.5, 'hdri_strength': 0.45},
    'interior': {'hdri': 'interior.exr', 'light': 1.6, 'hdri_strength': 0.9},
    'courtyard': {'hdri': 'courtyard.exr', 'light': 3.2, 'hdri_strength': 0.6},
    'sunset': {'hdri': 'sunset.exr', 'light': 1.8, 'hdri_strength': 0.8},
}


def run(product):
    src = os.path.join(ROOT, 'products', product)
    spec = json.load(open(os.path.join(src, 'product.json'), encoding='utf-8'))
    for name, render in LIGHTS.items():
        out = os.path.join(ROOT, 'runs', product, 'variation', name)
        tmp = os.path.join(ROOT, 'runs', product, 'variation', f'_{name}_product')
        os.makedirs(tmp, exist_ok=True)
        shutil.copy(os.path.join(src, 'product.glb'), tmp)
        json.dump({**spec, 'render': {**spec.get('render', {}), **render}},
                  open(os.path.join(tmp, 'product.json'), 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
        for view in VIEWS[product]:
            print(product, name, view, flush=True)
            subprocess.run([BLENDER, '-b', '-P', os.path.join(ROOT, 'pipeline', 'passes.py'), '--', tmp, out, '--view', view],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(tmp)


if __name__ == '__main__':
    for p in sys.argv[1:] or list(VIEWS):
        run(p)
