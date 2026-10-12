#!/usr/bin/env python3
"""Generate the mushroom-capped forest ranger sprite sheet.

Pure Python (no dependencies). Writes, next to this script:
  ranger_sheet.png      - the sheet, 48x48 frames, transparent background
  ranger_sheet.json     - frame/animation metadata
  ranger_sheet_4x.png   - 4x nearest-neighbour preview on a checkerboard
  preview.html          - open in a browser to see the animations play
"""
import json
import os
import struct
import zlib

FW = FH = 48
DIRS = ["down", "left", "right", "up"]


def C(r, g, b, a=255):
    return (r, g, b, a)


OUT = C(40, 26, 34)
CAP, CAP_HI, CAP_SH = C(198, 52, 50), C(234, 98, 82), C(138, 34, 44)
SPOT, SPOT_SH = C(248, 240, 222), C(214, 200, 186)
GILL, GILL_SH = C(228, 204, 164), C(186, 156, 120)
SKIN, SKIN_SH, BLUSH = C(242, 198, 152), C(208, 152, 112), C(232, 150, 130)
EYE, HAIR = C(40, 26, 34), C(120, 78, 46)
TUN, TUN_HI, TUN_SH = C(72, 132, 62), C(112, 172, 82), C(46, 92, 48)
CAPE, CAPE_SH = C(54, 104, 70), C(38, 78, 54)
BELT, BUCKLE = C(112, 72, 42), C(234, 194, 84)
PANTS, PANTS_SH = C(98, 74, 52), C(78, 58, 42)
BOOT, BOOT_HI = C(72, 48, 36), C(104, 72, 52)
WOOD, WOOD_SH = C(156, 104, 58), C(104, 66, 38)
STEEL, STEEL_SH = C(206, 216, 226), C(136, 150, 168)
LEAF = C(120, 190, 80)
SPORE, SPORE_HI = C(214, 230, 150), C(250, 250, 220)
SWOOSH = C(255, 255, 240, 160)
SPARK = C(255, 236, 140)


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self):
        self.p = [[None] * FW for _ in range(FH)]

    def px(self, x, y, c):
        x, y = int(x), int(y)
        if 0 <= x < FW and 0 <= y < FH and c:
            self.p[y][x] = c

    def get(self, x, y):
        return self.p[y][x] if 0 <= x < FW and 0 <= y < FH else None

    def rect(self, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.px(x, y, c)

    def ellipse(self, cx, cy, rx, ry, c, ymax=None):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            if ymax is not None and y > ymax:
                continue
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                nx, ny = (x - cx) / rx, (y - cy) / ry
                if nx * nx + ny * ny <= 1:
                    self.px(x, y, c(nx, ny) if callable(c) else c)

    def map(self, fn):
        out = Canvas()
        out.p = [[fn(c) if c else None for c in row] for row in self.p]
        return out

    def transformed(self, fn):
        """fn(x, y) -> source (x, y) for each destination pixel."""
        out = Canvas()
        for y in range(FH):
            for x in range(FW):
                out.p[y][x] = self.get(*fn(x, y))
        return out

    def shifted(self, dx, dy):
        return self.transformed(lambda x, y: (x - dx, y - dy))

    def mirrored(self):
        return self.transformed(lambda x, y: (FW - 1 - x, y))

    def rot_cw(self):
        return self.transformed(lambda x, y: (y, FH - 1 - x))

    def rot_ccw(self):
        return self.transformed(lambda x, y: (FW - 1 - y, x))

    def bbox(self):
        pts = [(x, y) for y in range(FH) for x in range(FW) if self.p[y][x]]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return min(xs), min(ys), max(xs), max(ys)

    def over(self, other):
        """Paint other's pixels on top of self."""
        for y in range(FH):
            for x in range(FW):
                if other.p[y][x]:
                    self.p[y][x] = other.p[y][x]
        return self


def outlined(cv):
    out = Canvas()
    out.p = [row[:] for row in cv.p]
    for y in range(FH):
        for x in range(FW):
            if cv.p[y][x] is None and any(
                cv.get(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            ):
                out.p[y][x] = OUT
    return out


def blend(c, t, k):
    return tuple(round(c[i] + (t[i] - c[i]) * k) for i in range(3)) + (c[3],)


def faded(c, a):
    return c[:3] + (round(c[3] * a),)


# ---------------------------------------------------------------- parts
def spear(cv, tx, ty, dx, dy, length=22):
    """Leaf-bladed spear; (tx, ty) is the tip, (dx, dy) the way it points."""
    qx, qy = -dy, dx
    for i, w in enumerate((0, 1, 1, 1, 0)):
        for j in range(-w, w + 1):
            cv.px(tx - dx * i + qx * j, ty - dy * i + qy * j, STEEL if j <= 0 else STEEL_SH)
    cv.px(tx - dx * 5, ty - dy * 5, BELT)
    cv.px(tx - dx * 6 + qx, ty - dy * 6 + qy, LEAF)
    cv.px(tx - dx * 7 + qx, ty - dy * 7 + qy, LEAF)
    for i in range(6, length):
        cv.px(tx - dx * i, ty - dy * i, WOOD_SH if i % 5 == 0 else WOOD)


def cap(cv, cx, cy, spots, gills=True):
    def shade(nx, ny):
        if ny > 0.55 or nx > 0.72:
            return CAP_SH
        if nx + ny < -0.85:
            return CAP_HI
        return CAP

    cv.ellipse(cx, cy, 12, 10, shade, ymax=cy + 2)
    for sx, sy, r in spots:
        for y in range(int(cy + sy - r) - 1, int(cy + sy + r) + 2):
            for x in range(int(cx + sx - r) - 1, int(cx + sx + r) + 2):
                d = ((x - cx - sx) ** 2 + (y - cy - sy) ** 2) ** 0.5
                if d <= r and y <= cy + 1 and cv.get(x, y) in (CAP, CAP_HI, CAP_SH):
                    edge = (x - cx - sx) + (y - cy - sy) > r * 0.6
                    cv.px(x, y, SPOT_SH if edge else SPOT)
    if gills:
        x0, x1 = int(cx - 9), int(cx + 9)
        cv.rect(x0, cy + 3, x1, cy + 3, GILL)
        cv.px(x0, cy + 3, GILL_SH)
        cv.px(x1, cy + 3, GILL_SH)


SPOTS_FRONT = [(-6, -4, 2.2), (4, -6, 2.6), (0, -1, 1.6), (8, -1, 1.6), (-9, 0, 1.2)]
SPOTS_BACK = [(6, -4, 2.2), (-4, -6, 2.6), (0, -1, 1.6), (-8, -1, 1.6), (9, 0, 1.2)]
SPOTS_SIDE = [(-5, -5, 2.2), (4, -6, 2.0), (1, -1, 1.6), (8, -1, 1.4), (-9, -1, 1.3)]


def pose(**kw):
    p = dict(b=0, lift=(0, 0), arm=(0, 0), legdx=(0, 0), armdx=0,
             eyes="open", spear="carry", tip=None)
    p.update(kw)
    return p


def render_front(P, back=False):
    """Facing down (back=False) or up (back=True)."""
    cv = Canvas()
    b = P["b"]
    y0 = 26 + b
    # legs
    for i, x0 in enumerate((19, 25)):
        bottom = 39 - P["lift"][i]
        cv.rect(x0, min(34 + b, bottom - 1), x0 + 3, bottom - 2, PANTS if i == 0 else PANTS_SH)
        cv.rect(x0, bottom - 1, x0 + 3, bottom, BOOT)
        cv.px(x0 + 1, bottom - 1, BOOT_HI)
    # tunic
    cv.rect(19, y0, 28, y0 + 9, TUN)
    cv.rect(18, y0 + 2, 29, y0 + 9, TUN)
    cv.rect(18, y0 + 2, 18, y0 + 8, TUN_HI)
    cv.rect(29, y0 + 2, 29, y0 + 8, TUN_SH)
    cv.rect(18, y0 + 9, 29, y0 + 9, TUN_SH)
    if back:
        cv.rect(19, y0, 28, y0 + 7, CAPE)
        cv.rect(27, y0, 28, y0 + 7, CAPE_SH)
        for x in range(19, 29, 2):
            cv.px(x, y0 + 8, CAPE)
        cv.rect(18, y0 + 6, 18, y0 + 6, BELT)
        cv.rect(29, y0 + 6, 29, y0 + 6, BELT)
    else:
        cv.rect(18, y0 + 6, 29, y0 + 6, BELT)
        cv.rect(23, y0 + 6, 24, y0 + 6, BUCKLE)
        cv.rect(23, y0, 24, y0, SKIN_SH)
    # sleeves
    for i, ax in enumerate((16, 30)):
        sw = P["arm"][i]
        cv.rect(ax, y0 + 1 + sw, ax + 1, y0 + 5 + sw, TUN if i == 0 else TUN_SH)
    # head
    if back:
        cv.rect(19, 20 + b, 28, 25 + b, SKIN_SH)
        cv.rect(19, 20 + b, 28, 23 + b, HAIR)
        for x in range(20, 28, 2):
            cv.px(x, 24 + b, HAIR)
    else:
        cv.rect(19, 20 + b, 28, 25 + b, SKIN)
        cv.rect(20, 26 + b, 27, 26 + b, SKIN)
        cv.rect(28, 21 + b, 28, 25 + b, SKIN_SH)
        e, y = P["eyes"], 22 + b
        if e == "open":
            for x in (21, 26):
                cv.rect(x, y, x, y + 1, EYE)
        elif e == "hurt":
            for x, s in ((20, 1), (27, -1)):
                cv.px(x, y - 1, EYE); cv.px(x + s, y, EYE); cv.px(x, y + 1, EYE)
        else:
            cv.rect(20, y + 1, 21, y + 1, EYE)
            cv.rect(26, y + 1, 27, y + 1, EYE)
        cv.px(20, 25 + b, BLUSH); cv.px(27, 25 + b, BLUSH)
        if e == "hurt":
            cv.rect(23, 25 + b, 24, 25 + b, EYE)
    cap(cv, 23.5, 17 + b, SPOTS_BACK if back else SPOTS_FRONT, gills=not back)
    # spear, then the hand that grips it
    hand = 0 if back else 1
    sx = 16 if back else 31
    if P["spear"] == "carry":
        sy = P["arm"][hand] + b
        if back:
            spear(cv, sx, 6 + sy, 0, -1, 34)
        else:
            spear(cv, sx, 6 + sy, 0, -1, 34)
    elif P["spear"] == "attack":
        spear(cv, sx, P["tip"], 0, -1 if back else 1, 24)
    for i, ax in enumerate((16, 30)):
        sw = P["arm"][i]
        cv.rect(ax, y0 + 6 + sw, ax + 1, y0 + 7 + sw, SKIN)
    return cv


def render_side(P):
    """Facing left; right is the mirror image."""
    cv = Canvas()
    b = P["b"]
    y0 = 26 + b
    if P["spear"] == "carry":
        spear(cv, 28, 2 + b, 0, -1, 38)
    # legs: back then front
    for x0, dx, col in ((24, P["legdx"][1], PANTS_SH), (21, P["legdx"][0], PANTS)):
        x0 += dx
        cv.rect(x0, min(34 + b, 37), x0 + 2, 37, col)
        cv.rect(x0 - 1, 38, x0 + 2, 39, BOOT)
        cv.px(x0, 38, BOOT_HI)
    # cape behind, tunic
    cv.rect(27, y0, 29, y0 + 8, CAPE_SH)
    cv.px(30, y0 + 8, CAPE_SH)
    cv.rect(19, y0, 28, y0 + 9, TUN)
    cv.rect(19, y0 + 1, 19, y0 + 8, TUN_HI)
    cv.rect(19, y0 + 9, 28, y0 + 9, TUN_SH)
    cv.rect(19, y0 + 6, 28, y0 + 6, BELT)
    cv.px(19, y0 + 6, BUCKLE)
    # head
    cv.rect(17, 21 + b, 27, 25 + b, SKIN)
    cv.rect(18, 26 + b, 25, 26 + b, SKIN)
    cv.px(16, 24 + b, SKIN)
    cv.rect(24, 21 + b, 27, 23 + b, HAIR)
    cv.rect(26, 24 + b, 27, 25 + b, HAIR)
    cv.rect(24, 24 + b, 25, 26 + b, SKIN_SH)
    e, y = P["eyes"], 22 + b
    if e == "open":
        cv.rect(19, y, 19, y + 1, EYE)
    elif e == "hurt":
        cv.px(18, y - 1, EYE); cv.px(19, y, EYE); cv.px(18, y + 1, EYE)
        cv.px(17, 25 + b, EYE)
    else:
        cv.rect(18, y + 1, 20, y + 1, EYE)
    cv.px(20, 25 + b, BLUSH)
    cap(cv, 22.5, 17 + b, SPOTS_SIDE)
    # front arm
    if P["spear"] == "attack":
        tip = P["tip"]
        sy = y0 + 3
        grip = tip + 10
        cv.rect(grip + 2, y0 + 1, 25, y0 + 3, TUN_SH)
        spear(cv, tip, sy, -1, 0, 24)
        cv.rect(grip, y0 + 2, grip + 1, y0 + 3, SKIN)
    else:
        ax = 23 + P["armdx"]
        cv.rect(ax, y0 + 1, ax + 1, y0 + 5, TUN_SH)
        cv.rect(ax, y0 + 6, ax + 1, y0 + 7, SKIN)
    return cv


def render(d, P, shift=(0, 0)):
    if d == "down":
        cv = render_front(P)
    elif d == "up":
        cv = render_front(P, back=True)
    else:
        cv = render_side(P)
    cv = outlined(cv)
    if d == "right":
        cv = cv.mirrored()
    if shift != (0, 0):
        cv = cv.shifted(*shift)
    return cv


# ---------------------------------------------------------------- effects
FACING = {"down": (0, 1), "up": (0, -1), "left": (-1, 0), "right": (1, 0)}


def swoosh(cv, d, tip):
    if d in ("down", "up"):
        s = 1 if d == "down" else -1
        x = 16 if d == "up" else 31
        for ox in (-3, 3):
            for i in range(4, 12):
                cv.px(x + ox, tip - s * i, SWOOSH)
    else:
        s = -1 if d == "left" else 1
        x = tip if d == "left" else FW - 1 - tip
        for oy in (-2, 3):
            for i in range(4, 13):
                cv.px(x - s * i, 29 + oy, SWOOSH)


def spark(cv, x, y):
    for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
        cv.px(x + dx, y + dy, SPOT if (dx, dy) == (0, 0) else SPARK)
    for dx, dy in ((2, 2), (-2, -2), (2, -2), (-2, 2)):
        cv.px(x + dx, y + dy, SPARK)


def tip_point(d, tip):
    if d == "down":
        return 31, tip + 1
    if d == "up":
        return 16, tip - 1
    if d == "left":
        return tip - 1, 29
    return FW - tip, 29


# ---------------------------------------------------------------- animations
def walk(d):
    if d in ("down", "up"):
        poses = [pose(lift=(0, 1), arm=(1, -1)), pose(b=-1),
                 pose(lift=(1, 0), arm=(-1, 1)), pose(b=-1)]
    else:
        poses = [pose(legdx=(-2, 2), armdx=1), pose(b=-1),
                 pose(legdx=(2, -2), armdx=-1), pose(b=-1)]
    return [render(d, p) for p in poses]


def attack(d):
    frames = []
    if d == "down":
        steps = [(-1, -2, 34), (1, 3, 45), (1, 3, 45), (0, 1, 40)]
        for i, (b, sw, tip) in enumerate(steps):
            frames.append((render(d, pose(b=b, arm=(0, sw), spear="attack", tip=tip)), tip))
    elif d == "up":
        steps = [(1, 1, 10), (-1, -3, 1), (-1, -3, 1), (0, -1, 5)]
        for b, sw, tip in steps:
            frames.append((render(d, pose(b=b, arm=(sw, 0), spear="attack", tip=tip)), tip))
    else:
        s = 1 if d == "right" else -1
        steps = [(-1, 14), (1, 1), (1, 1), (0, 6)]
        for lean, tip in steps:
            P = pose(spear="attack", tip=tip, legdx=(-1, 1) if lean > 0 else (0, 0))
            frames.append((render(d, P, shift=(s * lean, 0)), tip))
    out = []
    for i, (cv, tip) in enumerate(frames):
        if i == 1:
            swoosh(cv, d, tip)
        if i == 2:
            spark(cv, *tip_point(d, tip))
        out.append(cv)
    return out


def recoil(d, n):
    fx, fy = FACING[d]
    return (-fx * n, -fy * n)


def hurt(d):
    a = render(d, pose(eyes="hurt"), shift=recoil(d, 1)).map(lambda c: blend(c, C(255, 255, 255), 0.75))
    b = render(d, pose(eyes="hurt", arm=(-1, -1)), shift=recoil(d, 2)).map(lambda c: blend(c, C(255, 40, 40), 0.4))
    return [a, b]


def dropped_spear(d):
    cv = Canvas()
    spear(cv, 9, 42, -1, 0, 26)
    return outlined(cv).mirrored() if d == "right" else outlined(cv)


def lying(d):
    cv = render(d if d != "right" else "left", pose(eyes="closed", spear=None))
    cv = cv.rot_ccw() if d == "up" else cv.rot_cw()
    if d == "right":
        cv = cv.mirrored()
    x0, y0, x1, y1 = cv.bbox()
    return cv.shifted(24 - (x0 + x1 + 1) // 2, 41 - y1)


def spores(cv, rise, alpha=1.0):
    x0, y0, x1, y1 = cv.bbox()
    cx = (x0 + x1) // 2
    pts = [(-4, 2), (3, 4), (0, 1), (7, 3), (-8, 5)]
    for i, (dx, dy) in enumerate(pts[: 3 + rise // 3]):
        x, y = cx + dx, y0 - dy - rise - (i % 2)
        cv.px(x, y, faded(SPORE_HI, alpha))
        cv.px(x, y + 1, faded(SPORE, alpha))


def death(d):
    frames = []
    frames.append(render(d, pose(eyes="hurt", arm=(-1, -1)), shift=recoil(d, 2))
                  .map(lambda c: blend(c, C(255, 40, 40), 0.35)))
    for k, arm in ((2, 1), (4, 2)):
        body = render(d, pose(b=k, eyes="closed", arm=(arm, arm), spear=None))
        frames.append(dropped_spear(d).over(body))
    lie = lying(d)
    frames.append(dropped_spear(d).over(lie))
    f = dropped_spear(d).over(lie)
    spores(f, 0)
    frames.append(f)
    f = dropped_spear(d).over(lie).map(lambda c: faded(c, 0.45))
    spores(f, 6, 0.8)
    frames.append(f)
    return frames


ANIMS = [("walk", walk, 8, True), ("attack", attack, 12, False),
         ("hurt", hurt, 10, False), ("death", death, 8, False)]


# ---------------------------------------------------------------- output
def write_png(path, w, h, rows):
    raw = b"".join(b"\x00" + bytes(v for c in row for v in (c or (0, 0, 0, 0))) for row in rows)

    def chunk(t, data):
        return struct.pack(">I", len(data)) + t + data + struct.pack(">I", zlib.crc32(t + data) & 0xFFFFFFFF)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)))
        f.write(chunk(b"IDAT", zlib.compress(raw, 9)))
        f.write(chunk(b"IEND", b""))


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    rows_meta, grid = {}, []
    for name, fn, fps, loop in ANIMS:
        for d in DIRS:
            frames = fn(d)
            rows_meta[f"{name}_{d}"] = {"row": len(grid), "frames": len(frames), "fps": fps, "loop": loop}
            grid.append(frames)
    cols = max(len(r) for r in grid)
    W, H = cols * FW, len(grid) * FH
    sheet = [[None] * W for _ in range(H)]
    for r, frames in enumerate(grid):
        for c, cv in enumerate(frames):
            for y in range(FH):
                sheet[r * FH + y][c * FW:(c + 1) * FW] = cv.p[y]
    write_png(os.path.join(here, "ranger_sheet.png"), W, H, sheet)

    meta = {
        "image": "ranger_sheet.png",
        "frameWidth": FW, "frameHeight": FH, "columns": cols, "rows": len(grid),
        "origin": {"x": 24, "y": 40, "note": "feet / ground contact point inside each frame"},
        "layout": "one row per animation+direction; frames left to right; unused cells are empty",
        "animations": rows_meta,
    }
    with open(os.path.join(here, "ranger_sheet.json"), "w") as f:
        json.dump(meta, f, indent=2)

    # 4x preview on a checkerboard with frame grid lines
    S = 4
    prev = []
    for y in range(H * S):
        row = []
        for x in range(W * S):
            sx, sy = x // S, y // S
            c = sheet[sy][sx]
            bg = C(70, 74, 82) if ((sx // 4 + sy // 4) % 2) else C(82, 86, 96)
            if x % (FW * S) == 0 or y % (FH * S) == 0:
                bg = C(40, 42, 48)
            if c:
                a = c[3] / 255
                row.append(tuple(round(c[i] * a + bg[i] * (1 - a)) for i in range(3)) + (255,))
            else:
                row.append(bg)
        prev.append(row)
    write_png(os.path.join(here, "ranger_sheet_4x.png"), W * S, H * S, prev)

    html = PREVIEW_HTML.replace("__META__", json.dumps(meta))
    with open(os.path.join(here, "preview.html"), "w") as f:
        f.write(html)
    print(f"sheet {W}x{H}, {len(grid)} rows x {cols} cols")


PREVIEW_HTML = """<!doctype html>
<meta charset="utf-8"><title>Mushroom Ranger preview</title>
<style>
 body{background:#2b2d33;color:#ddd;font:14px sans-serif;margin:20px}
 .grid{display:grid;grid-template-columns:repeat(4,auto);gap:16px;justify-content:start}
 figure{margin:0;text-align:center} canvas{image-rendering:pixelated;background:#454a52;border-radius:6px}
 figcaption{margin-top:4px}
</style>
<h2>Mushroom-capped forest ranger</h2>
<div class="grid" id="g"></div>
<script>
const META = __META__;
const img = new Image(); img.src = META.image;
img.onload = () => {
  const g = document.getElementById('g'), S = 4, items = [];
  for (const [name, a] of Object.entries(META.animations)) {
    const fig = document.createElement('figure'), cv = document.createElement('canvas');
    cv.width = META.frameWidth * S; cv.height = META.frameHeight * S;
    const cap = document.createElement('figcaption'); cap.textContent = name;
    fig.append(cv, cap); g.append(fig);
    const ctx = cv.getContext('2d'); ctx.imageSmoothingEnabled = false;
    items.push({a, ctx, t0: performance.now()});
  }
  (function tick(now) {
    for (const it of items) {
      const {a, ctx} = it;
      let f = Math.floor((now - it.t0) / 1000 * a.fps);
      if (a.loop) f %= a.frames;
      else if (f >= a.frames + a.fps) { it.t0 = now; f = 0; }   // hold last frame ~1s, then replay
      else f = Math.min(f, a.frames - 1);
      ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
      ctx.drawImage(img, f * META.frameWidth, a.row * META.frameHeight, META.frameWidth, META.frameHeight,
                    0, 0, ctx.canvas.width, ctx.canvas.height);
    }
    requestAnimationFrame(tick);
  })(performance.now());
};
</script>
"""

if __name__ == "__main__":
    main()
