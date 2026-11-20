# 首が飛鳥：Blender（bpy）で板蓋宮と人物を作り、kubi.glb に書き出す
#   python3 tools/make_models.py -- 出力フォルダ
import bpy, bmesh, math, random, sys, os
from mathutils import Matrix, Vector, Euler

OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/home/claude/build"
os.makedirs(OUT, exist_ok=True)
random.seed(645)
bpy.ops.wm.read_factory_settings(use_empty=True)
COL = bpy.context.scene.collection
MATS = {}


def mat(name, col, rough=0.6, metal=0.0, alpha=1.0, emit=None):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (col[0], col[1], col[2], 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        try:
            m.blend_method = "BLEND"
        except Exception:
            pass
    if emit:
        for k in ("Emission Color", "Emission"):
            if k in b.inputs:
                b.inputs[k].default_value = (emit[0], emit[1], emit[2], 1)
                break
        if "Emission Strength" in b.inputs:
            b.inputs["Emission Strength"].default_value = emit[3] if len(emit) > 3 else 1.0
    MATS[name] = m
    return m


def TRS(loc=(0, 0, 0), rot=(0, 0, 0), scl=(1, 1, 1)):
    return Matrix.Translation(Vector(loc)) @ Euler(rot, "XYZ").to_matrix().to_4x4() @ Matrix.Diagonal((scl[0], scl[1], scl[2], 1))


class B:
    def __init__(s, name):
        s.name, s.bm, s.ms = name, bmesh.new(), []

    def mi(s, m):
        if m not in s.ms:
            s.ms.append(m)
        return s.ms.index(m)

    def _fin(s, verts, m, smooth):
        i = s.mi(m)
        fs = set()
        for v in verts:
            for f in v.link_faces:
                fs.add(f)
        for f in fs:
            f.material_index = i
            f.smooth = smooth

    def box(s, m, loc, size, rot=(0, 0, 0)):
        r = bmesh.ops.create_cube(s.bm, size=1, matrix=TRS(loc, rot, size))
        s._fin(r["verts"], m, False)

    def sph(s, m, loc, r, scl=(1, 1, 1), rot=(0, 0, 0), u=20, v=12):
        q = bmesh.ops.create_uvsphere(s.bm, u_segments=u, v_segments=v, radius=r, matrix=TRS(loc, rot, scl))
        s._fin(q["verts"], m, True)

    def cyl(s, m, loc, r1, r2, h, rot=(0, 0, 0), seg=18, smooth=True, scl=(1, 1, 1)):
        q = bmesh.ops.create_cone(s.bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r1, radius2=r2, depth=h, matrix=TRS(loc, rot, scl))
        i = s.mi(m)
        fs = set()
        for v in q["verts"]:
            for f in v.link_faces:
                fs.add(f)
        for f in fs:
            f.material_index = i
            f.smooth = smooth and len(f.verts) == 4

    def lathe(s, m, prof, seg=24, M=None, cap=True):
        M = M or Matrix.Identity(4)
        rings = []
        for r, z in prof:
            ring = [s.bm.verts.new(M @ Vector((r * math.cos(a * 2 * math.pi / seg), r * math.sin(a * 2 * math.pi / seg), z))) for a in range(seg)]
            rings.append(ring)
        vs = [v for r in rings for v in r]
        for a, b in zip(rings, rings[1:]):
            for i in range(seg):
                j = (i + 1) % seg
                s.bm.faces.new((a[i], a[j], b[j], b[i]))
        if cap:
            try:
                s.bm.faces.new(list(reversed(rings[0])))
                s.bm.faces.new(rings[-1])
            except Exception:
                pass
        i = s.mi(m)
        for v in vs:
            for f in v.link_faces:
                f.material_index = i
                f.smooth = len(f.verts) == 4

    def torus(s, m, loc, R, r, rot=(0, 0, 0), seg=20, ring=8, scl=(1, 1, 1)):
        M = TRS(loc, rot, scl)
        rs = []
        for a in range(seg):
            t = a * 2 * math.pi / seg
            row = []
            for b in range(ring):
                p = b * 2 * math.pi / ring
                q = R + r * math.cos(p)
                row.append(s.bm.verts.new(M @ Vector((q * math.cos(t), q * math.sin(t), r * math.sin(p)))))
            rs.append(row)
        i = s.mi(m)
        for a in range(seg):
            A, Bq = rs[a], rs[(a + 1) % seg]
            for b in range(ring):
                c = (b + 1) % ring
                f = s.bm.faces.new((A[b], Bq[b], Bq[c], A[c]))
                f.material_index = i
                f.smooth = True

    def done(s, loc=(0, 0, 0)):
        bmesh.ops.recalc_face_normals(s.bm, faces=s.bm.faces)
        me = bpy.data.meshes.new(s.name)
        s.bm.to_mesh(me)
        s.bm.free()
        for m in s.ms:
            me.materials.append(m)
        ob = bpy.data.objects.new(s.name, me)
        ob.location = loc
        COL.objects.link(ob)
        return ob


# ---------------- 色 ----------------
SHU = mat("shu", (0.62, 0.09, 0.04), 0.55)          # 朱の柱
SHU2 = mat("shu2", (0.33, 0.04, 0.022), 0.6)
W1 = mat("wood1", (0.20, 0.105, 0.05), 0.38)
W2 = mat("wood2", (0.24, 0.13, 0.062), 0.34)
W3 = mat("wood3", (0.165, 0.085, 0.042), 0.42)
WD = mat("woodd", (0.13, 0.08, 0.05), 0.75)
PLA = mat("plaster", (0.62, 0.55, 0.42), 0.95)
GRN = mat("renji", (0.10, 0.30, 0.20), 0.6)
STN = mat("stone", (0.46, 0.45, 0.42), 0.9)
GOLD = mat("gold", (0.90, 0.63, 0.16), 0.3, 0.9)
MISU = mat("misu", (0.72, 0.62, 0.34), 0.7, 0.0, 0.62)
CLO_R = mat("cloth_r", (0.70, 0.10, 0.10), 0.8)
CLO_Y = mat("cloth_y", (0.85, 0.66, 0.15), 0.8)
CLO_B = mat("cloth_b", (0.12, 0.22, 0.50), 0.8)
CLO_G = mat("cloth_g", (0.14, 0.42, 0.22), 0.8)
CLO_W = mat("cloth_w", (0.92, 0.90, 0.84), 0.8)
CLO_P = mat("cloth_p", (0.36, 0.12, 0.46), 0.8)
FIRE = mat("fire", (1.0, 0.65, 0.2), 0.5, 0, 1, (1.0, 0.55, 0.12, 4.0))
SKIN = mat("skin", (0.93, 0.74, 0.58), 0.55)
HAIR = mat("hair", (0.035, 0.03, 0.03), 0.5)
EYEW = mat("eyew", (0.97, 0.97, 0.95), 0.3)
MOUTH = mat("mouth", (0.25, 0.04, 0.04), 0.6)
NECK = mat("neckcut", (0.80, 0.52, 0.45), 0.7)
STEEL = mat("steel", (0.92, 0.94, 0.98), 0.22, 0.55)
PAPER = mat("paper", (0.95, 0.92, 0.80), 0.9)
INK = mat("ink", (0.08, 0.07, 0.07), 0.8)

# ---------------- 板蓋宮（まっすぐ奥が +Y＝ゲームでは -Z。入口は -Y） ----------------
HW, D0, D1, PH = 7.0, -13.0, 13.0, 6.0      # 半分の幅、手前、奥、柱の高さ
PX = 4.2                                    # 柱の列の位置
h = B("hall")
# 床板
n = 28
for i in range(n):
    x = -HW + (i + 0.5) * (2 * HW / n)
    h.box([W1, W2, W3, W2][(i * 7 + i // 3) % 4], (x, 0, -0.06), (2 * HW / n - 0.012, D1 - D0, 0.12))
# 柱・礎石・斗
ys = [D0 + 1.5 + k * 3.5 for k in range(8)]
for sx in (-PX, PX):
    for y in ys:
        h.cyl(STN, (sx, y, 0.06), 0.46, 0.40, 0.12, seg=20)
        h.cyl(SHU, (sx, y, PH / 2 + 0.1), 0.27, 0.24, PH, seg=22)
        h.box(SHU2, (sx, y, PH + 0.22), (0.86, 0.86, 0.24))
        h.box(SHU2, (sx, y, PH + 0.48), (1.25, 0.5, 0.26))
        h.torus(GOLD, (sx, y, 0.42), 0.275, 0.022, seg=22, ring=6)
        h.torus(GOLD, (sx, y, PH - 0.3), 0.25, 0.022, seg=22, ring=6)
    h.box(SHU2, (sx, 0, PH + 0.78), (0.42, D1 - D0, 0.36))
# 梁
for y in ys:
    h.box(SHU2, (0, y, PH + 1.1), (2 * HW + 0.2, 0.36, 0.42))
    h.box(WD, (0, y, PH + 2.3), (0.26, 0.26, 2.0))
# 屋根（板ぶき）と垂木
for sgn in (-1, 1):
    ang = math.atan2(2.4, HW)
    h.box(WD, (sgn * HW / 2, 0, PH + 2.2), (HW / math.cos(ang) + 0.8, D1 - D0 + 1.2, 0.1), (0, sgn * ang, 0))
    for k in range(18):
        y = D0 + 0.8 + k * (D1 - D0 - 1.6) / 17
        h.box(W3, (sgn * HW / 2, y, PH + 2.08), (HW / math.cos(ang) + 0.4, 0.14, 0.16), (0, sgn * ang, 0))
h.box(SHU2, (0, 0, PH + 3.32), (0.34, D1 - D0, 0.34))
# 壁：下のしっくい＋れんじ窓（緑の格子）＋上のしっくい
for sgn in (-1, 1):
    x = sgn * HW
    h.box(PLA, (x, 0, 0.7), (0.24, D1 - D0, 1.4))
    h.box(PLA, (x, 0, 5.0), (0.24, D1 - D0, 2.4))
    h.box(SHU2, (x, 0, 1.42), (0.34, D1 - D0, 0.16))
    h.box(SHU2, (x, 0, 3.78), (0.34, D1 - D0, 0.16))
    for k in range(9):
        y = D0 + k * (D1 - D0) / 8
        h.box(SHU, (x, y, 3.1), (0.36, 0.34, 6.2))
    yy = D0 + 0.35
    while yy < D1 - 0.3:
        h.box(GRN, (x, yy, 2.6), (0.10, 0.09, 2.3), (0, 0, math.pi / 4))
        yy += 0.27
# 奥の壁
h.box(PLA, (0, D1, 3.6), (2 * HW, 0.24, 7.4))
h.box(SHU2, (0, D1 - 0.14, 6.1), (2 * HW, 0.2, 0.3))
# 入口側：上だけ壁、下は大きく開いている
h.box(PLA, (0, D0, 6.3), (2 * HW, 0.24, 2.6))
h.box(SHU2, (0, D0, 4.9), (2 * HW, 0.34, 0.34))
for sx in (-HW + 1.2, HW - 1.2):
    h.box(PLA, (sx, D0, 2.4), (2.4, 0.24, 4.8))
for sx in (-HW + 2.5, HW - 2.5):
    h.box(SHU, (sx, D0, 2.5), (0.4, 0.4, 5.0))
# 壇（天皇の座）と階段
h.box(W3, (0, D1 - 2.3, 0.35), (9.0, 4.4, 0.7))
h.box(SHU2, (0, D1 - 4.52, 0.35), (9.1, 0.08, 0.72))
for k in range(3):
    h.box(W2, (0, D1 - 4.75 - k * 0.34, 0.52 - k * 0.2), (3.2, 0.34, 0.2))
h.box(GOLD, (0, D1 - 4.5, 0.72), (9.1, 0.1, 0.05))
# 御簾をつるす横木と、帽額（赤と金の幕）
h.box(SHU2, (0, D1 - 3.6, 4.3), (9.2, 0.22, 0.26))
h.box(CLO_R, (0, D1 - 3.62, 3.92), (9.0, 0.06, 0.5))
h.box(GOLD, (0, D1 - 3.66, 3.68), (9.0, 0.04, 0.05))
for k in range(7):
    h.box(CLO_Y, (-3.9 + k * 1.3, D1 - 3.67, 3.95), (0.12, 0.03, 0.44))
for sx in (-4.5, 4.5):
    h.box(SHU, (sx, D1 - 3.6, 2.5), (0.3, 0.3, 3.7))
# 天井から下がる幡（はた）
cl = [CLO_R, CLO_Y, CLO_B, CLO_G, CLO_W, CLO_P]
for k, y in enumerate(ys[1:7]):
    for sgn in (-1, 1):
        x = sgn * (PX - 0.75)
        m = cl[(k * 2 + (sgn > 0)) % 6]
        h.box(GOLD, (x, y + 0.4, PH + 0.75), (0.5, 0.05, 0.08))
        h.box(m, (x, y + 0.4, PH - 0.35), (0.42, 0.03, 2.2))
        h.box(cl[(k + 3) % 6], (x, y + 0.4, PH - 1.75), (0.42, 0.03, 0.6))
        for t in (-0.14, 0, 0.14):
            h.box(m, (x + t, y + 0.4, PH - 2.4), (0.09, 0.03, 0.7))
# 灯台（火は別の物にする）
LAMPS = [(-2.6, D1 - 5.6), (2.6, D1 - 5.6), (-3.3, 2.5), (3.3, 2.5)]
for (x, y) in LAMPS:
    h.cyl(WD, (x, y, 0.04), 0.2, 0.16, 0.08, seg=14)
    h.cyl(WD, (x, y, 0.7), 0.03, 0.03, 1.3, seg=8)
    h.cyl(GOLD, (x, y, 1.38), 0.08, 0.16, 0.08, seg=14)
h.done()
f = B("flame")
f.sph(FIRE, (0, 0, 0.06), 0.06, (0.8, 0.8, 1.7), u=10, v=8)
f.done()

# 御簾
ms = B("misu")
z = 0.75
while z < 3.7:
    ms.box(MISU, (0, 0, z), (8.8, 0.025, 0.05))
    z += 0.065
for x in (-3.3, -1.1, 1.1, 3.3):
    ms.box(CLO_R, (x, -0.02, 2.2), (0.1, 0.02, 3.0))
ms.done((0, D1 - 3.6, 0))


# ---------------- 人物 ----------------
def head(name, hat, face="calm", beard=False, skin=SKIN, hatm=None, mask=None):
    b = B(name)
    hm = hatm or HAIR
    b.cyl(skin, (0, 0, 0.03), 0.062, 0.058, 0.12, seg=14)
    b.cyl(NECK, (0, 0, -0.031), 0.060, 0.060, 0.004, seg=14)
    b.sph(skin, (0, 0, 0.185), 0.135, (0.96, 1.0, 1.12), u=24, v=16)
    b.sph(skin, (0, -0.02, 0.12), 0.105, (0.92, 0.95, 0.9), u=18, v=10)          # あご
    for sx in (-1, 1):
        b.sph(skin, (sx * 0.128, 0.0, 0.18), 0.03, (0.5, 0.8, 1.2), u=8, v=6)   # 耳
    b.sph(skin, (0, -0.132, 0.165), 0.022, (0.9, 1.0, 1.2), u=8, v=6)            # 鼻
    b.sph(HAIR, (0, 0.022, 0.215), 0.137, (0.98, 1.0, 1.08), u=20, v=12)         # 髪
    if face == "calm":
        for sx in (-1, 1):
            b.sph(INK, (sx * 0.05, -0.122, 0.2), 0.016, (1.25, 0.5, 0.75), u=8, v=6)
            b.box(HAIR, (sx * 0.05, -0.127, 0.232), (0.05, 0.012, 0.011), (0, sx * -0.25, 0))
        b.box(MOUTH, (0, -0.122, 0.118), (0.04, 0.012, 0.008))
    else:  # びっくり顔
        for sx in (-1, 1):
            b.sph(EYEW, (sx * 0.052, -0.112, 0.205), 0.036, (1.0, 0.55, 1.1), u=12, v=8)
            b.sph(INK, (sx * 0.052, -0.134, 0.205), 0.011, (1, 0.5, 1), u=8, v=6)
            b.box(HAIR, (sx * 0.052, -0.118, 0.262), (0.055, 0.012, 0.012), (0, sx * 0.45, 0))
        b.sph(MOUTH, (0, -0.108, 0.108), 0.036, (1.0, 0.5, 1.25), u=12, v=8)
    if beard:
        b.sph(HAIR, (0, -0.085, 0.082), 0.07, (0.95, 0.75, 1.0), u=12, v=8)
        b.box(HAIR, (0, -0.132, 0.137), (0.085, 0.014, 0.014))
    if mask:
        b.sph(mask, (0, -0.012, 0.135), 0.135, (0.99, 1.02, 0.78), u=18, v=10)
    if hat == "kanmuri":     # 冠（黒い布の冠。うしろが高い）
        b.cyl(hm, (0, 0.0, 0.325), 0.125, 0.105, 0.09, seg=18)
        b.box(hm, (0, 0.055, 0.42), (0.11, 0.07, 0.17), (0.15, 0, 0))
        b.box(hm, (0, 0.09, 0.3), (0.05, 0.02, 0.26), (-0.5, 0, 0))
    elif hat == "crown":     # 宝冠
        b.cyl(GOLD, (0, 0, 0.34), 0.125, 0.14, 0.09, seg=18)
        for k in range(8):
            a = k * math.pi / 4
            b.sph(GOLD, (0.13 * math.cos(a), 0.13 * math.sin(a), 0.41), 0.022, (1, 1, 1.6), u=6, v=4)
        b.sph(HAIR, (0, 0.02, 0.39), 0.06, u=10, v=6)
    elif hat == "mizura":    # みずら（皇子）
        b.sph(HAIR, (0, 0.03, 0.34), 0.05, (1, 1, 0.8), u=10, v=6)
        for sx in (-1, 1):
            b.sph(HAIR, (sx * 0.15, 0.0, 0.12), 0.042, (0.8, 0.9, 1.5), u=10, v=6)
            b.torus(CLO_R, (sx * 0.15, 0, 0.14), 0.036, 0.011, seg=10, ring=5)
    elif hat == "hood":
        b.sph(hm, (0, 0.012, 0.2), 0.145, (0.99, 1.0, 1.1), u=20, v=12)
        b.box(hm, (0, 0.1, 0.1), (0.05, 0.03, 0.3), (-0.35, 0, 0))
    return b.done((0, 0, 1.46))


def arm(name, robe, trim, skin=SKIN, side=1):
    b = B(name)
    b.sph(robe, (0, 0, 0), 0.105, u=14, v=8)
    b.lathe(robe, [(0.095, 0.0), (0.105, -0.2), (0.13, -0.42), (0.15, -0.54)], seg=14, M=TRS(scl=(1, 0.8, 1)))
    b.torus(trim, (0, 0, -0.54), 0.137, 0.018, seg=14, ring=6, scl=(1, 0.8, 1))
    b.sph(skin, (0, 0, -0.6), 0.052, (0.9, 0.9, 1.1), u=10, v=6)
    return b.done((side * 0.25, 0, 1.36))


def figure(name, robe, trim, hat, beard=False, hatm=None, mask=None, skin=SKIN, shock=False, belt=None):
    b = B(name + "_body")
    b.lathe(robe, [(0.36, 0.0), (0.33, 0.25), (0.27, 0.7), (0.235, 0.98), (0.25, 1.2), (0.245, 1.36), (0.15, 1.45), (0.075, 1.475)], seg=24, M=TRS(scl=(1, 0.74, 1)))
    b.torus(trim, (0, 0, 0.02), 0.35, 0.022, seg=24, ring=6, scl=(1, 0.74, 1))
    b.torus(belt or trim, (0, 0, 1.0), 0.235, 0.032, seg=24, ring=6, scl=(1, 0.76, 1))
    b.box(trim, (-0.035, -0.175, 1.3), (0.05, 0.02, 0.36), (0.12, 0.42, 0))     # えり
    b.box(trim, (0.035, -0.178, 1.3), (0.05, 0.02, 0.36), (0.12, -0.42, 0))
    b.cyl(NECK, (0, 0, 1.478), 0.066, 0.066, 0.006, seg=14)
    for sx in (-1, 1):                                                          # くつ
        b.sph(HAIR, (sx * 0.12, -0.25, 0.04), 0.07, (0.8, 1.5, 0.6), u=10, v=6)
    b.done()
    head(name + "_head", hat, "calm", beard, skin, hatm, mask)
    if shock:
        head(name + "_headS", hat, "shock", beard, skin, hatm, mask)
    arm(name + "_armL", robe, trim, skin, -1)
    arm(name + "_armR", robe, trim, skin, 1)


figure("prince", mat("r_prince", (0.90, 0.90, 0.86), 0.75), CLO_R, "mizura", shock=True, belt=CLO_R)
figure("iruka", mat("r_iruka", (0.30, 0.09, 0.40), 0.7), GOLD, "kanmuri", beard=True, hatm=mat("kan_p", (0.22, 0.05, 0.30), 0.6), shock=True)
figure("maro", mat("r_maro", (0.16, 0.38, 0.24), 0.75), CLO_Y, "kanmuri")
figure("tenno", mat("r_tenno", (0.72, 0.12, 0.10), 0.7), GOLD, "crown")
figure("assassin", mat("r_kage", (0.05, 0.05, 0.06), 0.85), mat("r_kage2", (0.16, 0.16, 0.18), 0.8), "hood", hatm=mat("r_kage", (0.05, 0.05, 0.06), 0.85), mask=mat("r_kage", (0.05, 0.05, 0.06), 0.85))
figure("kamatari", mat("r_kama", (0.45, 0.30, 0.16), 0.75), CLO_B, "kanmuri")
figure("guard", mat("r_guard", (0.22, 0.30, 0.42), 0.75), CLO_W, "kanmuri", hatm=mat("kan_b", (0.10, 0.14, 0.24), 0.6))

# ---------------- 小道具 ----------------
s = B("sword")                        # 直刀（柄を持つ所が原点、刃は +Z）
s.box(STEEL, (0, 0, 0.56), (0.062, 0.02, 0.92))
s.box(STEEL, (0, 0, 1.03), (0.044, 0.018, 0.044), (0, math.pi / 4, 0))
s.box(GOLD, (0, 0, 0.09), (0.09, 0.05, 0.022))
s.cyl(WD, (0, 0, 0.0), 0.02, 0.02, 0.17, seg=10)
s.torus(GOLD, (0, 0, -0.12), 0.032, 0.009, rot=(math.pi / 2, 0, 0), seg=14, ring=6)
s.done()

sc = B("scroll")                      # 上表文（開いた巻物。原点はまん中）
for k in range(8):
    a = (k - 3.5) * 0.09
    sc.box(PAPER, (0, math.sin(a * 2.2) * 0.02, -k * 0.055 + 0.19), (0.34, 0.006, 0.058), (a * 0.5, 0, 0))
for k in range(5):
    sc.box(INK, (-0.11 + k * 0.055, -0.006, 0.02), (0.012, 0.004, 0.3))
sc.cyl(WD, (0, 0, 0.225), 0.022, 0.022, 0.4, rot=(0, math.pi / 2, 0), seg=10)
sc.cyl(WD, (0, 0, -0.225), 0.022, 0.022, 0.4, rot=(0, math.pi / 2, 0), seg=10)
sc.done()

bw = B("bow")                         # 鎌足の弓
for k in range(14):
    t = (k - 6.5) / 6.5
    bw.cyl(WD, (0, -0.16 * (1 - t * t), t * 0.8), 0.014, 0.014, 0.135, rot=(-t * 0.42, 0, 0), seg=6)
bw.cyl(PAPER, (0, 0, 0), 0.003, 0.003, 1.66, seg=4)
bw.done()

g = B("gorinto")                      # 首塚（五輪塔）
g.box(STN, (0, 0, 0.06), (0.9, 0.9, 0.12))
g.box(STN, (0, 0, 0.36), (0.6, 0.6, 0.5))
g.sph(STN, (0, 0, 0.84), 0.3, (1, 1, 0.82), u=16, v=10)
g.cyl(STN, (0, 0, 1.2), 0.42, 0.1, 0.28, seg=4, smooth=False, rot=(0, 0, math.pi / 4))
g.sph(STN, (0, 0, 1.38), 0.14, (1, 1, 0.6), u=12, v=8)
g.sph(STN, (0, 0, 1.52), 0.1, (0.9, 0.9, 1.25), u=12, v=8)
g.done()

mt = B("mat")                         # 入鹿が座る敷物
mt.box(mat("tatami", (0.62, 0.60, 0.36), 0.9), (0, 0, 0.015), (1.6, 1.6, 0.03))
for sx in (-0.78, 0.78):
    mt.box(CLO_P, (sx, 0, 0.018), (0.1, 1.6, 0.034))
mt.done()

bpy.ops.object.select_all(action="SELECT")
path = os.path.join(OUT, "kubi.glb")
bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_apply=True, export_yup=True, use_selection=False)
tris = sum(len(p.vertices) - 2 for o in bpy.data.objects if o.type == "MESH" for p in o.data.polygons)
print("OK", path, os.path.getsize(path), "bytes", tris, "tris", len(bpy.data.objects), "objects")
