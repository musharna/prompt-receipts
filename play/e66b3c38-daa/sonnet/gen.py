import random, math, colorsys, sys
T = 640
N = 7  # grid 7x7 jittered -> 49 cells
random.seed(11)
cell = T / N
seeds = []
for i in range(N):
    for j in range(N):
        seeds.append(((i + .5 + random.uniform(-.38, .38)) * cell,
                      (j + .5 + random.uniform(-.38, .38)) * cell))
wrapped = [(x + dx * T, y + dy * T, k) for k, (x, y) in enumerate(seeds)
           for dx in (-1, 0, 1) for dy in (-1, 0, 1)]

def clip(poly, a, b, c):  # keep a*x+b*y<=c
    out = []
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        fp, fq = a*p[0]+b*p[1]-c, a*q[0]+b*q[1]-c
        if fp <= 0: out.append(p)
        if (fp < 0 < fq) or (fq < 0 < fp):
            t = fp / (fp - fq)
            out.append((p[0]+t*(q[0]-p[0]), p[1]+t*(q[1]-p[1])))
    return out

def voronoi(sx, sy):
    poly = [(sx-T, sy-T), (sx+T, sy-T), (sx+T, sy+T), (sx-T, sy+T)]
    for ox, oy, _ in sorted(wrapped, key=lambda w: (w[0]-sx)**2+(w[1]-sy)**2)[1:]:
        if (ox-sx)**2+(oy-sy)**2 > 4*(T*.5)**2 * 1.2: break
        a, b = ox-sx, oy-sy
        poly = clip(poly, a, b, (ox*ox+oy*oy-sx*sx-sy*sy)/2)
    return poly

cells = [(x, y, voronoi(x, y), k) for x, y, k in
         [(s[0], s[1], i) for i, s in enumerate(seeds)]]

def path(poly, cx=None, cy=None, s=1, ox=0, oy=0):
    pts = poly if cx is None else [(cx+(x-cx)*s, cy+(y-cy)*s) for x, y in poly]
    return "M" + "L".join(f"{x+ox:.1f} {y+oy:.1f}" for x, y in pts) + "Z"

# (hue, sat, light range) with a small hue drift per colourway
WAYS = {
  "amber":   dict(h=(24, 46), s=(.85, 1.0), l=(.30, .56), bg="#1c0d03", lead="#120802"),
  "cobalt":  dict(h=(205, 232), s=(.75, 1.0), l=(.26, .52), bg="#040b1f", lead="#030818"),
  "emerald": dict(h=(140, 166), s=(.65, .9), l=(.20, .44), bg="#03140c", lead="#020d08"),
}
for name, w in WAYS.items():
    rnd = random.Random(5)
    defs, body = [], []
    for ox in (-T, 0, T):
        for oy in (-T, 0, T):
            for x, y, poly, k in cells:
                r = random.Random(k)  # same colour for each tiled copy
                h = r.uniform(*w["h"]); s = r.uniform(*w["s"]); l = r.uniform(*w["l"])
                col = lambda dl: "#%02x%02x%02x" % tuple(int(255*c) for c in colorsys.hls_to_rgb(h/360, min(1, l+dl), s))
                gid = f"g{k}"
                if (ox, oy) == (0, 0):
                    defs.append(f'<radialGradient id="{gid}" gradientUnits="userSpaceOnUse" cx="{x:.1f}" cy="{y:.1f}" r="{cell*.9:.0f}">'
                                f'<stop offset="0" stop-color="{col(.14)}"/><stop offset="1" stop-color="{col(-.06)}"/></radialGradient>')
                tr = f'transform="translate({ox} {oy})"'
                body.append(f'<g {tr}><path d="{path(poly)}" fill="url(#{gid})"/>'
                            f'<path d="{path(poly,x,y,.8)}" fill="none" stroke="#fff" stroke-opacity=".10" stroke-width="2"/></g>')
    leads = "".join(f'<path d="{path(p)}" transform="translate({ox} {oy})"/>'
                    for ox in (-T,0,T) for oy in (-T,0,T) for _,_,p,_ in cells)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{T}" height="{T}" viewBox="0 0 {T} {T}">'
           f'<defs>{"".join(defs)}<filter id="n"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="3" stitchTiles="stitch"/>'
           f'<feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .5 -.18"/></filter></defs>'
           f'<rect width="{T}" height="{T}" fill="{w["bg"]}"/>{"".join(body)}'
           f'<rect width="{T}" height="{T}" filter="url(#n)" opacity=".35"/>'
           f'<g fill="none" stroke="{w["lead"]}" stroke-width="7" stroke-linejoin="round">{leads}</g>'
           f'<g fill="none" stroke="#fff" stroke-opacity=".07" stroke-width="1" transform="translate(-1.5 -1.5)" stroke-linejoin="round">{leads}</g>'
           f'</svg>')
    open(f"glass/stained-glass-{name}.svg", "w").write(svg)
