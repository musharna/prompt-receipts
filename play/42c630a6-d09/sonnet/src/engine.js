// Origami fold engine: faces carry paper (u,v) coords + 3D positions. Each fold rotates a set of faces
// about a line, so the crease pattern is recorded from the very folds that are animated.
(function (root) {
  const E = 1e-6;
  const sub = (a, b) => a.map((x, i) => x - b[i]);
  const ease = t => t * t * (3 - 2 * t);

  function rot(pt, O, u, phi) {
    const v = sub(pt, O), c = Math.cos(phi), s = Math.sin(phi);
    const k = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]];
    const d = (u[0] * v[0] + u[1] * v[1] + u[2] * v[2]) * (1 - c);
    return [O[0] + v[0] * c + k[0] * s + u[0] * d, O[1] + v[1] * c + k[1] * s + u[1] * d, O[2] + v[2] * c + k[2] * s + u[2] * d];
  }
  function normal(p) { // Newell
    let x = 0, y = 0, z = 0;
    for (let i = 0; i < p.length; i++) {
      const a = p[i], b = p[(i + 1) % p.length];
      x += (a[1] - b[1]) * (a[2] + b[2]); y += (a[2] - b[2]) * (a[0] + b[0]); z += (a[0] - b[0]) * (a[1] + b[1]);
    }
    return [x, y, z];
  }
  function info(f) {
    const n = f.p.length, c = [0, 0, 0], uc = [0, 0];
    f.p.forEach((q, i) => { for (let k = 0; k < 3; k++) c[k] += q[k] / n; uc[0] += f.uv[i][0] / n; uc[1] += f.uv[i][1] / n; });
    const nn = normal(f.p);
    return { id: f.id, cx: c[0], cy: c[1], cz: c[2], up: nn[2] > 0, area: Math.hypot(...nn) / 2, u: uc[0], v: uc[1] };
  }
  const clone = fs => fs.map(f => ({ id: f.id, uv: f.uv.map(a => a.slice()), p: f.p.map(a => a.slice()) }));
  const lerp3 = (a, b, t) => a.map((x, i) => x + (b[i] - x) * t);

  function newPaper(rotDeg) {
    const r = (rotDeg || 0) * Math.PI / 180, c = Math.cos(r), s = Math.sin(r);
    const U = (u, v) => { const x = u - .5, y = v - .5; return [x * c - y * s, x * s + y * c]; };
    const uv = [[0, 0], [1, 0], [1, 1], [0, 1]];
    return { U, faces: [{ id: 0, uv, p: uv.map(([u, v]) => [...U(u, v), 0]) }] };
  }

  function build(model) {
    const paper = newPaper(model.rot), U = paper.U;
    let faces = paper.faces, nextId = 1;
    const creases = [], seen = new Set(), timeline = [];
    const key = (a, b) => { const r = x => Math.round(x * 1e5); const s = [[r(a[0]), r(a[1])], [r(b[0]), r(b[1])]].sort(); return s.join('|'); };
    const onBoundary = (a, b) => [0, 1].some(k => [0, 1].some(w => Math.abs(a[k] - w) < E && Math.abs(b[k] - w) < E));

    function splitFaces(sd, sel, ctx) {
      const out = [];
      for (const f of faces) {
        if (!sel(info(f), ctx)) { out.push(f); continue; }
        const s = f.p.map(q => sd(q)), n = f.p.length;
        if (!(Math.max(...s) > E && Math.min(...s) < -E)) { out.push(f); continue; }
        const A = [], B = [];
        for (let i = 0; i < n; i++) {
          const j = (i + 1) % n, sc = s[i], sn = s[j];
          const cur = { uv: f.uv[i], p: f.p[i] };
          if (sc >= -E) A.push(cur); if (sc <= E) B.push(cur);
          if ((sc > E && sn < -E) || (sc < -E && sn > E)) {
            const t = sc / (sc - sn), nv = { uv: lerp3(f.uv[i], f.uv[j], t), p: lerp3(f.p[i], f.p[j], t) };
            A.push(nv); B.push(nv);
          }
        }
        for (const P of [A, B]) out.push({ id: nextId++, uv: P.map(x => x.uv.slice()), p: P.map(x => x.p.slice()) });
      }
      faces = out;
    }

    function compact(fs) { // snap layer heights to evenly spaced levels so they never drift apart
      const zs = [...new Set(fs.map(f => Math.round(info(f).cz * 1e4)))].sort((a, b) => a - b);
      fs.forEach(f => { const z = (zs.indexOf(Math.round(info(f).cz * 1e4)) - (zs.length - 1) / 2) * .004; f.p.forEach(q => q[2] = z); });
    }
    function addStep(st) { timeline.push(st); }

    for (const st of model.steps) {
      const last = timeline[timeline.length - 1];
      if (st.type === 'fold' || st.type === 'rotate' || st.type === 'turn') {
        let O, u, moved = new Set(), phi1, record = false;
        if (st.type === 'fold') {
          const p = st.p, q = st.q, L = Math.hypot(q[0] - p[0], q[1] - p[1]), d = [(q[0] - p[0]) / L, (q[1] - p[1]) / L];
          const sd = pt => d[0] * (pt[1] - p[1]) - d[1] * (pt[0] - p[0]);
          const sel = st.sel || (() => true);
          const zall = faces.flatMap(f => f.p.map(q => q[2])), ctx = { zmax: Math.max(...zall), zmin: Math.min(...zall) };
          splitFaces(sd, sel, ctx);
          const side = st.side, m = st.dir === 'm' ? -1 : 1;
          faces.forEach(f => { const i = info(f); if (sel(i, ctx) && Math.sign(sd([i.cx, i.cy])) === side) moved.add(f.id); });
          const mv = faces.filter(f => moved.has(f.id));
          if (!mv.length) throw new Error('empty fold: ' + st.title);
          const zs = faces.flatMap(f => f.p.map(q => q[2]));
          let zc = st.zc === 'mean' ? mv.flatMap(f => f.p.map(q => q[2])).reduce((a, b) => a + b, 0) / (mv.length * mv[0].p.length)
            : m > 0 ? Math.max(...zs) + .003 : Math.min(...zs) - .003;
          O = [p[0], p[1], zc]; u = [d[0], d[1], 0];
          phi1 = Math.PI * (st.angle === undefined ? 1 : st.angle / 180) * side * m;
          record = st.angle === undefined && st.record !== false;
          if (record) { // crease bookkeeping, relative to the side that faced up at the start
            for (const f of mv) {
              const up = info(f).up;
              for (let i = 0; i < f.p.length; i++) {
                const j = (i + 1) % f.p.length;
                if (Math.abs(sd(f.p[i])) < E && Math.abs(sd(f.p[j])) < E && !onBoundary(f.uv[i], f.uv[j])) {
                  const k = key(f.uv[i], f.uv[j]); if (seen.has(k)) continue; seen.add(k);
                  creases.push({ a: f.uv[i].slice(), b: f.uv[j].slice(), kind: (m > 0) === up ? 'V' : 'M', step: timeline.length });
                }
              }
            }
          }
        } else { // rotate whole model: 'rotate' about a line in the plane (flip), 'turn' about z
          faces.forEach(f => moved.add(f.id));
          const p = st.p;
          if (st.type === 'rotate') { const q = st.q, L = Math.hypot(q[0] - p[0], q[1] - p[1]); O = [p[0], p[1], 0]; u = [(q[0] - p[0]) / L, (q[1] - p[1]) / L, 0]; }
          else { O = [p[0], p[1], 0]; u = [0, 0, 1]; }
          phi1 = (st.angle === undefined ? 180 : st.angle) * Math.PI / 180;
        }
        const start = clone(faces), basePos = new Map(start.map(f => [f.id, f.p.map(a => a.slice())]));
        const entry = { kind: 'move', title: st.title, text: st.text, startFaces: start, moved, basePos, O, u, phi0: 0, phi1, isFold: st.type === 'fold' };
        entry.endFaces = clone(start).map(f => { if (moved.has(f.id)) f.p = f.p.map(q => rot(q, O, u, phi1)); return f; });
        if (st.angle === undefined) compact(entry.endFaces);
        faces = clone(entry.endFaces);
        addStep(entry);
      } else if (st.type === 'undo') {
        const pv = last; // must be a move
        const start = clone(faces);
        const entry = { kind: 'move', title: st.title, text: st.text, startFaces: start, moved: pv.moved, basePos: pv.basePos, O: pv.O, u: pv.u, phi0: pv.phi1, phi1: 0, isFold: false };
        entry.endFaces = clone(start).map(f => { if (pv.moved.has(f.id)) f.p = pv.basePos.get(f.id).map(a => a.slice()); return f; });
        compact(entry.endFaces);
        faces = clone(entry.endFaces);
        addStep(entry);
      } else if (st.type === 'collapse') {
        const targets = st.collapse(faces, info);
        const start = clone(faces);
        const entry = { kind: 'collapse', title: st.title, text: st.text, startFaces: start, lift: st.lift === undefined ? .35 : st.lift };
        entry.endFaces = clone(start).map(f => { f.p = targets.get(f.id); return f; });
        faces = clone(entry.endFaces);
        addStep(entry);
      } else if (st.type === 'hop') {
        addStep({ kind: 'hop', title: st.title, text: st.text, startFaces: clone(faces), endFaces: clone(faces) });
      } else throw new Error('bad step ' + st.type);
    }
    return { name: model.name, U, timeline, creases, initial: newPaper(model.rot).faces, info };
  }

  // positions of every face at step index i (0-based), progress t in [0,1]
  function frame(M, i, t) {
    const st = M.timeline[i], e = ease(t);
    const faces = st.startFaces.map(f => {
      let p;
      if (st.kind === 'move' && st.moved.has(f.id)) {
        const phi = st.phi0 + (st.phi1 - st.phi0) * e;
        p = st.basePos.get(f.id).map(q => rot(q, st.O, st.u, phi));
      } else if (st.kind === 'collapse') {
        const g = st.endFaces.find(x => x.id === f.id);
        p = f.p.map((q, k) => { const r = Math.hypot(q[0], q[1]); const x = lerp3(q, g.p[k], e); x[2] += st.lift * Math.sin(Math.PI * e) * (r + .15); return x; });
      } else p = f.p;
      return { id: f.id, uv: f.uv, p };
    });
    return { faces, hop: st.kind === 'hop' ? e : 0 };
  }
  root.Origami = { build, frame, info, ease, rot, normal };
  if (typeof module !== 'undefined') module.exports = root.Origami;
})(typeof window !== 'undefined' ? window : globalThis);
