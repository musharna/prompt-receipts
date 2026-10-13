(function () {
  const O = window.Origami;
  const ORDER = ['crane', 'frog', 'sailboat', 'swan', 'waterbomb'];
  const BLURB = {
    crane: 'The classic. Finish by gently pulling the wings apart.',
    frog: 'Press the back and slide your finger off: it jumps!',
    sailboat: 'A quick one: great for a first fold of the day.',
    swan: 'Same start as the crane, but with a long curved neck.',
    waterbomb: 'Squares and triangles, ending in a tiny balloon shape.'
  };
  const MODELS = window.MODEL_DEFS, BUILT = {};
  ORDER.forEach(k => { BUILT[k] = O.build(MODELS[k]); BUILT[k].def = MODELS[k]; });

  // ---------- crease patterns ----------
  const c = 0.5 * Math.tan(Math.PI / 8);
  const BASE_CP = (() => {
    const L = [], add = (a, b, kind) => L.push({ a, b, kind });
    add([.5, 0], [.5, 1], 'V'); add([0, .5], [1, .5], 'V');
    add([0, 0], [1, 1], 'M'); add([0, 1], [1, 0], 'M');
    [[0, 0], [1, 0], [0, 1], [1, 1]].forEach(([x, y]) => {
      const sx = x ? -1 : 1, sy = y ? -1 : 1;
      add([x, y], [.5, y + sy * c], 'V'); add([x, y], [x + sx * c, .5], 'V');
      add([.5, y + sy * c], [x + sx * c, .5], 'M');
    });
    return L;
  })();
  function creasesFor(key) {
    const M = BUILT[key];
    if (key === 'crane' || key === 'swan') return BASE_CP.concat(M.creases.filter(k => k.step >= 12));
    return M.creases;
  }
  function cpSVG(key, size) {
    const M = BUILT[key], cr = creasesFor(key), s = size || 300, m = 20, k = (s - 2 * m) / 1.42;
    const P = ([u, v]) => { const [x, y] = M.U(u, v); return [s / 2 + x * k, s / 2 - y * k]; };
    const corners = [[0, 0], [1, 0], [1, 1], [0, 1]].map(P).map(p => p.map(n => n.toFixed(1)).join(',')).join(' ');
    let out = `<svg viewBox="0 0 ${s} ${s}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Crease pattern for the ${M.name}">`;
    out += `<polygon points="${corners}" fill="#fffdf6" stroke="#222" stroke-width="2"/>`;
    cr.forEach(l => {
      const a = P(l.a), b = P(l.b), v = l.kind === 'V';
      out += `<line x1="${a[0].toFixed(1)}" y1="${a[1].toFixed(1)}" x2="${b[0].toFixed(1)}" y2="${b[1].toFixed(1)}" stroke="${v ? '#1565c0' : '#c62828'}" stroke-width="2" stroke-dasharray="${v ? '9 5' : '12 4 2 4'}" stroke-linecap="round"/>`;
    });
    return out + '</svg>';
  }
  const LEGEND = '<span class="lg"><svg width="40" height="8"><line x1="0" y1="4" x2="40" y2="4" stroke="#1565c0" stroke-width="2.5" stroke-dasharray="9 5"/></svg> valley fold</span><span class="lg"><svg width="40" height="8"><line x1="0" y1="4" x2="40" y2="4" stroke="#c62828" stroke-width="2.5" stroke-dasharray="12 4 2 4"/></svg> mountain fold</span>';

  // ---------- viewer ----------
  const cv = document.getElementById('cv'), g = cv.getContext('2d');
  const el = id => document.getElementById(id);
  let key = 'crane', M = BUILT[key], pos = 0, playing = false, last = 0, hold = 0, speed = 1, tilt = 0.5;
  const N = () => M.timeline.length;

  function shade(hex, f) {
    const n = parseInt(hex.slice(1), 16);
    return `rgb(${[16, 8, 0].map(s => Math.round(((n >> s) & 255) * f)).join(',')})`;
  }
  function draw() {
    const W = cv.width, H = cv.height;
    g.clearRect(0, 0, W, H);
    const si = Math.min(Math.floor(pos), N() - 1), t = pos >= N() ? 1 : pos - si;
    const fr = O.frame(M, si, t), st = M.timeline[si];
    const ex = O.ease(t), cs = Math.cos(tilt), sn = Math.sin(tilt);
    const lift = fr.hop ? Math.sin(Math.PI * fr.hop) : 0;
    const allPts = fs => fs.flatMap(f => f.p);
    const ext = pts => [Math.min(...pts.map(q => q[0])), Math.max(...pts.map(q => q[0])), Math.min(...pts.map(q => q[1])), Math.max(...pts.map(q => q[1]))];
    const a = ext(allPts(st.startFaces)), b = ext(allPts(st.endFaces));
    const bx = (a[0] + a[1] + (b[0] + b[1] - a[0] - a[1]) * ex) / 2, by = (a[2] + a[3] + (b[2] + b[3] - a[2] - a[3]) * ex) / 2;
    const S = Math.min(W, H) / 1.9;
    const P = q => [W / 2 + (q[0] - bx) * S, H * 0.56 - ((q[1] - by + lift * 0.55) * cs + q[2] * sn) * S];
    // table shadow
    g.fillStyle = 'rgba(0,0,0,.08)'; g.beginPath(); g.ellipse(W / 2, H * 0.56 + 0.45 * S * cs, 0.5 * S * (1 - 0.35 * lift), 0.1 * S, 0, 0, 7); g.fill();
    const order = fr.faces.map(f => ({ f, i: O.info(f) })).sort((p, q) => p.i.cz - q.i.cz);
    for (const { f } of order) {
      const n = O.normal(f.p), facing = -n[1] * sn + n[2] * cs > 0, len = Math.hypot(...n) || 1;
      const base = facing ? M.def.top : M.def.back, f2 = 0.78 + 0.22 * Math.abs(n[2] / len);
      g.beginPath(); f.p.forEach((q, k) => { const p = P(q); k ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1]); }); g.closePath();
      g.fillStyle = shade(base, f2); g.fill(); g.strokeStyle = 'rgba(40,30,20,.45)'; g.lineWidth = 1; g.lineJoin = 'round'; g.stroke();
    }
    el('slider').value = Math.round(Math.min(pos, N()) * 100);
    const shown = Math.min(si + (t > 0.02 ? 1 : 0) + (pos >= N() ? 0 : 0), N());
    const cur = pos >= N() ? N() - 1 : si;
    el('stepno').textContent = `Step ${cur + 1} of ${N()}`;
    el('steptitle').textContent = M.timeline[cur].title;
    el('steptext').textContent = M.timeline[cur].text;
    document.querySelectorAll('#steps li').forEach((li, k) => li.classList.toggle('on', k === cur));
  }
  function frameLoop(ts) {
    if (playing) {
      const dt = Math.min(0.05, (ts - last) / 1000);
      if (hold > 0) hold -= dt;
      else {
        const before = Math.floor(pos); pos += dt * 0.55 * speed;
        if (Math.floor(pos) > before && pos < N()) { pos = Math.floor(pos); hold = 0.5 / speed; }
        if (pos >= N()) { pos = N(); playing = false; el('play').textContent = '▶ Replay'; }
      }
    }
    last = ts; draw(); requestAnimationFrame(frameLoop);
  }
  function setPlaying(p) {
    if (p && pos >= N()) pos = 0;
    playing = p; hold = 0; el('play').textContent = p ? '⏸ Pause' : '▶ Play';
  }
  function load(k) {
    key = k; M = BUILT[k]; pos = 0; setPlaying(false);
    document.querySelectorAll('.tab').forEach(t => t.setAttribute('aria-selected', t.dataset.k === k));
    el('mname').textContent = M.name; el('blurb').textContent = BLURB[k];
    el('cp').innerHTML = cpSVG(k, 340) + '<div class="legend">' + LEGEND + '</div>';
    el('steps').innerHTML = M.timeline.map((s, i) => `<li><button data-i="${i}">${s.title}</button></li>`).join('');
    el('slider').max = N() * 100;
  }
  el('tabs').innerHTML = ORDER.map(k => `<button class="tab" role="tab" data-k="${k}">${BUILT[k].name}</button>`).join('');
  el('tabs').addEventListener('click', e => { const k = e.target.dataset.k; if (k) load(k); });
  el('play').onclick = () => setPlaying(!playing);
  el('prev').onclick = () => { setPlaying(false); pos = Math.max(0, (pos >= N() ? N() : Math.ceil(pos)) - 1); };
  el('next').onclick = () => { setPlaying(false); pos = Math.min(N(), Math.floor(pos) + 1); };
  el('slider').oninput = e => { setPlaying(false); pos = e.target.value / 100; };
  el('speed').oninput = e => { speed = +e.target.value; };
  el('tilt').oninput = e => { tilt = +e.target.value; };
  el('steps').addEventListener('click', e => { const i = e.target.dataset.i; if (i !== undefined) { setPlaying(false); pos = +i; } });
  el('print').onclick = () => {
    el('sheet').innerHTML = ORDER.map(k => `<section><h2>${BUILT[k].name}</h2>${cpSVG(k, 360)}<div class="legend">${LEGEND}</div><ol>${BUILT[k].timeline.map(s => `<li><b>${s.title}.</b> ${s.text}</li>`).join('')}</ol></section>`).join('');
    window.print();
  };
  load('crane'); requestAnimationFrame(frameLoop);
  window.__origami = { BUILT, cpSVG, load, draw };
})();
