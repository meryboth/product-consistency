# VELA V-43, an original low-attention e-ink phone, built from code so the geometry is exact (our "CAD").
# The third product of the study (research/PROTOCOL.md, P3): chosen to break things. Its screen is almost only text,
# its back carries 1.5 mm printed lines, it has three small keys to count, a switch on the top edge and a polished
# aluminium camera ring. The genre is the inspiration (research/P3_INSPIRACION.md); no real phone, brand or type is copied.
# Usage: py fixtures/vela/screen.py                                   (the screen texture, first)
#        blender -b -P fixtures/vela/build.py -- [colorway|all]        (a .blend per colorway, to look at)
#        blender -b -P fixtures/vela/build.py -- --export products/vela
# Units are metres at real size: the body is 66 x 124 x 10.5 mm. The front faces -Y, up is +Z.
import json
import math
import os
import sys

import bmesh
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
os.makedirs(OUT, exist_ok=True)
FONT = os.path.join(HERE, '..', '..', 'brands', 'meridian', 'fonts', 'InterTight.ttf')

# ---------- the design, in numbers ----------
W, H, D, R = 0.066, 0.124, 0.0105, 0.009   # body and corner radius
SCREEN_W, SCREEN_H = 0.056, 0.094          # 4.3 inch e-ink, portrait
SCREEN_TOP = 0.005                         # border above the screen (and at the sides); the chin below holds the keys
RECESS = 0.0006                            # the display sits this far below the front
KEY_W, KEY_H, KEY_GAP = 0.014, 0.006, 0.004
BACK_LINES = ['MODEL V-43 · E-INK 4.3"', 'DESIGNED FOR LESS']


def lin(h):
    """A hex colour -> the linear values a material takes."""
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(round(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4, 4) for v in c)


ACCENT, ALU, LENS = lin('#E8581C'), lin('#C9CACC'), lin('#0A0A0C')
COLORWAYS = {
    'graphite': dict(body=lin('#2B2B2A'), keys=lin('#3A3A38'), glyph=lin('#BDB9B0'), print=lin('#BDB9B0'),
                     engrave=lin('#232322'), rough=0.55),
    'paper': dict(body=lin('#E6E3DC'), keys=lin('#D3CFC6'), glyph=lin('#4A4843'), print=lin('#4A4843'),
                  engrave=lin('#D6D2CA'), rough=0.5),
}


# ---------- geometry helpers (the same vocabulary as fixtures/field16) ----------
def rounded_profile(w, h, r, seg=10, cx=0.0, cz=0.0):
    pts = []
    for (x, z), a0 in (((w / 2 - r, h / 2 - r), 0), ((-w / 2 + r, h / 2 - r), 90),
                       ((-w / 2 + r, -h / 2 + r), 180), ((w / 2 - r, -h / 2 + r), 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + x + r * math.cos(a), cz + z + r * math.sin(a)))
    return pts


def prism(name, profile, y0, depth, mat, bevel=0.0005, index=0):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    front = [bm.verts.new((x, y0, z)) for x, z in profile]
    back = [bm.verts.new((x, y0 + depth, z)) for x, z in profile]
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    n = len(profile)
    for i in range(n):
        bm.faces.new((front[i], front[(i + 1) % n], back[(i + 1) % n], back[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(mat)
    ob.pass_index = index
    if bevel:
        m = ob.modifiers.new('bevel', 'BEVEL')
        m.width, m.segments, m.limit_method, m.angle_limit = bevel, 4, 'ANGLE', math.radians(50)
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
    return ob


def disc(name, r, depth, x, y0, z, mat, index=0, bevel=0.0003, seg=64):
    return prism(name, [(x + r * math.cos(2 * math.pi * i / seg), z + r * math.sin(2 * math.pi * i / seg)) for i in range(seg)],
                 y0, depth, mat, bevel, index)


def material(name, color, rough=0.4, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    return m


def screen_material():
    """E-ink reflects light, it does not emit it: a matte texture, no glow."""
    m = material('screen', (1, 1, 1), 0.65)
    nt = m.node_tree
    tex = nt.nodes.new('ShaderNodeTexImage')
    path = os.path.join(HERE, 'screen.png')
    if not os.path.exists(path):
        raise SystemExit('Draw the screen first: py fixtures/vela/screen.py')
    tex.image = bpy.data.images.load(path)
    tex.image.pack()
    nt.links.new(tex.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color'])
    return m


def planar_uv(ob):
    """Front projection: the screen image lands flat on the display face."""
    me = ob.data
    uv = me.uv_layers.new(name='UVMap')
    xs = [v.co.x for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = ((co.x - min(xs)) / (max(xs) - min(xs)), (co.z - min(zs)) / (max(zs) - min(zs)))


def text(name, body, size, x, y, z, mat, back=False, extrude=0.00008, index=6):
    """Type on a face: on the front it reads from -Y, on the back from +Y."""
    rot = (math.radians(90), 0, math.radians(180) if back else 0)
    bpy.ops.object.text_add(location=(x, y, z), rotation=rot)
    t = bpy.context.object
    t.name = name
    t.data.body = body
    t.data.size = size
    t.data.extrude = extrude
    t.data.align_x, t.data.align_y = 'CENTER', 'CENTER'
    if os.path.exists(FONT):
        t.data.font = bpy.data.fonts.load(FONT, check_existing=True)
    t.data.materials.append(mat)
    t.pass_index = index
    return t


# ---------- the phone ----------
def build(cw):
    c = COLORWAYS[cw]
    body = material('body', c['body'], c['rough'])
    keys = material('keys', c['keys'], 0.6)
    glyph = material('glyph', c['glyph'], 0.5)
    printed = material('print', c['print'], 0.5)
    engrave = material('engrave', c['engrave'], c['rough'])
    accent = material('accent', ACCENT, 0.4)
    ring = material('ring', ALU, 0.12, metal=1.0)       # polished: the one shiny part, on purpose
    lens = material('lens', LENS, 0.05)
    flash = material('flash', lin('#F2EFE6'), 0.3)
    gasket = material('gasket', lin('#161616'), 0.7)
    screen = screen_material()

    # body, with the display pocket cut into the front
    shell = prism('body', rounded_profile(W, H, R), 0.0, D, body, 0.0012, 1)
    screen_cz = H / 2 - SCREEN_TOP - SCREEN_H / 2
    cutter = prism('cutter', rounded_profile(SCREEN_W + 0.0008, SCREEN_H + 0.0008, 0.0015, cz=screen_cz),
                   -0.001, 0.001 + RECESS, body, 0)
    cut = shell.modifiers.new('pocket', 'BOOLEAN')
    cut.operation, cut.object, cut.solver = 'DIFFERENCE', cutter, 'EXACT'
    cutter.hide_render = cutter.hide_viewport = True
    # a dark gasket line around the display, then the display itself, at the bottom of the pocket
    prism('gasket', rounded_profile(SCREEN_W + 0.0008, SCREEN_H + 0.0008, 0.0015, cz=screen_cz), RECESS - 0.0001, 0.0002, gasket, 0, 2)
    s = prism('screen', rounded_profile(SCREEN_W, SCREEN_H, 0.001, cz=screen_cz), RECESS - 0.00015, 0.0002, screen, 0, 2)
    planar_uv(s)

    # three pill keys on the chin: back, select, forward, each with its glyph
    key_z = -H / 2 + (H / 2 + screen_cz - SCREEN_H / 2) / 2 + 0.002
    for i, (name, x) in enumerate((('key_back', -(KEY_W + KEY_GAP)), ('key_select', 0.0), ('key_next', KEY_W + KEY_GAP))):
        prism(name, rounded_profile(KEY_W, KEY_H, KEY_H / 2 - 0.0001, cx=x, cz=key_z), -0.0007, 0.001, keys, 0.0004, 3)
        if name == 'key_select':
            disc('glyph_dot', 0.0009, 0.0001, x, -0.00078, key_z, glyph, 3, 0, 32)
        else:
            sgn = -1 if name == 'key_back' else 1
            tri = [(x + sgn * 0.0013, key_z), (x - sgn * 0.0009, key_z + 0.0014), (x - sgn * 0.0009, key_z - 0.0014)]
            prism(f'glyph_{name[4:]}', tri, -0.00078, 0.0001, glyph, 0, 3)
    # speaker: six holes in a row under the keys
    for i in range(6):
        disc(f'speaker_{i}', 0.0005, 0.0002, -0.00625 + 0.0025 * i, -0.0001, -H / 2 + 0.0055, gasket, 5, 0, 16)

    # right side: power and a volume rocker; top edge: the focus switch with an orange tell-tale
    prism('power', rounded_profile(0.0012, 0.008, 0.0005, cx=W / 2 + 0.0002, cz=0.030), D / 2 - 0.0015, 0.003, keys, 0.0002, 4)
    prism('volume', rounded_profile(0.0012, 0.018, 0.0005, cx=W / 2 + 0.0002, cz=0.010), D / 2 - 0.0015, 0.003, keys, 0.0002, 4)
    prism('switch', rounded_profile(0.008, 0.0014, 0.0005, cx=-0.012, cz=H / 2 + 0.0002), D / 2 - 0.0016, 0.0032, keys, 0.0002, 4)
    prism('switch_dot', rounded_profile(0.0016, 0.0009, 0.0003, cx=-0.0145, cz=H / 2 + 0.0002), D / 2 - 0.0017, 0.0002, accent, 0, 4)

    # back: the camera top left (seen from behind, that is +X), a flash, the engraved name and two printed lines
    cx, cz = W / 2 - 0.012, H / 2 - 0.013
    disc('camera_ring', 0.005, 0.0009, cx, D - 0.0001, cz, ring, 7, 0.0003)
    disc('camera_lens', 0.0035, 0.0007, cx, D + 0.00005, cz, lens, 7, 0.0002)
    disc('flash', 0.0015, 0.0003, cx - 0.0095, D - 0.0001, cz, flash, 7, 0.0001, 32)
    text('wordmark', 'VELA', 0.0056, 0.0, D + 0.00004, 0.004, engrave, back=True, extrude=0.00012)
    for i, line in enumerate(BACK_LINES):
        text(f'print_{i}', line, 0.0021, 0.0, D + 0.00002, -H / 2 + 0.016 - 0.0032 * i, printed, back=True, extrude=0.00002)


def export_product(folder):
    os.makedirs(folder, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build('graphite')
    for o in [o for o in bpy.data.objects if o.name == 'cutter']:
        o.hide_viewport = False
        bpy.context.view_layer.objects.active = o
    # bake the pocket into the body, then drop the cutter so it never reaches the passes
    body = bpy.data.objects['body']
    bpy.context.view_layer.objects.active = body
    for o in bpy.context.selected_objects:
        o.select_set(False)
    body.select_set(True)
    for m in list(body.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(bpy.data.objects['cutter'])
    # text becomes mesh, so the GLB carries the letters as geometry
    for o in [o for o in bpy.data.objects if o.type == 'FONT']:
        for s in bpy.context.selected_objects:
            s.select_set(False)
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.convert(target='MESH')
    bpy.ops.export_scene.gltf(filepath=os.path.join(folder, 'product.glb'), export_apply=True)
    colorways = {}
    for cw, c in COLORWAYS.items():
        colorways[cw] = {'body': {'color': list(c['body']), 'roughness': c['rough']},
                         'keys': {'color': list(c['keys'])}, 'glyph': {'color': list(c['glyph'])},
                         'print': {'color': list(c['print'])}, 'engrave': {'color': list(c['engrave'])},
                         'accent': {'color': list(ACCENT)}}
    screen_text = json.load(open(os.path.join(HERE, 'screen.json'), encoding='utf-8'))['lines']
    spec = {
        'name': 'VELA',
        'code': 'V-43',
        'year': '2026',
        'category': 'e-ink phone',
        'fictional': True,
        'size_mm': [66, 124, 10.5],
        'facts': ['A low-attention phone with a 4.3 inch e-ink screen', 'A text-only home screen: calls, messages, notes',
                  'Three keys under the screen: back, select, forward', 'A focus switch on the top edge',
                  'One camera with an aluminium ring on the back', 'Two colorways: Graphite and Paper'],
        'hero_material': 'body',
        'protected_materials': ['screen', 'gasket', 'keys', 'glyph', 'accent', 'ring', 'lens', 'flash', 'print', 'engrave'],
        'exact_materials': ['screen', 'glyph', 'print', 'lens'],
        'text': {'screen': screen_text, 'back': ['VELA'] + BACK_LINES},
        'passes': {'views': {'front': [0, 4], 'back': [155, 16]}},
        'colorways': colorways,
    }
    json.dump(spec, open(os.path.join(folder, 'product.json'), 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print('exported', folder)


args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
if '--export' in args:
    export_product(os.path.abspath(args[args.index('--export') + 1]))
    sys.exit(0)
for cw in (list(COLORWAYS) if args[:1] == ['all'] else (args[:1] or ['graphite'])):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build(cw)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'vela-{cw}.blend'))
    print('built', cw)
