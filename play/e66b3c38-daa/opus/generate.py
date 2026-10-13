#!/usr/bin/env python3
"""Generate seamless stained-glass (Voronoi) background tiles.

Outputs one SVG per colourway into ./patterns/. The tiles repeat
seamlessly in both directions, so they can be used directly as a CSS
background-image with background-repeat.

Usage: python3 generate.py [--seed N] [--cells N] [--size PX]
"""
import argparse
import math
import os
import random

PALETTES = {
    "amber": {
        "lead": "#2a1d12",
        "glass": ["#f6c45a", "#f2a93b", "#e08a1e", "#c96a12", "#a9500c", "#fbd98a"],
    },
    "cobalt": {
        "lead": "#0d1426",
        "glass": ["#5b8fe8", "#3f7fe0", "#2a63d6", "#1f4fbf", "#163a96", "#0f2a73"],
    },
    "emerald": {
        "lead": "#0e1d14",
        "glass": ["#62c98c", "#36a866", "#1f8a4c", "#17783f", "#0f6133", "#0a4a27"],
    },
}


def clip(poly, a, b, c):
    """Keep the part of polygon where a*x + b*y <= c (Sutherland-Hodgman)."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        dp = a * p[0] + b * p[1] - c
        dq = a * q[0] + b * q[1] - c
        if dp <= 0:
            out.append(p)
        if (dp < 0 < dq) or (dq < 0 < dp):
            t = dp / (dp - dq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def periodic_voronoi(sites, w, h):
    """Voronoi cell of each site, treating the plane as a w x h torus."""
    ghosts = [(x + dx * w, y + dy * h)
              for x, y in sites for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
    cells = []
    for sx, sy in sites:
        # Only nearby ghosts can bound this cell; sort by distance for speed.
        near = sorted(ghosts, key=lambda g: (g[0] - sx) ** 2 + (g[1] - sy) ** 2)[1:40]
        poly = [(sx - w, sy - h), (sx + w, sy - h), (sx + w, sy + h), (sx - w, sy + h)]
        for gx, gy in near:
            # Half-plane closer to (sx, sy) than to (gx, gy).
            a, b = gx - sx, gy - sy
            c = (gx * gx + gy * gy - sx * sx - sy * sy) / 2
            poly = clip(poly, a, b, c)
        cells.append(poly)
    return cells


def centroid(poly):
    area = cx = cy = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % len(poly)]
        cr = x0 * y1 - x1 * y0
        area += cr
        cx += (x0 + x1) * cr
        cy += (y0 + y1) * cr
    area /= 2
    return cx / (6 * area), cy / (6 * area)


def build_cells(n, size, rng, relax=3):
    sites = [(rng.uniform(0, size), rng.uniform(0, size)) for _ in range(n)]
    for _ in range(relax):  # Lloyd relaxation: evens out cell sizes a little
        cells = periodic_voronoi(sites, size, size)
        sites = [(cx % size, cy % size) for cx, cy in map(centroid, cells)]
    return periodic_voronoi(sites, size, size)


def shrink(poly, amount):
    """Pull vertices towards the centroid (used for the inner highlight)."""
    cx, cy = centroid(poly)
    out = []
    for x, y in poly:
        dx, dy = x - cx, y - cy
        d = math.hypot(dx, dy) or 1
        k = max(0.0, (d - amount) / d)
        out.append((cx + dx * k, cy + dy * k))
    return out


def path(poly, ox=0.0, oy=0.0):
    pts = " ".join(f"{x + ox:.1f},{y + oy:.1f}" for x, y in poly)
    return f"M{pts}Z"


def render(cells, size, palette, rng):
    lead = palette["lead"]
    glass = palette["glass"]
    defs = []
    for i, col in enumerate(glass):
        # Each pane is lit from the top-left, like light coming through glass.
        defs.append(
            f'<linearGradient id="g{i}" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="#fff" stop-opacity=".28"/>'
            f'<stop offset=".55" stop-color="#fff" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="#000" stop-opacity=".22"/>'
            f"</linearGradient>"
        )
    # Choose colours so neighbouring panes rarely share a shade.
    centres = [centroid(p) for p in cells]
    reach = 1.5 * size / math.sqrt(len(cells))
    choice = []
    for i, (cx, cy) in enumerate(centres):
        taken = set()
        for j in range(i):
            dx = abs(cx - centres[j][0]); dx = min(dx, size - dx)
            dy = abs(cy - centres[j][1]); dy = min(dy, size - dy)
            if math.hypot(dx, dy) < reach:
                taken.add(choice[j])
        free = [k for k in range(len(glass)) if k not in taken] or list(range(len(glass)))
        choice.append(rng.choice(free))
    offsets = [(dx * size, dy * size) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]

    panes, shades, highlights, leads = [], [], [], []
    for poly, ci in zip(cells, choice):
        inner = shrink(poly, 9)
        for ox, oy in offsets:
            # Skip copies that are entirely outside the tile.
            xs = [x + ox for x, _ in poly]
            ys = [y + oy for _, y in poly]
            if max(xs) < -10 or min(xs) > size + 10 or max(ys) < -10 or min(ys) > size + 10:
                continue
            d = path(poly, ox, oy)
            panes.append(f'<path d="{d}" fill="{glass[ci]}"/>')
            shades.append(f'<path d="{d}" fill="url(#g{ci})"/>')
            if len(inner) > 2:
                highlights.append(path(inner, ox, oy))
            leads.append(d)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">
<defs>{''.join(defs)}</defs>
<rect width="{size}" height="{size}" fill="{lead}"/>
<g>{''.join(panes)}</g>
<g>{''.join(shades)}</g>
<path fill="none" stroke="#fff" stroke-opacity=".18" stroke-width="1.5" stroke-linejoin="round" d="{''.join(highlights)}"/>
<path fill="none" stroke="{lead}" stroke-width="5" stroke-linejoin="round" d="{''.join(leads)}"/>
</svg>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--cells", type=int, default=42)
    ap.add_argument("--size", type=int, default=600)
    args = ap.parse_args()

    # Same cell layout for every colourway, so they feel like one family.
    cells = build_cells(args.cells, args.size, random.Random(args.seed))
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "patterns")
    os.makedirs(out_dir, exist_ok=True)
    for name, palette in PALETTES.items():
        svg = render(cells, args.size, palette, random.Random(args.seed + 1))
        with open(os.path.join(out_dir, f"stained-glass-{name}.svg"), "w") as f:
            f.write(svg)
        print(f"wrote patterns/stained-glass-{name}.svg ({len(svg) // 1024} KB)")


if __name__ == "__main__":
    main()
