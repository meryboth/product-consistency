# Blind labelling for Study A (research/PROTOCOL.md §7). A tiny local page: one generated photo at a time, next to
# the reference render of the same product, view and colorway, in a random order, with nothing that tells which
# condition, seed or metric it comes from. Every answer is written to disk the moment it is given.
# Usage: py tools/label.py [--pass 1|2] [--port 8765]     then open http://localhost:8765
#   pass 1  every image of phase 2 (raw and finished)
#   pass 2  the test-retest: a random 20 % of pass 1, in a new order, at least 3 days later (PROTOCOL.md §7)
# Answers go to research/labels/pass<N>.jsonl, one line per image; the last line for an image wins.
import hashlib
import http.server
import json
import os
import random
import sys
import time
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARGS = sys.argv[1:]
PASS = int(ARGS[ARGS.index('--pass') + 1]) if '--pass' in ARGS else 1
PORT = int(ARGS[ARGS.index('--port') + 1]) if '--port' in ARGS else 8765
OUT = os.path.join(ROOT, 'research', 'labels', f'pass{PASS}.jsonl')


def items():
    """Every phase-2 image, keyed by an opaque id; the mapping never reaches the page."""
    rows = []
    for product in ('lumen', 'field16', 'vela'):
        ledger = os.path.join(ROOT, 'runs', product, 'gen', 'ledger.jsonl')
        if not os.path.exists(ledger):
            continue
        for line in open(ledger, encoding='utf-8'):
            r = json.loads(line)
            for kind in ('raw', 'final'):
                path = r[kind]
                ref = f"runs/{product}/passes/{r['view']}/beauty_{r['colorway']}.png"
                rows.append({'id': hashlib.sha1(path.encode()).hexdigest()[:12], 'path': path, 'ref': ref})
    rows = list({r['id']: r for r in rows}.values())
    random.Random(PASS * 7919).shuffle(rows)
    if PASS == 2:
        rows = rows[:max(1, len(rows) // 5)]
    return rows


ITEMS = items()
BY_ID = {r['id']: r for r in ITEMS}

PAGE = '''<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Etiquetado</title>
<style>
:root{--bg:#f6f5f2;--ink:#1c1c1a;--muted:#6e6c66;--line:#dcdad4;--on:#1c5cab}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,sans-serif}
header{display:flex;justify-content:space-between;padding:10px 20px;border-bottom:1px solid var(--line)}
main{display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:16px 20px}
figure{margin:0}figcaption{color:var(--muted);font-size:13px;margin-bottom:4px}
img{width:100%;max-height:70vh;object-fit:contain;background:#c8c8c6;border-radius:6px}
.bar{display:flex;gap:10px;flex-wrap:wrap;padding:0 20px 20px}
button{font:inherit;padding:8px 14px;border:1px solid var(--line);border-radius:6px;background:#fff;cursor:pointer}
button.on{background:var(--on);color:#fff;border-color:var(--on)}
kbd{font:12px ui-monospace,monospace;border:1px solid var(--line);border-radius:3px;padding:0 4px;margin-right:4px}
.help{color:var(--muted);font-size:13px;padding:0 20px 20px}
</style></head><body>
<header><strong>Etiquetado a ciegas · pasada PASS</strong><span id="count"></span></header>
<main><figure><figcaption>Referencia: el producto correcto</figcaption><img id="ref"></figure>
<figure><figcaption>Foto a juzgar</figcaption><img id="img"></figure></main>
<div class="bar">
<button data-k="shape"><kbd>1</kbd>Forma / partes mal (inventadas, faltantes, deformadas)</button>
<button data-k="colour"><kbd>2</kbd>Color mal</button>
<button data-k="text"><kbd>3</kbd>Texto / logo mal</button>
<button data-k="other"><kbd>4</kbd>Otro problema del producto</button>
</div>
<div class="bar"><button id="ok"><kbd>S</kbd>Sirve: la publicaría</button><button id="no"><kbd>N</kbd>No sirve</button>
<button id="back"><kbd>←</kbd>Anterior</button></div>
<p class="help">Juzgá solo el producto, no la escena ni la luz. Marcá las fallas que veas (1-4) y después decidí con S o N; eso guarda y pasa a la siguiente.</p>
<script>
let items=[],i=0,flags={};
const $=s=>document.querySelector(s);
function show(){ if(i>=items.length){document.body.innerHTML='<p style="padding:40px">Listo. Todas las imágenes tienen etiqueta.</p>';return}
  const it=items[i]; $('#img').src='/img/'+it.id; $('#ref').src='/ref/'+it.id;
  flags=Object.assign({shape:false,colour:false,text:false,other:false},it.prev||{});
  document.querySelectorAll('[data-k]').forEach(b=>b.classList.toggle('on',flags[b.dataset.k]));
  $('#count').textContent=(i+1)+' / '+items.length; }
function toggle(k){flags[k]=!flags[k];document.querySelector('[data-k='+k+']').classList.toggle('on',flags[k])}
async function answer(ok){ const it=items[i];
  await fetch('/label',{method:'POST',body:JSON.stringify({id:it.id,ok,...flags})});
  it.prev={...flags}; i++; show(); }
document.querySelectorAll('[data-k]').forEach(b=>b.onclick=()=>toggle(b.dataset.k));
$('#ok').onclick=()=>answer(true); $('#no').onclick=()=>answer(false); $('#back').onclick=()=>{if(i>0){i--;show()}};
document.onkeydown=e=>{const m={'1':'shape','2':'colour','3':'text','4':'other'};
  if(m[e.key])toggle(m[e.key]); else if(e.key==='s'||e.key==='S')answer(true);
  else if(e.key==='n'||e.key==='N')answer(false); else if(e.key==='ArrowLeft'&&i>0){i--;show()}};
fetch('/items').then(r=>r.json()).then(d=>{items=d.items;i=d.start;show()});
</script></body></html>'''


def done_ids():
    if not os.path.exists(OUT):
        return set()
    return {json.loads(l)['id'] for l in open(OUT, encoding='utf-8')}


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, ctype='application/json'):
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else body.encode('utf-8'))

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == '/':
            return self.send(PAGE.replace('PASS', str(PASS)), 'text/html; charset=utf-8')
        if path == '/items':
            done = done_ids()
            order = [{'id': r['id']} for r in ITEMS]
            start = next((k for k, r in enumerate(ITEMS) if r['id'] not in done), len(ITEMS))
            return self.send(json.dumps({'items': order, 'start': start}))
        for prefix, field in (('/img/', 'path'), ('/ref/', 'ref')):
            if path.startswith(prefix) and path[len(prefix):] in BY_ID:
                return self.send(open(os.path.join(ROOT, BY_ID[path[len(prefix):]][field]), 'rb').read(), 'image/png')
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path != '/label':
            self.send_response(404)
            return self.end_headers()
        data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if data.get('id') not in BY_ID:
            self.send_response(400)
            return self.end_headers()
        row = {'id': data['id'], 'path': BY_ID[data['id']]['path'], 'ok': bool(data['ok']),
               **{k: bool(data.get(k)) for k in ('shape', 'colour', 'text', 'other')},
               'pass': PASS, 'at': time.strftime('%Y-%m-%d %H:%M:%S')}
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, 'a', encoding='utf-8') as f:
            f.write(json.dumps(row) + '\n')
        self.send('{"saved": true}')


if __name__ == '__main__':
    print(f'{len(ITEMS)} images, pass {PASS}; answers go to {os.path.relpath(OUT, ROOT)}')
    print(f'open http://localhost:{PORT}')
    http.server.ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
