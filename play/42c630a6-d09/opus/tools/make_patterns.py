"""Generate origami crease patterns by simulating each model's folding sequence.

Each model is folded with simple flat folds (plus a few hand-built starting bases).
Every crease made is mapped back onto the flat sheet, giving the crease pattern.
Each interior vertex is then checked for local flat-foldability (Kawasaki + Maekawa
via crimp reduction). Output: Origami-Simulator-compatible SVGs + index.html.
"""
import math, os, re, sys, json

EPS = 1e-7
TOL = 1e-6   # vertex-merge tolerance (loosened for the imported crane)
OUT = sys.argv[1] if len(sys.argv) > 1 else "out"

# ---------- affine maps: (a,b,c,d,e,f) means x' = a x + b y + c, y' = d x + e y + f
I = (1, 0, 0, 0, 1, 0)
def ap(T, p): return (T[0]*p[0] + T[1]*p[1] + T[2], T[3]*p[0] + T[4]*p[1] + T[5])
def comp(A, B):  # A after B
    a, b, c, d, e, f = A; g, h, i, j, k, l = B
    return (a*g + b*j, a*h + b*k, a*i + b*l + c, d*g + e*j, d*h + e*k, d*i + e*l + f)
def inv(T):
    a, b, c, d, e, f = T; det = a*e - b*d
    return (e/det, -b/det, (b*f - c*e)/det, -d/det, a/det, (c*d - a*f)/det)
def flipped(T): return T[0]*T[4] - T[1]*T[3] < 0
def refl(p, q):
    """Reflection across the line through p and q."""
    dx, dy = q[0]-p[0], q[1]-p[1]; n = math.hypot(dx, dy); dx, dy = dx/n, dy/n
    a, b, d = 2*dx*dx-1, 2*dx*dy, 2*dy*dy-1
    return (a, b, p[0] - a*p[0] - b*p[1], b, d, p[1] - b*p[0] - d*p[1])

def side(p, q, r):
    return (q[0]-p[0])*(r[1]-p[1]) - (q[1]-p[1])*(r[0]-p[0])

def split(poly, p, q):
    """Split polygon by line pq -> (left part, right part, chord)."""
    L, R, chord = [], [], []
    n = len(poly)
    for k in range(n):
        a, b = poly[k], poly[(k+1) % n]
        sa, sb = side(p, q, a), side(p, q, b)
        if sa >= -EPS: L.append(a)
        if sa <= EPS: R.append(a)
        if abs(sa) <= EPS: chord.append(a)
        if (sa > EPS and sb < -EPS) or (sa < -EPS and sb > EPS):
            t = sa / (sa - sb); x = (a[0] + t*(b[0]-a[0]), a[1] + t*(b[1]-a[1]))
            L.append(x); R.append(x); chord.append(x)
    return L, R, chord

def area(poly):
    return sum(poly[k][0]*poly[(k+1) % len(poly)][1] - poly[(k+1) % len(poly)][0]*poly[k][1]
               for k in range(len(poly))) / 2

class Model:
    def __init__(self, name, outline, pieces=None, creases=None):
        self.name, self.outline = name, outline
        self.pieces = pieces or [dict(poly=outline, T=I, tags=set())]
        self.creases = creases or []      # (p, q, 'M'|'V')
        self.back = False                 # True once the model has been turned over

    def turn_over(self): self.back = not self.back

    def fold(self, p, q, toward, mv, select=lambda pc: True, tag=None, spine=None):
        """Fold along line pq (folded-state coords). Pieces on the side containing
        point `toward` move. mv = 'V'/'M' as seen by the folder, or a function of piece."""
        s_move = side(p, q, toward)
        R = refl(p, q); new = []
        for pc in self.pieces:
            if not select(pc):
                new.append(pc); continue
            Ti = inv(pc['T']); pp, qq = ap(Ti, p), ap(Ti, q)
            L, Rt, chord = split(pc['poly'], pp, qq)
            # orientation of paper-side split depends on whether piece is mirrored
            mv_side = s_move if not flipped(pc['T']) else -s_move
            mov, stay = (L, Rt) if mv_side > 0 else (Rt, L)
            m = mv(pc) if callable(mv) else mv
            if abs(area(mov)) > 1e-9 and abs(area(stay)) > 1e-9:
                if len(chord) >= 2:
                    paper_mv = m if (self.back ^ flipped(pc['T'])) is False else ('M' if m == 'V' else 'V')
                    self.creases.append((chord[0], chord[-1], paper_mv))
                new.append(dict(poly=stay, T=pc['T'], tags=set(pc['tags'])))
                new.append(dict(poly=mov, T=comp(R, pc['T']), tags=pc['tags'] | ({tag} if tag else set())))
            elif abs(area(mov)) > 1e-9:
                new.append(dict(poly=pc['poly'], T=comp(R, pc['T']), tags=pc['tags'] | ({tag} if tag else set())))
            else:
                new.append(pc)
        if spine:   # reverse fold: the spine crease inside the moved flap changes direction
            moved = [pc for pc in new if tag in pc['tags'] and pc not in self.pieces]
            cuts = [v for pc in moved for v in pc['poly'] if abs(side(*spine, v)) < 1e-9]
            out = []
            for a, b, mvv in self.creases:
                if abs(side(*spine, a)) > 1e-9 or abs(side(*spine, b)) > 1e-9:
                    out.append((a, b, mvv)); continue
                L2 = (b[0]-a[0])**2 + (b[1]-a[1])**2
                ts = sorted({0, 1} | {((c[0]-a[0])*(b[0]-a[0]) + (c[1]-a[1])*(b[1]-a[1])) / L2 for c in cuts} - {x for x in [] })
                ts = [t for t in ts if -1e-9 <= t <= 1+1e-9]
                for t0, t1 in zip(ts, ts[1:]):
                    if t1 - t0 < 1e-9: continue
                    pa = (a[0]+t0*(b[0]-a[0]), a[1]+t0*(b[1]-a[1])); pb = (a[0]+t1*(b[0]-a[0]), a[1]+t1*(b[1]-a[1]))
                    mid = ((pa[0]+pb[0])/2, (pa[1]+pb[1])/2)
                    inside = any(on_seg(mid, pc['poly'][k], pc['poly'][(k+1) % len(pc['poly'])]) for pc in moved for k in range(len(pc['poly'])))
                    out.append((pa, pb, ('M' if mvv == 'V' else 'V') if inside else mvv))
            self.creases = out
        self.pieces = new

# ---------- crease-pattern graph + flat-foldability check
def build_graph(creases, outline):
    segs = [(a, b, m) for a, b, m in creases]
    n = len(outline)
    segs += [(outline[k], outline[(k+1) % n], 'B') for k in range(n)]
    pts_on = [[s[0], s[1]] for s in segs]
    for i in range(len(segs)):
        for j in range(i+1, len(segs)):
            a, b, _ = segs[i]; c, d, _ = segs[j]
            r = (b[0]-a[0], b[1]-a[1]); s = (d[0]-c[0], d[1]-c[1])
            den = r[0]*s[1] - r[1]*s[0]
            if abs(den) < 1e-12:
                # collinear overlap: add endpoints lying inside
                if abs(side(a, b, c)) < 1e-9:
                    for e in (c, d):
                        if on_seg(e, a, b): pts_on[i].append(e)
                    for e in (a, b):
                        if on_seg(e, c, d): pts_on[j].append(e)
                continue
            t = ((c[0]-a[0])*s[1] - (c[1]-a[1])*s[0]) / den
            u = ((c[0]-a[0])*r[1] - (c[1]-a[1])*r[0]) / den
            if -1e-9 <= t <= 1+1e-9 and -1e-9 <= u <= 1+1e-9:
                x = (a[0]+t*r[0], a[1]+t*r[1]); pts_on[i].append(x); pts_on[j].append(x)
    verts = []
    def vid(p):
        for k, v in enumerate(verts):
            if abs(v[0]-p[0]) < TOL and abs(v[1]-p[1]) < TOL: return k
        verts.append(p); return len(verts)-1
    edges = {}
    for (a, b, m), pts in zip(segs, pts_on):
        L2 = (b[0]-a[0])**2 + (b[1]-a[1])**2
        ids = sorted({vid(p) for p in pts},
                     key=lambda k: ((verts[k][0]-a[0])*(b[0]-a[0]) + (verts[k][1]-a[1])*(b[1]-a[1])) / L2)
        for u, v in zip(ids, ids[1:]):
            key = (min(u, v), max(u, v))
            if key in edges and edges[key] != m:
                if 'B' in (edges[key], m): m = 'B'
                else: raise ValueError(f"conflicting crease {verts[u]}-{verts[v]}: {edges[key]} vs {m}")
            edges[key] = m
    return verts, edges

def on_seg(p, a, b):
    if abs(side(a, b, p)) > TOL*1e-3 + 1e-9: return False
    return min(a[0], b[0])-1e-9 <= p[0] <= max(a[0], b[0])+1e-9 and min(a[1], b[1])-1e-9 <= p[1] <= max(a[1], b[1])+1e-9

def check(verts, edges, full=None):
    """Return list of problems. full: set of edge keys that fold fully flat (default all)."""
    probs = []
    for k, v in enumerate(verts):
        inc = [(key, m) for key, m in edges.items() if k in key]
        if any(m == 'B' for _, m in inc): continue
        if full is not None and any(key not in full for key, _ in inc): continue
        cr = sorted((math.atan2(verts[key[0] if key[1] == k else key[1]][1]-v[1],
                                verts[key[0] if key[1] == k else key[1]][0]-v[0]) % (2*math.pi), m)
                    for key, m in inc)
        if not crimp_ok([c[0] for c in cr], [c[1] for c in cr]):
            probs.append((round(v[0], 4), round(v[1], 4), [(round(math.degrees(a), 2), m) for a, m in cr]))
    return probs

def crimp_ok(angles, mvs):
    n = len(angles)
    if n % 2: return False
    sec = [(angles[(i+1) % n] - angles[i]) % (2*math.pi) for i in range(n)]  # sector i: crease i -> i+1
    if abs(sum(sec[0::2]) - math.pi) > (0.02 if TOL > 1e-5 else 1e-6): return False   # Kawasaki
    mv = list(mvs)
    while len(mv) > 2:
        n = len(mv)
        for i in range(n):
            j = (i+1) % n
            tl = 0.02 if TOL > 1e-5 else 1e-9
            if sec[i] <= sec[i-1] + tl and sec[i] <= sec[j] + tl and mv[i] != mv[j]:
                merged = sec[i-1] - sec[i] + sec[j]
                keep = [k for k in range(n) if k not in (i, j)]
                sec = [merged if k == (i-1) % n else sec[k] for k in keep]
                mv = [mv[k] for k in keep]
                break
        else:
            return False
    return mv[0] == mv[1]

# ---------- models
def sailboat():
    m = Model("sailboat", [(0, 0), (1, 0), (1, 1), (0, 1)])
    m.fold((0, 0), (1, 1), (1, 0), 'M', tag='back')          # 1 fold in half diagonally, behind
    m.fold((0, .25), (.75, 1), (0, 0), 'V',                   # 2 hull: front layer strip up
           select=lambda pc: 'back' not in pc['tags'])
    m.fold((0, .25), (.75, 1), (0, 0), 'M',                   #   back layer strip up behind
           select=lambda pc: 'back' in pc['tags'])
    m.steps = ["Coloured side up, turn the square so it's a diamond. Fold it in half corner to corner, folding the bottom-right half <b>behind</b>, to make a triangle.",
               "Turn the triangle so its long folded edge is at the bottom. Fold a strip about a quarter of the way up along that long edge, front layer only.",
               "Turn over and fold the back layer up the same way. The strips stick out at both sides: that's the hull, and the big triangle is the sail."]
    m.view_rot = -45
    return m

def waterbomb_base(m, a, b, c, d, o, front_mv):
    """Hand-built flat waterbomb base. a,b = front-face corners; returns dict of tags."""
    pass

def waterbomb():
    m = Model("waterbomb", [(0, 0), (1, 0), (1, 1), (0, 1)])
    O = (.5, .5)
    R = refl(O, (1, 0)); Ry = refl((0, .5), (1, .5)); Rd = refl((0, 0), (1, 1))
    m.pieces = [dict(poly=[(0, 0), (1, 0), O], T=I, tags={'F', 'R', 'L'}),
                dict(poly=[(1, 0), (1, .5), O], T=R, tags={'F', 'R'}),
                dict(poly=[(1, .5), (1, 1), O], T=comp(R, Ry), tags={'K', 'R'}),
                dict(poly=[(1, 1), (0, 1), O], T=comp(R, comp(Ry, Rd)), tags={'K', 'R', 'L'}),
                dict(poly=[(0, 0), O, (0, .5)], T=Rd, tags={'F', 'L'}),
                dict(poly=[(0, .5), O, (0, 1)], T=comp(Rd, Ry), tags={'K', 'L'})]
    m.creases = [((0, 0), O, 'M'), ((1, 0), O, 'M'), ((1, 1), O, 'M'), ((0, 1), O, 'M'),
                 ((1, .5), O, 'V'), ((0, .5), O, 'V')]
    for face in ('F', 'K'):
        for s in (1, -1):   # right, left (mirror x -> 1-x)
            X = lambda x: .5 + s*(x - .5)
            sd = 'R' if s == 1 else 'L'
            sel = lambda pc, f=face, sd=sd: f in pc['tags'] and sd in pc['tags']
            ck = f'corner{face}{sd}'
            m.fold((X(.5), 0), (X(1), .5), (X(1), 0), 'V', select=sel, tag=ck)
            m.fold((X(.625), 0), (X(.625), 1), (X(1), .25), 'V', select=sel)
            sel2 = lambda pc, ck=ck: ck in pc['tags']
            m.fold((X(.5), .375), (X(.625), .375), (X(.5), .5), 'V', select=sel2)
            m.fold((X(.5), .25), (X(.625), .375), (X(.5), .5), 'V', select=sel2)
        m.turn_over()
    m.steps = ["Coloured side up: fold both diagonals (valley) and unfold. Turn over; fold in half both ways (valley) and unfold.",
               "Collapse into a <b>waterbomb base</b>: push the sides in so the square folds into a triangle with the point at the top.",
               "Fold the two bottom corners of the front layer up to the top point (makes a diamond).",
               "Fold the left and right corners of the diamond (front layers) in to the centre line.",
               "Fold the loose top flaps down, then tuck them into the pockets of the triangles you just made.",
               "Turn over and repeat steps 3–5 on the back.",
               "Blow gently into the hole at the bottom to inflate it into a cube-ish balloon."]
    m.view_rot = 0
    return m

def swan():
    m = Model("swan", [(0, 0), (1, 0), (1, 1), (0, 1)])
    t1, t2 = math.tan(math.radians(22.5)), math.tan(math.radians(33.75))
    m.fold((0, 0), (1, t1), (1, 0), 'V')                       # kite
    m.fold((0, 0), (t1, 1), (0, 1), 'V')
    m.turn_over()
    m.fold((0, 0), (1, t2), (1, 0), 'V')                       # narrow kite
    m.fold((0, 0), (t2, 1), (0, 1), 'V')
    m.fold((1, 0), (0, 1), (0, 0), 'V', tag='neck')            # point up to top
    m.fold((1, .72), (.72, 1), (1, 1), 'V', select=lambda pc: 'neck' in pc['tags'])  # head
    m.fold((0, 0), (1, 1), (0, 1), 'M', tag='half')            # in half, behind
    # neck/head are pulled up by hand at the end (not part of this flat pattern)
    m.steps = ["White side up, diamond orientation. Fold in half along the vertical diagonal and unfold.",
               "Fold the two lower edges to the centre crease (a kite).",
               "Turn over. Fold the lower edges to the centre again (a thin kite).",
               "Fold the thin bottom point up to the top point (this will be the neck).",
               "Fold the tip of that point back down a little (the head).",
               "Fold the model in half behind, along the centre line.",
               "Hold the body and pull the neck up and away from the body; pinch the base flat so it stays (outside reverse fold).",
               "Pull the head forward the same way. Done! (These last two shaping moves are done by eye and are not drawn on the crease pattern.)"]
    m.view_rot = -45
    return m

def frog():
    H = 1.6
    m = Model("jumping-frog", [(0, 0), (1, 0), (1, H), (0, H)])
    O, A, B, C, D = (.5, 1.1), (0, .6), (1, .6), (1, H), (0, H)
    Ry = refl((0, 1.1), (1, 1.1)); Rb = refl(O, B); Ra = refl(O, A)
    m.pieces = [dict(poly=[(0, 0), (1, 0), B, O, A], T=I, tags={'body'}),
                dict(poly=[B, (1, 1.1), O], T=Rb, tags=set()),
                dict(poly=[(1, 1.1), C, O], T=comp(Rb, Ry), tags={'flapR'}),
                dict(poly=[C, D, O], T=Ry, tags={'flapR', 'flapL'}),
                dict(poly=[A, O, (0, 1.1)], T=Ra, tags=set()),
                dict(poly=[(0, 1.1), O, D], T=comp(Ra, Ry), tags={'flapL'})]
    m.creases = [(A, O, 'V'), (B, O, 'V'), (C, O, 'V'), (D, O, 'V'), ((1, 1.1), O, 'M'), ((0, 1.1), O, 'M')]
    m.fold((.5, .6), (.75, .85), (1, .6), 'V', select=lambda pc: 'flapR' in pc['tags'])   # front legs
    m.fold((.5, .6), (.25, .85), (0, .6), 'V', select=lambda pc: 'flapL' in pc['tags'])
    m.fold((.75, 0), (.75, 1), (1, .3), 'M')                                               # sides behind
    m.fold((.25, 0), (.25, 1), (0, .3), 'M')
    m.fold((0, .3), (1, .3), (.5, 0), 'V', tag='up')                                       # spring pleat
    m.fold((0, .45), (1, .45), (.5, .6), 'V', select=lambda pc: 'up' in pc['tags'])
    m.steps = ["Use a 3×5 index card (or paper cut 5:8). White side up. Fold the top-right corner to the left edge and unfold; repeat with the top-left corner — an X crease.",
               "Turn over. Fold the top down through the centre of the X and unfold. Turn back over.",
               "Push the sides in at the horizontal crease and bring the top down: a triangle (waterbomb base) on top of the card.",
               "Fold the triangle's bottom corners (top layer) up to its top point — these are the front legs.",
               "Fold the left and right sides of the card <b>behind</b> to the centre.",
               "Fold the bottom edge up to the base of the triangle.",
               "Fold that flap back down in half — this zig-zag is the spring.",
               "Turn over. Press on the back edge and slide your finger off: it jumps!"]
    m.view_rot = 0
    return m

def crane():
    """Traditional crane from Origami Simulator (MIT, Amanda Ghassaei), renormalised."""
    src = open(os.path.join(os.path.dirname(__file__), '..', 'reference', 'traditionalCrane.svg')).read()
    rx, ry, rw, rh = (float(re.search(f'<rect[^>]* {k}="([-\\d.]+)"', src).group(1)) for k in ('x', 'y', 'width', 'height'))
    m = Model("crane", [(0, 0), (1, 0), (1, 1), (0, 1)])
    m.facets, m.angles = [], {}
    for el in re.findall(r'<line[^>]*/>', src):
        g = lambda k: re.search(f' {k}="([^"]*)"', el)
        col = g('stroke').group(1).upper()
        op = float(g('opacity').group(1)) if g('opacity') else 1.0
        p = ((float(g('x1').group(1)) - rx) / rw, 1 - (float(g('y1').group(1)) - ry) / rh)
        q = ((float(g('x2').group(1)) - rx) / rw, 1 - (float(g('y2').group(1)) - ry) / rh)
        p, q = tuple(round(v, 6) for v in p), tuple(round(v, 6) for v in q)
        if col == '#FFFF00': m.facets.append((p, q)); continue
        mv = {'#FF0000': 'M', '#0000FF': 'V'}[col]
        m.creases.append((p, q, mv)); m.angles[(p, q)] = op
    m.steps = ["Coloured side up: fold both diagonals (valley), unfold. Turn over; fold in half both ways, unfold.",
               "Collapse into a <b>preliminary (square) base</b>, open end pointing down.",
               "Fold the lower edges of the front layers to the centre line (kite), fold the top triangle down over them, then unfold these three folds.",
               "<b>Petal fold</b>: lift the bottom corner of the front layer up along the horizontal crease, letting the sides fold in on the kite creases. Flatten.",
               "Turn over and repeat steps 3–4: this is the <b>bird base</b>.",
               "Narrow the two lower flaps: fold their outer edges to the centre, front and back.",
               "Inside-reverse fold the two thin flaps up between the layers: one is the neck, one is the tail.",
               "Inside-reverse fold the tip of the neck to make the head. Fold the wings down and gently spread them."]
    m.view_rot = 0
    return m

# ---------- output
def to_px(p, outline, size=400, pad=20):
    W = max(x for x, _ in outline); Hh = max(y for _, y in outline); s = size / max(W, Hh)
    return pad + p[0]*s, pad + (Hh - p[1])*s

def cp_svg(m, verts, edges, for_sim=True):
    W = max(x for x, _ in m.outline); Hh = max(y for _, y in m.outline); s = 400 / max(W, Hh)
    w, h = W*s + 40, Hh*s + 40
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}">']
    col = {'M': '#ff0000', 'V': '#0000ff', 'B': '#000000'}
    dash = {'M': ' stroke-dasharray="10 3 2 3"', 'V': ' stroke-dasharray="6 4"', 'B': ''}
    for (a, b), mv in sorted(edges.items(), key=lambda e: e[1] == 'B'):
        p, q = to_px(verts[a], m.outline), to_px(verts[b], m.outline)
        op = ''
        if getattr(m, 'angles', None) and mv != 'B':
            op_v = crane_opacity(m, verts[a], verts[b])
            if op_v < 1: op = f' opacity="{op_v}"'
        style = '' if for_sim else dash[mv]
        out.append(f'<line x1="{p[0]:.3f}" y1="{p[1]:.3f}" x2="{q[0]:.3f}" y2="{q[1]:.3f}" stroke="{col[mv]}"{op}{style} stroke-width="{2 if mv == "B" else 1.5}" fill="none"/>')
    for p, q in getattr(m, 'facets', []):
        p, q = to_px(p, m.outline), to_px(q, m.outline)
        out.append(f'<line x1="{p[0]:.3f}" y1="{p[1]:.3f}" x2="{q[0]:.3f}" y2="{q[1]:.3f}" stroke="#ffff00" stroke-width="1" fill="none"/>')
    out.append('</svg>')
    return '\n'.join(out)

def crane_opacity(m, a, b):
    for (p, q), op in m.angles.items():
        if on_seg(a, p, q) and on_seg(b, p, q): return op
    return 1.0

def folded_svg(m):
    if m.name == 'crane': return ''
    th = math.radians(getattr(m, 'view_rot', 0))
    rot = lambda p: (p[0]*math.cos(th) - p[1]*math.sin(th), p[0]*math.sin(th) + p[1]*math.cos(th))
    polys = [[rot(ap(pc['T'], v)) for v in pc['poly']] for pc in m.pieces]
    xs = [x for P in polys for x, _ in P]; ys = [y for P in polys for _, y in P]
    x0, y0, s = min(xs), min(ys), 260 / max(max(xs)-min(xs), max(ys)-min(ys))
    w, h = (max(xs)-x0)*s + 20, (max(ys)-y0)*s + 20
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}">']
    for pc, P in zip(m.pieces, polys):
        fill = '#e8553a' if flipped(pc['T']) == m.__dict__.get('colour_flipped', False) else '#f4d6a0'
        pts = ' '.join(f'{10+(x-x0)*s:.1f},{10+(max(ys)-y)*s:.1f}' for x, y in P)
        out.append(f'<polygon points="{pts}" fill="{fill}" fill-opacity="0.45" stroke="#333" stroke-width="0.8"/>')
    out.append('</svg>')
    return '\n'.join(out)

def main():
    os.makedirs(os.path.join(OUT, 'crease-patterns'), exist_ok=True)
    models = [crane(), frog(), sailboat(), swan(), waterbomb()]
    report = {}
    global TOL
    for m in models:
        TOL = 2e-3 if m.name == 'crane' else 1e-6
        verts, edges = build_graph(m.creases, m.outline)
        full = None
        if m.name == 'crane':
            full = {k for k, mv in edges.items() if mv == 'B' or crane_opacity(m, verts[k[0]], verts[k[1]]) >= 1}
        probs = check(verts, edges, full)
        nM = sum(v == 'M' for v in edges.values()); nV = sum(v == 'V' for v in edges.values())
        report[m.name] = dict(vertices=len(verts), mountain=nM, valley=nV, problems=probs)
        print(f"{m.name:14s} verts={len(verts):3d} M={nM:3d} V={nV:3d} problems={len(probs)}")
        for p in probs: print("   ", p)
        m.svg_sim = cp_svg(m, verts, edges, True)
        m.svg_print = cp_svg(m, verts, edges, False)
        open(os.path.join(OUT, 'crease-patterns', f'{m.name}.svg'), 'w').write(m.svg_sim)
        m.folded = folded_svg(m)
        if m.folded: open(os.path.join('/tmp', f'folded-{m.name}.svg'), 'w').write(m.folded)
    write_html(models)
    return report

TITLES = {'crane': 'Crane', 'jumping-frog': 'Jumping frog', 'sailboat': 'Sailboat', 'swan': 'Swan', 'waterbomb': 'Waterbomb (balloon)'}
LEVEL = {'crane': 'Intermediate', 'jumping-frog': 'Beginner+', 'sailboat': 'Beginner', 'swan': 'Beginner', 'waterbomb': 'Beginner+'}
PAPER = {'crane': 'square', 'jumping-frog': '3×5 card (5:8)', 'sailboat': 'square', 'swan': 'square', 'waterbomb': 'square'}

def write_html(models):
    order = ['sailboat', 'swan', 'waterbomb', 'jumping-frog', 'crane']
    ms = sorted(models, key=lambda m: order.index(m.name))
    cards = []
    for m in ms:
        steps = ''.join(f'<li>{s}</li>' for s in m.steps)
        prev = f'<figure><div class="fold">{m.folded}</div><figcaption>Flat-folded shape (computed from the pattern)</figcaption></figure>' if m.folded else ''
        cards.append(f'''<section class="model" id="{m.name}">
<h2>{TITLES[m.name]} <small>{LEVEL[m.name]} · {PAPER[m.name]}</small></h2>
<div class="row"><figure><div class="cp">{m.svg_print}</div><figcaption>Crease pattern · <a href="crease-patterns/{m.name}.svg" download>download SVG for Origami Simulator</a></figcaption></figure>{prev}</div>
<ol>{steps}</ol></section>''')
    html = f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>Origami club — crease patterns</title>
<style>
body{{font:16px/1.5 system-ui,sans-serif;max-width:980px;margin:2rem auto;padding:0 1rem;color:#222}}
h1{{margin-bottom:.2rem}} .legend span{{display:inline-block;margin-right:1.5rem}}
.model{{border-top:2px solid #ddd;padding-top:1rem;margin-top:2rem;break-inside:avoid;page-break-before:always}}
.model h2 small{{font-weight:normal;color:#777;font-size:.8em}}
.row{{display:flex;gap:2rem;flex-wrap:wrap;align-items:flex-start}} figure{{margin:0}} figcaption{{font-size:.85rem;color:#555}}
.cp svg{{max-width:420px;height:auto}} .howto{{background:#f4f7ff;border-radius:8px;padding:1rem 1.2rem}}
@media print{{.howto,.noprint{{display:none}} .model{{border:0}}}}
</style>
<h1>Origami club — 5 models</h1>
<p class="legend"><span><svg width="50" height="8"><line x1="0" y1="4" x2="50" y2="4" stroke="#0000ff" stroke-width="2" stroke-dasharray="6 4"/></svg> valley fold</span>
<span><svg width="50" height="8"><line x1="0" y1="4" x2="50" y2="4" stroke="#ff0000" stroke-width="2" stroke-dasharray="10 3 2 3"/></svg> mountain fold</span>
<span>Patterns are viewed from the side facing you at step 1. Only creases that are folded in the finished model are drawn.</span></p>
<div class="howto noprint"><b>Watch each one fold:</b> open <a href="https://origamisimulator.org" target="_blank">origamisimulator.org</a>,
then drag one of the downloaded SVGs from <code>crease-patterns/</code> onto the page (or <i>File → Import</i>). Drag the <i>Fold Percent</i> slider from 0% to 100% (or press play)
to watch the flat sheet fold into the model in 3D; you can rotate it with the mouse. Tip: turn on <i>Strain</i> view to see where the paper is stressed.
The crane is also built in under <i>Examples → Origami → Traditional Crane</i>.
<br>Printing this page gives one model per page.</div>
{''.join(cards)}
<p style="font-size:.8rem;color:#777;margin-top:3rem">Crane crease pattern adapted from the Origami Simulator example set by Amanda Ghassaei (MIT licence).</p>
</html>'''
    open(os.path.join(OUT, 'index.html'), 'w').write(html)

if __name__ == '__main__':
    main()
