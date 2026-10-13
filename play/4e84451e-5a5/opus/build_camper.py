#!/usr/bin/env python3
"""Vintage camper van brick model: validates the build and renders an
instruction booklet (camper_van_instructions.html) with isometric SVG steps.

Coordinates: x = length in studs (0 = rear, 13 = front), y = width in studs
(0 = right side, 5 = left/driver side), z = height in plates (brick = 3 plates).
"""
import math
from collections import Counter, OrderedDict

L, W = 14, 6          # footprint in studs
PLATE = 0.4           # plate height in stud units (3.2mm / 8mm)

COLORS = {
    "Dark Turquoise":     ("#1E9AA4", False),
    "White":              ("#F6F6F2", False),
    "Light Bluish Gray":  ("#A3A9AE", False),
    "Dark Bluish Gray":   ("#5E6366", False),
    "Black":              ("#2B2B2B", False),
    "Reddish Brown":      ("#7A3B1C", False),
    "Tan":                ("#DCC593", False),
    "Red":                ("#C8261B", False),
    "Yellow":             ("#F4C21B", False),
    "Trans-Light Blue":   ("#9FE3EE", True),
    "Trans-Yellow":       ("#F7D63B", True),
    "Trans-Red":          ("#E0301E", True),
}

PART_NUMBERS = {
    ("brick", 1, 1): "3005", ("brick", 1, 2): "3004", ("brick", 1, 3): "3622",
    ("brick", 1, 4): "3010", ("brick", 1, 6): "3009", ("brick", 1, 8): "3008",
    ("brick", 2, 4): "3001",
    ("plate", 1, 1): "3024", ("plate", 1, 2): "3023", ("plate", 1, 3): "3623",
    ("plate", 1, 4): "3710", ("plate", 1, 6): "3666", ("plate", 2, 8): "3034",
    ("plate", 4, 4): "3031", ("plate", 4, 12): "3029", ("plate", 6, 6): "3958",
    ("plate", 6, 8): "3036", ("plate", 6, 14): "3456",
    ("tile", 1, 2): "3069b", ("round", 1, 1): "4073",
    ("technic", 1, 2): "3700",
}
KIND_HEIGHT = {"brick": 3, "technic": 3, "plate": 1, "tile": 1, "round": 1}
KIND_LABEL = {"brick": "Brick", "technic": "Technic brick (with hole)",
              "plate": "Plate", "tile": "Tile", "round": "Round plate"}


class Part:
    def __init__(self, kind, color, x, y, z, dx, dy):
        self.kind, self.color = kind, color
        self.x, self.y, self.z, self.dx, self.dy = x, y, z, dx, dy
        self.h = KIND_HEIGHT[kind]

    @property
    def studs(self):
        return self.kind != "tile"

    def cells(self):
        return [(i, j, k) for i in range(self.x, self.x + self.dx)
                for j in range(self.y, self.y + self.dy)
                for k in range(self.z, self.z + self.h)]

    def key(self):
        a, b = sorted((self.dx, self.dy))
        return (self.kind, a, b, self.color)

    def name(self):
        a, b = sorted((self.dx, self.dy))
        n = f"{KIND_LABEL[self.kind]} {a}x{b}"
        if self.kind == "technic":
            n = f"Technic brick {a}x{b} with hole"
        if self.kind == "brick" and COLORS[self.color][1] and (a, b) == (1, 2):
            n += " (no bottom tube)"
        return n

    def part_no(self):
        a, b = sorted((self.dx, self.dy))
        if self.kind == "brick" and COLORS[self.color][1] and (a, b) == (1, 2):
            return "3065"
        return PART_NUMBERS[(self.kind, a, b)]


class Axle:
    """Technic axle along y; x/z are centre-line coordinates (z in plates)."""
    color = "Light Bluish Gray"

    def __init__(self, x, z, y0, y1):
        self.x, self.z, self.y0, self.y1 = x, z, y0, y1

    def key(self):
        return ("axle", 8, 8, "Light Bluish Gray")


class Wheel:
    def __init__(self, x, z, y0, y1, r=2.2):
        self.x, self.z, self.y0, self.y1, self.r = x, z, y0, y1, r

    def key(self):
        return ("wheel", 0, 0, "Black")


# ---------------------------------------------------------------- the model
def B(c, x, y, z, dx, dy): return Part("brick", c, x, y, z, dx, dy)
def P(c, x, y, z, dx, dy): return Part("plate", c, x, y, z, dx, dy)
def T(c, x, y, z, dx, dy): return Part("tile", c, x, y, z, dx, dy)

DT, WH, LBG, DBG = "Dark Turquoise", "White", "Light Bluish Gray", "Dark Bluish Gray"
GL = "Trans-Light Blue"
AXLE_Z = 1.8   # hole centre of a 1x2 Technic brick, in plates

STEPS = [
    dict(title="Wheels and axles",
         text="Stand the 4 black Technic bricks on the table in two pairs, with a 4-stud gap "
              "inside each pair. Slide an 8-long axle through each pair, then push a wheel onto "
              "each end. Make sure the wheels spin freely!",
         parts=[Part("technic", "Black", 2, 0, 0, 2, 1), Part("technic", "Black", 2, 5, 0, 2, 1),
                Part("technic", "Black", 10, 0, 0, 2, 1), Part("technic", "Black", 10, 5, 0, 2, 1),
                Axle(3, AXLE_Z, -1, 7), Axle(11, AXLE_Z, -1, 7),
                Wheel(3, AXLE_Z, -1, -0.2), Wheel(3, AXLE_Z, 6.2, 7),
                Wheel(11, AXLE_Z, -1, -0.2), Wheel(11, AXLE_Z, 6.2, 7)]),
    dict(title="Chassis",
         text="Press the big 6x14 plate onto the Technic bricks. Each pair sits on the 3rd and 4th "
              "studs from one end. No 6x14 plate? Use a 6x8 plus a 6x6 placed side by side; the "
              "walls will lock them together.",
         parts=[P(DBG, 0, 0, 3, 14, 6)]),
    dict(title="Bumpers and side skirts",
         text="Gray bumpers go across the front and back. Turquoise plates run down both sides.",
         parts=[P(LBG, 13, 0, 4, 1, 6), P(LBG, 0, 0, 4, 1, 6),
                P(DT, 1, 0, 4, 6, 1), P(DT, 7, 0, 4, 6, 1),
                P(DT, 1, 5, 4, 6, 1), P(DT, 7, 5, 4, 6, 1)]),
    dict(title="Driver's cab",
         text="Build the dashboard, the steering wheel (on the driver's side), and a comfy bench "
              "seat with a tall backrest.",
         parts=[B(LBG, 12, 1, 4, 1, 4), Part("round", "Black", 12, 4, 7, 1, 1),
                B("Reddish Brown", 11, 1, 4, 1, 4),
                B("Reddish Brown", 10, 1, 4, 1, 4), B("Reddish Brown", 10, 1, 7, 1, 4)]),
    dict(title="Camping corner",
         text="Make a bed at the back with two pillows, and a little stove across from the door.",
         parts=[B("Tan", 1, 1, 4, 4, 2), B("Tan", 1, 3, 4, 4, 2),
                P("Red", 1, 1, 7, 4, 4),
                T(WH, 1, 1, 8, 1, 2), T(WH, 1, 3, 8, 1, 2),
                B(WH, 7, 1, 4, 2, 1), T("Black", 7, 1, 7, 2, 1)]),
    dict(title="Lower walls & lights",
         text="First row of walls. Yellow headlights go on the front corners, red taillights on "
              "the back corners. Leave the 3-stud gap on the left side: that's the big door!",
         parts=[Part("brick", "Trans-Yellow", 13, 0, 5, 1, 1), B(DT, 13, 1, 5, 1, 4),
                Part("brick", "Trans-Yellow", 13, 5, 5, 1, 1),
                Part("brick", "Trans-Red", 0, 0, 5, 1, 1), B(DT, 0, 1, 5, 1, 4),
                Part("brick", "Trans-Red", 0, 5, 5, 1, 1),
                B(DT, 1, 0, 5, 6, 1), B(DT, 7, 0, 5, 6, 1),
                B(DT, 1, 5, 5, 3, 1), B(DT, 4, 5, 5, 2, 1), B(DT, 9, 5, 5, 4, 1)]),
    dict(title="Second row & the classic V",
         text="Second row of walls. The white brick in the middle of the front starts the famous "
              "V-shaped nose of a vintage camper.",
         parts=[B(DT, 13, 0, 8, 1, 2), B(WH, 13, 2, 8, 1, 2), B(DT, 13, 4, 8, 1, 2),
                B(DT, 0, 0, 8, 1, 6),
                B(DT, 1, 0, 8, 8, 1), B(DT, 9, 0, 8, 4, 1),
                B(DT, 1, 5, 8, 2, 1), B(DT, 3, 5, 8, 3, 1), B(DT, 9, 5, 8, 4, 1)]),
    dict(title="White belt line",
         text="A ring of white plates all the way around gives the two-tone paint job. "
              "Keep the door gap open.",
         parts=[P(WH, 13, 0, 11, 1, 6), P(WH, 0, 0, 11, 1, 6),
                P(WH, 1, 0, 11, 6, 1), P(WH, 7, 0, 11, 6, 1),
                P(WH, 1, 5, 11, 3, 1), P(WH, 4, 5, 11, 2, 1), P(WH, 9, 5, 11, 4, 1)]),
    dict(title="Side windows",
         text="Alternate white pillars and see-through window bricks along both sides.",
         parts=[B(WH, 1, 0, 12, 1, 1), B(GL, 2, 0, 12, 2, 1), B(WH, 4, 0, 12, 1, 1),
                B(GL, 5, 0, 12, 2, 1), B(WH, 7, 0, 12, 1, 1), B(GL, 8, 0, 12, 2, 1),
                B(WH, 10, 0, 12, 1, 1), B(GL, 11, 0, 12, 2, 1),
                B(WH, 1, 5, 12, 1, 1), B(GL, 2, 5, 12, 2, 1), B(WH, 4, 5, 12, 2, 1),
                B(WH, 9, 5, 12, 2, 1), B(GL, 11, 5, 12, 2, 1)]),
    dict(title="Split windscreen & rear window",
         text="Two window bricks side by side make the split windscreen of the classic camper. "
              "Add the small rear window at the back.",
         parts=[B(WH, 13, 0, 12, 1, 1), B(GL, 13, 1, 12, 1, 2), B(GL, 13, 3, 12, 1, 2),
                B(WH, 13, 5, 12, 1, 1),
                B(WH, 0, 0, 12, 1, 2), B(GL, 0, 2, 12, 1, 2), B(WH, 0, 4, 12, 1, 2)]),
    dict(title="Roof",
         text="Lay the two big white plates on top. They bridge over the door opening.",
         parts=[P(WH, 0, 0, 15, 8, 6), P(WH, 8, 0, 15, 6, 6)]),
    dict(title="Rounded roof top",
         text="The 4x12 plate locks the roof together and gives it a rounded, stepped look. "
              "Now the whole roof lifts off in one piece to play inside!",
         parts=[P(WH, 1, 1, 16, 12, 4)]),
    dict(title="Roof rack & surfboard",
         text="Two gray roof-rack bars, then strap on the surfboard. Surf's up! The camper is done!",
         parts=[P(LBG, 3, 1, 17, 1, 4), P(LBG, 10, 1, 17, 1, 4), P("Yellow", 3, 2, 18, 8, 2)]),
]


# ---------------------------------------------------------------- validation
def validate():
    occ, placed = {}, []
    errors = []
    for s, step in enumerate(STEPS, 1):
        for p in step["parts"]:
            if not isinstance(p, Part):
                continue
            for c in p.cells():
                if c in occ:
                    errors.append(f"step {s}: {p.name()} overlaps at {c}")
            below = {occ.get((i, j, p.z - 1)) for i, j, _ in p.cells()} - {None}
            above = {occ.get((i, j, p.z + p.h)) for i, j, _ in p.cells()} - {None}
            ok_below = [q for q in below if q.studs]
            if any(not q.studs for q in below):
                errors.append(f"step {s}: {p.name()} sits on a tile")
            if p.z != 0 and not ok_below and not (above and p.studs):
                errors.append(f"step {s}: {p.name()} {p.color} at {(p.x, p.y, p.z)} is floating")
            for c in p.cells():
                occ[c] = p
            placed.append(p)
    # whole-model connectivity (stud connections)
    adj = {id(p): set() for p in placed}
    for (i, j, k), p in occ.items():
        q = occ.get((i, j, k + 1))
        if q is not None and q is not p and p.studs:
            adj[id(p)].add(id(q)); adj[id(q)].add(id(p))
    seen, todo = set(), [id(placed[0])]
    while todo:
        n = todo.pop()
        if n not in seen:
            seen.add(n); todo.extend(adj[n] - seen)
    if len(seen) != len(placed):
        errors.append(f"model splits apart: {len(placed) - len(seen)} parts not connected")
    return errors


# ---------------------------------------------------------------- rendering
C30 = math.cos(math.radians(30))


def hex2rgb(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
def rgb2hex(c): return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in c)
def shade(h, f): return rgb2hex([v * f for v in hex2rgb(h)])
def mix(h, other, t): return rgb2hex([a * (1 - t) + b * t for a, b in zip(hex2rgb(h), hex2rgb(other))])


class View:
    def __init__(self, s, rotate):
        self.s, self.rotate = s, rotate

    def proj(self, x, y, z):  # world coords: x, y studs; z plates
        if self.rotate:
            x, y = L - x, W - y
        return self.raw(x, y, z)

    def raw(self, x, y, z):  # already in view coords
        zt = z * PLATE
        return ((x - y) * C30 * self.s, ((x + y) * 0.5 - zt) * self.s)


def pts(points):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def render(items, view, highlight=None, bbox=None, faded=False):
    """items: list of parts (Part/Axle/Wheel). highlight: set of ids drawn in full colour
    (others washed out). Returns (svg_body, bbox)."""
    occ = {}
    for p in items:
        if isinstance(p, Part):
            for (i, j, k) in p.cells():
                if view.rotate:
                    i, j = L - 1 - i, W - 1 - j
                occ[(i, j, k)] = p

    def col(p):
        base, trans = COLORS[p.color]
        if highlight is not None and id(p) not in highlight:
            base = mix(base, "#ffffff", 0.55)
        return base, trans

    draws = []  # (key, order, svg)
    S = view.s
    pr = view.raw

    for (i, j, k), p in occ.items():
        base, trans = col(p)
        op = ' fill-opacity="0.55"' if trans else ""
        stroke = shade(base, 0.45) if not trans else shade(base, 0.6)
        key = i + j + k
        out = []

        def same(c):
            return occ.get(c) is p

        def face(poly, fill, edges):
            out.append(f'<polygon points="{pts(poly)}" fill="{fill}"{op}/>')
            for a, b, nb in edges:
                if not nb:
                    out.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" '
                               f'stroke="{stroke}" stroke-width="1.1" stroke-linecap="round"/>')
        # top face
        if (i, j, k + 1) not in occ:
            z = k + 1
            c = [pr(i, j, z), pr(i + 1, j, z), pr(i + 1, j + 1, z), pr(i, j + 1, z)]
            exp = lambda cc: same(cc) and (cc[0], cc[1], cc[2] + 1) not in occ
            face(c, base, [(c[0], c[1], exp((i, j - 1, k))), (c[1], c[2], exp((i + 1, j, k))),
                           (c[2], c[3], exp((i, j + 1, k))), (c[3], c[0], exp((i - 1, j, k)))])
        # +x face
        if (i + 1, j, k) not in occ:
            c = [pr(i + 1, j, k), pr(i + 1, j + 1, k), pr(i + 1, j + 1, k + 1), pr(i + 1, j, k + 1)]
            exp = lambda cc: same(cc) and (cc[0] + 1, cc[1], cc[2]) not in occ
            face(c, shade(base, 0.82), [(c[0], c[1], exp((i, j, k - 1))), (c[1], c[2], exp((i, j + 1, k))),
                                        (c[2], c[3], exp((i, j, k + 1))), (c[3], c[0], exp((i, j - 1, k)))])
        # +y face
        if (i, j + 1, k) not in occ:
            c = [pr(i, j + 1, k), pr(i + 1, j + 1, k), pr(i + 1, j + 1, k + 1), pr(i, j + 1, k + 1)]
            exp = lambda cc: same(cc) and (cc[0], cc[1] + 1, cc[2]) not in occ
            face(c, shade(base, 0.66), [(c[0], c[1], exp((i, j, k - 1))), (c[1], c[2], exp((i + 1, j, k))),
                                        (c[2], c[3], exp((i, j, k + 1))), (c[3], c[0], exp((i - 1, j, k)))])
        if out:
            draws.append((key, 0, "".join(out)))
        # stud
        top_of_part = (k == p.z + p.h - 1)
        if p.studs and top_of_part and (i, j, k + 1) not in occ:
            cx, cy = pr(i + 0.5, j + 0.5, k + 1)
            rx, ry, hh = 0.3 * 1.2247 * S, 0.3 * 0.7071 * S, 0.2125 * S
            draws.append((key + 1, 1,
                f'<g{op}><ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{shade(base, 0.7)}"/>'
                f'<rect x="{cx - rx:.1f}" y="{cy - hh:.1f}" width="{2 * rx:.1f}" height="{hh:.1f}" fill="{shade(base, 0.75)}"/>'
                f'<ellipse cx="{cx:.1f}" cy="{cy - hh:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{mix(base, "#ffffff", 0.18)}" '
                f'stroke="{shade(base, 0.6)}" stroke-width="0.6"/></g>'))

    for p in items:
        if isinstance(p, Axle):
            hl = highlight is None or id(p) in highlight
            colr = "#9aa0a5" if hl else "#d5d8da"
            a, b = view.proj(p.x, p.y0, p.z), view.proj(p.x, p.y1, p.z)
            draws.append((-1000, 0, f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" '
                                    f'stroke="{colr}" stroke-width="{0.3 * S:.1f}" stroke-linecap="round"/>'))
        if isinstance(p, Wheel):
            hl = highlight is None or id(p) in highlight
            yy = (p.y0 + p.y1) / 2
            near = (yy > W / 2) != view.rotate
            tire = "#262626" if hl else "#b9b9b9"
            rim = "#f2f2f2" if hl else "#f7f7f7"
            hub = "#9aa0a5" if hl else "#d9dbdc"
            svg = []
            ys = [p.y0 + (p.y1 - p.y0) * t / 6 for t in range(7)]
            if view.rotate:  # draw slices far-to-near in view space
                ys = ys[::-1]
            def disc(y, r, fill, extra=""):
                poly = [view.proj(p.x + r * math.cos(t), y, p.z + (r / PLATE) * math.sin(t))
                        for t in [2 * math.pi * n / 40 for n in range(40)]]
                return f'<polygon points="{pts(poly)}" fill="{fill}"{extra}/>'
            R = p.r * PLATE
            for y in ys[:-1]:
                svg.append(disc(y, R, tire))
            outer = ys[-1]
            svg.append(disc(outer, R, shade(tire, 1.35) if hl else tire, ' stroke="#111" stroke-width="0.6"'))
            svg.append(disc(outer, R * 0.62, rim))
            svg.append(disc(outer, R * 0.3, hub))
            draws.append((10000 if near else -2000, 0, "".join(svg)))

    draws.sort(key=lambda d: (d[0], d[1]))
    body = "".join(d[2] for d in draws)
    if bbox is None:
        bbox = scene_bbox(items, view)
    return body, bbox


def scene_bbox(items, view):
    xs, ys = [], []
    for p in items:
        if isinstance(p, Part):
            for x in (p.x, p.x + p.dx):
                for y in (p.y, p.y + p.dy):
                    for z in (p.z, p.z + p.h + 0.6):
                        X, Y = view.proj(x, y, z); xs.append(X); ys.append(Y)
        elif isinstance(p, (Wheel, Axle)):
            r = 2.3
            for x in (p.x - r * PLATE, p.x + r * PLATE):
                for y in (p.y0, p.y1):
                    for z in (p.z - r, p.z + r):
                        X, Y = view.proj(x, y, z); xs.append(X); ys.append(Y)
    m = 8
    return (min(xs) - m, min(ys) - m, max(xs) - min(xs) + 2 * m, max(ys) - min(ys) + 2 * m)


def svg_wrap(body, bbox, width=None, cls=""):
    x, y, w, h = bbox
    wattr = f' width="{width}" height="{int(width * h / w)}"' if width else ""
    return (f'<svg class="{cls}" xmlns="http://www.w3.org/2000/svg" viewBox="{x:.1f} {y:.1f} {w:.1f} {h:.1f}"'
            f'{wattr} preserveAspectRatio="xMidYMid meet">{body}</svg>')


def part_icon(p):
    """Small standalone render of a single part, positioned at the origin."""
    if isinstance(p, Part):
        q = Part(p.kind, p.color, 0, 0, 0, max(p.dx, p.dy), min(p.dx, p.dy))
        items = [q]
    elif isinstance(p, Axle):
        items = [Axle(0.5, 1, 0, 8)]
    else:
        items = [Wheel(0.5, 2.2, 0, 0.8)]
    v = View(14, False)
    body, bbox = render(items, v)
    return svg_wrap(body, bbox, cls="icon")


def part_label(p):
    if isinstance(p, Part):
        return p.name()
    if isinstance(p, Axle):
        return "Technic axle, 8 long"
    return "Wheel with tire"


def part_number(p):
    if isinstance(p, Part):
        return p.part_no()
    if isinstance(p, Axle):
        return "3707"
    return "any small wheel + tire that fits a Technic axle"


# ---------------------------------------------------------------- booklet
def build_html():
    all_parts = [p for st in STEPS for p in st["parts"]]
    main = View(26, False)
    rear = View(26, True)
    bb_main = scene_bbox(all_parts, main)
    bb_rear = scene_bbox(all_parts, rear)

    pages = []
    hero, _ = render(all_parts, main, bbox=bb_main)
    hero_r, _ = render(all_parts, rear, bbox=bb_rear)
    n_pieces = len(all_parts)
    pages.append(f"""
<section class="page cover">
  <h1>The Vintage Camper Van</h1>
  <p class="sub">A toy brick model &middot; {n_pieces} pieces &middot; {len(STEPS)} steps &middot; ages 7+</p>
  {svg_wrap(hero, bb_main, cls="hero")}
  <div class="row">{svg_wrap(hero_r, bb_rear, cls="hero-small")}
  <p class="blurb">Happy birthday! This classic split-window camper has a lift-off roof,
  a bench seat and steering wheel, a bed with pillows, a little stove, a big side door for
  your minifigures, and a surfboard on the roof rack.</p></div>
</section>""")

    # bill of materials
    bom = OrderedDict()
    for p in all_parts:
        k = p.key()
        if k not in bom:
            bom[k] = [p, 0]
        bom[k][1] += 1
    rows = "".join(
        f'<div class="bom-item">{part_icon(p)}<div><b>{n}&times;</b> {part_label(p)}<br>'
        f'<span class="muted">{p.color if not isinstance(p, Wheel) else "Black tire, white rim"} &middot; '
        f'#{part_number(p)}</span></div></div>'
        for p, n in sorted(bom.values(), key=lambda v: (str(type(v[0])), v[0].key())))
    pages.append(f"""
<section class="page">
  <h2>Parts list <span class="muted">({n_pieces} pieces)</span></h2>
  <p class="muted">Numbers are standard design IDs, handy for ordering missing pieces from a
  brick parts marketplace. Colors are suggestions; any colors will work!</p>
  <div class="bom">{rows}</div>
</section>""")

    shown = []
    for s, st in enumerate(STEPS, 1):
        new = st["parts"]
        shown = shown + new
        hl = {id(p) for p in new}
        body, _ = render(shown, main, highlight=hl, bbox=bb_main)
        need_rear = any(isinstance(p, Part) and (p.y == 0 or p.x == 0) for p in new) and s > 2
        rear_svg = ""
        if need_rear:
            rb, _ = render(shown, rear, highlight=hl, bbox=bb_rear)
            rear_svg = (f'<div class="alt"><div class="muted">Other side</div>'
                        f'{svg_wrap(rb, bb_rear, cls="alt-svg")}</div>')
        cnt = OrderedDict()
        for p in new:
            k = p.key()
            cnt.setdefault(k, [p, 0])[1] += 1
        callout = "".join(f'<div class="c-item">{part_icon(p)}<span>{n}&times;</span></div>'
                          for p, n in cnt.values())
        pages.append(f"""
<section class="page step">
  <div class="step-head"><div class="num">{s}</div><div><h2>{st['title']}</h2>
  <p>{st['text']}</p></div></div>
  <div class="callout">{callout}</div>
  <div class="views">{svg_wrap(body, bb_main, cls="main-svg")}{rear_svg}</div>
</section>""")

    pages.append(f"""
<section class="page cover">
  <h1>Ready for a road trip!</h1>
  {svg_wrap(hero, bb_main, cls="hero")}
  <ul class="ideas">
    <li>Lift the roof off to put minifigures in the bed or behind the wheel.</li>
    <li>Swap the surfboard for a canoe, bikes, or a pile of luggage.</li>
    <li>Try a new paint job: red, orange, or sky blue with a white roof all look great.</li>
  </ul>
</section>""")

    css = """
body{font-family:'Trebuchet MS',Verdana,sans-serif;margin:0;background:#e9eef0;color:#1d2a30}
.page{background:#fff;max-width:900px;margin:24px auto;padding:32px 40px;border-radius:12px;
 box-shadow:0 2px 10px rgba(0,0,0,.08);page-break-after:always;break-after:page}
h1{font-size:44px;margin:0;color:#1E9AA4} h2{margin:0 0 6px;font-size:28px}
.sub,.muted{color:#6b7a80}.muted{font-size:13px;font-weight:normal}
.hero{width:100%;height:auto;max-height:520px}.hero-small{width:42%;height:auto}
.row{display:flex;align-items:center;gap:24px}.blurb{font-size:18px;line-height:1.5}
.bom{display:grid;grid-template-columns:repeat(3,1fr);gap:10px 18px}
.bom-item{display:flex;align-items:center;gap:10px;font-size:14px}
.bom-item .icon{width:64px;height:48px;flex:none}
.step-head{display:flex;gap:18px;align-items:flex-start}
.num{font-size:64px;font-weight:bold;line-height:1;color:#1E9AA4;min-width:70px}
.step-head p{font-size:17px;line-height:1.45;margin:4px 0 0}
.callout{display:inline-flex;flex-wrap:wrap;gap:14px;border:3px solid #1E9AA4;border-radius:10px;
 padding:10px 14px;margin:16px 0;background:#f3fbfb}
.c-item{display:flex;flex-direction:column;align-items:center;font-weight:bold;font-size:18px}
.c-item .icon{width:80px;height:60px}
.views{display:flex;flex-direction:column;align-items:center}
.main-svg{width:100%;height:auto;max-height:560px}.alt{align-self:flex-end;text-align:center;width:45%;
 border-top:1px dashed #c6d2d6;margin-top:-30px}.alt-svg{width:100%;height:auto}
.ideas{font-size:18px;line-height:1.7}
@media print{body{background:#fff}.page{box-shadow:none;margin:0;border-radius:0;max-width:none}}
"""
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Vintage Camper Van - Building Instructions</title><style>{css}</style></head>
<body>{''.join(pages)}</body></html>"""


if __name__ == "__main__":
    import sys
    errs = validate()
    if errs:
        print("VALIDATION FAILED:\n  " + "\n  ".join(errs))
        sys.exit(1)
    total = sum(len(s["parts"]) for s in STEPS)
    print(f"model OK: {total} pieces in {len(STEPS)} steps, no overlaps, all supported & connected")
    html = build_html()
    with open("camper_van_instructions.html", "w") as f:
        f.write(html)
    print("wrote camper_van_instructions.html")
    if "--png" in sys.argv:
        all_parts = [p for st in STEPS for p in st["parts"]]
        for name, v in (("preview_front", View(26, False)), ("preview_rear", View(26, True))):
            body, bb = render(all_parts, v)
            with open(f"{name}.svg", "w") as f:
                f.write(svg_wrap(body, bb, width=900))
