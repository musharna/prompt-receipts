import math, struct, zlib, json, sys

W, H = 48, 32
P = {
    'ol': (59, 38, 52), 'skin': (240, 210, 160), 'skin2': (214, 168, 120), 'skin3': (190, 140, 100),
    'sh': (224, 130, 70), 'sh_hi': (248, 190, 110), 'sh_lo': (176, 90, 56), 'sp': (122, 58, 46),
    'st': (170, 182, 204), 'st_hi': (232, 238, 248), 'st_lo': (108, 120, 150),
    'red': (214, 69, 80), 'red2': (160, 44, 64), 'wood': (140, 90, 52), 'wood2': (104, 64, 40),
    'white': (255, 250, 240), 'blush': (240, 140, 140), 'trail': (255, 244, 214), 'dark': (40, 24, 40),
}

class Img:
    def __init__(s): s.px = [[None] * W for _ in range(H)]
    def set(s, x, y, c):
        if 0 <= x < W and 0 <= y < H: s.px[y][x] = c
    def get(s, x, y): return s.px[y][x] if 0 <= x < W and 0 <= y < H else None

def line_pts(x0, y0, x1, y1):
    x0, y0, x1, y1 = map(round, (x0, y0, x1, y1))
    dx, dy = abs(x1 - x0), -abs(y1 - y0); sx = 1 if x0 < x1 else -1; sy = 1 if y0 < y1 else -1
    e = dx + dy; out = []
    while True:
        out.append((x0, y0))
        if x0 == x1 and y0 == y1: break
        e2 = 2 * e
        if e2 >= dy: e += dy; x0 += sx
        if e2 <= dx: e += dx; y0 += sy
    return out

def ell(cx, cy, rx, ry, clip=None):
    pts = set()
    for y in range(H):
        for x in range(W):
            if ((x + .5 - cx) / rx) ** 2 + ((y + .5 - cy) / ry) ** 2 <= 1:
                if clip is None or clip(x, y): pts.add((x, y))
    return pts

def part(img, pts, colfn, outline=True):
    if outline:
        for (x, y) in pts:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if (x + dx, y + dy) not in pts: img.set(x + dx, y + dy, P['ol'])
    for (x, y) in pts: img.set(x, y, P[colfn(x, y)])

def render(bob=0, phase=0, lean=0, ang=-50, ln=12, trail=None, hide=0.0, sway=0, blink=False):
    im = Img()
    t = hide
    # --- body (foot + neck + head) ---
    hx = round(32 + lean - 8 * t); hy = round(18 + 4 * t + bob)
    if t < 0.95:
        x0 = 5 + 16 * t; x1 = 34 - 8 * t
        foot = ell((x0 + x1) / 2, 27.5, (x1 - x0) / 2, 2.8, clip=lambda x, y: y <= 29)
        nx = (hx + 28 - 8 * t) / 2
        neck = ell(nx, (hy + 27) / 2, 3.6, (27 - hy) / 2 + 2)
        head = ell(hx, hy, 4.6, 4.6)
        body = foot | neck | head
        def bc(x, y):
            if y >= 28: return 'skin3'
            if y in (26, 27) and (x, y) in foot: return 'skin2' if ((x + phase + (y - 26) * 3) // 3) % 2 else 'skin'
            if (x, y) in head and y >= hy + 2: return 'skin2'
            return 'skin'
        part(im, body, bc)
        if t < 0.7:
            # helmet dome
            dome = ell(hx - .5, hy - 2.5, 4.8, 3.8, clip=lambda x, y: y <= hy - 2)
            part(im, dome, lambda x, y: 'st_hi' if (x < hx - 1 and y < hy - 4) else ('st_lo' if y >= hy - 3 or x > hx + 2 else 'st'))
            for x in range(hx - 4, hx + 5): im.set(x, hy - 1, P['ol'])
            # plume
            for (dx, dy, c) in ((-4, -6, 'red'), (-5, -5, 'red'), (-5, -4, 'red2'), (-6, -4 + sway, 'red2'), (-4, -5, 'red')):
                im.set(hx + dx, hy + dy, P[c])
            # face
            ey = hy
            if blink: im.set(hx + 2, ey, P['ol']); im.set(hx + 3, ey, P['ol'])
            else: im.set(hx + 2, ey, P['ol']); im.set(hx + 2, ey + 1, P['ol'])
            im.set(hx + 3, hy + 2, P['blush']); im.set(hx, hy + 2, P['blush'])
            im.set(hx + 2, hy + 3, P['ol']); im.set(hx + 3, hy + 3, P['ol'])
            # eye stalks poking from helmet
            for k, sx in enumerate((hx - 2, hx + 1)):
                lx = sx + sway; top = hy - 10 + k
                pts = line_pts(sx, hy - 5, lx + 1, top + 2)
                for (px, py) in pts: im.set(px, py, P['skin2'])
                for (px, py) in pts: im.set(px, py + 0, P['skin2'])
                for (px, py) in pts[:-1]:
                    pass
                ex, ey2 = lx + 1, top
                for dx in (0, 1):
                    for dy in (0, 1):
                        pass
                eye = {(ex, ey2), (ex + 1, ey2), (ex, ey2 + 1), (ex + 1, ey2 + 1)}
                part(im, eye, lambda x, y: 'white')
                im.set(ex + 1, ey2 + 1, P['ol'])
        # lance
        if t < 0.85:
            L = ln * (1 - 1.1 * t); a = math.radians(ang - 60 * t)
            px, py = hx + 2, hy + 5
            ux, uy = math.cos(a), math.sin(a)
            if trail:
                for ta in [trail[0] + (trail[1] - trail[0]) * i / 14 for i in range(15)]:
                    r = math.radians(ta)
                    for rr in (L + 1, L - 1):
                        im.set(round(px + rr * math.cos(r)), round(py + rr * math.sin(r)), P['trail'])
            back = line_pts(px - 3 * ux, py - 3 * uy, px + L * ux, py + L * uy)
            for i, (x, y) in enumerate(back):
                im.set(x, y, P['wood']); im.set(x, y + 1, P['wood2']) if abs(ux) > abs(uy) else im.set(x + 1, y, P['wood2'])
            tipx, tipy = px + L * ux, py + L * uy
            for k, (d, c) in enumerate(((0, 'st'), (1, 'st_hi'), (2, 'st_hi'), (3, 'st_hi'))):
                im.set(round(tipx + d * ux), round(tipy + d * uy), P[c])
            im.set(round(tipx + 4 * ux), round(tipy + 4 * uy), P['ol'])
            # pennant
            bx, by = px + (L - 3) * ux, py + (L - 3) * uy
            for (dx, dy, c) in ((0, 1, 'red'), (-1, 1, 'red'), (-2, 1, 'red2'), (-1, 2, 'red2')):
                im.set(round(bx + dx), round(by + dy - (1 if uy < -.5 else 0)), P[c])
            # hand
            part(im, {(px, py), (px + 1, py), (px, py + 1), (px + 1, py + 1)}, lambda x, y: 'skin')
    # --- shell ---
    r = 9 + t; cx = 15 + 9 * t; cy = 18 + t + bob * 0.0
    cy = cy + (bob if t < .5 else 0)
    shell = ell(cx, cy, r, r, clip=lambda x, y: y <= 29)
    def sc(x, y):
        d = (-(x + .5 - cx) * .6 - (y + .5 - cy) * .8) / r
        return 'sh_hi' if d > .55 else ('sh_lo' if d < -.35 else 'sh')
    part(im, shell, sc)
    # spiral
    th = 0.0
    while th < 3.3 * math.pi:
        rr = r * 0.82 * (1 - th / (3.7 * math.pi))
        x = round(cx - .5 + rr * math.cos(th + .6)); y = round(cy - .5 + rr * math.sin(th + .6))
        if (x, y) in shell: im.set(x, y, P['sp'])
        th += 0.07
    if t >= 0.8:
        ap = ell(cx + r - 3, cy + 4, 3.2, 4.4, clip=lambda x, y: (x, y) in shell and y <= 28)
        part(im, ap, lambda x, y: 'dark')
        ax, ay = round(cx + r - 4), round(cy + 3)
        if not blink:
            im.set(ax, ay, P['white']); im.set(ax + 2, ay, P['white'])
    # --- global outline ---
    out = [row[:] for row in im.px]
    for y in range(H):
        for x in range(W):
            if im.px[y][x] is None and any(im.get(x + dx, y + dy) is not None for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out[y][x] = P['ol']
    SH = 3
    im.px = [row[SH:] + [None] * SH for row in out]
    return im

def frames():
    walk = []
    for i in range(6):
        s = math.sin(2 * math.pi * i / 6)
        walk.append(render(bob=[0, 0, -1, 0, 0, -1][i], phase=i, lean=round(s * 1), ang=-50 + round(s * 3), sway=round(s), blink=False))
    atk_params = [(0, -50, 0, None), (-2, -80, 0, None), (-3, -98, 0, None), (1, -50, 0, (-98, -50)),
                  (3, 2, 0, (-50, 2)), (3, 12, 0, (2, 12)), (1, -35, 0, None)]
    attack = [render(lean=l, ang=a, ln=13 if l >= 1 else 12, trail=tr, sway=-1 if l < 0 else 1, blink=(i == 4)) for i, (l, a, _, tr) in enumerate(atk_params)]
    hide = [render(hide=t, ang=-50, bob=0, blink=(i == 5 and False), phase=0) for i, t in enumerate((0, .2, .4, .6, .8, 1.0))]
    return {'walk': walk, 'attack': attack, 'hide': hide}

def png(path, rows, scale=1):
    h = len(rows); w = len(rows[0])
    raw = b''
    for row in rows:
        line = b''
        for c in row:
            px = (c + (255,)) if c else (0, 0, 0, 0)
            line += bytes(px) * scale
        for _ in range(scale): raw += b'\x00' + line
    def chunk(t, d):
        c = struct.pack('>I', len(d)) + t + d
        return c + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w * scale, h * scale, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))

if __name__ == '__main__':
    out = sys.argv[1]
    fr = frames()
    cols = max(len(v) for v in fr.values())
    sheet = [[None] * (W * cols) for _ in range(H * len(fr))]
    atlas = {'frame_width': W, 'frame_height': H, 'animations': {}}
    for r, (name, lst) in enumerate(fr.items()):
        atlas['animations'][name] = {'row': r, 'frames': len(lst)}
        for c, im in enumerate(lst):
            for y in range(H):
                for x in range(W): sheet[r * H + y][c * W + x] = im.px[y][x]
    png(f'{out}/snail_knight_sheet.png', sheet)
    png(f'{out}/snail_knight_sheet_x4.png', sheet, 4)
    json.dump(atlas, open(f'{out}/snail_knight_atlas.json', 'w'), indent=2)
