// Procedural canyon parallax generator. Usage: node gen_canyon.js <outdir>
// Every layer is W px wide and wraps seamlessly (all noise/heightfields are periodic in x).
const fs = require('fs'), zlib = require('zlib'), path = require('path');
const W = 2048, H = 576;
const outDir = process.argv[2] || 'canyon';
fs.mkdirSync(outDir, { recursive: true });

// ---------- utils ----------
const clamp = (v, a = 0, b = 1) => v < a ? a : v > b ? b : v;
const lerp = (a, b, t) => a + (b - a) * t;
const smooth = (a, b, v) => { const t = clamp((v - a) / (b - a)); return t * t * (3 - 2 * t); };
const hex = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
const mix = (a, b, t) => [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)];
function hash2(i, j, s) {
  let h = (Math.imul(i, 374761393) + Math.imul(j, 668265263) + Math.imul(s, 1274126177)) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177); h ^= h >>> 16;
  return (h >>> 0) / 4294967296;
}
function rng(seed) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
function vnoise(x, y, px, s) { // value noise, periodic in x with period px lattice cells
  const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  const h = (i, j) => hash2(((i % px) + px) % px, j, s);
  return lerp(lerp(h(xi, yi), h(xi + 1, yi), u), lerp(h(xi, yi + 1), h(xi + 1, yi + 1), u), v);
}
function fbm(x, y, px, s, oct = 4) {
  let a = 0.5, f = 1, sum = 0, n = 0;
  for (let o = 0; o < oct; o++) { sum += a * vnoise(x * f, y * f, px * f, s + o * 17); n += a; a *= 0.5; f *= 2; }
  return sum / n;
}

// ---------- buffers ----------
const newBuf = () => new Float32Array(W * H * 4);
function over(b, i, r, g, bl, a) {
  if (a <= 0) return;
  const da = b[i + 3], oa = a + da * (1 - a);
  const k = da * (1 - a);
  b[i] = (r * a + b[i] * k) / oa; b[i + 1] = (g * a + b[i + 1] * k) / oa; b[i + 2] = (bl * a + b[i + 2] * k) / oa; b[i + 3] = oa;
}
function add(b, i, r, g, bl, a) { // additive light on an opaque pixel
  b[i] = Math.min(255, b[i] + r * a); b[i + 1] = Math.min(255, b[i + 1] + g * a); b[i + 2] = Math.min(255, b[i + 2] + bl * a);
}

// ---------- PNG ----------
const crcT = new Uint32Array(256).map((_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; });
const crc32 = buf => { let c = 0xFFFFFFFF; for (const b of buf) c = crcT[(c ^ b) & 255] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; };
function chunk(type, data) {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
  const td = Buffer.concat([Buffer.from(type), data]);
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(td));
  return Buffer.concat([len, td, crc]);
}
function writePNG(file, b) {
  const raw = Buffer.alloc((W * 4 + 1) * H);
  for (let y = 0; y < H; y++) {
    raw[y * (W * 4 + 1)] = 0;
    for (let x = 0; x < W; x++) {
      const i = (y * W + x) * 4, o = y * (W * 4 + 1) + 1 + x * 4;
      const d = (hash2(x, y, 99) - 0.5) * 1.6; // dither against banding
      raw[o] = clamp(Math.round(b[i] + d), 0, 255); raw[o + 1] = clamp(Math.round(b[i + 1] + d), 0, 255);
      raw[o + 2] = clamp(Math.round(b[i + 2] + d), 0, 255); raw[o + 3] = clamp(Math.round(b[i + 3] * 255), 0, 255);
    }
  }
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(W, 0); ihdr.writeUInt32BE(H, 4); ihdr[8] = 8; ihdr[9] = 6;
  fs.writeFileSync(file, Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(raw, { level: 9 })), chunk('IEND', Buffer.alloc(0))]));
}

// ---------- terrain (heightfield columns, periodic) ----------
function height(T, x) {
  const r = rng(T.seed); let v = 0, n = 0;
  for (const [f, a] of T.comps) { v += a * Math.sin(2 * Math.PI * f * x / W + r() * 6.2832); n += a; }
  return v / n;
}
function surface(T) {
  const ys = new Float32Array(W);
  // phases come from a fresh rng per call, so precompute per component once
  const r = rng(T.seed), ph = T.comps.map(() => r() * 6.2832), tot = T.comps.reduce((s, c) => s + c[1], 0);
  for (let x = 0; x < W; x++) {
    let v = 0; T.comps.forEach(([f, a], k) => v += a * Math.sin(2 * Math.PI * f * x / W + ph[k]));
    const hgt = v / tot * T.amp, t = hgt / T.step, fl = Math.floor(t), fr = t - fl;
    const s = clamp((fr - 0.5) * T.sharp + 0.5);
    const jitter = (vnoise(x / 16, 0, W / 16, T.seed) - 0.5) * (T.jitter ?? 3);
    ys[x] = T.base - (fl + s) * T.step + jitter;
  }
  return ys;
}
function drawTerrain(b, T) {
  const ys = surface(T), S = T.strata, lc = hex(T.lit), sc = hex(T.shadow), rc = hex(T.rim), hc = hex(T.haze[0]);
  const top = hex(T.top), bot = hex(T.bottom), sl = hex(S.light), sd = hex(S.dark);
  for (let x = 0; x < W; x++) {
    const slope = (ys[(x + 2) % W] - ys[(x - 2 + W) % W]) / 4;
    const fl = clamp(slope * T.lightDir / 3, -1, 1);
    for (let y = Math.max(0, Math.floor(ys[x])); y < H; y++) {
      const a = clamp(y + 1 - ys[x]); if (a <= 0) continue;
      const d = y - ys[x];
      let c = mix(top, bot, clamp((y - T.gy0) / (T.gy1 - T.gy0)));
      // strata: wavy bands with per-band tone
      const n = vnoise(x * 24 / W, y / 26, 24, T.seed + 3);
      const bp = (y + 10 * (n - 0.5) * 2) / S.h, idx = Math.floor(bp), fr = bp - idx;
      const tone = hash2(idx, 7, T.seed) - 0.5;
      c = mix(c, tone > 0 ? sl : sd, Math.abs(tone) * 2 * S.amt);
      if (fr < 0.14) c = mix(c, sd, (1 - fr / 0.14) * S.line);
      // desert-varnish streaks
      c = mix(c, sd, vnoise(x / 8, y / 140, W / 8, T.seed + 9) * T.streak);
      // cliff faces: lit side brightens, shadow side darkens
      if (fl > 0) c = mix(c, lc, fl * T.faceLit); else c = mix(c, sc, -fl * T.faceShadow);
      // rim light on the top edge
      c = mix(c, rc, clamp(1 - d / T.rimW) * T.rimAmt * clamp(1.3 - Math.abs(slope) / 1.2));
      c = mix(c, hc, T.haze[1]);
      over(b, (y * W + x) * 4, c[0], c[1], c[2], a);
    }
  }
  return ys;
}

// ---------- sky pieces ----------
function drawSky(b, P) {
  const stops = P.sky.map(([t, h]) => [t, hex(h)]);
  for (let y = 0; y < H; y++) {
    const t = y / H; let k = 0; while (k < stops.length - 2 && t > stops[k + 1][0]) k++;
    const c = mix(stops[k][1], stops[k + 1][1], clamp((t - stops[k][0]) / (stops[k + 1][0] - stops[k][0])));
    for (let x = 0; x < W; x++) { const i = (y * W + x) * 4; b[i] = c[0]; b[i + 1] = c[1]; b[i + 2] = c[2]; b[i + 3] = 1; }
  }
}
function wrapPaint(cx, rad, fn) { // run fn(x, wrappedX) for columns near cx, wrapping across the tile seam
  for (let x = Math.floor(cx - rad); x <= Math.ceil(cx + rad); x++) fn(x, ((x % W) + W) % W);
}
function drawStars(b, P) {
  if (!P.stars) return; const r = rng(P.seed + 5), col = hex(P.starColor);
  for (let s = 0; s < P.stars; s++) {
    const cx = r() * W, cy = H * 0.64 * Math.pow(r(), 1.5), mag = 0.35 + r() * r() * 1.1, rad = 1 + mag * 1.3;
    const fade = 1 - 0.6 * cy / (H * 0.64);
    wrapPaint(cx, rad + 2, (x, wx) => { for (let y = Math.floor(cy - rad - 2); y <= cy + rad + 2; y++) {
      if (y < 0 || y >= H) continue; const d = Math.hypot(x + 0.5 - cx, y + 0.5 - cy);
      const a = (Math.exp(-d * d / (0.5 * mag * mag + 0.25)) + 0.12 * Math.exp(-d / 3) * (mag > 1)) * fade * (P.starAlpha ?? 1);
      if (a > 0.003) add(b, (y * W + wx) * 4, col[0], col[1], col[2], a);
    } });
  }
}
function drawCelestial(b, P) {
  const o = P.orb, core = hex(o.color), glow = hex(o.glow), rad = o.r;
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    let dx = Math.abs(x + 0.5 - o.x); dx = Math.min(dx, W - dx); const d = Math.hypot(dx, y + 0.5 - o.y);
    const g = o.glowAmt * (Math.exp(-d / (o.glowR * 0.18)) * 0.6 + Math.exp(-d / (o.glowR * 0.5)) * 0.4);
    const i = (y * W + x) * 4;
    if (g > 0.004) add(b, i, glow[0], glow[1], glow[2], g);
    const disc = clamp(rad + 0.5 - d);
    if (disc > 0) {
      let c = core;
      if (o.moon) { // soft maria + limb darkening
        const m = fbm((x - o.x) / 22 + 40, (y - o.y) / 22 + 40, 1 << 20, 11, 3);
        c = mix(core, [150, 165, 205], smooth(0.5, 0.65, m) * 0.55);
        c = mix(c, [170, 185, 225], smooth(rad * 0.7, rad, d) * 0.4);
      }
      b[i] = lerp(b[i], c[0], disc); b[i + 1] = lerp(b[i + 1], c[1], disc); b[i + 2] = lerp(b[i + 2], c[2], disc);
    }
  }
}
function drawClouds(b, P) {
  const C = P.clouds; if (!C) return; const lit = hex(C.lit), sh = hex(C.shadow);
  for (let y = 0; y < H * 0.75; y++) {
    const band = smooth(C.y0, C.y0 + 50, y) * (1 - smooth(C.y1 - 70, C.y1, y)); if (band <= 0) continue;
    for (let x = 0; x < W; x++) {
      const f = (yy) => fbm(x * 6 / W, yy / C.ys, 6, P.seed + 31, 4);
      const d = f(y) * 0.8 + 0.2 * band;
      const dens = smooth(C.thr, C.thr + C.soft, d) * band; if (dens <= 0.004) continue;
      const lightUp = clamp(0.5 + (d - f(y + C.ys * 0.12)) * 9); // thin edges toward the light catch it
      const c = mix(sh, lit, lightUp);
      over(b, (y * W + x) * 4, c[0], c[1], c[2], dens * C.alpha);
    }
  }
}

// ---------- foreground extras ----------
function drawOverhang(b, P) {
  const O = P.overhang, top = hex(O.top), bot = hex(O.bottom), rim = hex(O.rim);
  const r = rng(P.seed + 77), ph = [r() * 6.28, r() * 6.28, r() * 6.28];
  const spikes = []; for (let i = 0; i < 26; i++) spikes.push({ c: r() * W, w: 8 + r() * 22, l: 14 + r() * r() * 46 });
  const ys = new Float32Array(W);
  for (let x = 0; x < W; x++) {
    let v = Math.sin(2 * Math.PI * 3 * x / W + ph[0]) * 0.5 + Math.sin(2 * Math.PI * 7 * x / W + ph[1]) * 0.3 + Math.sin(2 * Math.PI * 13 * x / W + ph[2]) * 0.2;
    let y = O.base + v * O.amp + (vnoise(x / 10, 3, W / 10, P.seed) - 0.5) * 6;
    for (const s of spikes) { let dx = Math.abs(x - s.c); dx = Math.min(dx, W - dx); y = Math.max(y, O.base + v * O.amp + s.l * (1 - dx / s.w)); }
    ys[x] = y;
  }
  for (let x = 0; x < W; x++) for (let y = 0; y < Math.ceil(ys[x]) && y < H; y++) {
    const a = clamp(ys[x] - y), d = ys[x] - y;
    let c = mix(bot, top, clamp(y / ys[x]));
    c = mix(c, rim, clamp(1 - d / 3) * O.rimAmt);
    over(b, (y * W + x) * 4, c[0], c[1], c[2], a);
  }
}
function drawCacti(b, P, ys) {
  const K = P.cacti, col = hex(K.color), rim = hex(K.rim), r = rng(P.seed + 123);
  for (let n = 0; n < K.count; n++) {
    const cx = Math.floor(((n + 0.2 + r() * 0.6) / K.count) * W), gy = ys[cx] + 6, h = 55 + r() * 55, tr = 5 + r() * 2.5;
    const caps = [[cx, gy, cx, gy - h, tr]];
    const arm = (side, at, out, up) => { const ay = gy - h * at; caps.push([cx, ay, cx + side * out, ay, tr * 0.75], [cx + side * out, ay, cx + side * out, ay - up, tr * 0.75]); };
    if (r() < 0.9) arm(-1, 0.35 + r() * 0.15, 18 + r() * 8, 20 + r() * 16);
    if (r() < 0.9) arm(1, 0.5 + r() * 0.15, 18 + r() * 8, 20 + r() * 16);
    for (let off = -W; off <= W; off += W) for (let y = Math.floor(gy - h - 40); y < gy; y++) for (let x = cx - 60; x <= cx + 60; x++) {
      const px = x + off, wx = ((x % W) + W) % W; if (y < 0 || y >= H || px !== x + off) continue;
      let best = 1e9, nx = 0, ny = 0;
      for (const [x1, y1, x2, y2, rad] of caps) {
        const vx = x2 - x1, vy = y2 - y1, t = clamp(((x + .5 - x1) * vx + (y + .5 - y1) * vy) / (vx * vx + vy * vy || 1));
        const qx = x1 + vx * t, qy = y1 + vy * t, dd = Math.hypot(x + .5 - qx, y + .5 - qy) - rad;
        if (dd < best) { best = dd; nx = (x + .5 - qx); ny = (y + .5 - qy); }
      }
      const a = clamp(0.5 - best); if (a <= 0 || off !== 0) continue;
      const l = Math.hypot(nx, ny) || 1, lit = clamp((nx / l * P.lightDir - ny / l * 0.4 - 0.45) * 2.2);
      const c = mix(col, rim, lit * K.rimAmt);
      over(b, (y * W + wx) * 4, c[0], c[1], c[2], a);
    }
  }
}

// ---------- palettes ----------
const strata = (light, dark, amt, line, h) => ({ light, dark, amt, line, h });
const PAL = {
  dawn: {
    seed: 11, lightDir: 1,
    sky: [[0, '#1f1d52'], [.3, '#51407f'], [.52, '#c0628a'], [.68, '#f58f6f'], [.8, '#ffc47e'], [1, '#ffd9a0']],
    stars: 70, starColor: '#ffeedd', starAlpha: 0.55,
    orb: { x: 1480, y: 402, r: 56, color: '#fff3c9', glow: '#ffa66a', glowAmt: 0.8, glowR: 520 },
    clouds: { lit: '#ffb38a', shadow: '#7b4a86', y0: 70, y1: 340, ys: 34, thr: 0.5, soft: 0.14, alpha: 0.8 },
    farA: { seed: 21, comps: [[2, 1], [3, .7], [5, .4], [8, .2]], base: 392, amp: 75, step: 36, sharp: 26, top: '#a45f93', bottom: '#d27d8c', gy0: 300, gy1: 470, haze: ['#f59a78', .35], lit: '#ffb27a', shadow: '#6c3f7d', lightDir: 1, faceLit: .25, faceShadow: .25, rim: '#ffc890', rimAmt: .35, rimW: 3, streak: .05, strata: strata('#ffb487', '#6c3f7d', .12, .1, 12) },
    farB: { seed: 22, comps: [[3, 1], [4, .6], [7, .45], [11, .2]], base: 438, amp: 85, step: 30, sharp: 26, top: '#74447e', bottom: '#93508a', gy0: 340, gy1: 500, haze: ['#f09a7a', .22], lit: '#ffb27a', shadow: '#40224f', lightDir: 1, faceLit: .3, faceShadow: .35, rim: '#ffc890', rimAmt: .45, rimW: 3, streak: .06, strata: strata('#ffb487', '#3a1c4a', .15, .12, 11) },
    mid: { seed: 31, comps: [[2, 1], [3, .8], [5, .5], [9, .25]], base: 482, amp: 150, step: 34, sharp: 28, top: '#b55a62', bottom: '#552f58', gy0: 330, gy1: 576, haze: ['#f09a7a', .06], lit: '#ffb27a', shadow: '#2a1236', lightDir: 1, faceLit: .45, faceShadow: .6, rim: '#ffd29a', rimAmt: .7, rimW: 3, streak: .12, strata: strata('#ffb487', '#2c1436', .3, .22, 13) },
    near: { seed: 41, comps: [[4, 1], [6, .5], [11, .3]], base: 530, amp: 55, step: 24, sharp: 26, top: '#241231', bottom: '#150a20', gy0: 470, gy1: 576, haze: ['#000000', 0], lit: '#8a4a5a', shadow: '#0c0614', lightDir: 1, faceLit: .35, faceShadow: .5, rim: '#ff9a68', rimAmt: .6, rimW: 3, streak: .1, strata: strata('#4a2848', '#0c0614', .2, .15, 9) },
    overhang: { top: '#150a20', bottom: '#2c1738', rim: '#ff9a68', rimAmt: .35, base: 28, amp: 22 },
    cacti: { count: 4, color: '#1a0d27', rim: '#ff9a68', rimAmt: .8 },
  },
  noon: {
    seed: 12, lightDir: 0.5,
    sky: [[0, '#2a73c9'], [.35, '#4f9be0'], [.62, '#8fc8f0'], [.8, '#cfeaf9'], [1, '#eaf6fb']],
    stars: 0, starColor: '#fff',
    orb: { x: 1350, y: 118, r: 34, color: '#ffffff', glow: '#fff6c8', glowAmt: 0.65, glowR: 320 },
    clouds: { lit: '#ffffff', shadow: '#a9c4e0', y0: 50, y1: 330, ys: 52, thr: 0.52, soft: 0.12, alpha: 0.95 },
    farA: { seed: 23, comps: [[2, 1], [3, .7], [5, .4], [8, .2]], base: 398, amp: 75, step: 36, sharp: 26, top: '#9fb3cf', bottom: '#c4d3e3', gy0: 300, gy1: 470, haze: ['#dff0fa', .3], lit: '#e6eef8', shadow: '#7f93b4', lightDir: .5, faceLit: .2, faceShadow: .25, rim: '#f2f6fb', rimAmt: .25, rimW: 2, streak: .04, strata: strata('#d0dcec', '#7f93b4', .12, .08, 12) },
    farB: { seed: 24, comps: [[3, 1], [4, .6], [7, .45], [11, .2]], base: 440, amp: 85, step: 30, sharp: 26, top: '#8498b8', bottom: '#a9b9d0', gy0: 340, gy1: 500, haze: ['#dff0fa', .18], lit: '#d6e0ee', shadow: '#566a8e', lightDir: .5, faceLit: .25, faceShadow: .35, rim: '#e8eff8', rimAmt: .3, rimW: 2, streak: .05, strata: strata('#c3d0e4', '#566a8e', .16, .1, 11) },
    mid: { seed: 32, comps: [[2, 1], [3, .8], [5, .5], [9, .25]], base: 482, amp: 150, step: 34, sharp: 28, top: '#e0814a', bottom: '#9a4426', gy0: 330, gy1: 576, haze: ['#dff0fa', .04], lit: '#ffb070', shadow: '#4e1d10', lightDir: .5, faceLit: .35, faceShadow: .5, rim: '#ffdc9a', rimAmt: .55, rimW: 2, streak: .12, strata: strata('#ffc287', '#5c2312', .32, .22, 13) },
    near: { seed: 42, comps: [[4, 1], [6, .5], [11, .3]], base: 530, amp: 55, step: 24, sharp: 26, top: '#4d2316', bottom: '#2e130c', gy0: 470, gy1: 576, haze: ['#000000', 0], lit: '#a85a34', shadow: '#1a0a06', lightDir: .5, faceLit: .35, faceShadow: .45, rim: '#d7814a', rimAmt: .5, rimW: 3, streak: .1, strata: strata('#8a4426', '#1a0a06', .22, .15, 9) },
    overhang: { top: '#2a110a', bottom: '#4d2316', rim: '#d7814a', rimAmt: .3, base: 28, amp: 22 },
    cacti: { count: 4, color: '#3a1a0f', rim: '#d7814a', rimAmt: .7 },
  },
  night: {
    seed: 13, lightDir: -1,
    sky: [[0, '#03050f'], [.3, '#080e26'], [.55, '#101a42'], [.75, '#1c2c5e'], [1, '#2a3d78']],
    stars: 260, starColor: '#dfe8ff', starAlpha: 1,
    orb: { x: 560, y: 150, r: 38, color: '#eef3ff', glow: '#7f9bff', glowAmt: 0.5, glowR: 360, moon: true },
    clouds: { lit: '#3b4d8a', shadow: '#0a1230', y0: 80, y1: 320, ys: 40, thr: 0.55, soft: 0.12, alpha: 0.5 },
    farA: { seed: 25, comps: [[2, 1], [3, .7], [5, .4], [8, .2]], base: 394, amp: 75, step: 36, sharp: 26, top: '#1f2c5c', bottom: '#2a3b72', gy0: 300, gy1: 470, haze: ['#2a3d78', .3], lit: '#4a62b0', shadow: '#0e1636', lightDir: -1, faceLit: .25, faceShadow: .25, rim: '#8fb0ff', rimAmt: .3, rimW: 2, streak: .05, strata: strata('#4a62b0', '#0e1636', .12, .1, 12) },
    farB: { seed: 26, comps: [[3, 1], [4, .6], [7, .45], [11, .2]], base: 438, amp: 85, step: 30, sharp: 26, top: '#141d44', bottom: '#1c2858', gy0: 340, gy1: 500, haze: ['#2a3d78', .15], lit: '#3a52a0', shadow: '#080c22', lightDir: -1, faceLit: .3, faceShadow: .4, rim: '#8fb0ff', rimAmt: .4, rimW: 2, streak: .06, strata: strata('#3a52a0', '#080c22', .15, .12, 11) },
    mid: { seed: 33, comps: [[2, 1], [3, .8], [5, .5], [9, .25]], base: 482, amp: 150, step: 34, sharp: 28, top: '#2d3f7c', bottom: '#0b1128', gy0: 330, gy1: 576, haze: ['#2a3d78', .05], lit: '#6f8cff', shadow: '#03050e', lightDir: -1, faceLit: .4, faceShadow: .6, rim: '#a9c2ff', rimAmt: .65, rimW: 2, streak: .12, strata: strata('#6f88d6', '#040712', .28, .22, 13) },
    near: { seed: 43, comps: [[4, 1], [6, .5], [11, .3]], base: 530, amp: 55, step: 24, sharp: 26, top: '#070a18', bottom: '#03050d', gy0: 470, gy1: 576, haze: ['#000000', 0], lit: '#2a3a78', shadow: '#010206', lightDir: -1, faceLit: .35, faceShadow: .5, rim: '#4560b0', rimAmt: .6, rimW: 3, streak: .08, strata: strata('#1c2650', '#010206', .2, .15, 9) },
    overhang: { top: '#02030a', bottom: '#0a1028', rim: '#4560b0', rimAmt: .4, base: 28, amp: 22 },
    cacti: { count: 4, color: '#04060f', rim: '#6f8cff', rimAmt: .7 },
  },
};

// ---------- compose ----------
const results = {};
for (const [name, P] of Object.entries(PAL)) {
  console.log('rendering', name);
  const far = newBuf(); drawSky(far, P); drawStars(far, P); drawCelestial(far, P); drawClouds(far, P);
  drawTerrain(far, P.farA); drawTerrain(far, P.farB);
  const mid = newBuf(); drawTerrain(mid, P.mid);
  const near = newBuf(); drawOverhang(near, P); const nys = drawTerrain(near, P.near); drawCacti(near, P, nys);
  const files = [['1_far', far], ['2_mid', mid], ['3_near', near]];
  for (const [tag, buf] of files) writePNG(path.join(outDir, `canyon_${name}_${tag}.png`), buf);
  // stacked preview
  const prev = newBuf();
  for (const [, buf] of files) for (let i = 0; i < W * H * 4; i += 4) over(prev, i, buf[i], buf[i + 1], buf[i + 2], buf[i + 3]);
  writePNG(path.join(outDir, `preview_${name}.png`), prev);
}
