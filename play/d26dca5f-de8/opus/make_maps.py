#!/usr/bin/env python3
"""Generate printable maps for 'The Drowned Bell of Saint Corvane' one-shot.

Outputs (in ./maps):
  1-foundry-ruins-gm.svg / -player.svg
  2-upper-tunnels-gm.svg / -player.svg
  3-sea-caves-gm.svg     / -player.svg
  print-all.html   (open in a browser, print landscape, margins: none)
"""
import math
import os
import random
from html import escape

PAGE_W, PAGE_H = 1056, 816          # 11 x 8.5 in at 96 dpi (fits A4 when scaled)
S = 30                              # pixels per 5-ft square
COLS, ROWS = 24, 22
OX, OY = 36, 104                    # map origin
MW, MH = COLS * S, ROWS * S
KX = OX + MW + 26                   # key column x
KW = PAGE_W - KX - 30

INK = "#1b1b1b"
WATER = "#d6e4ec"
WAVE = "#6f97ad"


def X(c): return OX + c * S
def Y(r): return OY + r * S
def f(v): return f"{v:.1f}"


# ---------------------------------------------------------------- shapes
def rect_path(x, y, w, h):
    return f"M{f(X(x))},{f(Y(y))}h{f(w*S)}v{f(h*S)}h{f(-w*S)}Z"


def circle_path(cx, cy, r):
    x, y, rr = X(cx), Y(cy), r * S
    # sweep=1 winds clockwise like rects/blobs so overlapping shapes union under nonzero
    return (f"M{f(x-rr)},{f(y)}a{f(rr)},{f(rr)} 0 1,1 {f(2*rr)},0"
            f"a{f(rr)},{f(rr)} 0 1,1 {f(-2*rr)},0Z")


def smooth_closed(pts):
    """Catmull-Rom -> cubic bezier closed path through pixel points."""
    n = len(pts)
    d = f"M{f(pts[0][0])},{f(pts[0][1])}"
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f"C{f(c1[0])},{f(c1[1])} {f(c2[0])},{f(c2[1])} {f(p2[0])},{f(p2[1])}"
    return d + "Z"


def blob(cx, cy, rx, ry, seed, rough=0.09, n=40):
    rnd = random.Random(seed)
    harm = [(k, rnd.uniform(0.4, 1.0) * rough * (1.6 if k < 4 else 1), rnd.uniform(0, 6.3))
            for k in range(2, 7)]
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        m = 1 + sum(a * math.sin(k * t + ph) for k, a, ph in harm)
        pts.append((X(cx + rx * m * math.cos(t)), Y(cy + ry * m * math.sin(t))))
    return smooth_closed(pts)


def tunnel(points, width, seed, step=0.3):
    """Organic tunnel: chain of overlapping wobbly circles along a polyline."""
    rnd = random.Random(seed)
    out, phase = [], rnd.uniform(0, 6)
    dist = 0
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        seg = math.hypot(x2 - x1, y2 - y1)
        k = max(1, int(seg / step))
        for i in range(k + 1):
            t = i / k
            dist += seg / k
            r = width / 2 * (1 + 0.16 * math.sin(dist * 1.3 + phase) + 0.08 * math.sin(dist * 3.1))
            out.append(circle_path(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, r))
    return out


def halo(x, y, text, cls, anchor="middle", fill=None):
    """Text with a white knockout halo (no reliance on paint-order support)."""
    st = f'text-anchor:{anchor}'
    fs = f';fill:{fill}' if fill else ''
    return (f'<text x="{f(x)}" y="{f(y)}" class="{cls}" style="{st};fill:#fff;stroke:#fff;stroke-width:3.5px;stroke-linejoin:round">{text}</text>'
            f'<text x="{f(x)}" y="{f(y)}" class="{cls}" style="{st}{fs}">{text}</text>')


def wrap(text, n):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > n and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- map object
class Map:
    def __init__(self, num, title, subtitle):
        self.num, self.title, self.subtitle = num, title, subtitle
        self.floors = []        # path d strings (cave/room floor)
        self.water = []         # path d strings (clipped to floor)
        self.under = []         # svg drawn below grid (inside floor)
        self.feat = []          # (svg, gm_only) drawn above grid
        self.top = []           # (svg, gm_only) drawn above walls (doors, labels)
        self.key = []

    def add(self, svg, gm=False): self.feat.append((svg, gm))
    def add_top(self, svg, gm=False): self.top.append((svg, gm))

    # --- symbols -------------------------------------------------------
    def label(self, n, cx, cy):
        x, y = X(cx), Y(cy)
        self.add_top(f'<circle cx="{f(x)}" cy="{f(y)}" r="11" fill="#fff" stroke="{INK}" stroke-width="1.6"/>'
                     f'<text x="{f(x)}" y="{f(y+4.2)}" class="num">{n}</text>', gm=True)

    def door(self, cx, cy, orient, w=0.8):
        L, T = w * S, 9
        ww, hh = (L, T) if orient == "h" else (T, L)
        self.add_top(f'<rect x="{f(X(cx)-ww/2)}" y="{f(Y(cy)-hh/2)}" width="{f(ww)}" height="{f(hh)}" '
                     f'fill="#fff" stroke="{INK}" stroke-width="1.6"/>')

    def secret(self, cx, cy):
        self.add_top(halo(X(cx), Y(cy) + 6, "S", "secret", fill="#b00000"), gm=True)

    def trap(self, cx, cy):
        x, y = X(cx), Y(cy)
        self.add(f'<rect x="{f(x-8)}" y="{f(y-8)}" width="16" height="16" fill="#fff" stroke="{INK}" '
                 f'stroke-width="1.4" stroke-dasharray="3 2"/><text x="{f(x)}" y="{f(y+4.5)}" class="small b">T</text>',
                 gm=True)

    def stairs(self, x, y, w, h, along="x", n=None, gm=False):
        s = [f'<rect x="{f(X(x))}" y="{f(Y(y))}" width="{f(w*S)}" height="{f(h*S)}" fill="#fff" stroke="{INK}" stroke-width="1.4"/>']
        length = w if along == "x" else h
        n = n or int(length * 3)
        for i in range(1, n):
            t = i / n
            if along == "x":
                xx = X(x + w * t)
                s.append(f'<line x1="{f(xx)}" y1="{f(Y(y))}" x2="{f(xx)}" y2="{f(Y(y+h))}" stroke="{INK}" stroke-width="1.2"/>')
            else:
                yy = Y(y + h * t)
                s.append(f'<line x1="{f(X(x))}" y1="{f(yy)}" x2="{f(X(x+w))}" y2="{f(yy)}" stroke="{INK}" stroke-width="1.2"/>')
        self.add("".join(s), gm)

    def pit(self, cx, cy, r):
        x, y, rr = X(cx), Y(cy), r * S
        self.add(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(rr)}" fill="url(#pithatch)" stroke="{INK}" stroke-width="2.5"/>'
                 f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(rr*0.55)}" fill="#3a3a3a"/>')

    def shaft(self, cx, cy, r, letter, gm=False):
        x, y, rr = X(cx), Y(cy), r * S
        self.add(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(rr)}" fill="#2b2b2b" stroke="{INK}" stroke-width="2"/>'
                 f'<text x="{f(x)}" y="{f(y+5)}" class="conn" style="fill:#fff">{letter}</text>', gm)

    def conn(self, cx, cy, letter, gm=False):
        x, y = X(cx), Y(cy)
        self.add_top(f'<rect x="{f(x-10)}" y="{f(y-10)}" width="20" height="20" transform="rotate(45 {f(x)} {f(y)})" '
                     f'fill="#fff" stroke="{INK}" stroke-width="1.6"/><text x="{f(x)}" y="{f(y+5)}" class="conn">{letter}</text>', gm)

    def note(self, cx, cy, text, anchor="middle", gm=False, cls="note"):
        self.add_top(halo(X(cx), Y(cy), escape(text), cls, anchor), gm)

    def column(self, cx, cy, r=0.28):
        self.add(f'<circle cx="{f(X(cx))}" cy="{f(Y(cy))}" r="{f(r*S)}" fill="{INK}"/>')

    def crate(self, cx, cy, s=0.7, rot=0):
        x, y, h = X(cx), Y(cy), s * S / 2
        self.add(f'<g transform="rotate({rot} {f(x)} {f(y)})"><rect x="{f(x-h)}" y="{f(y-h)}" width="{f(2*h)}" height="{f(2*h)}" '
                 f'fill="#fff" stroke="{INK}" stroke-width="1.3"/><path d="M{f(x-h)},{f(y-h)}L{f(x+h)},{f(y+h)}M{f(x+h)},{f(y-h)}L{f(x-h)},{f(y+h)}" '
                 f'stroke="{INK}" stroke-width="0.8"/></g>')

    def barrel(self, cx, cy, r=0.3):
        x, y, rr = X(cx), Y(cy), r * S
        self.add(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(rr)}" fill="#fff" stroke="{INK}" stroke-width="1.3"/>'
                 f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(rr*0.45)}" fill="none" stroke="{INK}" stroke-width="0.8"/>')

    def rubble(self, cx, cy, spread, n, seed):
        rnd = random.Random(seed)
        s = []
        for _ in range(n):
            px = X(cx + rnd.gauss(0, spread))
            py = Y(cy + rnd.gauss(0, spread))
            r = rnd.uniform(2, 6)
            k = rnd.randint(4, 6)
            a0 = rnd.uniform(0, 6)
            pts = " ".join(f"{f(px + r*rnd.uniform(.6,1.1)*math.cos(a0+i*6.283/k))},"
                           f"{f(py + r*rnd.uniform(.6,1.1)*math.sin(a0+i*6.283/k))}" for i in range(k))
            s.append(f'<polygon points="{pts}" fill="#bdbdbd" stroke="{INK}" stroke-width="0.9"/>')
        self.add("".join(s))

    def rect(self, x, y, w, h, fill="#fff", sw=1.4, extra=""):
        self.add(f'<rect x="{f(X(x))}" y="{f(Y(y))}" width="{f(w*S)}" height="{f(h*S)}" fill="{fill}" '
                 f'stroke="{INK}" stroke-width="{sw}" {extra}/>')

    def bed(self, x, y, w=0.7, h=1.6):
        self.rect(x, y, w, h)
        self.rect(x + 0.08, y + 0.08, w - 0.16, 0.35, fill="#ddd", sw=0.8)

    def hammock(self, x1, y1, x2, y2):
        mx, my = (X(x1) + X(x2)) / 2, (Y(y1) + Y(y2)) / 2
        nx, ny = -(Y(y2) - Y(y1)), X(x2) - X(x1)
        L = math.hypot(nx, ny) or 1
        bx, by = mx + nx / L * 6, my + ny / L * 6
        cx2, cy2 = mx - nx / L * 6, my - ny / L * 6
        self.add(f'<path d="M{f(X(x1))},{f(Y(y1))}Q{f(bx)},{f(by)} {f(X(x2))},{f(Y(y2))}Q{f(cx2)},{f(cy2)} {f(X(x1))},{f(Y(y1))}Z" '
                 f'fill="#eee" stroke="{INK}" stroke-width="1.1"/>')

    def bell(self, cx, cy, r):
        x, y, rr = X(cx), Y(cy), r * S
        self.add(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(rr)}" fill="#c9b27a" stroke="{INK}" stroke-width="3"/>'
                 f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(rr*0.78)}" fill="none" stroke="{INK}" stroke-width="1.2"/>'
                 f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(rr*0.5)}" fill="none" stroke="{INK}" stroke-width="1"/>'
                 f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(rr*0.16)}" fill="{INK}"/>'
                 f'<path d="M{f(x+rr*0.55)},{f(y-rr*0.55)}l{f(rr*0.2)},{f(rr*0.12)}" stroke="{INK}" stroke-width="1.5"/>')

    def boat(self, cx, cy, length, rot):
        x, y, L = X(cx), Y(cy), length * S / 2
        w = L * 0.36
        self.add(f'<g transform="rotate({rot} {f(x)} {f(y)})">'
                 f'<path d="M{f(x-L)},{f(y)}Q{f(x-L*0.5)},{f(y-w*1.3)} {f(x+L*0.45)},{f(y-w)}L{f(x+L)},{f(y)}'
                 f'L{f(x+L*0.45)},{f(y+w)}Q{f(x-L*0.5)},{f(y+w*1.3)} {f(x-L)},{f(y)}Z" fill="#e7dcc6" stroke="{INK}" stroke-width="2"/>'
                 + "".join(f'<line x1="{f(x+t*L)}" y1="{f(y-w*0.9)}" x2="{f(x+t*L)}" y2="{f(y+w*0.9)}" stroke="{INK}" stroke-width="1"/>'
                           for t in (-0.45, -0.05, 0.35))
                 + f'<circle cx="{f(x-0.05*L)}" cy="{f(y)}" r="3" fill="{INK}"/></g>')

    def jetty(self, x, y, w, h, along="x"):
        s = [f'<rect x="{f(X(x))}" y="{f(Y(y))}" width="{f(w*S)}" height="{f(h*S)}" fill="#e9dcc0" stroke="{INK}" stroke-width="1.6"/>']
        length = w if along == "x" else h
        n = int(length * 3)
        for i in range(1, n):
            if along == "x":
                xx = X(x + w * i / n)
                s.append(f'<line x1="{f(xx)}" y1="{f(Y(y))}" x2="{f(xx)}" y2="{f(Y(y+h))}" stroke="{INK}" stroke-width="0.7"/>')
            else:
                yy = Y(y + h * i / n)
                s.append(f'<line x1="{f(X(x))}" y1="{f(yy)}" x2="{f(X(x+w))}" y2="{f(yy)}" stroke="{INK}" stroke-width="0.7"/>')
        self.add("".join(s))

    def stalag(self, cx, cy, seed, n=5, spread=0.6):
        rnd = random.Random(seed)
        for _ in range(n):
            x, y = X(cx + rnd.uniform(-spread, spread)), Y(cy + rnd.uniform(-spread, spread))
            r = rnd.uniform(2.5, 5)
            self.add(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="#fff" stroke="{INK}" stroke-width="1.2"/>'
                     f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r*0.35)}" fill="{INK}"/>')

    # --- render ---------------------------------------------------------
    def render(self, gm, style="cave", surface_svg=""):
        o = []
        o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {PAGE_W} {PAGE_H}" width="11in" height="8.5in">')
        o.append(DEFS)
        o.append(f'<rect width="{PAGE_W}" height="{PAGE_H}" fill="#fff"/>')
        # title block
        o.append(f'<text x="{OX}" y="50" class="title">The Drowned Bell of Saint Corvane</text>')
        o.append(f'<text x="{OX}" y="82" class="sub">{self.num}. {escape(self.title)}'
                 f'<tspan class="subi"> — {escape(self.subtitle)}{" · GM map" if gm else " · Player map"}</tspan></text>')
        o.append(f'<line x1="{OX}" y1="92" x2="{PAGE_W-30}" y2="92" stroke="{INK}" stroke-width="1.2"/>')

        o.append(f'<clipPath id="mapclip"><rect x="{OX}" y="{OY}" width="{MW}" height="{MH}"/></clipPath>')
        o.append('<g clip-path="url(#mapclip)">')
        if style == "surface":
            o.append(surface_svg)
        else:
            clip = "".join(f'<path d="{d}"/>' for d in self.floors)
            o.append(f'<clipPath id="floorclip">{clip}</clipPath>')
            o.append(f'<rect x="{OX}" y="{OY}" width="{MW}" height="{MH}" fill="#f4f4f4"/>')
            o.append(f'<g fill="none" stroke="url(#hatch)" stroke-width="30">'
                     + "".join(f'<path d="{d}"/>' for d in self.floors) + '</g>')
            o.append(f'<g fill="none" stroke="{INK}" stroke-width="5">'
                     + "".join(f'<path d="{d}"/>' for d in self.floors) + '</g>')
            o.append('<g fill="#fff">' + "".join(f'<path d="{d}"/>' for d in self.floors) + '</g>')
            o.append('<g clip-path="url(#floorclip)">')
            o.extend(self.under)
            if self.water:
                wd = "".join(f'<path d="{d}"/>' for d in self.water)
                o.append(f'<g fill="{WATER}">{wd}</g><g fill="url(#waves)">{wd}</g>')
            o.append(grid_lines("#9a9a9a", 0.6))
            o.append('</g>')
        o.extend(s for s, g in self.feat if gm or not g)
        o.extend(s for s, g in self.top if gm or not g)
        o.append('</g>')
        o.append(f'<rect x="{OX}" y="{OY}" width="{MW}" height="{MH}" fill="none" stroke="{INK}" stroke-width="2.5"/>')
        o.append(compass(OX + MW - 34, OY + 40))
        o.append(scale_bar(OX, OY + MH + 22))

        # side column
        y = OY + 4
        if gm:
            o.append(f'<text x="{KX}" y="{y+12}" class="khead">Key</text>')
            y += 30
            for n, name, desc in self.key:
                o.append(f'<circle cx="{KX+9}" cy="{y-4}" r="9" fill="#fff" stroke="{INK}" stroke-width="1.3"/>'
                         f'<text x="{KX+9}" y="{y}" class="numk">{n}</text>'
                         f'<text x="{KX+24}" y="{y}" class="kname">{escape(name)}</text>')
                y += 15
                for line in wrap(desc, 40):
                    o.append(f'<text x="{KX+24}" y="{y}" class="kdesc">{escape(line)}</text>')
                    y += 13
                y += 9
        else:
            o.append(legend(KX, y))
        o.append('</svg>')
        return "\n".join(o)


def grid_lines(color, w):
    s = [f'<g stroke="{color}" stroke-width="{w}">']
    for c in range(COLS + 1):
        s.append(f'<line x1="{X(c)}" y1="{OY}" x2="{X(c)}" y2="{OY+MH}"/>')
    for r in range(ROWS + 1):
        s.append(f'<line x1="{OX}" y1="{Y(r)}" x2="{OX+MW}" y2="{Y(r)}"/>')
    s.append('</g>')
    return "".join(s)


def compass(x, y):
    return (f'<g><circle cx="{x}" cy="{y}" r="20" fill="#fff" stroke="{INK}" stroke-width="1.3"/>'
            f'<path d="M{x},{y-17}L{x+6},{y+4}L{x},{y}L{x-6},{y+4}Z" fill="{INK}"/>'
            f'<path d="M{x},{y+17}L{x+6},{y+4}L{x},{y}L{x-6},{y+4}Z" fill="#fff" stroke="{INK}" stroke-width="1"/>'
            f'<text x="{x}" y="{y-24}" class="small b">N</text></g>')


def scale_bar(x, y):
    s = [f'<g>']
    for i in range(4):
        s.append(f'<rect x="{x+i*S}" y="{y-8}" width="{S}" height="8" fill="{INK if i%2==0 else "#fff"}" stroke="{INK}" stroke-width="1"/>')
    s.append(f'<text x="{x}" y="{y+12}" class="small" style="text-anchor:start">0</text>'
             f'<text x="{x+4*S}" y="{y+12}" class="small">20 ft</text>'
             f'<text x="{x+4*S+40}" y="{y}" class="small" style="text-anchor:start;font-size:12px">1 square = 5 feet</text></g>')
    return "".join(s)


def legend(x, y):
    s = [f'<text x="{x}" y="{y+12}" class="khead">Legend</text>']
    y += 44
    rows = [
        (f'<rect x="{x}" y="{y-9}" width="24" height="9" fill="#fff" stroke="{INK}" stroke-width="1.6"/>', "Door"),
        (f'<rect x="{x}" y="{y-12}" width="24" height="14" fill="#fff" stroke="{INK}" stroke-width="1.3"/>'
         + "".join(f'<line x1="{x+i*6}" y1="{y-12}" x2="{x+i*6}" y2="{y+2}" stroke="{INK}" stroke-width="1.1"/>' for i in range(1, 4)),
         "Stairs / slope"),
        (f'<rect x="{x+2}" y="{y-12}" width="20" height="20" transform="rotate(45 {x+12} {y-2})" fill="#fff" stroke="{INK}" stroke-width="1.4"/>'
         f'<text x="{x+12}" y="{y+3}" class="conn">A</text>', "Connects to another map"),
        (f'<circle cx="{x+12}" cy="{y-3}" r="10" fill="#2b2b2b"/>', "Shaft / drop"),
        (f'<rect x="{x}" y="{y-12}" width="24" height="16" fill="{WATER}" stroke="{INK}" stroke-width="0.8"/>'
         f'<rect x="{x}" y="{y-12}" width="24" height="16" fill="url(#waves)"/>', "Water"),
        (f'<circle cx="{x+12}" cy="{y-3}" r="5" fill="{INK}"/>', "Pillar"),
        (f'<polygon points="{x+4},{y} {x+9},{y-8} {x+14},{y-1}" fill="#bdbdbd" stroke="{INK}"/>'
         f'<polygon points="{x+13},{y+2} {x+19},{y-6} {x+23},{y+1}" fill="#bdbdbd" stroke="{INK}"/>', "Rubble"),
        (f'<rect x="{x}" y="{y-12}" width="24" height="16" fill="url(#hatch)" stroke="{INK}" stroke-width="0.8"/>', "Solid rock / wall"),
    ]
    for i, (sym, txt) in enumerate(rows):
        s.append(f'<g transform="translate(0 {i*36})">{sym}'
                 f'<text x="{x+36}" y="{y}" class="kname" style="font-weight:normal">{txt}</text></g>')
    y += 36 * len(rows)
    y += 10
    for line in ["Notes:"] + [""] * 10:
        s.append(f'<text x="{x}" y="{y}" class="kname">{line}</text>'
                 f'<line x1="{x}" y1="{y+6}" x2="{x+KW}" y2="{y+6}" stroke="#bbb" stroke-width="0.8"/>' if line
                 else f'<line x1="{x}" y1="{y+6}" x2="{x+KW}" y2="{y+6}" stroke="#bbb" stroke-width="0.8"/>')
        y += 26
    return "".join(s)


DEFS = f'''<defs>
<style>
text {{ font-family: Georgia, "Times New Roman", serif; fill: {INK}; }}
.title {{ font-size: 30px; font-weight: bold; letter-spacing: 1px; font-variant: small-caps; }}
.sub {{ font-size: 20px; font-weight: bold; }}
.subi {{ font-size: 16px; font-weight: normal; font-style: italic; }}
.num {{ font-size: 12px; font-weight: bold; text-anchor: middle; }}
.numk {{ font-size: 10px; font-weight: bold; text-anchor: middle; }}
.secret {{ font-size: 17px; font-weight: bold; }}
.conn {{ font-size: 13px; font-weight: bold; text-anchor: middle; }}
.note {{ font-size: 11px; font-style: italic; }}
.small {{ font-size: 10px; text-anchor: middle; }}
.b {{ font-weight: bold; }}
.khead {{ font-size: 18px; font-weight: bold; font-variant: small-caps; }}
.kname {{ font-size: 12px; font-weight: bold; }}
.kdesc {{ font-size: 10.5px; }}
</style>
<pattern id="hatch" patternUnits="userSpaceOnUse" width="7" height="7" patternTransform="rotate(40)">
  <rect width="7" height="7" fill="#f4f4f4"/><line x1="0" y1="0" x2="0" y2="7" stroke="#4a4a4a" stroke-width="1.3"/>
</pattern>
<pattern id="pithatch" patternUnits="userSpaceOnUse" width="5" height="5" patternTransform="rotate(-45)">
  <rect width="5" height="5" fill="#8a8a8a"/><line x1="0" y1="0" x2="0" y2="5" stroke="#222" stroke-width="1.4"/>
</pattern>
<pattern id="waves" patternUnits="userSpaceOnUse" width="30" height="12">
  <path d="M2,6 q4,-4 8,0 t8,0" fill="none" stroke="{WAVE}" stroke-width="1"/>
  <path d="M17,12 q4,-4 8,0" fill="none" stroke="{WAVE}" stroke-width="1"/>
</pattern>
<pattern id="flags" patternUnits="userSpaceOnUse" width="{S}" height="{S}" x="{OX}" y="{OY}">
  <rect width="{S}" height="{S}" fill="#eeeae2"/>
  <path d="M0,{S/2}H{S/2}V{S}M{S/2},0V{S/4}" stroke="#d4cfc4" stroke-width="1" fill="none"/>
</pattern>
</defs>'''


# ================================================================ MAP I
def foundry():
    m = Map("I", "The Foundry Ruins", "surface")
    m.key = [
        (1, "Gatehouse", "Collapsed arch. A tripwire across the gap (T) jangles a crow-scarer bell hidden in the ivy."),
        (2, "Casting Hall", "Roofless hall of soot-black pillars. The 20-ft casting pit hides a winch platform beneath a cracked bell mould; rope down to A."),
        (3, "Furnace House", "Cold furnace big enough to crawl inside. The flue is a lookout's hidey-hole with a view over the bay."),
        (4, "Pattern Store", "Rotting wooden bell patterns. Oilskins, hooded lanterns and a tide table chalked on the wall."),
        (5, "Test Tower", "Stump of the bell tower; a spiral stair climbs to a broken top 30 ft up. A shuttered lantern signals ships."),
        (6, "Foreman's House", "The only roofed building. Old Mother Hesk 'keeps an eye on the place for the parish'. She is the gang's lookout."),
        (7, "Founders' Chapel", "Defaced shrine to St. Corvane. The altar slides aside (S) onto stairs down to the crypt (B)."),
        (8, "Foundry Yard", "Nettles and slag heaps. Cart ruts run from the gate to the casting hall, and they are suspiciously fresh."),
    ]
    W = 7  # wall stroke
    s = []
    # ground
    s.append(f'<rect x="{OX}" y="{OY}" width="{MW}" height="{MH}" fill="#fbfaf6"/>')
    # sea + cliff along the top
    rnd = random.Random(7)
    cliff = [(X(c), Y(1.0 + 0.35 * math.sin(c * 1.7) + rnd.uniform(-0.15, 0.15))) for c in [i * 0.5 for i in range(-1, 51)]]
    cl = " ".join(f"L{f(a)},{f(b)}" for a, b in cliff)
    s.append(f'<path d="M{X(-1)},{Y(-1)}{cl}L{X(25)},{Y(-1)}Z" fill="{WATER}"/>')
    s.append(f'<path d="M{X(-1)},{Y(-1)}{cl}L{X(25)},{Y(-1)}Z" fill="url(#waves)"/>')
    s.append(f'<path d="M{cl[1:]}" fill="none" stroke="url(#hatch)" stroke-width="16"/>')
    s.append(f'<path d="M{cl[1:]}" fill="none" stroke="{INK}" stroke-width="2.5"/>')
    # cart track from the gate south off-map
    s.append(f'<path d="M{X(12.4)},{Y(22.5)}C{X(12.6)},{Y(20)} {X(12.2)},{Y(19)} {X(12.5)},{Y(17)}" fill="none" stroke="#d9d2c1" stroke-width="44" stroke-linecap="round"/>')
    # building floors (flagstones)
    floors = [rect_path(7, 2, 10, 9), rect_path(17, 3, 5, 6), rect_path(2, 3, 5, 5),
              rect_path(19, 12, 4, 6), rect_path(2, 14, 5, 6), rect_path(10.5, 18, 4, 3),
              circle_path(4.5, 11, 2), rect_path(6.2, 10.5, 1.2, 1)]
    s.append('<g fill="url(#flags)">' + "".join(f'<path d="{d}"/>' for d in floors) + '</g>')
    # grass tufts in yard / outside
    rnd = random.Random(3)
    tufts = []
    def inside_building(c, r):
        boxes = [(6.6, 1.6, 17.4, 11.4), (16.6, 2.6, 22.4, 9.4), (1.6, 2.6, 7.4, 8.4), (18.6, 11.6, 23.4, 18.4),
                 (1.6, 13.6, 7.4, 20.4), (10.1, 17.6, 14.9, 21.4), (2.2, 8.7, 6.8, 13.3), (11, 17, 14, 23)]
        return any(a <= c <= b2 and bb <= r <= d for a, bb, b2, d in boxes)
    for _ in range(260):
        c, r = rnd.uniform(0.3, 23.7), rnd.uniform(1.8, 21.7)
        if inside_building(c, r):
            continue
        x, y = X(c), Y(r)
        tufts.append(f"M{f(x-3)},{f(y)}l2,-5M{f(x)},{f(y)}l0,-6M{f(x+3)},{f(y)}l-1,-5")
    s.append(f'<path d="{"".join(tufts)}" stroke="#7c8b6a" stroke-width="0.9" fill="none"/>')
    s.append(grid_lines("#b5b5b5", 0.5))
    # trees
    for (c, r, rad, sd) in [(1, 21, 1.3, 1), (22.5, 20.5, 1.4, 2), (21, 21.6, 1, 3), (0.6, 12.5, 0.9, 4),
                            (16.5, 20.5, 1.0, 5), (8, 21.2, 0.9, 6), (23.3, 10.5, 1.0, 7)]:
        s.append(f'<path d="{blob(c, r, rad, rad, sd, rough=0.12)}" fill="#dfe6d4" stroke="#55624a" stroke-width="1.4"/>')
        s.append(f'<circle cx="{f(X(c))}" cy="{f(Y(r))}" r="3" fill="#55624a"/>')
    # walls
    def wall_rect(x, y, w, h):
        return f'<rect x="{X(x)}" y="{Y(y)}" width="{w*S}" height="{h*S}" fill="none" stroke="{INK}" stroke-width="{W}" stroke-linejoin="miter"/>'
    walls = [wall_rect(7, 2, 10, 9), wall_rect(17, 3, 5, 6), wall_rect(2, 3, 5, 5), wall_rect(19, 12, 4, 6),
             wall_rect(2, 14, 5, 6),
             f'<path d="M{X(10.5)},{Y(21)}V{Y(18)}H{X(14.5)}V{Y(21)}" fill="none" stroke="{INK}" stroke-width="{W}"/>',
             f'<circle cx="{X(4.5)}" cy="{Y(11)}" r="{2*S}" fill="none" stroke="{INK}" stroke-width="{W}"/>',
             f'<path d="M{X(6.3)},{Y(10.5)}H{X(7.4)}M{X(6.3)},{Y(11.5)}H{X(7.4)}" stroke="{INK}" stroke-width="{W-2}"/>']
    s.extend(walls)

    # openings (cover walls with floor colour)
    def gap(x, y, w, h, fill="#eeeae2"):
        s.append(f'<rect x="{f(X(x))}" y="{f(Y(y))}" width="{f(w*S)}" height="{f(h*S)}" fill="{fill}"/>')
    gap(16.85, 4.6, 0.3, 2.8)          # casting hall -> furnace arch
    gap(6.4, 10.62, 0.75, 0.76)          # tower passage into tower
    gap(7.0 - 0.15, 10.6, 0.3, 0.8)    # tower passage into yard (wall of casting hall corner)
    gap(10.85, 1.85, 2.6, 0.3, "#fbfaf6")  # breach in north wall of hall
    gap(21.85, 6.0, 0.3, 1.8, "#fbfaf6")   # breach in furnace house
    gap(11.6, 17.85, 1.8, 0.3)          # gate arch inner
    s.append(f'<rect x="{X(11.9)}" y="{Y(20.6)}" width="{1.2*S}" height="{0.8*S}" fill="#e2dccd"/>')  # gate gap (collapsed)
    m.under = []
    surface = "".join(s)

    # features
    m.pit(12, 6.5, 2.1)
    m.shaft(12, 6.5, 0.6, "A")
    m.rubble(11.5, 6.0, 0.25, 6, 11)   # broken mould
    for c in (8.5, 15.5):
        for r in (3.5, 6.5, 9.5):
            m.column(c, r)
    m.rubble(12.2, 1.7, 0.5, 14, 12)
    m.rubble(22, 7, 0.45, 12, 13)
    m.rubble(16.2, 9.8, 0.4, 8, 14)
    m.rubble(12.5, 20.9, 0.45, 12, 15)
    m.rubble(9.2, 15, 0.6, 9, 16)   # slag heap
    m.rubble(16.3, 13.6, 0.5, 9, 17)
    # furnace
    m.add(f'<rect x="{X(19)}" y="{Y(3.4)}" width="{2.6*S}" height="{2.6*S}" fill="#9a9a9a" stroke="{INK}" stroke-width="2"/>'
          f'<path d="M{X(19.6)},{Y(6)}A{0.7*S},{0.7*S} 0 0,1 {X(21)},{Y(6)}Z" fill="#2b2b2b"/>'
          f'<circle cx="{X(20.3)}" cy="{Y(4.6)}" r="9" fill="#2b2b2b"/>')
    m.crate(18, 8, 0.6)
    # pattern store: shelves + patterns
    m.rect(2.2, 3.2, 4.6, 0.5, fill="#d8cbb0")
    m.add(f'<path d="M{X(3)},{Y(6.8)}a{0.7*S},{0.9*S} 0 0,1 {1.4*S},0z" fill="#d8cbb0" stroke="{INK}" stroke-width="1.3"/>')
    m.add(f'<path d="M{X(4.8)},{Y(7.4)}a{0.6*S},{0.8*S} 0 0,1 {1.2*S},0z" fill="#d8cbb0" stroke="{INK}" stroke-width="1.3"/>')
    m.barrel(6.3, 4.3)
    # tower spiral stair
    tx, ty = X(4.5), Y(11)
    spoke = "".join(f'<line x1="{f(tx)}" y1="{f(ty)}" x2="{f(tx+1.4*S*math.cos(a*math.pi/6))}" y2="{f(ty+1.4*S*math.sin(a*math.pi/6))}" stroke="{INK}" stroke-width="1"/>'
                    for a in range(12))
    m.add(f'<circle cx="{f(tx)}" cy="{f(ty)}" r="{1.4*S}" fill="#fff" stroke="{INK}" stroke-width="1.3"/>{spoke}'
          f'<circle cx="{f(tx)}" cy="{f(ty)}" r="5" fill="{INK}"/>')
    # foreman's house
    m.bed(22, 12.3, 0.8, 1.6)
    m.rect(19.5, 15.8, 1.6, 1, fill="#fff")
    m.add(f'<rect x="{X(21.6)}" y="{Y(16.9)}" width="{1.2*S}" height="{0.9*S}" fill="#9a9a9a" stroke="{INK}" stroke-width="1.5"/>')  # hearth
    m.barrel(20, 12.6)
    # chapel
    m.rect(3.6, 14.4, 1.8, 0.8, fill="#bdbdbd", sw=1.8)        # altar
    for r in (16.3, 17.4, 18.5):
        m.rect(2.5, r, 1.4, 0.4)
        m.rect(5.1, r, 1.4, 0.4)
    m.stairs(3.7, 15.25, 1.6, 0.9, along="x", n=5, gm=True)
    m.conn(4.5, 15.7, "B", gm=True)
    m.secret(4.5, 14.75)
    # doors
    m.door(12, 11, "h")
    m.door(7, 5.5, "v")
    m.door(19, 15, "v")
    m.door(7, 17, "v")
    m.door(20.5, 9, "h")
    m.trap(12.5, 21.5)
    # labels
    for n, c, r in [(1, 13.6, 19.4), (2, 10, 9.2), (3, 18.2, 6.6), (4, 3.2, 5), (5, 4.5, 13.0),
                    (6, 20.4, 14.2), (7, 2.8, 19.3), (8, 15.5, 15.5)]:
        m.label(n, c, r)
    m.note(12, 0.6, "sheer sea cliffs, 80 ft drop", cls="note")
    m.note(12.5, 6.5 - 2.5, "casting pit (20 ft)", cls="note")
    m.note(17.5, 21.7, "track to Corvane village", cls="note")
    m.note(12, 1.4, "breach", cls="note")
    m.note(20.3, 7.6, "furnace", cls="note")
    return m, surface


# ================================================================ MAP II
def upper():
    m = Map("II", "The Upper Tunnels", "beneath the foundry")
    m.key = [
        (9, "Pit Bottom", "Winch landing below the casting pit (A). Hauling the rope rings a handbell in the guard post."),
        (10, "Guard Post", "Two smugglers dicing by a brazier. An alarm gong is hung by the door."),
        (11, "Old Culvert", "Foundry drain, knee-deep sludge, 5 ft wide. Dead-ends at a secret door (S) into the ossuary."),
        (12, "Crypt Ossuary", "The founders' bones in wall niches. Stairs up to the chapel (B). Their names are cast on the Drowned Bell."),
        (13, "Bunkroom", "Hammocks for eight; most of the gang sleep by day. Sea chests hold wages and knives."),
        (14, "Counting Room", "Lieutenant Varro Quill and his ledgers, which name the bribed harbourmaster. Locked strongbox."),
        (15, "Goods Store", "Brandy casks, silk bolts and crates stamped with a noble house's crest."),
        (16, "Rotten Shoring", "Creaking props (T). Loud noise or a careless shove brings the roof down; the tunnel may block."),
        (17, "Bell Shaft", "Natural chimney 60 ft down to the sea caves (C). Rope ladder plus a goods hoist."),
        (18, "The Slope", "Slick, cut steps winding down to the sea caves (D). Seawater trickles down them at high tide."),
    ]
    F = m.floors
    # worked rooms
    F += [rect_path(9, 3, 6, 6), rect_path(15.6, 4, 4, 4), rect_path(16, 16, 5, 4.5)]
    # culvert (worked)
    F += [rect_path(3, 5.5, 6.2, 1), rect_path(3, 5.5, 1, 9.6)]
    # ossuary
    F += [rect_path(1, 15.5, 5.5, 5)]
    # natural caves
    F.append(blob(19.5, 12.4, 3.0, 2.0, 21))
    F.append(blob(11.4, 15.3, 3.0, 2.6, 22))
    F.append(blob(9.0, 19.9, 1.8, 1.5, 23))
    # tunnels
    F += tunnel([(12, 8.8), (11.6, 11), (11, 13)], 1.6, 31)
    F += tunnel([(13.8, 15.2), (15.5, 13.8), (17, 12.8)], 1.5, 32)
    F += tunnel([(17.6, 7.8), (17.8, 9.5), (18.6, 10.8)], 1.3, 33)
    F += tunnel([(9.8, 17), (9.2, 18.6)], 1.5, 34)
    F += tunnel([(22, 11.4), (23.2, 9.8), (24.6, 9.4)], 1.6, 35)
    F.append(rect_path(18, 13.6, 1, 2.6))   # short worked link bunkroom -> counting room
    F.append(rect_path(15.0, 5.5, 0.8, 1.0))  # doorway pit -> guard

    # features
    m.shaft(12, 5.6, 0.75, "A")
    m.add(f'<rect x="{X(10.2)}" y="{Y(4)}" width="{3.6*S}" height="{3.2*S}" fill="none" stroke="{INK}" stroke-width="1.2" stroke-dasharray="5 3"/>')
    m.note(12, 7.6, "winch platform lands here", cls="note")
    m.rect(9.3, 3.3, 0.8, 0.8, fill="#bdbdbd")
    m.crate(14.3, 8.3, 0.6)
    m.crate(13.5, 8.4, 0.5, 15)
    m.add(f'<circle cx="{X(17.6)}" cy="{Y(6)}" r="{0.45*S}" fill="#9a9a9a" stroke="{INK}" stroke-width="1.5"/>')   # brazier
    m.rect(16.2, 4.5, 1.2, 0.8)
    m.add(f'<circle cx="{X(19.1)}" cy="{Y(4.6)}" r="8" fill="#c9b27a" stroke="{INK}" stroke-width="1.5"/>')  # gong
    m.door(15.3, 6, "v")
    # culvert sludge
    m.water += [rect_path(3, 5.5, 6.0, 1), rect_path(3, 5.5, 1, 9.6)]
    m.secret(3.5, 15.3)
    # ossuary
    for r in (16.5, 18, 19.5):
        m.rect(1.05, r - 0.35, 0.4, 0.7, fill="#ddd")
        m.rect(6.05, r - 0.35, 0.4, 0.7, fill="#ddd")
    m.rect(2.3, 16.8, 2.8, 1.2, fill="#ddd", sw=1.6)   # founders' tomb
    m.stairs(1.5, 18.6, 2, 1.4, along="x", n=6)
    m.conn(2.5, 19.3, "B")
    m.rubble(5.6, 20, 0.25, 6, 41)
    # bunkroom
    for (a, b, c, d) in [(17.2, 11.2, 18.6, 12.2), (17.4, 13.1, 18.8, 14.0), (19.8, 10.9, 21.3, 11.4),
                         (20.3, 12.5, 21.7, 13.3), (19.2, 13.9, 20.6, 14.2)]:
        m.hammock(a, b, c, d)
    m.crate(21.5, 14.0, 0.55, 20)
    m.crate(19.5, 11.9, 0.5, 5)
    # counting room
    m.rect(17.5, 17.6, 2, 1, fill="#e3d6bb")
    m.rect(20, 16.4, 0.8, 0.7, fill="#555")   # strongbox
    m.rect(16.3, 19.8, 2.5, 0.5, fill="#d8cbb0")
    m.door(18.5, 16, "h")
    # goods store
    for i, (c, r) in enumerate([(9.2, 14.3), (9.9, 14.0), (9.3, 15.1), (12.4, 13.8), (13.1, 14.0), (12.6, 16.8)]):
        m.crate(c, r, 0.6, i * 11)
    for c, r in [(9.5, 16.5), (10.1, 16.9), (10.7, 17.1), (11.3, 17.1), (9.8, 17.5)]:
        m.barrel(c, r)
    m.rect(10.4, 14.6, 1.6, 0.7, fill="#ece3f0")
    m.stalag(13.2, 16.0, 51, 3, 0.3)
    # rotten shoring
    for r in (8.5, 9.4, 10.2):
        m.add(f'<line x1="{X(17.1)}" y1="{Y(r)}" x2="{X(18.5)}" y2="{Y(r+0.15)}" stroke="#7a5b33" stroke-width="4"/>')
    m.rubble(18.3, 10.5, 0.25, 7, 42)
    m.trap(17.8, 9.4)
    # bell shaft
    m.shaft(9.0, 20.0, 0.85, "C")
    m.stalag(7.8, 19.4, 52, 3, 0.3)
    m.rect(9.9, 20.2, 0.8, 0.6, fill="#d8cbb0")   # hoist
    m.note(9.0, 21.9, "60-ft chimney", cls="note")
    # slope
    m.stairs(22.2, 9.3, 1.8, 1.3, along="x", n=7)
    m.conn(23.2, 8.5, "D")
    m.note(21.6, 7.4, "down to sea caves", cls="note")
    m.stalag(21.0, 12.3, 53, 4, 0.5)
    # labels
    for n, c, r in [(9, 10, 8.2), (10, 18.8, 7.2), (11, 6.2, 4.9), (12, 4.7, 19.8), (13, 21.6, 12.0),
                    (14, 20.3, 19.4), (15, 11.2, 13.4), (16, 16.5, 9.4), (17, 7.6, 20.7), (18, 22.6, 11.0)]:
        m.label(n, c, r)
    return m


# ================================================================ MAP III
def sea():
    m = Map("III", "The Lower Sea Caves", "at the waterline")
    m.key = [
        (19, "Shaft Foot", "Bottom of the bell shaft (C). Hoist cradle, nets and crab pots. Echoes carry far from here."),
        (20, "Slope Foot", "Bottom of the cut steps (D). A barnacled tide-mark runs 4 ft up the walls."),
        (21, "Smugglers' Dock", "Timber jetty and a moored lugger half-loaded with casks. At high tide the shingle floods waist deep."),
        (22, "The Drowned Bell", "The foundry's lost great bell hangs on chains over a pool. When rung it booms across the bay to signal ships, and it wakes something else too."),
        (23, "Sea Mouth", "Opens onto the bay. A boat can only get through at low tide; at high tide it's a churning sump."),
        (24, "Tide Passage", "Shingle at low tide, a 5-ft-deep swim at high tide with a strong pull towards the sea mouth."),
        (25, "Captain's Grotto", "Captain Isolde Marrow's dry ledge: charts, the payroll chest and her collection of ship's bells."),
        (26, "Bone Pool", "Hidden behind the bell (S). Informers end up here, and the thing that eats them is still hungry."),
    ]
    F = m.floors
    F.append(blob(5, 4, 2.4, 2.0, 61))
    F.append(blob(20, 3.8, 2.6, 2.0, 62))
    F.append(blob(12.5, 12, 5.0, 3.6, 63, rough=0.08))
    F.append(blob(4.6, 12.6, 2.9, 2.6, 64))
    F.append(blob(20.4, 17.0, 2.6, 2.2, 65))
    F.append(blob(3.5, 19.2, 2.1, 1.7, 66))
    F += tunnel([(5.5, 5.8), (7.2, 8.0), (9.0, 9.6)], 1.7, 71)
    F += tunnel([(19.5, 5.6), (17.8, 7.6), (16.0, 9.2)], 1.8, 72)
    F += tunnel([(8.2, 12.6), (7.0, 12.8)], 1.6, 73)
    F += tunnel([(14.0, 15.0), (14.0, 18.5), (14.6, 22.8)], 4.2, 74)
    F += tunnel([(16.8, 14.0), (18.2, 15.4), (19.0, 16.2)], 1.6, 75)
    F += tunnel([(3.6, 16.2), (3.5, 17.6)], 1.1, 76)

    # water
    m.water.append(f"M{X(7)},{Y(12.6)}C{X(10)},{Y(11.4)} {X(14)},{Y(13.2)} {X(18)},{Y(11.4)}L{X(18)},{Y(24)}L{X(7)},{Y(24)}Z")
    m.water.append(blob(4.4, 12.9, 1.9, 1.7, 81, rough=0.06))
    m.water.append(f"M{X(16.4)},{Y(13.4)}L{X(19.6)},{Y(16.0)}L{X(18.2)},{Y(17.2)}L{X(15.5)},{Y(14.6)}Z")
    m.water.append(blob(3.6, 19.6, 1.3, 0.9, 82, rough=0.05))

    m.shaft(5, 3.6, 0.8, "C")
    m.add(f'<rect x="{X(5.9)}" y="{Y(4.6)}" width="{1.0*S}" height="{0.7*S}" fill="#d8cbb0" stroke="{INK}" stroke-width="1.3"/>')
    for c, r in [(3.2, 5.0), (3.7, 5.6)]:
        m.add(f'<circle cx="{X(c)}" cy="{Y(r)}" r="7" fill="#fff" stroke="{INK}" stroke-width="1.1" stroke-dasharray="2 1.5"/>')
    m.stalag(6.4, 2.6, 91, 3, 0.4)
    m.stairs(19.4, 2.0, 1.5, 1.5, along="y", n=6)
    m.conn(21.6, 2.6, "D")
    m.stalag(21.2, 4.8, 92, 4, 0.5)
    m.barrel(18.6, 3.8)
    m.barrel(18.4, 4.5)
    # dock
    m.jetty(10.5, 11.6, 1.2, 5.8, along="y")
    m.jetty(11.7, 15.2, 2.4, 1.0, along="x")
    m.boat(15.8, 15.6, 4.0, -80)
    for c, r in [(9.0, 10.6), (9.7, 10.3), (13.5, 9.6), (14.2, 9.9)]:
        m.crate(c, r, 0.6, int(c * 13))
    for c, r in [(15.8, 10.4), (16.4, 10.8), (11.4, 9.4)]:
        m.barrel(c, r)
    m.add(f'<path d="M{X(12)},{Y(9.2)}l{0.8*S},0l0,{0.6*S}l{-0.8*S},0z" fill="none" stroke="{INK}" stroke-width="1" stroke-dasharray="3 2"/>')
    m.note(13.0, 13.1, "low-tide shingle line", cls="note")
    # drowned bell
    m.bell(4.4, 12.9, 1.25)
    for (a, b) in [(-1, -1), (1, -1), (0, 1.3)]:
        m.add(f'<line x1="{f(X(4.4+a*0.9))}" y1="{f(Y(12.9+b*0.9))}" x2="{f(X(4.4+a*1.9))}" y2="{f(Y(12.9+b*1.6))}" stroke="{INK}" stroke-width="2.5" stroke-dasharray="4 2"/>')
    m.note(4.4, 10.3, "hangs on chains", cls="note")
    # sea mouth
    m.note(14.4, 21.4, "to the open bay", cls="note")
    m.rubble(12.0, 19.5, 0.4, 7, 93)
    m.rubble(16.5, 20.5, 0.4, 7, 94)
    # captain
    m.rect(20.6, 16.2, 1.6, 1.0, fill="#e3d6bb")
    m.rect(21.4, 18.0, 0.9, 0.7, fill="#555")
    m.bed(19.1, 17.6, 1.4, 0.7)
    for c, r in [(22.2, 15.4), (21.5, 15.0)]:
        m.add(f'<circle cx="{X(c)}" cy="{Y(r)}" r="6" fill="#c9b27a" stroke="{INK}" stroke-width="1.2"/>')
    # bone pool
    m.secret(3.6, 15.5)
    m.rubble(2.3, 18.4, 0.25, 6, 95)
    m.add("".join(f'<path d="M{f(X(c))},{f(Y(r))}l8,3m-8,0l8,-3" stroke="{INK}" stroke-width="1.4"/>'
                  for c, r in [(4.8, 18.4), (2.0, 20.3), (5.0, 20.2)]))
    # labels
    for n, c, r in [(19, 3.0, 2.9), (20, 18.5, 2.4), (21, 8.6, 13.7), (22, 6.5, 11.0), (23, 12.0, 21.0),
                    (24, 17.0, 16.4), (25, 22.6, 17.2), (26, 5.0, 19.2)]:
        m.label(n, c, r)
    return m


def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "maps")
    os.makedirs(out, exist_ok=True)
    m1, surface = foundry()
    pages = []
    for slug, m, style, extra in [("1-foundry-ruins", m1, "surface", surface),
                                  ("2-upper-tunnels", upper(), "cave", ""),
                                  ("3-sea-caves", sea(), "cave", "")]:
        for gm in (True, False):
            svg = m.render(gm, style, extra)
            name = f"{slug}-{'gm' if gm else 'player'}.svg"
            with open(os.path.join(out, name), "w") as fh:
                fh.write(svg)
            pages.append((gm, name))
    order = [p for p in pages if p[0]] + [p for p in pages if not p[0]]
    html = ['<!doctype html><html><head><meta charset="utf-8"><title>The Drowned Bell of Saint Corvane — maps</title>',
            '<style>@page{size:11in 8.5in;margin:0}body{margin:0;background:#888}'
            '.pg{width:11in;height:8.5in;margin:0 auto 12px;background:#fff;page-break-after:always;break-after:page}'
            '.pg img{width:100%;height:100%;display:block}'
            '@media print{body{background:#fff}.pg{margin:0}}</style></head><body>']
    html += [f'<div class="pg"><img src="{n}" alt="{n}"></div>' for _, n in order]
    html.append('</body></html>')
    with open(os.path.join(out, "print-all.html"), "w") as fh:
        fh.write("\n".join(html))
    print("wrote", out)


if __name__ == "__main__":
    main()
