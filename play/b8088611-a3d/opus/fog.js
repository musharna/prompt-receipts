/*!
 * FogBackground — animated colour ASCII fog for a page background.
 * No dependencies. Usage:
 *
 *   <script src="fog.js"></script>
 *   <script>const fog = FogBackground.mount({ });</script>
 *
 * fog.pause(), fog.resume(), fog.destroy()
 */
(function (global) {
  'use strict';

  var DEFAULTS = {
    container: null,          // element to fill; null = fixed full-viewport background
    cellSize: 16,             // character height in CSS px (width is ~0.6 of this)
    chars: ' .·:-~=+*%#@',    // light → dense
    fps: 30,
    speed: 1,                 // overall animation speed multiplier
    wind: [0.06, -0.012],     // drift direction/speed in noise units per second
    scale: 0.0024,            // noise frequency per CSS px (smaller = bigger fog banks)
    density: 0.5,             // 0..1, how much of the screen is covered
    background: '#06070d',
    // Two gradients (thin fog → dense fog). Each cell blends between them
    // using a slow-moving noise field, so colours wander across the screen.
    palette: ['#06070d', '#1a2140', '#3c4a86', '#8a8fd6', '#d9ccff', '#fff6fb'],
    accent:  ['#06070d', '#10302f', '#1f6b68', '#4fb3a6', '#b4f0dc', '#f2fff9'],
    interactive: true,        // fog parts gently around the pointer
    pointerRadius: 160,       // CSS px
    font: 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace',
    seed: 1337
  };

  var LEVELS = 16;   // colour steps along density
  var TINTS = 8;     // colour steps between palette and accent

  // ---------------------------------------------------------------- noise

  function makeNoise(seed) {
    var perm = new Uint8Array(512);
    var vals = new Float32Array(256);
    var s = seed >>> 0 || 1;
    function rnd() { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; return (s >>> 0) / 4294967296; }
    var i, j, tmp, p = new Uint8Array(256);
    for (i = 0; i < 256; i++) { p[i] = i; vals[i] = rnd(); }
    for (i = 255; i > 0; i--) { j = (rnd() * (i + 1)) | 0; tmp = p[i]; p[i] = p[j]; p[j] = tmp; }
    for (i = 0; i < 512; i++) perm[i] = p[i & 255];

    // 3D value noise in [0, 1]
    function noise(x, y, z) {
      var xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z);
      var xf = x - xi, yf = y - yi, zf = z - zi;
      var X = xi & 255, Y = yi & 255, Z = zi & 255;
      var u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf), w = zf * zf * (3 - 2 * zf);
      var a = perm[X] + Y, b = perm[X + 1] + Y;
      var aa = perm[a] + Z, ab = perm[a + 1] + Z, ba = perm[b] + Z, bb = perm[b + 1] + Z;
      var x1 = vals[perm[aa]] + (vals[perm[ba]] - vals[perm[aa]]) * u;
      var x2 = vals[perm[ab]] + (vals[perm[bb]] - vals[perm[ab]]) * u;
      var x3 = vals[perm[aa + 1]] + (vals[perm[ba + 1]] - vals[perm[aa + 1]]) * u;
      var x4 = vals[perm[ab + 1]] + (vals[perm[bb + 1]] - vals[perm[ab + 1]]) * u;
      var y1 = x1 + (x2 - x1) * v, y2 = x3 + (x4 - x3) * v;
      return y1 + (y2 - y1) * w;
    }

    function fbm(x, y, z, octaves) {
      var sum = 0, amp = 0.5, norm = 0;
      for (var o = 0; o < octaves; o++) {
        sum += noise(x, y, z) * amp;
        norm += amp;
        x = x * 2.03 + 17.1; y = y * 2.03 - 9.7; z *= 1.7;
        amp *= 0.5;
      }
      return sum / norm;
    }

    return fbm;
  }

  // ---------------------------------------------------------------- colour

  function hexToRgb(hex) {
    hex = hex.replace('#', '');
    if (hex.length === 3) hex = hex.replace(/./g, '$&$&');
    var n = parseInt(hex, 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }

  function sampleGradient(stops, t) {
    var f = t * (stops.length - 1), i = Math.min(Math.floor(f), stops.length - 2), k = f - i;
    var a = stops[i], b = stops[i + 1];
    return [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k];
  }

  // ---------------------------------------------------------------- mount

  function mount(options) {
    var o = {};
    for (var key in DEFAULTS) o[key] = DEFAULTS[key];
    for (key in options || {}) o[key] = options[key];

    var fbm = makeNoise(o.seed);
    var chars = Array.from(o.chars);
    var palette = o.palette.map(hexToRgb), accent = o.accent.map(hexToRgb);
    var reducedMotion = global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches;

    var canvas = document.createElement('canvas');
    canvas.setAttribute('aria-hidden', 'true');
    var st = canvas.style;
    st.display = 'block'; st.pointerEvents = 'none';
    var host = o.container;
    if (host) {
      if (getComputedStyle(host).position === 'static') host.style.position = 'relative';
      st.position = 'absolute'; st.inset = '0'; st.width = '100%'; st.height = '100%'; st.zIndex = '0';
      host.insertBefore(canvas, host.firstChild);
    } else {
      st.position = 'fixed'; st.inset = '0'; st.width = '100vw'; st.height = '100vh'; st.zIndex = '-1';
      document.body.insertBefore(canvas, document.body.firstChild);
    }
    var ctx = canvas.getContext('2d', { alpha: false });
    var atlas = document.createElement('canvas');

    var dpr, cssW, cssH, cellW, cellH, cols, rows;
    var time = Math.random() * 100, last = 0, raf = 0, running = false, fadeIn = 0;
    var pointer = { x: -1e4, y: -1e4, tx: -1e4, ty: -1e4 };

    // Pre-render every (char × colour) glyph once; frames are then just drawImage blits.
    function buildAtlas() {
      atlas.width = cellW * chars.length;
      atlas.height = cellH * LEVELS * TINTS;
      var a = atlas.getContext('2d');
      a.font = Math.round(cellH * 0.9) + 'px ' + o.font;
      a.textAlign = 'center';
      a.textBaseline = 'middle';
      for (var t = 0; t < TINTS; t++) {
        for (var l = 0; l < LEVELS; l++) {
          var lt = 0.25 + 0.75 * (l / (LEVELS - 1));     // skip the darkest stops
          var c1 = sampleGradient(palette, lt), c2 = sampleGradient(accent, lt), m = t / (TINTS - 1);
          a.fillStyle = 'rgb(' + Math.round(c1[0] + (c2[0] - c1[0]) * m) + ',' +
            Math.round(c1[1] + (c2[1] - c1[1]) * m) + ',' + Math.round(c1[2] + (c2[2] - c1[2]) * m) + ')';
          var row = (t * LEVELS + l) * cellH + cellH / 2;
          for (var c = 1; c < chars.length; c++) a.fillText(chars[c], c * cellW + cellW / 2, row);
        }
      }
    }

    function resize() {
      var rect = host ? host.getBoundingClientRect() : { width: global.innerWidth, height: global.innerHeight };
      dpr = Math.min(global.devicePixelRatio || 1, 2);
      cssW = rect.width; cssH = rect.height;
      canvas.width = Math.max(1, Math.round(cssW * dpr));
      canvas.height = Math.max(1, Math.round(cssH * dpr));
      cellH = Math.max(4, Math.round(o.cellSize * dpr));
      cellW = Math.max(3, Math.round(cellH * 0.6));
      cols = Math.ceil(canvas.width / cellW);
      rows = Math.ceil(canvas.height / cellH);
      buildAtlas();
      render();
    }

    function render() {
      ctx.globalAlpha = 1;
      ctx.fillStyle = o.background;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.globalAlpha = Math.min(1, fadeIn);

      var t = time, sc = o.scale, nC = chars.length - 1;
      var wx = o.wind[0] * t, wy = o.wind[1] * t;
      var lo = 0.62 - o.density * 0.3, range = 0.3;
      var r2 = o.pointerRadius * o.pointerRadius, px0 = pointer.x, py0 = pointer.y;
      var cwCss = cellW / dpr, chCss = cellH / dpr;

      for (var y = 0; y < rows; y++) {
        var py = (y + 0.5) * chCss, ny = py * sc;
        var ground = 0.75 + 0.4 * (py / cssH);              // fog pools toward the bottom
        for (var x = 0; x < cols; x++) {
          var px = (x + 0.5) * cwCss, nx = px * sc;

          // Domain-warped fbm: the warp field makes fog curl instead of just scrolling.
          var qx = fbm(nx + wx * 0.5, ny, t * 0.05, 2);
          var qy = fbm(nx + 5.2, ny + 1.3 + wy * 0.5, t * 0.05 + 3.1, 2);
          var d = fbm(nx + 2.2 * qx - wx, ny + 2.2 * qy - wy, t * 0.03, 4);

          d = (d - lo) / range * ground;
          if (o.interactive && px0 > -1e3) {
            var dx = px - px0, dy = py - py0;
            d *= 1 - 0.75 * Math.exp(-(dx * dx + dy * dy) / r2);
          }
          if (d <= 0) continue;
          if (d > 1) d = 1;

          // tiny static per-cell jitter breaks up banding between characters
          var jitter = ((x * 73856093 ^ y * 19349663) & 1023) / 1023 - 0.5;
          var ci = Math.round(d * nC + jitter * 0.6);
          if (ci < 1) continue;
          if (ci > nC) ci = nC;

          var level = (d * (LEVELS - 1)) | 0;
          var tint = (qy - 0.3) / 0.4;
          tint = tint < 0 ? 0 : tint > 1 ? TINTS - 1 : (tint * (TINTS - 1)) | 0;

          ctx.drawImage(atlas, ci * cellW, (tint * LEVELS + level) * cellH, cellW, cellH,
            x * cellW, y * cellH, cellW, cellH);
        }
      }
    }

    function frame(now) {
      raf = requestAnimationFrame(frame);
      var step = 1000 / o.fps;
      if (now - last < step) return;
      var dt = Math.min((now - last) / 1000, 0.1);  // clamp so tab switches don't jump
      last = now;
      time += dt * o.speed;
      fadeIn += dt / 1.5;
      pointer.x += (pointer.tx - pointer.x) * 0.08;
      pointer.y += (pointer.ty - pointer.y) * 0.08;
      render();
    }

    function onPointer(e) {
      var r = canvas.getBoundingClientRect();
      if (pointer.x < -1e3) { pointer.x = e.clientX - r.left; pointer.y = e.clientY - r.top; }
      pointer.tx = e.clientX - r.left; pointer.ty = e.clientY - r.top;
    }
    function onLeave() { pointer.tx = pointer.ty = -1e4; pointer.x = pointer.y = -1e4; }
    function onVisibility() { document.hidden ? pause() : resume(); }

    var resizeTimer;
    function onResize() { clearTimeout(resizeTimer); resizeTimer = setTimeout(resize, 100); }

    function pause() { running = false; cancelAnimationFrame(raf); }
    function resume() {
      if (running || reducedMotion) return;
      running = true; last = performance.now();
      raf = requestAnimationFrame(frame);
    }
    function destroy() {
      pause();
      global.removeEventListener('resize', onResize);
      global.removeEventListener('pointermove', onPointer);
      document.removeEventListener('pointerleave', onLeave);
      document.removeEventListener('visibilitychange', onVisibility);
      if (ro) ro.disconnect();
      canvas.remove();
    }

    var ro = null;
    if (host && global.ResizeObserver) { ro = new ResizeObserver(onResize); ro.observe(host); }
    else global.addEventListener('resize', onResize);
    if (o.interactive && !reducedMotion) {
      global.addEventListener('pointermove', onPointer, { passive: true });
      document.addEventListener('pointerleave', onLeave);
    }
    document.addEventListener('visibilitychange', onVisibility);

    if (reducedMotion) fadeIn = 1;   // single still frame
    resize();
    resume();

    return { canvas: canvas, pause: pause, resume: resume, destroy: destroy, options: o };
  }

  global.FogBackground = { mount: mount, defaults: DEFAULTS };
})(typeof window !== 'undefined' ? window : this);
