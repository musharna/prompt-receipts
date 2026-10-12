#!/usr/bin/env python3
"""Procedural park trees exported as glTF binary (.glb).

Conventions: Y-up, metres, origin at the trunk base on the ground plane
(roots sink ~0.3 m below y=0). Colours are baked into vertex colours, so the
models need no textures. Each file holds one mesh with up to three
primitives/materials: bark, leaves, blossom (leaves/blossom are double-sided).

Usage: python3 make_trees.py [out_dir]
"""
import json
import math
import os
import random
import struct
import sys

UP = (0.0, 1.0, 0.0)
DOWN = (0.0, -1.0, 0.0)


# ---------------------------------------------------------------- vectors
def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def mul(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def length(a): return math.sqrt(dot(a, a))
def lerp(a, b, t): return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)
def vsum(*vs):
    x = y = z = 0.0
    for v in vs:
        x += v[0]; y += v[1]; z += v[2]
    return (x, y, z)


def norm(a):
    l = length(a)
    return (0.0, 1.0, 0.0) if l < 1e-12 else (a[0] / l, a[1] / l, a[2] / l)


def perp(v):
    ref = (1.0, 0.0, 0.0) if abs(v[0]) < 0.9 else (0.0, 0.0, 1.0)
    return norm(cross(v, ref))


def rotate(v, axis, ang):
    k = norm(axis)
    c, s = math.cos(ang), math.sin(ang)
    return add(add(mul(v, c), mul(cross(k, v), s)), mul(k, dot(k, v) * (1 - c)))


def rand_unit(rng):
    return norm((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1)))


def outward(p):
    return norm((p[0], 0.0, p[2])) if abs(p[0]) + abs(p[2]) > 1e-6 else (1.0, 0.0, 0.0)


def horiz(az):
    return (math.cos(az), 0.0, math.sin(az))


def tilt_from_up(az, ang):
    """Direction `ang` radians away from vertical, toward azimuth `az`."""
    return add(mul(UP, math.cos(ang)), mul(horiz(az), math.sin(ang)))


def branch_dir(T, ang, az):
    """Rotate tangent T away by `ang`, then spin it by `az` around T."""
    ref = cross(T, UP)
    if length(ref) < 1e-3:
        ref = cross(T, (1.0, 0.0, 0.0))
    return rotate(rotate(T, ref, ang), T, az)


def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x


# ---------------------------------------------------------------- noise
def _hash(ix, iy, iz, seed):
    n = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
    n &= 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def vnoise(x, y, z, seed=0):
    ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = x - ix, y - iy, z - iz
    fx, fy, fz = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy), fz * fz * (3 - 2 * fz)
    def h(a, b, c): return _hash(ix + a, iy + b, iz + c, seed)
    x00 = h(0, 0, 0) + (h(1, 0, 0) - h(0, 0, 0)) * fx
    x10 = h(0, 1, 0) + (h(1, 1, 0) - h(0, 1, 0)) * fx
    x01 = h(0, 0, 1) + (h(1, 0, 1) - h(0, 0, 1)) * fx
    x11 = h(0, 1, 1) + (h(1, 1, 1) - h(0, 1, 1)) * fx
    y0 = x00 + (x10 - x00) * fy
    y1 = x01 + (x11 - x01) * fy
    return y0 + (y1 - y0) * fz


def fbm(x, y, z, seed=0, octaves=3):
    total, amp, freq, wsum = 0.0, 1.0, 1.0, 0.0
    for o in range(octaves):
        total += amp * vnoise(x * freq, y * freq, z * freq, seed + o * 31)
        wsum += amp
        amp *= 0.5
        freq *= 2.03
    return total / wsum


# ---------------------------------------------------------------- colour
def rgb(hexv):
    """sRGB hex -> linear float triple (glTF vertex colours are linear)."""
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (lin((hexv >> 16) & 255), lin((hexv >> 8) & 255), lin(hexv & 255))


def cmix(a, b, t): return lerp(a, b, clamp(t))
def cscale(c, s): return (c[0] * s, c[1] * s, c[2] * s)


# ---------------------------------------------------------------- geometry
class Mesh:
    def __init__(self):
        self.pos, self.nrm, self.col, self.idx = [], [], [], []

    def vert(self, p, n, c):
        self.pos.append(p); self.nrm.append(n); self.col.append(c)
        return len(self.pos) - 1

    def tri(self, a, b, c):
        self.idx.extend((a, b, c))


class Branch:
    def __init__(self, pts, radii):
        self.pts, self.radii = pts, radii
        self.length = sum(length(sub(pts[i + 1], pts[i])) for i in range(len(pts) - 1))

    def at(self, t):
        n = len(self.pts) - 1
        f = clamp(t) * n
        i = min(int(f), n - 1)
        u = f - i
        p = lerp(self.pts[i], self.pts[i + 1], u)
        T = norm(sub(self.pts[i + 1], self.pts[i]))
        r = self.radii[i] + (self.radii[i + 1] - self.radii[i]) * u
        return p, T, r

    def tip(self):
        return self.at(1.0)


def grow(rng, start, d, length_, r0, r1, seg=0.1, bend=None, wander=0.0,
         kink_p=0.0, kink=0.0, taper=1.0):
    """Walk a branch path. `bend(t, d, p)` is a curvature vector in rad/m,
    `wander` a random-walk strength (rad/sqrt(m)), kinks are sudden turns."""
    n = max(2, int(math.ceil(length_ / seg)))
    step = length_ / n
    p, d = start, norm(d)
    pts = [p]
    for i in range(1, n + 1):
        t = i / n
        if bend:
            d = norm(add(d, mul(bend(t, d, p), step)))
        if wander:
            d = norm(add(d, mul(rand_unit(rng), wander * math.sqrt(step))))
        if kink_p and rng.random() < kink_p * step:
            d = norm(add(d, mul(rand_unit(rng), kink)))
        p = add(p, mul(d, step))
        pts.append(p)
    radii = [r1 + (r0 - r1) * (1 - i / n) ** taper for i in range(n + 1)]
    return Branch(pts, radii)


class Model:
    def __init__(self):
        self.bark, self.leaf, self.blossom = Mesh(), Mesh(), Mesh()

    # -- tubes -----------------------------------------------------------
    def tube(self, br, sides, color_fn, rmod=None, cap=True):
        m = self.bark
        pts, radii = br.pts, br.radii
        n = len(pts)
        base = len(m.pos)
        tangents = []
        for i in range(n):
            a, b = pts[max(i - 1, 0)], pts[min(i + 1, n - 1)]
            tangents.append(norm(sub(b, a)))
        N = perp(tangents[0])
        s = 0.0
        for i in range(n):
            T = tangents[i]
            if i:
                s += length(sub(pts[i], pts[i - 1]))
                N = sub(N, mul(T, dot(N, T)))
                N = perp(T) if length(N) < 1e-6 else norm(N)
            B = cross(T, N)
            t = i / (n - 1)
            for j in range(sides):
                th = 2 * math.pi * j / sides
                dv = add(mul(N, math.cos(th)), mul(B, math.sin(th)))
                k = rmod(t, th, s, pts[i], dv, radii[i]) if rmod else 1.0
                p = add(pts[i], mul(dv, radii[i] * k))
                m.vert(p, dv, color_fn(p, th, s, radii[i], k, dv))
        first_idx = len(m.idx)
        for i in range(n - 1):
            r0, r1 = base + i * sides, base + (i + 1) * sides
            for j in range(sides):
                j2 = (j + 1) % sides
                m.tri(r0 + j, r0 + j2, r1 + j2)
                m.tri(r0 + j, r1 + j2, r1 + j)
        if cap and radii[-1] > 0.004:
            p, T, r = br.tip()
            c = m.vert(add(p, mul(T, r * 0.4)), T, m.col[-1])
            last = base + (n - 1) * sides
            for j in range(sides):
                m.tri(last + j, last + (j + 1) % sides, c)
        self._smooth(m, base, first_idx)

    @staticmethod
    def _smooth(m, vbase, ibase):
        acc = {}
        idx = m.idx
        for k in range(ibase, len(idx), 3):
            a, b, c = idx[k], idx[k + 1], idx[k + 2]
            fn = cross(sub(m.pos[b], m.pos[a]), sub(m.pos[c], m.pos[a]))
            for v in (a, b, c):
                acc[v] = add(acc.get(v, (0.0, 0.0, 0.0)), fn)
        for v, n in acc.items():
            if length(n) > 1e-12:
                m.nrm[v] = norm(n)

    # -- leaves ------------------------------------------------------------
    def add_leaf(self, P, D, hint, size, width_fn, stations, color, fold=0.25,
             curl=0.12, petiole=0.15, tip_color=None):
        m = self.leaf
        D = norm(D)
        S = cross(D, hint)
        if length(S) < 1e-4:
            S = perp(D)
        S = norm(S)
        Nn = cross(S, D)
        start = add(P, mul(D, size * petiole))
        tip_color = tip_color or color
        vis = []
        for i in range(stations + 1):
            u = i / stations
            mid = vsum(start, mul(D, u * size), mul(Nn, -curl * size * u * u))
            w = width_fn(u) * size
            col = cmix(color, tip_color, u)
            nl, nr = norm(sub(Nn, mul(S, fold))), norm(add(Nn, mul(S, fold)))
            row = [m.vert(mid, Nn, cscale(col, 1.08))]
            if w > 1e-5:
                row.append(m.vert(vsum(mid, mul(S, w), mul(Nn, fold * w)), nl, col))
                row.append(m.vert(vsum(mid, mul(S, -w), mul(Nn, fold * w)), nr, col))
            vis.append(row)
        for i in range(stations):
            a, b = vis[i], vis[i + 1]
            for side in (1, 2):
                ma, mb = a[0], b[0]
                sa = a[side] if len(a) > 1 else None
                sb = b[side] if len(b) > 1 else None
                if sa is not None and sb is not None:
                    self._ftri(m, ma, sa, sb, Nn); self._ftri(m, ma, sb, mb, Nn)
                elif sb is not None:
                    self._ftri(m, ma, sb, mb, Nn)
                elif sa is not None:
                    self._ftri(m, ma, sa, mb, Nn)

    @staticmethod
    def _ftri(m, a, b, c, N):
        fn = cross(sub(m.pos[b], m.pos[a]), sub(m.pos[c], m.pos[a]))
        if dot(fn, N) < 0:
            b, c = c, b
        m.tri(a, b, c)

    # -- flowers -------------------------------------------------------------
    def flower(self, P, F, radius, c_center, c_edge, petals=5, cup=0.35, rng=None):
        m = self.blossom
        F = norm(F)
        S = perp(F)
        U = cross(F, S)
        rot = rng.uniform(0, 2 * math.pi) if rng else 0.0
        centre = m.vert(P, F, c_center)
        ring = []
        k_total = petals * 2
        for k in range(k_total):
            a = rot + 2 * math.pi * k / k_total
            ph = k % 2            # 0: between petals, 1: petal tip
            rr = radius * (0.45 if ph == 0 else 1.0)
            q = vsum(P, mul(S, math.cos(a) * rr), mul(U, math.sin(a) * rr), mul(F, cup * rr))
            ring.append(m.vert(q, norm(add(F, mul(sub(q, P), -0.8 / max(radius, 1e-6)))),
                               cmix(c_center, c_edge, 0.55 if ph == 0 else 1.0)))
        for k in range(k_total):
            self._ftri(m, centre, ring[k], ring[(k + 1) % k_total], F)

    # -- baked crown occlusion -------------------------------------------------
    def occlude(self, mesh, strength=0.55):
        if not mesh.pos:
            return
        xs = [p[0] for p in mesh.pos]; ys = [p[1] for p in mesh.pos]; zs = [p[2] for p in mesh.pos]
        c = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2)
        e = (max((max(xs) - min(xs)) / 2, 0.1), max((max(ys) - min(ys)) / 2, 0.1), max((max(zs) - min(zs)) / 2, 0.1))
        y0, y1 = min(ys), max(ys)
        for i, p in enumerate(mesh.pos):
            q = ((p[0] - c[0]) / e[0], (p[1] - c[1]) / e[1], (p[2] - c[2]) / e[2])
            d = clamp(length(q))
            h = (p[1] - y0) / max(y1 - y0, 1e-6)
            ao = clamp((1 - strength) + strength * (0.75 * d ** 1.3 + 0.35 * h), 0.3, 1.0)
            mesh.col[i] = cscale(mesh.col[i], ao)

    def stats(self):
        return {k: (len(getattr(self, k).pos), len(getattr(self, k).idx) // 3)
                for k in ("bark", "leaf", "blossom")}


# ---------------------------------------------------------------- shared shapes
def flare_rmod(seed, flare=0.4, roots=5, ridges=0.0, ridge_n=9, ground=0.3, knobs=0.0):
    rr = random.Random(seed)
    ph = rr.uniform(0, 6.3)
    def f(t, th, s, P, dv, r):
        h = max(0.0, s - ground)
        k = 1.0 + flare * math.exp(-h / 0.45) * (0.35 + 0.65 * max(0.0, math.cos(roots * (th - ph))) ** 2)
        if ridges:
            k += ridges * math.sin(ridge_n * th + s * 0.7)
        if knobs:
            q = add(P, mul(dv, r))
            k += knobs * (fbm(q[0] * 3, q[1] * 3, q[2] * 3, seed) - 0.5)
        return k
    return f


def width_lanceolate(ratio):
    return lambda u: ratio * math.sin(math.pi * u) ** 0.8


# ================================================================ WILLOW
def make_willow(seed=11):
    rng = random.Random(seed)
    M = Model()
    c_bark, c_fiss, c_whip = rgb(0x6b6052), rgb(0x2e2822), rgb(0x8c8a48)

    def bark(p, th, s, r, k, dv):
        if r < 0.016:
            return cmix(c_whip, c_bark, r / 0.016)
        q = add(p, mul(dv, 0.0))
        streak = vnoise(dv[0] * 7 + q[0], s * 1.2, dv[2] * 7 + q[2] + dv[1] * 7, 3)
        v = fbm(q[0] * 4, q[1] * 4, q[2] * 4, 5)
        c = cmix(c_bark, c_fiss, clamp((streak - 0.45) * 2.4) * clamp(r * 6))
        return cscale(c, 0.8 + 0.4 * v)

    trunk = grow(rng, (0, -0.3, 0), (0.07, 1, 0.03), 3.3, 0.5, 0.36, seg=0.1, wander=0.08)
    M.tube(trunk, 22, bark, flare_rmod(1, flare=0.5, roots=5, ridges=0.05, knobs=0.18))

    def leaf_on(p, T, side):
        D = norm(vsum(T, mul(side, 0.6), mul(rand_unit(rng), 0.2)))
        hint = norm(add(outward(p), mul(rand_unit(rng), 0.6)))
        col = cmix(rgb(0x6f8f2c), rgb(0xa2b552), rng.random())
        M.add_leaf(p, D, hint, rng.uniform(0.13, 0.18), width_lanceolate(0.075), 2, col,
               fold=0.2, curl=0.15, tip_color=cscale(col, 0.85))

    def whip(p, T):
        d = norm(vsum(mul(T, 0.5), mul(outward(p), 0.7), mul(UP, 0.25), mul(rand_unit(rng), 0.25)))
        end_y = rng.uniform(0.35, 2.4) if rng.random() < 0.8 else p[1] - rng.uniform(1.0, 3.0)
        L = max(0.8, p[1] - end_y + 0.5)
        drift = mul(rand_unit(rng), 0.05)
        w = grow(rng, p, d, L, 0.012, 0.003, seg=0.15, wander=0.05,
                 bend=lambda t, d_, p_: add(mul(DOWN, 3.2), drift))
        M.tube(w, 3, bark, cap=False)
        n = int(w.length / 0.075)
        for i in range(n):
            t = 0.06 + 0.94 * (i + rng.random() * 0.4) / n
            q, Tq, r = w.at(t)
            side = branch_dir(Tq, math.pi / 2, i * math.pi + rng.uniform(-0.6, 0.6))
            leaf_on(add(q, mul(side, r)), Tq, side)

    def whips_along(br, t0, t1, spacing):
        n = max(1, int(br.length * (t1 - t0) / spacing))
        for i in range(n):
            p, T, r = br.at(t0 + (t1 - t0) * (i + rng.random()) / n)
            whip(p, T)

    nsc = 5
    for k in range(nsc):
        p, T, r = trunk.at(rng.uniform(0.82, 0.98))
        az = 2 * math.pi * k / nsc + rng.uniform(-0.3, 0.3)
        out = horiz(az)
        sc = grow(rng, p, tilt_from_up(az, rng.uniform(0.35, 0.75)), rng.uniform(4.5, 6.0),
                  r * 0.62, 0.05, seg=0.12, wander=0.15,
                  bend=lambda t, d, p_, out=out: add(mul(out, 0.12), mul(UP, 0.10 - 0.35 * t)))
        M.tube(sc, 14, bark, flare_rmod(k + 10, flare=0.0, knobs=0.12))
        ns = rng.randint(6, 9)
        for j in range(ns):
            ts = 0.25 + 0.75 * (j + rng.random() * 0.6) / ns
            p2, T2, r2 = sc.at(ts)
            d2 = norm(add(branch_dir(T2, rng.uniform(0.5, 0.9), rng.uniform(0, 6.283)), (0, 0.4, 0)))
            sb = grow(rng, p2, d2, rng.uniform(1.8, 3.2) * (1.1 - 0.4 * ts), min(r2 * 0.7, 0.06), 0.012,
                      seg=0.12, wander=0.2, bend=lambda t, d, p_: (0, 0.15 - 0.9 * t, 0))
            M.tube(sb, 6, bark)
            whips_along(sb, 0.2, 1.0, 0.15)
        whips_along(sc, 0.55, 1.0, 0.28)

    M.occlude(M.leaf, 0.45)
    return M


# ================================================================ SILVER BIRCH
def make_birch(seed=23):
    rng = random.Random(seed)
    M = Model()
    c_white, c_mark, c_base, c_twig = rgb(0xe9e6dc), rgb(0x2b2a28), rgb(0x45403a), rgb(0x5a3e36)

    def bark(p, th, s, r, k, dv):
        if r < 0.03:
            return cmix(c_twig, c_white, (r - 0.012) / 0.018)
        lent = vnoise(dv[0] * 1.6 + 50, s * 26, dv[2] * 1.6 + dv[1] * 1.6, 7)
        blot = fbm(dv[0] * 2 + 9, s * 3.0, dv[2] * 2 + dv[1] * 2, 9)
        c = cmix(c_white, rgb(0xcfc8b8), blot)
        if lent > 0.74:
            c = cmix(c, c_mark, (lent - 0.74) * 8)
        base = clamp((1.7 - p[1]) / 1.4)          # rough black base
        if base > 0:
            fiss = vnoise(dv[0] * 6, s * 2.5, dv[2] * 6, 4)
            c = cmix(c, cmix(c_base, rgb(0x8a8378), fiss), base ** 0.7)
        return c

    trunk = grow(rng, (0, -0.3, 0), (0.03, 1, 0.0), 15.8, 0.21, 0.012, seg=0.06, wander=0.05, taper=0.85)
    M.tube(trunk, 18, bark, flare_rmod(2, flare=0.28, roots=4, knobs=0.06))

    def leaf_on(p, T, side, scale=1.0):
        D = norm(vsum(mul(T, 0.45), side, mul(DOWN, 0.35), mul(rand_unit(rng), 0.25)))
        hint = norm(add(UP, mul(rand_unit(rng), 0.7)))
        col = cmix(rgb(0x5f8f2a), rgb(0x9cbd4a), rng.random())
        if rng.random() < 0.06:
            col = rgb(0xc2b640)
        M.add_leaf(p, D, hint, rng.uniform(0.085, 0.11) * scale,
               lambda u: 0.45 * (1 - u) * (1 - (1 - u) ** 4), 3, col, fold=0.15, curl=0.1)

    def leaves_along(br, t0, t1, spacing):
        n = int(br.length * (t1 - t0) / spacing)
        for i in range(n):
            p, T, r = br.at(t0 + (t1 - t0) * (i + rng.random() * 0.5) / n)
            side = branch_dir(T, math.pi / 2, i * math.pi + rng.uniform(-0.8, 0.8))
            leaf_on(add(p, mul(side, r)), T, side)

    n = 46
    for k in range(n):
        h = 4.0 + 11.0 * (k + rng.random() * 0.7) / n
        p, T, r = trunk.at((h + 0.3) / 15.8)
        rel = (h - 4.0) / 11.0
        az = k * 2.39996 + rng.uniform(-0.4, 0.4)
        L = (0.5 + 3.4 * (1 - rel) ** 0.8 * min(1.0, (rel + 0.12) * 3.5)) * rng.uniform(0.8, 1.15)
        prim = grow(rng, p, tilt_from_up(az, 1.15 - 0.7 * rel + rng.uniform(-0.15, 0.15)), L,
                    min(r * 0.55, 0.03 + 0.025 * L / 3.4), 0.005, seg=0.1, wander=0.15,
                    bend=lambda t, d, p_: mul(UP, 0.35 - 1.1 * t))
        M.tube(prim, 8, bark)
        ns = int(prim.length / 0.18)
        for j in range(ns):
            t = 0.15 + 0.85 * (j + rng.random() * 0.5) / max(ns, 1)
            p2, T2, r2 = prim.at(t)
            d2 = norm(add(branch_dir(T2, rng.uniform(0.5, 0.9), rng.uniform(0, 6.283)), (0, -0.2, 0)))
            sec = grow(rng, p2, d2, rng.uniform(0.6, 1.4) * (1 - 0.4 * t), min(r2 * 0.7, 0.012), 0.003,
                       seg=0.08, wander=0.25, bend=lambda t_, d, p_: mul(DOWN, 1.4))
            M.tube(sec, 4, bark, cap=False)
            leaves_along(sec, 0.1, 1.0, 0.04)
        leaves_along(prim, 0.5, 1.0, 0.06)
    tip = trunk.at(0.93)
    leaves_along(Branch(trunk.pts[int(len(trunk.pts) * 0.93):], trunk.radii[int(len(trunk.pts) * 0.93):]), 0, 1, 0.05)
    M.occlude(M.leaf, 0.35)
    return M


# ================================================================ OLIVE
def make_olive(seed=5):
    rng = random.Random(seed)
    M = Model()
    c_grey, c_light, c_crev = rgb(0x8a857a), rgb(0xa9a497), rgb(0x2f2c27)

    def bark(p, th, s, r, k, dv):
        n = fbm(p[0] * 3.5, p[1] * 3.5, p[2] * 3.5, 21)
        c = cmix(c_grey, c_light, n * 1.4 - 0.3)
        if r > 0.05:
            crev = clamp((1.0 - k) * 3.0 + 0.25) * clamp(r * 5)
            c = cmix(c, c_crev, crev)
            stripe = vnoise(dv[0] * 9, s * 2.0 + dv[1] * 9, dv[2] * 9, 22)
            c = cmix(c, c_crev, clamp((stripe - 0.6) * 2.5) * 0.7)
        else:
            c = cmix(c, rgb(0x6d6a5c), 0.5)
        return c

    def gnarl(seed_, amp0, flare=0.0, roots=4, fade=None):
        rr = random.Random(seed_)
        p1, p2, p3 = rr.uniform(0, 6.3), rr.uniform(0, 6.3), rr.uniform(0, 6.3)
        def f(t, th, s, P, dv, r):
            amp = amp0 if fade is None else amp0 * max(0.45, 1 - max(0.0, s - fade) / 1.2)
            k = 1.0 + amp * (0.20 * math.sin(3 * th + s * 2.0 + p1) + 0.09 * math.sin(5 * th - s * 3.1 + p2))
            q = add(P, mul(dv, r))
            k += amp * 0.5 * (fbm(q[0] * 2.4, q[1] * 2.4, q[2] * 2.4, seed_) - 0.5)
            if flare:
                k += flare * math.exp(-max(0.0, s - 0.25) / 0.35) * max(0.0, math.cos(roots * (th - p3))) ** 2
            return max(0.35, k)
        return f

    def leaf_pair(p, T, az):
        for sgn in (1, -1):
            side = branch_dir(T, math.pi / 2, az + (0 if sgn > 0 else math.pi))
            D = norm(vsum(mul(T, 0.7), side, mul(rand_unit(rng), 0.25)))
            hint = norm(add(UP, mul(rand_unit(rng), 0.9)))
            if rng.random() < 0.35:   # silvery underside catching the light
                col = cmix(rgb(0x9aa38a), rgb(0xb5bca6), rng.random())
            else:
                col = cmix(rgb(0x45532f), rgb(0x66734a), rng.random())
            M.add_leaf(p, D, hint, rng.uniform(0.085, 0.115), width_lanceolate(0.1), 2, col,
                   fold=0.3, curl=0.08, petiole=0.08)

    def leaves_along(br, t0, t1, spacing):
        n = int(br.length * (t1 - t0) / spacing)
        for i in range(n):
            p, T, r = br.at(t0 + (t1 - t0) * (i + 0.5) / max(n, 1))
            leaf_pair(p, T, i * math.pi / 2 + rng.uniform(-0.3, 0.3))

    def twig_set(br, t0, t1):
        n = int(br.length * (t1 - t0) / 0.09)
        for i in range(n):
            t = t0 + (t1 - t0) * (i + rng.random() * 0.6) / max(n, 1)
            p, T, r = br.at(t)
            d = norm(add(branch_dir(T, rng.uniform(0.5, 1.0), rng.uniform(0, 6.283)), (0, 0.15, 0)))
            tw = grow(rng, p, d, rng.uniform(0.25, 0.55), min(r * 0.7, 0.01), 0.003, seg=0.06,
                      wander=0.4, bend=lambda t_, d_, p_: mul(DOWN, 0.5))
            M.tube(tw, 4, bark, cap=False)
            leaves_along(tw, 0.05, 1.0, 0.035)

    stems = []
    for k in range(3):
        a = 2 * math.pi * k / 3 + rng.uniform(-0.3, 0.3)
        start = (math.cos(a) * 0.22, -0.3, math.sin(a) * 0.22)
        d = norm(vsum(UP, mul(horiz(a), 0.18)))
        st = grow(rng, start, d, rng.uniform(1.9, 2.5), 0.38, 0.2, seg=0.07, wander=0.2,
                  kink_p=0.4, kink=0.15, taper=0.7,
                  bend=lambda t, d_, p: vsum(mul(norm(cross(UP, outward(p))), 0.35), mul(UP, 0.5), mul(outward(p), 0.06)))
        stems.append(st)

    for si, st in enumerate(stems):
        nl = rng.randint(2, 3)
        for j in range(nl):
            if j == 0:
                p, T, r = st.tip(); d = T; r0 = r
            else:
                p, T, r = st.at(rng.uniform(0.7, 0.92)); r0 = r * 0.6
                d = norm(vsum(mul(T, 0.6), mul(outward(p), 0.5), mul(UP, 0.4), mul(rand_unit(rng), 0.3)))
            limb = grow(rng, p, d, rng.uniform(2.0, 2.8), r0, 0.035, seg=0.09, wander=0.3,
                        kink_p=0.8, kink=0.3,
                        bend=lambda t, d_, p_: vsum(mul(UP, 0.45 * (1 - t)), mul(outward(p_), 0.12)))
            if j == 0:   # main limb continues the stem as one seamless tube
                M.tube(Branch(st.pts + limb.pts[1:], st.radii + limb.radii[1:]), 24, bark,
                       gnarl(30 + si, 1.0, flare=0.7, fade=st.length))
            else:
                M.tube(limb, 14, bark, gnarl(60 + si * 5 + j, 0.6))
            ns = rng.randint(9, 12)
            for q in range(ns):
                t = 0.25 + 0.75 * (q + rng.random() * 0.6) / ns
                p2, T2, r2 = limb.at(t)
                d2 = norm(vsum(branch_dir(T2, rng.uniform(0.5, 1.0), rng.uniform(0, 6.283)), mul(outward(p2), 0.4), (0, 0.15, 0)))
                sec = grow(rng, p2, d2, rng.uniform(1.0, 1.8), min(r2 * 0.65, 0.045), 0.01, seg=0.08,
                           wander=0.35, kink_p=0.8, kink=0.3,
                           bend=lambda t_, d_, p_: add(mul(outward(p_), 0.12), mul(DOWN, 0.35 * t_)))
                M.tube(sec, 6, bark)
                twig_set(sec, 0.2, 1.0)
                leaves_along(sec, 0.65, 1.0, 0.05)
            twig_set(limb, 0.75, 1.0)
    M.occlude(M.leaf, 0.5)
    return M


# ================================================================ CHERRY
def make_cherry(seed=31):
    rng = random.Random(seed)
    M = Model()
    c_bark, c_band, c_twig = rgb(0x5e3f37), rgb(0x9c887c), rgb(0x6b4a3e)

    def bark(p, th, s, r, k, dv):
        n = fbm(p[0] * 5, p[1] * 5, p[2] * 5, 41)
        c = cscale(c_bark, 0.75 + 0.5 * n)
        if r > 0.02:
            band = vnoise(dv[0] * 2.2, s * 22, dv[2] * 2.2 + dv[1] * 2.2, 42)
            if band > 0.68:
                c = cmix(c, c_band, (band - 0.68) * 5)
        else:
            c = cmix(c_twig, c, r / 0.02)
        return c

    pinks = [(0xfbe3ec, 0xe48aa9), (0xf8d0de, 0xd96b92), (0xfdeef3, 0xeaa0bb)]

    def cluster(p, T, r):
        side = branch_dir(T, math.pi / 2, rng.uniform(0, 6.283))
        base = add(p, mul(side, r))
        edge, centre = pinks[rng.randrange(len(pinks))]
        for i in range(rng.randint(4, 6)):
            dd = norm(vsum(side, mul(rand_unit(rng), 0.9), mul(UP, 0.3)))
            fp = add(base, mul(dd, rng.uniform(0.03, 0.07)))
            M.flower(fp, norm(add(dd, mul(rand_unit(rng), 0.35))), rng.uniform(0.04, 0.055),
                     cscale(rgb(centre), rng.uniform(0.85, 1.0)), cscale(rgb(edge), rng.uniform(0.9, 1.0)),
                     rng=rng)
        if rng.random() < 0.3:
            col = cmix(rgb(0x7d6a2e), rgb(0x6f8a34), rng.random())
            D = norm(vsum(side, mul(T, 0.5), mul(rand_unit(rng), 0.3)))
            M.add_leaf(base, D, UP, rng.uniform(0.06, 0.09), width_lanceolate(0.22), 3, col, fold=0.4, curl=0.2)

    def clusters_along(br, t0, t1, spacing):
        n = int(br.length * (t1 - t0) / spacing)
        for i in range(n):
            cluster(*br.at(t0 + (t1 - t0) * (i + rng.random() * 0.5) / max(n, 1)))
        if t1 >= 1.0:
            cluster(*br.tip())

    trunk = grow(rng, (0, -0.3, 0), (0.08, 1, -0.04), 2.1, 0.3, 0.22, seg=0.08, wander=0.1)
    M.tube(trunk, 18, bark, flare_rmod(3, flare=0.4, roots=5, knobs=0.1))
    nsc = 5
    for k in range(nsc):
        p, T, r = trunk.at(rng.uniform(0.75, 1.0))
        az = 2 * math.pi * k / nsc + rng.uniform(-0.35, 0.35)
        sc = grow(rng, p, tilt_from_up(az, rng.uniform(0.6, 0.95)), rng.uniform(3.2, 4.4), 0.17, 0.035,
                  seg=0.1, wander=0.2, kink_p=0.4, kink=0.2,
                  bend=lambda t, d, p_: mul(UP, 0.15 - 0.45 * t))
        M.tube(sc, 12, bark, flare_rmod(k + 50, flare=0.0, knobs=0.1))
        ns = rng.randint(7, 10)
        for j in range(ns):
            t = 0.2 + 0.8 * (j + rng.random() * 0.6) / ns
            p2, T2, r2 = sc.at(t)
            d2 = norm(vsum(branch_dir(T2, rng.uniform(0.5, 0.9), rng.uniform(0, 6.283)), (0, 0.3, 0), mul(outward(p2), 0.2)))
            sec = grow(rng, p2, d2, rng.uniform(1.2, 2.2) * (1 - 0.3 * t), min(r2 * 0.6, 0.05), 0.008,
                       seg=0.08, wander=0.3, kink_p=1.0, kink=0.25,
                       bend=lambda t_, d, p_: mul(UP, 0.2 - 0.6 * t_))
            M.tube(sec, 6, bark)
            nt = int(sec.length / 0.2)
            for q in range(nt):
                t3 = 0.15 + 0.85 * (q + rng.random() * 0.6) / max(nt, 1)
                p3, T3, r3 = sec.at(t3)
                ter = grow(rng, p3, branch_dir(T3, rng.uniform(0.5, 1.0), rng.uniform(0, 6.283)),
                           rng.uniform(0.3, 0.8), min(r3 * 0.7, 0.01), 0.003, seg=0.06, wander=0.4,
                           bend=lambda t_, d, p_: mul(UP, 0.2))
                M.tube(ter, 4, bark, cap=False)
                clusters_along(ter, 0.1, 1.0, 0.055)
            clusters_along(sec, 0.2, 1.0, 0.06)
        clusters_along(sc, 0.7, 1.0, 0.12)
    M.occlude(M.blossom, 0.25)
    M.occlude(M.leaf, 0.4)
    return M


# ================================================================ YOUNG OAK
def make_oak(seed=47):
    rng = random.Random(seed)
    M = Model()
    c_bark, c_dark, c_twig = rgb(0x6d665b), rgb(0x3b362f), rgb(0x6b5a45)

    def bark(p, th, s, r, k, dv):
        n = fbm(p[0] * 6, p[1] * 6, p[2] * 6, 61)
        c = cscale(c_bark, 0.8 + 0.4 * n)
        if r > 0.05:
            fiss = vnoise(dv[0] * 7, s * 3.0, dv[2] * 7 + dv[1] * 7, 62)
            c = cmix(c, c_dark, clamp((fiss - 0.55) * 3) * clamp((r - 0.05) * 15))
        if r < 0.015:
            c = cmix(c_twig, c, r / 0.015)
        return c

    def oak_width(u):
        shape = 0.36 * u ** 0.6 * (1 - u) ** 0.45
        return shape * (0.38 + 0.62 * abs(math.sin(3.5 * math.pi * u)))

    def leaf_at(p, T, side):
        D = norm(vsum(mul(T, 0.6), side, mul(rand_unit(rng), 0.35)))
        hint = norm(add(UP, mul(rand_unit(rng), 0.7)))
        col = cmix(rgb(0x4f7a2c), rgb(0x76a03e), rng.random())
        M.add_leaf(p, D, hint, rng.uniform(0.12, 0.16), oak_width, 10, col, fold=0.12, curl=0.1,
               petiole=0.05, tip_color=cscale(col, 0.9))

    def leaves_along(br, t0, t1, spacing, tip_cluster=5):
        n = int(br.length * (t1 - t0) / spacing)
        for i in range(n):
            p, T, r = br.at(t0 + (t1 - t0) * (i + rng.random() * 0.5) / max(n, 1))
            side = branch_dir(T, math.pi / 2, i * 2.39996 + rng.uniform(-0.4, 0.4))
            leaf_at(add(p, mul(side, r)), T, side)
        p, T, r = br.tip()
        for i in range(tip_cluster):
            side = branch_dir(T, math.pi / 2, i * 2 * math.pi / tip_cluster + rng.uniform(-0.3, 0.3))
            leaf_at(p, T, norm(add(side, mul(T, 0.4))))

    trunk = grow(rng, (0, -0.3, 0), (0.03, 1, 0.02), 6.5, 0.14, 0.008, seg=0.08, wander=0.12,
                 kink_p=0.3, kink=0.12, taper=0.9, bend=lambda t, d, p: mul(UP, 0.1))
    M.tube(trunk, 14, bark, flare_rmod(4, flare=0.35, roots=5, knobs=0.08))
    n = 18
    for k in range(n):
        h = 1.5 + 4.5 * (k + rng.random() * 0.7) / n
        p, T, r = trunk.at((h + 0.3) / 6.5)
        rel = (h - 1.5) / 4.5
        az = k * 2.39996 + rng.uniform(-0.4, 0.4)
        L = (0.5 + 2.2 * (1 - rel) ** 0.7 * min(1.0, (rel + 0.25) * 2.5)) * rng.uniform(0.85, 1.15)
        prim = grow(rng, p, tilt_from_up(az, 1.25 - 0.7 * rel + rng.uniform(-0.15, 0.15)), L,
                    min(r * 0.5, 0.045), 0.005, seg=0.08, wander=0.3, kink_p=0.8, kink=0.35,
                    bend=lambda t, d, p_: mul(UP, 0.25))
        M.tube(prim, 7, bark)
        ns = int(prim.length / 0.11)
        for j in range(ns):
            t = 0.15 + 0.85 * (j + rng.random() * 0.5) / max(ns, 1)
            p2, T2, r2 = prim.at(t)
            sec = grow(rng, p2, branch_dir(T2, rng.uniform(0.6, 1.0), rng.uniform(0, 6.283)),
                       rng.uniform(0.35, 0.9) * (1 - 0.4 * t), min(r2 * 0.7, 0.012), 0.003, seg=0.06,
                       wander=0.35, kink_p=1.0, kink=0.3, bend=lambda t_, d, p_: mul(UP, 0.3))
            M.tube(sec, 4, bark, cap=False)
            leaves_along(sec, 0.2, 1.0, 0.045)
        leaves_along(prim, 0.5, 1.0, 0.08)
    leaves_along(Branch(trunk.pts[-12:], trunk.radii[-12:]), 0.0, 1.0, 0.06, tip_cluster=6)
    M.occlude(M.leaf, 0.35)
    return M


# ================================================================ glTF export
MATERIALS = {
    "bark":    {"name": "bark", "pbrMetallicRoughness": {"baseColorFactor": [1, 1, 1, 1], "metallicFactor": 0.0, "roughnessFactor": 0.95}},
    "leaf":    {"name": "leaves", "doubleSided": True, "pbrMetallicRoughness": {"baseColorFactor": [1, 1, 1, 1], "metallicFactor": 0.0, "roughnessFactor": 0.7}},
    "blossom": {"name": "blossom", "doubleSided": True, "pbrMetallicRoughness": {"baseColorFactor": [1, 1, 1, 1], "metallicFactor": 0.0, "roughnessFactor": 0.65}},
}


def write_glb(path, name, model):
    blob = bytearray()
    views, accessors, prims, mats = [], [], [], []

    def view(data, target):
        while len(blob) % 4:
            blob.append(0)
        views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(data), "target": target})
        blob.extend(data)
        return len(views) - 1

    def acc(v, ctype, count, typ, **extra):
        accessors.append(dict(bufferView=v, componentType=ctype, count=count, type=typ, **extra))
        return len(accessors) - 1

    for key in ("bark", "leaf", "blossom"):
        m = getattr(model, key)
        if not m.idx:
            continue
        n = len(m.pos)
        flat = [c for p in m.pos for c in p]
        mins = [min(flat[i::3]) for i in range(3)]
        maxs = [max(flat[i::3]) for i in range(3)]
        a_pos = acc(view(struct.pack("<%df" % (3 * n), *flat), 34962), 5126, n, "VEC3", min=mins, max=maxs)
        a_nrm = acc(view(struct.pack("<%df" % (3 * n), *[c for v in m.nrm for c in v]), 34962), 5126, n, "VEC3")
        cols = bytearray()
        for c in m.col:
            cols.extend((round(clamp(c[0]) * 255), round(clamp(c[1]) * 255), round(clamp(c[2]) * 255), 255))
        a_col = acc(view(bytes(cols), 34962), 5121, n, "VEC4", normalized=True)
        if n < 65536:
            a_idx = acc(view(struct.pack("<%dH" % len(m.idx), *m.idx), 34963), 5123, len(m.idx), "SCALAR")
        else:
            a_idx = acc(view(struct.pack("<%dI" % len(m.idx), *m.idx), 34963), 5125, len(m.idx), "SCALAR")
        mats.append(MATERIALS[key])
        prims.append({"attributes": {"POSITION": a_pos, "NORMAL": a_nrm, "COLOR_0": a_col},
                      "indices": a_idx, "material": len(mats) - 1, "mode": 4})
    while len(blob) % 4:
        blob.append(0)
    gltf = {
        "asset": {"version": "2.0", "generator": "make_trees.py"},
        "scene": 0, "scenes": [{"name": name, "nodes": [0]}],
        "nodes": [{"name": name, "mesh": 0}],
        "meshes": [{"name": name, "primitives": prims}],
        "materials": mats, "accessors": accessors, "bufferViews": views,
        "buffers": [{"byteLength": len(blob)}],
    }
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    total = 12 + 8 + len(js) + 8 + len(blob)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(js), 0x4E4F534A)); f.write(js)
        f.write(struct.pack("<II", len(blob), 0x004E4942)); f.write(blob)


TREES = {
    "weeping_willow": make_willow,
    "silver_birch": make_birch,
    "olive_old": make_olive,
    "cherry_blossom": make_cherry,
    "oak_young": make_oak,
}

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "models"
    only = sys.argv[2:] or list(TREES)
    os.makedirs(out, exist_ok=True)
    for name in only:
        model = TREES[name]()
        path = os.path.join(out, name + ".glb")
        write_glb(path, name, model)
        xs = [p for mesh in (model.bark, model.leaf, model.blossom) for p in mesh.pos]
        size = [max(p[i] for p in xs) - min(p[i] for p in xs) for i in range(3)]
        tris = sum(t for _, t in model.stats().values())
        print("%-16s %6.2f MB  %7d tris  W%.1f x H%.1f x D%.1f m  %s" % (
            name, os.path.getsize(path) / 1e6, tris, size[0], size[1], size[2], model.stats()))
