"""JACK A7 + table, 1:1, built from photogrammetry of the owner's photos.
Units: 1 Blender unit = 1 cm.  Table coordinates (x right, y up, z toward operator, origin = table top front-left)
are mapped to Blender as (x, -z, y).  glTF export (+Y up) gives back exactly the table coordinates.
Run: blender -b --factory-startup -P build.py -- OUTDIR [render]"""
import bpy, bmesh, math, json, os, sys
import numpy as np
from mathutils import Vector, Matrix

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = ARGS[0] if ARGS else os.path.dirname(__file__)
DO_RENDER = 'render' in ARGS
HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'tex')
CAL = json.load(open(os.path.join(HERE, 'calib.json')))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'NONE'

def V(x, y, z): return Vector((x, -z, y))

# ------------------------------------------------------------------ materials
MATS = {}
def mat(name, color, rough=.5, metal=0., img=None, alpha=False, emis=None, coat=0.):
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    if coat: bsdf.inputs['Coat Weight'].default_value = coat
    if img:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.join(TEX, img))
        t.extension = 'CLIP'
        nt.links.new(t.outputs['Color'], bsdf.inputs['Base Color'])
        if alpha:
            nt.links.new(t.outputs['Alpha'], bsdf.inputs['Alpha'])
            m.blend_method = 'BLEND' if hasattr(m, 'blend_method') else None
    if emis:
        bsdf.inputs['Emission Color'].default_value = (*emis, 1); bsdf.inputs['Emission Strength'].default_value = 1.0
    MATS[name] = m; return m

def srgb(h):
    h = h.lstrip('#'); c = [int(h[i:i+2], 16)/255 for i in (0, 2, 4)]
    return tuple(((v+0.055)/1.055)**2.4 if v > 0.04045 else v/12.92 for v in c)

ENAMEL = mat('enamel', srgb('#eef0ec'), .55)
CYAN = mat('cyan', srgb('#12a5d9'), .38)
CHROME = mat('chrome', srgb('#e6e9ec'), .14, 1.)
STEEL = mat('steel', srgb('#b4babf'), .32, .9)
BLACK = mat('black', srgb('#16191c'), .4)
RUBBER = mat('rubber', srgb('#2b2e31'), .85)
GREYM = mat('motor_grey', srgb('#9aa0a6'), .55)
GREYD = mat('dial_grey', srgb('#4b5156'), .6)
GREYL = mat('light_grey', srgb('#b9bec3'), .55)
LAMIN = mat('laminate', srgb('#f1f1ee'), .8)
BEECH = mat('beech', srgb('#cf8d55'), .6)
FRAME = mat('frame_white', srgb('#ecedea'), .45)
CONE = mat('thread_cone', srgb('#f4f4ef'), .9)
CLEAR = mat('clear', srgb('#e7f1f5'), .08)
RED = mat('red', srgb('#d23128'), .4)
CAST = mat('casting', srgb('#8c9398'), .55, .3)
PLATEG = mat('plate_grey', srgb('#8f969c'), .35, .6)
GLASS = mat('panel_glass', srgb('#0a0d10'), .08, 0., coat=1.)
RULER = mat('ruler', (1, 1, 1), .6, img='ruler.jpg')
LOGO = mat('logo', (1, 1, 1), .4, img='logo.png', alpha=True)
STICK = mat('sticker', (1, 1, 1), .5, img='sticker.png')
MOTF = mat('motor_front', (1, 1, 1), .55, img='motorfront.png')
PANELP = mat('panel_photo', (1, 1, 1), .1, img='panelproj.jpg', coat=1.)

# ------------------------------------------------------------------ helpers
ROOT = bpy.data.collections.new('JACK_A7'); scene.collection.children.link(ROOT)
def link(obj, part=None, name=None):
    ROOT.objects.link(obj)
    if part: obj['part'] = part
    return obj

def finish(me, name, m, part=None, bevel=0., seg=3, angle=35, smooth=True):
    obj = bpy.data.objects.new(name, me); link(obj, part)
    if isinstance(m, (list, tuple)):
        for mm in m: me.materials.append(mm)
    else: me.materials.append(m)
    if smooth:
        for pl in me.polygons: pl.use_smooth = True
    if bevel > 0:
        b = obj.modifiers.new('bevel', 'BEVEL'); b.width = bevel; b.segments = seg
        b.limit_method = 'ANGLE'; b.angle_limit = math.radians(angle); b.harden_normals = True
        b.miter_outer = 'MITER_ARC'
    else:
        obj.modifiers.new('wn', 'WEIGHTED_NORMAL').keep_sharp = True
    return obj

def rpoly(pts, radii, seg=8):
    """rounded polygon: corner i gets radius radii[i]; returns sampled (x,y) list"""
    n = len(pts); out = []
    if not isinstance(radii, (list, tuple)): radii = [radii]*n
    for i in range(n):
        p0, p1, p2 = Vector(pts[i-1]), Vector(pts[i]), Vector(pts[(i+1) % n])
        r = radii[i]
        if r <= 0: out.append(tuple(p1)); continue
        a, c = (p0-p1).normalized(), (p2-p1).normalized()
        ang = a.angle(c); t = r/math.tan(ang/2); t = min(t, (p0-p1).length*.49, (p2-p1).length*.49); r = t*math.tan(ang/2)
        s, e = p1+a*t, p1+c*t
        bis = (a+c).normalized(); ctr = p1+bis*(r/math.sin(ang/2))
        a0 = math.atan2(s.y-ctr.y, s.x-ctr.x); a1 = math.atan2(e.y-ctr.y, e.x-ctr.x)
        d = a1-a0
        while d > math.pi: d -= 2*math.pi
        while d < -math.pi: d += 2*math.pi
        for k in range(seg+1):
            aa = a0+d*k/seg; out.append((ctr.x+r*math.cos(aa), ctr.y+r*math.sin(aa)))
    return out

def prism(name, outline, z_front, z_back, m, part=None, bevel=0., seg=3, mats_side=None):
    """extrude 2D outline (x,y) along table z from z_back to z_front"""
    bm = bmesh.new()
    vf = [bm.verts.new(V(x, y, z_front)) for x, y in outline]
    vb = [bm.verts.new(V(x, y, z_back)) for x, y in outline]
    ff = bm.faces.new(vf); fb = bm.faces.new(list(reversed(vb)))
    n = len(outline)
    for i in range(n):
        bm.faces.new([vf[i], vb[i], vb[(i+1) % n], vf[(i+1) % n]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return finish(me, name, m, part, bevel, seg)

def box(name, x0, x1, y0, y1, z0, z1, m, part=None, bevel=0., seg=3):
    return prism(name, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], max(z0, z1), min(z0, z1), m, part, bevel, seg)

def rbox(name, cx, cy, cz, w, h, d, r, m, part=None, bevel=0.):
    o = rpoly([(cx-w/2, cy-h/2), (cx+w/2, cy-h/2), (cx+w/2, cy+h/2), (cx-w/2, cy+h/2)], r, 6)
    return prism(name, o, cz+d/2, cz-d/2, m, part, bevel)

def cyl(name, c, axis, r, h, m, part=None, seg=40, r2=None, bevel=0., cap=True):
    """cylinder centred at table point c, axis 'x'|'y'|'z' (table axes)"""
    bpy.ops.mesh.primitive_cone_add(vertices=seg, radius1=r, radius2=(r if r2 is None else r2), depth=h,
                                    end_fill_type='NGON' if cap else 'NOTHING', location=V(*c))
    o = bpy.context.active_object; o.name = name
    for coll in o.users_collection: coll.objects.unlink(o)
    link(o, part)
    rot = {'y': (0, 0, 0), 'x': (0, math.pi/2, 0), 'z': (math.pi/2, 0, 0)}[axis]
    o.rotation_euler = rot
    o.data.materials.append(m)
    for pl in o.data.polygons: pl.use_smooth = True
    if bevel > 0:
        b = o.modifiers.new('bevel', 'BEVEL'); b.width = bevel; b.segments = 3; b.limit_method = 'ANGLE'; b.harden_normals = True
    else:
        o.modifiers.new('wn', 'WEIGHTED_NORMAL').keep_sharp = True
    return o

def tube(name, pts, r, m, part=None, closed=False, flat=None, res=6):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = res
    cu.use_fill_caps = True
    sp = cu.splines.new('POLY' if flat == 'poly' else 'NURBS'); sp.points.add(len(pts)-1)
    for i, p in enumerate(pts): sp.points[i].co = (*V(*p), 1)
    if sp.type == 'NURBS': sp.order_u = min(4, len(pts)); sp.use_endpoint_u = True
    sp.use_cyclic_u = closed
    o = bpy.data.objects.new(name, cu); link(o, part); cu.materials.append(m)
    if flat and flat != 'poly': o.scale = (1, 1, 1)
    return o

def knurl(name, c, axis, r, h, part=None, teeth=28):
    o = cyl(name, c, axis, r, h, CHROME, part, seg=teeth*2)
    me = o.data
    for v in me.vertices:
        rad = math.hypot(v.co.x, v.co.y)
        if rad > r*.9:
            a = math.atan2(v.co.y, v.co.x); k = 1+.05*(1 if int(round(a/(math.pi/teeth))) % 2 else -1)
            v.co.x *= k; v.co.y *= k
    return o

def plane_uv(obj, fn):
    """assign UVs from a function of table coords"""
    me = obj.data; uv = me.uv_layers.new(name='UVMap')
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co; x, y, z = co.x, co.z, -co.y
        uv.data[loop.index].uv = fn(x, y, z)

def rod_between(name, a, b, r, m, part=None):
    A, B = V(*a), V(*b); d = B-A
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=r, depth=d.length, location=(A+B)/2)
    o = bpy.context.active_object; o.name = name
    for coll in o.users_collection: coll.objects.unlink(o)
    link(o, part); o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    o.data.materials.append(m)
    for pl in o.data.polygons: pl.use_smooth = True
    return o

# camera projection for photo-textured faces
def project_px(cam, x, y, z):
    import mathutils
    rv = Vector(cam['r']); ang = rv.length
    R = Matrix.Rotation(ang, 3, rv.normalized()) if ang > 1e-9 else Matrix.Identity(3)
    pc = R @ Vector((x, y, z)) + Vector(cam['t'])
    return (CAL['W']/2 + cam['f']*pc.x/pc.z, CAL['H']/2 + cam['f']*pc.y/pc.z)

def proj_uv(obj, crop):
    u0, v0, u1, v1 = CAL['crops'][crop]; cam = CAL['cams']['c3']
    def fn(x, y, z):
        u, v = project_px(cam, x, y, z); return ((u-u0)/(u1-u0), 1-(v-v0)/(v1-v0))
    plane_uv(obj, fn)

# ==================================================================== MEASUREMENTS (cm, table coords)
BED = dict(x0=38.64, x1=90.34, zf=-11.05, zb=-28.85, top=0.30)
ZA = -15.7          # arm / needle-head front face
ZAB = -25.0         # arm back face (top-back silhouette in photo 3)
ZP = -12.7          # pillar housing front face
ZPB = -25.8         # pillar back
TOP = 22.8          # head top (≈22.5 above bed)
UNDER = 14.6        # arm underside (front edge)
NX, NZ = 45.2, -20.1   # needle
HL = 42.4           # needle-head left face
HR_NEEDLE = 52.75   # needle-head right side (throat starts)
PL = 71.2           # pillar left face (vertical part)
PR = 90.1           # pillar right face
MOT = dict(x0=90.1, x1=96.6, y0=0.0, y1=23.0, zf=-14.5, zb=-28.5)

# ==================================================================== TABLE
TL, TD, TT = 104.1, 53.5, 4.0
tb = box('table_top', 0, TL, -TT, 0, 0, -TD, LAMIN, 'table', bevel=.25, seg=2)
tb.data.materials.append(BEECH)
for pl in tb.data.polygons:   # side faces beech
    if abs(pl.normal.z) < .5: pl.material_index = 1
fr = bpy.data.meshes.new('ruler_face')
bm = bmesh.new(); vs = [bm.verts.new(V(*p)) for p in [(0, -TT+.05, .02), (TL, -TT+.05, .02), (TL, -.05, .02), (0, -.05, .02)]]
bm.faces.new(vs); bm.to_mesh(fr); bm.free()
ro = finish(fr, 'table_ruler', RULER, 'table')
plane_uv(ro, lambda x, y, z: (x/TL, (y+TT)/TT))
# legs (posts measured at x 22 / 94), table height 76
FLOOR = -76.0
for lx, nm in ((22.0, 'L'), (94.0, 'R')):
    box(f'leg_{nm}_post_lo', lx-2.6, lx+2.6, FLOOR+3.5, -40, -24.9, -28.9, FRAME, 'table', bevel=.5)
    box(f'leg_{nm}_post_hi', lx-2.1, lx+2.1, -42, -9, -25.3, -28.5, FRAME, 'table', bevel=.45)
    for i in range(6): cyl(f'leg_{nm}_hole{i}', (lx, -14.5-i*3.6, -24.9), 'z', .42, .1, GREYD)
    # bracket: trapezoid in the (z,y) plane, thickness along x
    bm = bmesh.new(); prof = [(-5.0, -4.0), (-48.5, -4.0), (-30.0, -13.0), (-23.5, -13.0)]
    f1 = [bm.verts.new(V(lx-2.2, y, z)) for z, y in prof]; f2 = [bm.verts.new(V(lx+2.2, y, z)) for z, y in prof]
    bm.faces.new(f1); bm.faces.new(list(reversed(f2)))
    for i in range(4): bm.faces.new([f1[i], f1[(i+1) % 4], f2[(i+1) % 4], f2[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); me = bpy.data.meshes.new('br'); bm.to_mesh(me); bm.free()
    finish(me, f'leg_{nm}_bracket', FRAME, 'table', bevel=.4)
    box(f'leg_{nm}_foot', lx-2.6, lx+2.6, FLOOR+1.6, FLOOR+5.0, 6.0, -60.0, FRAME, 'table', bevel=1.0)
    for fz in (3.5, -57.5): cyl(f'leg_{nm}_rubber{fz}', (lx, FLOOR+.8, fz), 'y', 2.4, 1.6, RUBBER, 'table', r2=2.1)
    for by in (-6.5, -8.8): cyl(f'leg_{nm}_bolt{by}', (lx+2.25, by, -14.0), 'x', .55, .3, STEEL)
box('crossbar', 22, 94, -50, -40, -26.0, -27.6, FRAME, 'table', bevel=.4)
box('drawer', 3.0, 21.0, -12.8, -4.0, -2.0, -34.0, LAMIN, 'table', bevel=.8)
box('drawer_lip', 7.0, 17.0, -6.2, -5.0, -1.4, -2.0, GREYL, 'table', bevel=.3)
# oil pan under the bed (grey, ribbed)
box('oil_pan', 37.0, 80.0, -11.5, -4.0, -12.5, -29.5, CAST, None, bevel=1.2)
for i in range(9): box(f'oil_pan_rib{i}', 38.5+i*4.6, 39.7+i*4.6, -12.6, -6.0, -12.0, -29.0, CAST, None, bevel=.3)
# pedal on the diagonal slotted bar
A, Bb = Vector((22.0, -60.0)), Vector((94.0, -8.0))
d = (Bb-A); ang = math.atan2(d.y, d.x)
L = d.length
bar = box('pedal_bar', 0, L, FLOOR+3.0, FLOOR+4.4, 2.6, -2.6, FRAME, 'pedal', bevel=.6)
bar.location = V(22.0, 0, -60.0) + Vector((0, 0, 0)); bar.rotation_euler = (0, 0, ang)
ped = rbox('pedal', 0, 0, 0, 27, 30, 2.8, 2.2, FRAME, 'pedal', bevel=.6)
ped.rotation_euler = (math.pi/2-0.12, 0, ang)
ped.location = V(44.0, FLOOR+6.0, -24.0)
pr = rbox('pedal_rubber', 0, 0, 1.45, 21, 24, .5, 1.2, RUBBER, 'pedal'); pr.parent = ped
rod_between('pedal_rod', (49.0, FLOOR+7.0, -30.0), (43.0, -6.0, -22.0), .3, STEEL, 'pedal')
cyl('pedal_turnbuckle', (47.6, -26.0, -28.0), 'y', .45, 2.2, STEEL, 'pedal')
box('pedal_sensor', 38.0, 48.0, -8.5, -4.0, -18.0, -25.0, GREYL, 'pedal', bevel=.8)
# knee lifter (under table, right of the bed)
rod_between('knee_lifter_rod', (84.0, -5.0, -14.0), (82.0, -19.0, -4.0), .5, STEEL, 'knee_lifter')
kl = rbox('knee_lifter_pad', 0, 0, 0, 9, 4.2, 2.0, 1.2, GREYD, 'knee_lifter', bevel=.4); kl.location = V(81.5, -20.5, -3.2)
box('knee_lifter_bracket', 78, 92, -6.0, -4.0, -8.0, -18.0, GREYL, 'knee_lifter', bevel=.4)
# head rest
cyl('head_rest', (74.8, 3.6, -37.5), 'y', .95, 7.2, GREYD, 'table')
cyl('head_rest_cap', (74.8, 7.4, -37.5), 'y', 1.25, .7, RUBBER, 'table')

# ==================================================================== THREAD STAND (std. hole 5/5 cm from the right-back corner)
SX, SZ = 99.1, -48.5
cyl('stand_clamp', (SX, .6, SZ), 'y', 2.1, 1.2, GREYL, 'thread_stand')
cyl('stand_rod', (SX, 35.0, SZ), 'y', .78, 70.0, FRAME, 'thread_stand', seg=24)
cyl('stand_cap', (SX, 70.6, SZ), 'y', .9, 1.6, BLACK, 'thread_stand', seg=24)
box('stand_joint', SX-1.3, SX+1.3, 27.0, 33.0, SZ+1.3, SZ-1.3, FRAME, 'thread_stand', bevel=.4)
box('stand_arm_low', 73.5, SX+.9, 37.0, 39.0, SZ+1.25, SZ-1.25, CYAN, 'thread_stand', bevel=.45)
box('stand_arm_top', 73.5, SX+.9, 66.8, 68.6, SZ+.8, SZ-.8, CYAN, 'thread_stand', bevel=.4)
for i, px in enumerate((78.0, 90.7)):
    cyl(f'stand_plate{i}', (px, 39.3, SZ), 'y', 4.6, .3, PLATEG, 'thread_stand', seg=48, r2=4.3)
    cyl(f'stand_pin{i}', (px, 46.5, SZ), 'y', .28, 14.5, STEEL, 'thread_stand', seg=10)
    cyl(f'stand_cone{i}', (px, 46.0, SZ), 'y', 3.3, 13.0, CONE, 'thread_stand', seg=48, r2=1.35)
    bpy.ops.mesh.primitive_torus_add(major_radius=.5, minor_radius=.1, location=V(px, 66.3, SZ))
    o = bpy.context.active_object; o.name = f'stand_eye{i}'
    for coll in o.users_collection: coll.objects.unlink(o)
    link(o, 'thread_stand'); o.data.materials.append(CHROME)
    for bx in (px-3, px+3): cyl(f'stand_bolt{i}{bx}', (bx, 67.7, SZ+.85), 'z', .4, .3, BLACK)

# ==================================================================== MACHINE
# bed plate
bo = rpoly([(BED['x0'], BED['zf']), (BED['x1'], BED['zf']), (BED['x1'], BED['zb']), (BED['x0'], BED['zb'])], 2.2, 8)
bm = bmesh.new()
top = [bm.verts.new(V(x, BED['top'], z)) for x, z in bo]; bot = [bm.verts.new(V(x, -.6, z)) for x, z in bo]
bm.faces.new(top); bm.faces.new(list(reversed(bot)))
for i in range(len(bo)): bm.faces.new([top[i], bot[i], bot[(i+1) % len(bo)], top[(i+1) % len(bo)]])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces); me = bpy.data.meshes.new('bed'); bm.to_mesh(me); bm.free()
finish(me, 'bed', ENAMEL, None, bevel=.18, seg=2)
for nm, cx, cz in (('L', 39.4, -11.6), ('R', 86.2, -11.9)):
    o = rbox(f'bed_rubber_{nm}', 0, 0, 0, 3.6, 3.0, 1.0, .9, GREYD, None, bevel=.25)
    o.rotation_euler = (math.pi/2, 0, 0); o.location = V(cx, .25, cz)

# arm + needle head + pillar: one cast profile
arm_outline = rpoly([(HL, 10.8), (HR_NEEDLE, 10.8), (HR_NEEDLE, UNDER), (PL, UNDER), (PL, BED['top']), (PR, BED['top']), (PR, TOP), (HL, TOP)],
                    [1.0, .8, 1.6, 4.6, .3, .3, 2.6, 1.3], 10)
arm = prism('head_casting', arm_outline, ZA, ZAB, ENAMEL, None, bevel=1.05, seg=5)

# pillar / control housing: front at ZP, nose of the panel recedes to the arm face
NOSE = (67.55, 19.9); PTL = (70.6, TOP-.15); PBL = (72.1, 15.95)
house_front = [NOSE, PTL, (PR, TOP), (PR, BED['top']), (PL, BED['top']), (PL, 13.4), PBL]
def house_mesh():
    bm = bmesh.new(); n = len(house_front)
    zf = [ZA+.2 if i == 0 else ZP for i in range(n)]
    F = [bm.verts.new(V(x, y, zf[i])) for i, (x, y) in enumerate(house_front)]
    # back ring: nose region pushed onto the arm face, pillar part straight back
    back_xy = [(NOSE[0]-0.6, NOSE[1]), (PTL[0]-2.6, PTL[1]), (PR, TOP), (PR, BED['top']), (PL, BED['top']), (PL, 13.4), (PBL[0]-2.4, PBL[1])]
    Bk = [bm.verts.new(V(x, y, ZPB)) for x, y in back_xy]
    bm.faces.new([F[1], F[2], F[3], F[4], F[5], F[6]])     # planar front (panel + sticker face)
    bm.faces.new([F[0], F[1], F[6]])                       # slanted nose triangle
    bm.faces.new(list(reversed(Bk)))
    for i in range(n): bm.faces.new([F[i], Bk[i], Bk[(i+1) % n], F[(i+1) % n]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new('housing'); bm.to_mesh(me); bm.free(); return me
house = finish(house_mesh(), 'pillar_housing', ENAMEL, None, bevel=.7, seg=4, angle=25)

# panel: cyan bezel ring + glass (photo-projected) following the hexagon outline
def offset_poly(poly, d):
    out = []; n = len(poly)
    for i in range(n):
        p0, p1, p2 = Vector(poly[i-1]), Vector(poly[i]), Vector(poly[(i+1) % n])
        e1 = (p1-p0).normalized(); e2 = (p2-p1).normalized()
        n1 = Vector((e1.y, -e1.x)); n2 = Vector((e2.y, -e2.x)); m = (n1+n2).normalized()
        out.append(tuple(p1 + m*(d/max(.3, m.dot(n1)))))
    return out
panel_outer = [(67.65, 19.9), (70.75, 22.55), (87.95, 22.55), (87.95, 15.9), (72.15, 15.9)]
panel_inner = offset_poly(panel_outer, .38)   # outline is CW in x/y → positive d = inward
_N0 = Vector((NOSE[0], NOSE[1], ZA+.2)); _N1 = Vector((PTL[0], PTL[1], ZP)); _N2 = Vector((PBL[0], PBL[1], ZP))
_NN = (_N1-_N0).cross(_N2-_N0)
def zsurf(x, y):
    # left of the PTL→PBL line → slanted nose plane, else the flat housing front
    side = (PBL[0]-PTL[0])*(y-PTL[1]) - (PBL[1]-PTL[1])*(x-PTL[0])
    if side > 0: return ZP
    return _N0.z - (_NN.x*(x-_N0.x) + _NN.y*(y-_N0.y))/_NN.z
def zpanel(x, y=None): return zsurf(x, 19.0 if y is None else y)
def ring_mesh(outer, inner, lift, name):
    bm = bmesh.new()
    O = [bm.verts.new(V(x, y, zpanel(x, y)+lift)) for x, y in outer]; I_ = [bm.verts.new(V(x, y, zpanel(x, y)+lift)) for x, y in inner]
    n = len(outer)
    for i in range(n): bm.faces.new([O[i], O[(i+1) % n], I_[(i+1) % n], I_[i]])
    Ob = [bm.verts.new(V(x, y, zpanel(x, y)-.3)) for x, y in outer]
    for i in range(n): bm.faces.new([Ob[i], Ob[(i+1) % n], O[(i+1) % n], O[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); return me
bez = finish(ring_mesh(panel_outer, panel_inner, .18, 'bezel'), 'panel_bezel', CYAN, 'control_panel')
# glass: fine grid clipped to the inner outline, each vertex placed on the housing surface (+lift)
from mathutils.geometry import intersect_point_tri_2d
bm = bmesh.new(); xs = np.linspace(67.9, 87.6, 140); ys = np.linspace(16.25, 22.2, 44)
poly = panel_inner
def inside(x, y):
    c = False; n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i+1) % n]
        if (y1 > y) != (y2 > y) and x < (x2-x1)*(y-y1)/(y2-y1)+x1: c = not c
    return c
grid = {}
for i, x in enumerate(xs):
    for j, y in enumerate(ys):
        if inside(x, y): grid[i, j] = bm.verts.new(V(x, y, zsurf(x, y)+.12))
for (i, j), v in list(grid.items()):
    q = [grid.get(k) for k in ((i, j), (i+1, j), (i+1, j+1), (i, j+1))]
    if all(q): bm.faces.new(q)
me = bpy.data.meshes.new('glass'); bm.to_mesh(me); bm.free()
glass = finish(me, 'panel_glass', PANELP, 'control_panel'); proj_uv(glass, 'panelproj')

# stripe (tapered, 1.1 → 1.0 cm) and logo on the arm face
def strip(name, pts, z, m, part=None):
    bm = bmesh.new(); vs = [bm.verts.new(V(x, y, z)) for x, y in pts]; bm.faces.new(vs)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); return finish(me, name, m, part, smooth=False)
strip('stripe_front', [(HL+.9, 20.25), (67.9, 19.75), (67.6, 20.62), (HL+.9, 21.35)], ZA+.02, CYAN)
bm = bmesh.new(); vs = [bm.verts.new(V(HL-.02, y, z)) for z, y in [(ZA-1.35, 20.25), (ZA-1.35, 21.35), (ZAB+1.35, 21.45), (ZAB+1.35, 20.35)]]
bm.faces.new(vs); me = bpy.data.meshes.new('sl'); bm.to_mesh(me); bm.free(); finish(me, 'stripe_left', CYAN, None, smooth=False)
lg = strip('logo_jack', [(52.2, 15.9), (60.7, 15.9), (60.7, 18.4), (52.2, 18.4)], ZA+.03, LOGO)
plane_uv(lg, lambda x, y, z: ((x-52.2)/8.5, (y-15.9)/2.5))
# pillar sticker + oil window, motor front (rectified photo textures)
stk = strip('sticker_a7', [(72.0, 3.6), (90.0, 3.6), (90.0, 13.9), (72.0, 13.9)], ZP+.03, STICK)
plane_uv(stk, lambda x, y, z: ((x-72.0)/18.0, (y-3.6)/10.3))
rbox('oil_window', 81.1, 2.4, ZP+.05, 1.5, 2.7, .5, .65, CLEAR, 'oil_window')
box('oil_window_mark', 81.03, 81.17, 1.6, 3.3, ZP+.32, ZP+.28, RED, 'oil_window')

# motor housing + dial
mo = rpoly([(MOT['x0'], MOT['y0']), (MOT['x1'], MOT['y0']), (MOT['x1'], MOT['y1']), (MOT['x0'], MOT['y1'])], [.4, 1.2, 2.4, 1.0], 8)
motor = prism('servo_motor', mo, MOT['zf'], MOT['zb'], GREYM, 'servo_motor', bevel=.9, seg=4)
mf = strip('motor_front_print', [(90.9, .7), (95.3, .7), (95.3, 8.4), (90.9, 8.4)], MOT['zf']+.02, MOTF, 'servo_motor')
plane_uv(mf, lambda x, y, z: ((x-89.6)/8.2, y/24.0))
box('motor_seam', MOT['x0']-.15, MOT['x0']+.15, .4, MOT['y1']-.6, MOT['zf']-.05, MOT['zb']+.4, GREYD, 'servo_motor')
DC = (MOT['x1']+.05, 13.0, -21.5)
cyl('dial_frame', (DC[0]-.1, DC[1], DC[2]), 'x', 7.1, .5, GREYL, 'handwheel', seg=72)
cyl('dial', (DC[0]+.25, DC[1], DC[2]), 'x', 6.3, .6, GREYD, 'handwheel', seg=72)
for i, rr in enumerate((5.6, 4.4, 3.2)):
    bpy.ops.mesh.primitive_torus_add(major_radius=rr, minor_radius=.16, major_segments=72, location=V(DC[0]+.6, DC[1], DC[2]))
    o = bpy.context.active_object; o.name = f'dial_ring{i}'
    for coll in o.users_collection: coll.objects.unlink(o)
    link(o, 'handwheel'); o.rotation_euler = (0, math.pi/2, 0); o.data.materials.append(GREYL if i == 0 else GREYD)
for i in range(16):
    a = i/16*2*math.pi; y = DC[1]+math.sin(a)*3.8; z = DC[2]+math.cos(a)*3.8
    o = box(f'dial_fin{i}', DC[0]+.5, DC[0]+.85, y-.18, y+.18, z+.9, z-.9, GREYD, 'handwheel')
cyl('dial_hub', (DC[0]+.75, DC[1], DC[2]), 'x', 1.7, .7, GREYL, 'handwheel', r2=1.5)

# ---- top cover details (back-projected on y = TOP)
T_ = TOP
knurl('presser_screw_nut', (44.9, T_+.32, -22.0), 'y', 1.05, .64, 'presser_pressure_screw')
cyl('presser_screw_thread', (44.9, T_+1.2, -22.0), 'y', .55, 1.4, STEEL, 'presser_pressure_screw', seg=24)
knurl('presser_screw_cap', (44.9, T_+2.15, -22.0), 'y', .92, .65, 'presser_pressure_screw', teeth=24)
box('presser_screw_slot', 44.2, 45.6, T_+2.42, T_+2.5, -21.93, -22.07, BLACK)
for nm, x, z, r in (('plug_a', 46.6, -20.7, .42), ('plug_b', 48.8, -21.3, .55), ('plug_big', 49.0, -19.1, .78), ('hole_s', 51.2, -18.2, .36), ('plug_l', 44.9, -19.3, .55)):
    cyl(nm, (x, T_+.06, z), 'y', r, .16, BLACK, None, seg=32, r2=r*.93)
cyl('thread_guide_rod', (56.5, T_+2.2, -24.2), 'y', .25, 4.4, CHROME, 'arm_thread_guide', seg=14)
box('thread_guide_rod_plate', 56.4, 56.6, T_+2.6, T_+4.3, -23.85, -24.55, CHROME, 'arm_thread_guide')
for i, yy in enumerate((T_+2.9, T_+3.5, T_+4.1)): cyl(f'rod_hole{i}', (56.62, yy, -24.2), 'x', .1, .05, BLACK, seg=10)
cyl('winder_base', (62.4, T_+.08, -20.0), 'y', 2.05, .16, CHROME, 'bobbin_winder', seg=48)
cyl('winder_disc', (62.4, T_+.5, -19.8), 'y', 1.45, .55, CHROME, 'bobbin_winder', seg=48)
cyl('winder_spindle', (62.0, T_+1.35, -19.6), 'y', .3, 1.3, BLACK, 'bobbin_winder', seg=16)
wa = rbox('winder_arm', 0, 0, 0, 2.6, .4, .9, .2, CHROME, 'bobbin_winder'); wa.location = V(64.4, T_+.6, -19.5); wa.rotation_euler = (0, 0, -.35)
cyl('winder_screw', (62.6, T_+.1, -17.7), 'y', .5, .14, STEEL, 'bobbin_winder', seg=20)
box('winder_lever_stud', 69.9, 70.5, T_+.1, T_+1.3, -18.0, -18.6, BLACK, 'bobbin_winder', bevel=.1)
box('winder_lever_plate', 69.4, 71.2, T_+.05, T_+.2, -17.6, -18.9, CHROME, 'bobbin_winder')
cyl('winder_tension_base', (74.5, T_+.25, -19.8), 'y', .75, .5, CHROME, 'bobbin_winder', seg=24)
cyl('winder_tension_discs', (74.5, T_+.9, -19.8), 'y', .62, .5, CHROME, 'bobbin_winder', seg=24)
cyl('winder_tension_cap', (74.5, T_+2.0, -19.8), 'y', .55, .9, GREYL, 'bobbin_winder', seg=24)
cyl('winder_clear_guide', (75.7, T_+.9, -18.7), 'y', .55, 1.8, CLEAR, 'bobbin_winder', seg=24)
cyl('top_black_cap', (79.5, T_+.06, -21.0), 'y', 1.42, .16, BLACK, None, seg=48)
for nm, x, z in (('front_hole_l', 75.3, -15.5), ('front_hole_r', 84.2, -14.9)): cyl(nm, (x, T_+.04, z), 'y', .4, .1, BLACK)

# ---- needle-head front (z = ZA)
zf = ZA
tube('take_up_guard', [(44.2, 22.9, zf-.6), (44.0, 22.6, zf+.6), (44.05, 20.0, zf+1.25), (44.6, 15.0, zf+1.25), (45.6, 13.2, zf+.9), (46.4, 12.6, zf+.2)], .3, CHROME, 'take_up_lever')
tube('take_up_guard_inner', [(45.6, 22.6, zf-.2), (45.4, 22.0, zf+.8), (45.45, 19.0, zf+1.0), (45.9, 15.5, zf+.9), (46.4, 14.3, zf+.3)], .2, CHROME, 'take_up_lever')
box('take_up_slot', 45.85, 46.35, 15.6, 20.6, zf+.03, zf+.01, BLACK)
tu_pivot = bpy.data.objects.new('take_up_lever_pivot', None); link(tu_pivot); tu_pivot.location = V(47.6, 19.0, zf)
tul = box('take_up_lever_arm', -2.0, .2, -.3, .3, 1.15, .05, CHROME, 'take_up_lever', bevel=.08); tul.parent = tu_pivot
bpy.ops.mesh.primitive_torus_add(major_radius=.3, minor_radius=.09, location=(0, 0, 0)); te = bpy.context.active_object; te.name = 'take_up_lever_eye'
for coll in te.users_collection: coll.objects.unlink(te)
link(te, 'take_up_lever'); te.parent = tu_pivot; te.location = V(-2.1, 0, .9); te.rotation_euler = (math.pi/2, 0, 0); te.data.materials.append(CHROME)
# upper disc (pre-tension) + thread guide bar
for i, (dz, r, m) in enumerate(((.25, 1.0, GREYL), (.6, .8, CHROME), (.85, .8, CHROME))):
    cyl(f'pretension_d{i}', (49.1, 20.6, zf+dz), 'z', r, .22 if i else .5, m, 'pretension', seg=40)
cyl('pretension_stud', (49.1, 20.6, zf+1.2), 'z', .2, 1.2, STEEL, 'pretension', seg=12)
knurl('pretension_nut', (49.1, 20.6, zf+1.65), 'z', .55, .6, 'pretension', teeth=20)
box('upper_guide_bar', 49.35, 49.75, 15.6, 20.0, zf+.45, zf+.2, CHROME, 'pretension', bevel=.1)
tube('upper_guide_hook', [(49.5, 15.8, zf+.5), (49.2, 15.3, zf+.6), (49.7, 15.0, zf+.6), (49.9, 15.4, zf+.5)], .07, CHROME, 'pretension')
tube('upper_guide_wire', [(50.4, 21.1, zf+.2), (51.0, 21.9, zf+.6), (51.5, 23.0, zf+.6)], .06, CHROME, 'pretension')
box('three_hole_guide', 47.9, 50.9, 14.95, 15.75, zf+.25, zf+.05, CHROME, 'needle_bar_guide', bevel=.1)
for i, xx in enumerate((48.6, 49.4, 50.2)): cyl(f'three_hole_{i}', (xx, 15.35, zf+.27), 'z', .14, .05, BLACK, seg=12)
# main tension, check spring, thread release
TX, TY = 48.5, 12.3
cyl('tension_base', (TX, TY, zf+.25), 'z', 1.3, .5, GREYL, 'tension_assembly', seg=48)
for i, dz in enumerate((.62, .9)): cyl(f'tension_disc{i}', (TX, TY, zf+dz), 'z', 1.0, .14, CHROME, 'tension_assembly', seg=48)
sp = [(TX+math.cos(a)*.5, TY+math.sin(a)*.5, zf+1.05+a/(2*math.pi*6)*.95) for a in np.linspace(0, 2*math.pi*6, 120)]
tube('tension_spring', sp, .05, STEEL, 'tension_assembly', flat='poly', res=3)
knurl('tension_nut', (TX, TY, zf+2.35), 'z', .85, .75, 'tension_assembly', teeth=26)
cyl('tension_nut_face', (TX, TY, zf+2.74), 'z', .6, .05, GREYL, 'tension_assembly')
cyl('tension_stud', (TX, TY, zf+1.5), 'z', .22, 2.6, STEEL, 'tension_assembly', seg=12)
ck = [(TX+math.cos(a)*1.45, TY+math.sin(a)*1.45, zf+.75) for a in np.linspace(math.radians(110), math.radians(330), 40)]
tube('check_spring', ck, .055, STEEL, 'check_spring', flat='poly', res=3)
tube('check_spring_arm', [ck[-1], (TX+1.0, TY-1.9, zf+.8), (TX+.6, TY-2.4, zf+.7)], .05, STEEL, 'check_spring', flat='poly')
box('lower_thread_guide', 45.6, 47.0, 11.0, 11.5, zf+.35, zf+.05, CHROME, 'needle_bar_guide', bevel=.08)
# blue reverse paddle (lower-left → upper-right), grey mount plate behind
box('reverse_mount', 51.9, 53.3, 13.4, 15.0, zf+.45, zf-.1, GREYL, 'reverse_lever', bevel=.25)
pad = rbox('reverse_lever', 0, 0, 0, 4.8, 1.35, .9, .5, CYAN, 'reverse_lever', bevel=.2)
pad.location = V(50.95, 12.7, zf+1.7); pad.rotation_euler = (0, 0, math.radians(50))

# ---- needle bar, needle, presser bar & foot
nb = bpy.data.objects.new('needle_bar_group', None); link(nb)
cyl('needle_bar', (NX, 7.8, NZ), 'y', .42, 6.0, CHROME, 'needle_bar', seg=24).parent = nb
box('needle_clamp', NX-.55, NX+.55, 4.3, 5.4, NZ+.6, NZ-.6, STEEL, 'needle_bar', bevel=.15).parent = nb
cyl('needle_bar_thread_guide', (NX, 5.9, NZ+.48), 'z', .16, .3, CHROME, 'needle_bar_guide').parent = nb
cyl('needle_shank', (NX, 3.7, NZ), 'y', .1, 1.4, CHROME, 'needle', seg=12).parent = nb
cyl('needle_blade', (NX, 2.25, NZ), 'y', .06, 1.5, CHROME, 'needle', seg=10, r2=.02).parent = nb
cyl('presser_bar', (NX-.1, 7.2, NZ-1.5), 'y', .42, 7.6, CHROME, 'presser_foot', seg=24)
box('presser_bar_clamp', NX-.6, NX+.6, 3.0, 4.4, NZ-.9, NZ-2.1, STEEL, 'presser_foot', bevel=.15)
box('presser_shank', NX-.45, NX+.45, 1.0, 3.2, NZ-.6, NZ-1.4, CHROME, 'presser_foot', bevel=.12)
foot = box('presser_sole', NX-.95, NX+.95, BED['top']+.08, BED['top']+.38, NZ+1.9, NZ-1.8, CHROME, 'presser_foot', bevel=.1)
box('presser_toe_gap', NX-.12, NX+.12, BED['top']+.08, BED['top']+.4, NZ+1.95, NZ+.4, STEEL)

# ---- needle plate (D shape), slide plate, round oil plate, feed dog (y = bed top)
yb = BED['top']
def flat(name, outline_xz, y0, y1, m, part=None, bevel=.04):
    bm = bmesh.new(); A_ = [bm.verts.new(V(x, y1, z)) for x, z in outline_xz]; B_ = [bm.verts.new(V(x, y0, z)) for x, z in outline_xz]
    bm.faces.new(A_); bm.faces.new(list(reversed(B_)))
    n = len(A_)
    for i in range(n): bm.faces.new([A_[i], B_[i], B_[(i+1) % n], A_[(i+1) % n]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return finish(me, name, m, part, bevel=bevel, seg=2)
D = [(43.4, -16.8)] + [(46.0+3.3*math.cos(a), -20.25+3.45*math.sin(a)) for a in np.linspace(-math.pi/2+.25, math.pi/2-.25, 24)][::-1] + [(43.9, -23.7)]
D = [(43.4, -16.8), (46.6, -16.8)] + [(46.6+2.7*math.cos(a), -20.25+3.45*math.sin(a)) for a in np.linspace(-math.pi/2, math.pi/2, 24)] + [(46.6, -23.7), (43.9, -23.7)]
flat('needle_plate', D, yb-.05, yb+.12, PLATEG, 'needle_plate')
flat('slide_plate', [(38.75, -16.8), (43.4, -16.8), (43.9, -23.65), (42.6, -23.65)], yb-.05, yb+.1, PLATEG, 'bobbin_case')
for nm, x, z, r in (('np_screw_f', 46.3, -17.7, .32), ('np_screw_b', 46.5, -22.1, .32), ('slide_hole', 40.0, -20.1, .28), ('needle_hole', NX, NZ, .12)):
    cyl(nm, (x, yb+.13, z), 'y', r, .03, BLACK, None, seg=20)
for i, dx in enumerate((-.85, .85)):
    box(f'feed_dog_slot{i}', NX+dx-.22, NX+dx+.22, yb+.12, yb+.14, NZ+1.6, NZ-1.6, BLACK)
    box(f'feed_dog{i}', NX+dx-.16, NX+dx+.16, yb+.12, yb+.24, NZ+1.3, NZ-1.3, GREYD, 'feed_dog')
cyl('round_oil_plate', (50.1, yb+.04, -18.8), 'y', 1.3, .1, PLATEG, None, seg=40)
for i, (dx, dz, r) in enumerate(((-.5, .2, .18), (.5, .2, .18), (0, -.55, .3))): cyl(f'round_oil_hole{i}', (50.1+dx, yb+.1, -18.8+dz), 'y', r, .02, BLACK, seg=16)

# ---- under the bed (hidden unless x-ray): hook, bobbin case, bobbin, trimmer
HY = -2.6
cyl('hook', (NX+.4, HY, NZ), 'x', 1.9, 1.3, STEEL, 'hook', seg=48)
cyl('hook_shaft', (NX+5, HY, NZ), 'x', .4, 8, STEEL, 'hook', seg=16)
cyl('bobbin_case', (NX-.5, HY, NZ), 'x', 1.4, 1.1, CHROME, 'bobbin_case', seg=40)
box('bobbin_case_latch', NX-1.2, NX-.95, HY-.3, HY+.6, NZ+.6, NZ-.6, STEEL, 'bobbin_case')
cyl('bobbin', (NX-1.25, HY, NZ), 'x', 1.05, .55, CONE, 'bobbin', seg=40)
cyl('bobbin_flange', (NX-1.6, HY, NZ), 'x', 1.12, .08, STEEL, 'bobbin', seg=40)
box('trimmer_knife', NX-.4, NX+2.4, -.9, -.75, NZ+.2, NZ-.5, STEEL, 'trimmer')
box('trimmer_link', NX+2.2, NX+2.6, -.9, -.75, NZ+.1, NZ-2.0, STEEL, 'trimmer')

# ---- threads (upper path + to the bobbin winder), saved as curves for the site
def thread(name, pts, m):
    o = tube(name, pts, .045, m, None, flat='poly', res=2); o['thread'] = 1; return o
THR = mat('thread', srgb('#ffffff'), .9)

# ==================================================================== EXPORT / RENDER
for o in ROOT.objects:
    if o.type == 'CURVE':
        bpy.context.view_layer.objects.active = o
for o in list(ROOT.objects):
    if o.type == 'CURVE':
        o.select_set(True)
bpy.context.view_layer.update()

os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'jack_a7.blend'))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'jack_a7.glb'), export_format='GLB', export_extras=True,
                          export_apply=True, export_yup=True, export_image_format='AUTO', use_selection=False)
print('EXPORTED', os.path.join(OUT, 'jack_a7.glb'))

if DO_RENDER:
    world = bpy.data.worlds.new('w'); scene.world = world; world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.85, .87, .9, 1); world.node_tree.nodes['Background'].inputs['Strength'].default_value = .9
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); scene.collection.objects.link(sun)
    sun.data.energy = 3.0; sun.rotation_euler = (math.radians(50), 0, math.radians(-30))
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = 1500, 2000; scene.render.resolution_percentage = 50
    for key in ('c2', 'c3'):
        c = CAL['cams'][key]; rv = Vector(c['r']); R = Matrix.Rotation(rv.length, 3, rv.normalized())
        Cw = -(R.transposed() @ Vector(c['t']))
        right, down, fwd = R[0], R[1], R[2]
        tob = lambda v: Vector((v[0], -v[2], v[1]))
        M3 = Matrix((tob(right), tob(-down), tob(-fwd))).transposed()
        cam = bpy.data.objects.new(key, bpy.data.cameras.new(key)); scene.collection.objects.link(cam)
        cam.matrix_world = Matrix.Translation(tob(Cw)) @ M3.to_4x4()
        cam.data.sensor_fit = 'VERTICAL'; cam.data.sensor_height = 36.0; cam.data.lens = c['f']*36.0/2000.0
        cam.data.clip_start = 1; cam.data.clip_end = 2000
        scene.camera = cam; scene.render.filepath = os.path.join(OUT, f'render_{key}.png')
        bpy.ops.render.render(write_still=True); print('RENDERED', scene.render.filepath)
