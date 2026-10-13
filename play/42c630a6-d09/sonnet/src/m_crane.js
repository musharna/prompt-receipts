const F = (title, text, p, q, side, o = {}) => Object.assign({ type: 'fold', title, text, p, q, side }, o);
const UNDO = (title, text) => ({ type: 'undo', title, text });
const r5 = x => Math.round(x * 1e5);
const ekey = (a, b) => [[r5(a[0]), r5(a[1])], [r5(b[0]), r5(b[1])]].sort().join('|');

// Flat-fold every shared crease: each face is the mirror image of its neighbour across the shared edge.
// layerZ decides which layer a face sits on in the finished flat shape.
function collapseAll(rootAt) {
  return (faces, info) => {
    const edges = new Map();
    faces.forEach(f => f.uv.forEach((a, i) => { const k = ekey(a, f.uv[(i + 1) % f.uv.length]); (edges.get(k) || edges.set(k, []).get(k)).push([f, i]); }));
    const byId = new Map(faces.map(f => [f.id, f]));
    const root = faces.reduce((b, f) => { const i = info(f), j = info(b); return Math.hypot(i.cx - rootAt[0], i.cy - rootAt[1]) < Math.hypot(j.cx - rootAt[0], j.cy - rootAt[1]) ? f : b; });
    const M = new Map([[root.id, [1, 0, 0, 0, 1, 0, 1]]]); // a b tx / c d ty / det
    const ap = (m, p) => [m[0] * p[0] + m[1] * p[1] + m[2], m[3] * p[0] + m[4] * p[1] + m[5]];
    const queue = [root];
    while (queue.length) {
      const f = queue.shift(), mf = M.get(f.id);
      for (let i = 0; i < f.uv.length; i++) {
        const j = (i + 1) % f.uv.length, list = edges.get(ekey(f.uv[i], f.uv[j]));
        for (const [g] of list) {
          if (g === f || M.has(g.id)) continue;
          const P = ap(mf, f.p[i]), Q = ap(mf, f.p[j]), L = Math.hypot(Q[0] - P[0], Q[1] - P[1]), dx = (Q[0] - P[0]) / L, dy = (Q[1] - P[1]) / L;
          // reflection across line through P with direction (dx,dy), applied after mf
          const R = [dx * dx - dy * dy, 2 * dx * dy, 0, 2 * dx * dy, dy * dy - dx * dx, 0];
          const tx = P[0] - (R[0] * P[0] + R[1] * P[1]), ty = P[1] - (R[3] * P[0] + R[4] * P[1]);
          const mg = [R[0] * mf[0] + R[1] * mf[3], R[0] * mf[1] + R[1] * mf[4], R[0] * mf[2] + R[1] * mf[5] + tx,
            R[3] * mf[0] + R[4] * mf[3], R[3] * mf[1] + R[4] * mf[4], R[3] * mf[2] + R[4] * mf[5] + ty, -mf[6]];
          M.set(g.id, mg); queue.push(g);
        }
      }
    }
    const out = new Map();
    faces.forEach(f => {
      const m = M.get(f.id), down = !info(f).up, finalDown = m[6] > 0 ? down : !down;
      out.set(f.id, f.p.map(q => { const p = ap(m, q); return [p[0], p[1], finalDown ? .01 : -.01]; }));
    });
    return out;
  };
}
exports.collapseAll = collapseAll;

const topN = n => (i, c) => i.cz > c.zmax - (n - .5) * .004;
const T = [.25, -.104], KY = .3967;
const rad = d => d * Math.PI / 180, dir = d => [Math.cos(rad(d)), Math.sin(rad(d))];
const NECK = i => i.v > .5 && i.u < .5, TAIL = i => i.v < .5 && i.u < .5;

// reverse fold of one leg: leg points at angle th0 from pivot P, mirror line at angle alpha
function reverse(title, text, sel, P, alpha, th0) {
  const d = dir(alpha), tip = dir(th0), side = Math.sign(d[0] * tip[1] - d[1] * tip[0]);
  return { step: F(title, text, P, [P[0] + d[0], P[1] + d[1]], side, { sel, zc: 'mean' }), th1: 2 * alpha - th0 };
}
function bird(opts) {
  const steps = [
    F('Fold in half', 'Fold the left edge over to the right edge.', [0, -.5], [0, .5], 1),
    F('Fold in half again', 'Fold the top edge down to the bottom edge. You have a small square.', [0, 0], [.5, 0], -1),
    { type: 'turn', title: 'Turn it', text: 'Turn the square so the corner with the folds points up.', p: [.25, .25], angle: -135 },
    F('Fold the left edge in', 'Fold the lower left edge of the top layer to the middle line.', T, [-.133, .82], 1, { sel: topN(1) }),
    F('Fold the right edge in', 'Fold the lower right edge of the top layer to the middle line too.', T, [.633, .82], -1, { sel: topN(2) }),
    F('Fold the point up', 'Fold the bottom point up, as high as the side folds reach. This is the petal fold.', [-.5, KY], [.5, KY], -1, { sel: topN(3) }),
    { type: 'rotate', title: 'Turn over', text: 'Flip the model over.', p: [.25, -.5], q: [.25, .8] },
    F('Fold the left edge in', 'Do the same on the back: fold the lower left edge to the middle line.', T, [-.133, .82], 1, { sel: topN(1) }),
    F('Fold the right edge in', 'Fold the lower right edge to the middle line.', T, [.633, .82], -1, { sel: topN(2) }),
    F('Fold the point up', 'Fold the bottom point up. You have made the bird base!', [-.5, KY], [.5, KY], -1, { sel: topN(3) }),
    F('Narrow the left leg', 'Fold the lower left edges (all layers) in to the middle line.', T, [-.133, .82], 1),
    F('Narrow the right leg', 'Fold the lower right edges in too. The two legs will become the neck and the tail.', T, [.633, .82], -1)
  ];
  const n = reverse(opts.neckTitle, opts.neckText, NECK, opts.neckP, opts.neckA, -90);
  const t = reverse(opts.tailTitle, opts.tailText, TAIL, opts.tailP, opts.tailA, -90);
  steps.push(n.step, t.step);
  const H = [opts.neckP[0] + opts.headAt * dir(n.th1)[0], opts.neckP[1] + opts.headAt * dir(n.th1)[1]];
  const hd = reverse(opts.headTitle, opts.headText, NECK, H, (n.th1 + opts.headTh) / 2, n.th1);
  steps.push(hd.step);
  const wing = (dirn, sel, text) => F('Open the wings', text, [-.5, KY], [.5, KY], 1, { sel: i => sel(i) && i.cy > KY - .01, dir: dirn, angle: opts.wing, zc: 'mean' });
  steps.push(wing('v', i => i.u > .5 && i.v > .5, 'Gently pull the front wing towards you...'));
  steps.push(wing('m', i => i.u > .5 && i.v < .5, '...and the back wing away from you. Spread them like a bird in flight!'));
  return { rot: 0, top: '#fbf3df', back: opts.color, steps };
}
exports.crane = Object.assign({ name: 'Crane' }, bird({
  color: '#e4572e', wing: 60,
  neckTitle: 'Make the neck', neckText: 'Open the left leg and fold it up and out. This is an inside reverse fold.', neckP: [.25, .30], neckA: 30,
  tailTitle: 'Make the tail', tailText: 'Do the same with the right leg, in the opposite direction.', tailP: [.25, .30], tailA: 150,
  headAt: .27, headTh: 215, headTitle: 'Fold the head', headText: 'Fold the tip of the neck over (another reverse fold) to make the head.'
}));
exports.swan = Object.assign({ name: 'Swan' }, bird({
  color: '#4a6fd8', wing: 40,
  neckTitle: 'Make the neck', neckText: 'Open the left leg and fold it up so it stands tall. This is an inside reverse fold.', neckP: [.25, .30], neckA: 20,
  tailTitle: 'Make the tail', tailText: 'Fold the right leg up and out, but keep it short and stubby.', tailP: [.25, .20], tailA: 150,
  headAt: .30, headTh: 190, headTitle: 'Curve the neck', headText: 'Fold the top of the neck over to make a graceful swan curve with a head that bows.'
}));
