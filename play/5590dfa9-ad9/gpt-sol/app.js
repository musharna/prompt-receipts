const canvas = document.querySelector('#slime-canvas');
const ctx = canvas.getContext('2d');
const meterFill = document.querySelector('#meter-fill');
const viscosityLabel = document.querySelector('#viscosity-label');
const resetButton = document.querySelector('#reset-button');
const hint = document.querySelector('#hint');

let width = 0;
let height = 0;
let dpr = 1;
let time = 0;
let lastTime = performance.now();
let pointer = { x: 0, y: 0, down: false, id: null, speed: 0, lastX: 0, lastY: 0 };
let activeBlob = null;
let pull = null;
let shake = 0;
let stars = [];
let motes = [];
let blobs = [];

const palette = ['#ec69d3', '#b457e2', '#7044de', '#2d78da', '#25a7c5'];

function makeBlob(x, y, r, phase = Math.random() * 10) {
  return { x, y, vx: 0, vy: 0, r, targetR: r, phase, squash: 0, flash: 0 };
}

function reset() {
  blobs = [makeBlob(width * .69, height * .49, Math.min(width, height) * .205, 2.4)];
  pull = null;
  activeBlob = null;
  shake = 0;
  scatterMotes(width * .69, height * .49, 22, 1);
}

function resize() {
  const oldW = width || innerWidth;
  const oldH = height || innerHeight;
  width = innerWidth;
  height = innerHeight;
  dpr = Math.min(devicePixelRatio || 1, 2);
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  stars = Array.from({ length: Math.floor(width * height / 8500) }, () => ({
    x: Math.random() * width, y: Math.random() * height, r: Math.random() * 1.1 + .15,
    a: Math.random() * .45 + .08, tw: Math.random() * 4 + 1
  }));
  if (!blobs.length) reset();
  else blobs.forEach(b => { b.x *= width / oldW; b.y *= height / oldH; });
}

function scatterMotes(x, y, count, force) {
  for (let i = 0; i < count; i++) {
    const a = Math.random() * Math.PI * 2;
    const s = (Math.random() * 2 + .3) * force;
    motes.push({ x, y, vx: Math.cos(a) * s, vy: Math.sin(a) * s, life: 1, size: Math.random() * 2 + .5 });
  }
}

function hitBlob(x, y) {
  return [...blobs].reverse().find(b => Math.hypot(x - b.x, y - b.y) < b.r * 1.06);
}

function onPointerDown(e) {
  const b = hitBlob(e.clientX, e.clientY);
  if (!b) return;
  pointer = { ...pointer, x: e.clientX, y: e.clientY, lastX: e.clientX, lastY: e.clientY, down: true, id: e.pointerId, speed: 0 };
  activeBlob = b;
  pull = {
    anchorX: b.x, anchorY: b.y, x: e.clientX, y: e.clientY,
    carry: blobs.length > 1,
    offsetX: e.clientX - b.x, offsetY: e.clientY - b.y
  };
  b.flash = 1;
  canvas.setPointerCapture(e.pointerId);
  canvas.classList.add('grabbing');
  hint.classList.add('hidden');
  scatterMotes(e.clientX, e.clientY, 7, .5);
}

function onPointerMove(e) {
  if (!pointer.down || e.pointerId !== pointer.id) return;
  const dx = e.clientX - pointer.lastX;
  const dy = e.clientY - pointer.lastY;
  pointer.speed = pointer.speed * .7 + Math.hypot(dx, dy) * .3;
  pointer.x = e.clientX; pointer.y = e.clientY;
  pointer.lastX = e.clientX; pointer.lastY = e.clientY;
  if (pull) {
    pull.x = pointer.x; pull.y = pointer.y;
    if (pull.carry && activeBlob) {
      const nextX = pointer.x - pull.offsetX, nextY = pointer.y - pull.offsetY;
      activeBlob.vx = (nextX - activeBlob.x) * .18;
      activeBlob.vy = (nextY - activeBlob.y) * .18;
      activeBlob.x += (nextX - activeBlob.x) * .34;
      activeBlob.y += (nextY - activeBlob.y) * .34;
      activeBlob.squash = Math.min(.42, pointer.speed * .018);
    }
  }
}

function onPointerUp(e) {
  if (!pointer.down || e.pointerId !== pointer.id) return;
  if (activeBlob && pull) {
    const dist = Math.hypot(pull.x - pull.anchorX, pull.y - pull.anchorY);
    const splitAt = activeBlob.r * 1.55;
    if (!pull.carry && dist > splitAt && activeBlob.r > 62) {
      const angle = Math.atan2(pull.y - pull.anchorY, pull.x - pull.anchorX);
      const old = activeBlob;
      const r = old.r * .73;
      old.r = r; old.targetR = r; old.x = pull.anchorX; old.y = pull.anchorY;
      old.vx = -Math.cos(angle) * 2; old.vy = -Math.sin(angle) * 2;
      const baby = makeBlob(pull.x, pull.y, r, old.phase + 1.7);
      baby.vx = Math.cos(angle) * 5; baby.vy = Math.sin(angle) * 5;
      blobs.push(baby);
      scatterMotes((old.x + baby.x) / 2, (old.y + baby.y) / 2, 35, 2.3);
      shake = 7;
    } else if (!pull.carry) {
      activeBlob.vx += (pull.x - pull.anchorX) * .035;
      activeBlob.vy += (pull.y - pull.anchorY) * .035;
      activeBlob.squash = Math.min(dist / activeBlob.r, .8);
      scatterMotes(pull.x, pull.y, 10, .8);
    }
  }
  pointer.down = false; pointer.id = null; activeBlob = null; pull = null;
  canvas.classList.remove('grabbing');
}

function update(dt) {
  const dragStretch = pull && activeBlob && !pull.carry ? Math.hypot(pull.x - pull.anchorX, pull.y - pull.anchorY) / (activeBlob.r * 1.55) : 0;
  meterFill.style.width = `${Math.min(100, 24 + dragStretch * 76)}%`;
  viscosityLabel.textContent = dragStretch > .82 ? 'SNAPPY!' : dragStretch > .45 ? 'STRETCHY' : 'WOBBLY';

  for (const b of blobs) {
    b.x += b.vx * dt; b.y += b.vy * dt;
    b.vx *= Math.pow(.91, dt); b.vy *= Math.pow(.91, dt);
    b.squash *= Math.pow(.89, dt); b.flash *= Math.pow(.9, dt);
    const pad = b.r * .72;
    if (b.x < pad) { b.x = pad; b.vx = Math.abs(b.vx) * .7; b.squash = .35; }
    if (b.x > width - pad) { b.x = width - pad; b.vx = -Math.abs(b.vx) * .7; b.squash = .35; }
    if (b.y < pad) { b.y = pad; b.vy = Math.abs(b.vy) * .7; b.squash = .35; }
    if (b.y > height - pad) { b.y = height - pad; b.vy = -Math.abs(b.vy) * .7; b.squash = .35; }
  }

  // Separate blobs attract and melt back together when their surfaces touch.
  if (blobs.length > 1 && !pointer.down) {
    for (let i = 0; i < blobs.length; i++) for (let j = i + 1; j < blobs.length; j++) {
      const a = blobs[i], b = blobs[j];
      const dx = b.x - a.x, dy = b.y - a.y, d = Math.max(1, Math.hypot(dx, dy));
      const touching = d < (a.r + b.r) * .83;
      if (d < (a.r + b.r) * 1.75) {
        const tug = touching ? .024 : .004;
        a.vx += dx / d * tug * dt; a.vy += dy / d * tug * dt;
        b.vx -= dx / d * tug * dt; b.vy -= dy / d * tug * dt;
      }
      if (touching) {
        const areaR = Math.sqrt(a.r * a.r + b.r * b.r);
        a.x = (a.x * a.r + b.x * b.r) / (a.r + b.r);
        a.y = (a.y * a.r + b.y * b.r) / (a.r + b.r);
        a.r = areaR; a.targetR = areaR; a.squash = .75; a.flash = 1;
        a.vx = (a.vx + b.vx) * .5; a.vy = (a.vy + b.vy) * .5;
        blobs.splice(j, 1); j--;
        scatterMotes(a.x, a.y, 24, 1.3); shake = 4;
      }
    }
  }

  motes.forEach(m => { m.x += m.vx * dt; m.y += m.vy * dt; m.vx *= .98; m.vy *= .98; m.life -= .018 * dt; });
  motes = motes.filter(m => m.life > 0);
  shake *= Math.pow(.75, dt);
}

function blobPath(cx, cy, rx, ry, phase, wobble = 1) {
  const points = 48;
  ctx.beginPath();
  for (let i = 0; i <= points; i++) {
    const a = i / points * Math.PI * 2;
    const noise = 1 + (Math.sin(a * 3 + time * .0017 + phase) * .035 + Math.sin(a * 5 - time * .0011 + phase * 2) * .018) * wobble;
    const x = cx + Math.cos(a) * rx * noise;
    const y = cy + Math.sin(a) * ry * noise;
    if (!i) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  }
  ctx.closePath();
}

function drawGalaxyFill(b, cx = b.x, cy = b.y, rx = b.r, ry = b.r) {
  const grad = ctx.createRadialGradient(cx - rx * .35, cy - ry * .42, rx * .05, cx, cy, rx * 1.15);
  grad.addColorStop(0, '#f89bdd');
  grad.addColorStop(.22, '#c94bd3');
  grad.addColorStop(.5, '#7632c5');
  grad.addColorStop(.76, '#255fc2');
  grad.addColorStop(1, '#083c70');
  ctx.fillStyle = grad; ctx.fill();

  ctx.save(); ctx.clip();
  ctx.globalCompositeOperation = 'screen';
  for (let i = 0; i < 8; i++) {
    const a = i * 2.399 + b.phase;
    const px = cx + Math.cos(a + time * .00005) * rx * ((i % 4) / 5);
    const py = cy + Math.sin(a) * ry * ((i % 5) / 6);
    const g = ctx.createRadialGradient(px, py, 0, px, py, rx * (.2 + (i % 3) * .06));
    g.addColorStop(0, i % 2 ? '#ff61cf99' : '#48c8ec88'); g.addColorStop(1, '#00000000');
    ctx.fillStyle = g; ctx.fillRect(cx - rx, cy - ry, rx * 2, ry * 2);
  }
  for (let i = 0; i < 38; i++) {
    const seed = (i * 97.31 + b.phase * 13) % 37;
    const a = seed * 2.17;
    const rr = Math.sqrt(((i * 41.7) % 100) / 100) * .84;
    const sx = cx + Math.cos(a) * rx * rr, sy = cy + Math.sin(a) * ry * rr;
    const sr = i % 9 === 0 ? 1.8 : .45 + (i % 3) * .3;
    ctx.globalAlpha = .35 + (Math.sin(time * .003 + i) + 1) * .22;
    ctx.fillStyle = i % 5 === 0 ? '#aaf4ff' : '#fff4ff';
    ctx.beginPath(); ctx.arc(sx, sy, sr, 0, Math.PI * 2); ctx.fill();
    if (i % 11 === 0) { ctx.fillRect(sx - sr * 3, sy - .35, sr * 6, .7); ctx.fillRect(sx - .35, sy - sr * 3, .7, sr * 6); }
  }
  ctx.restore(); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
}

function drawBlob(b) {
  let cx = b.x, cy = b.y, rx = b.r * (1 + b.squash * .18), ry = b.r * (1 - b.squash * .12);
  if (pull && activeBlob === b && !pull.carry) {
    const dx = pull.x - pull.anchorX, dy = pull.y - pull.anchorY;
    const d = Math.hypot(dx, dy), a = Math.atan2(dy, dx);
    const max = b.r * 2.1, stretch = Math.min(d, max);
    cx = pull.anchorX + Math.cos(a) * stretch * .34; cy = pull.anchorY + Math.sin(a) * stretch * .34;
    rx = b.r + stretch * .38; ry = b.r * Math.max(.42, 1 - stretch / (b.r * 3));
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(a); ctx.translate(-cx, -cy);
  } else ctx.save();

  ctx.shadowColor = '#bd48e0'; ctx.shadowBlur = 45 + b.flash * 25;
  blobPath(cx, cy, rx, ry, b.phase, 1 + b.squash);
  drawGalaxyFill(b, cx, cy, rx, ry);
  ctx.shadowBlur = 0;
  const edge = ctx.createLinearGradient(cx - rx, cy - ry, cx + rx, cy + ry);
  edge.addColorStop(0, '#ffffffb8'); edge.addColorStop(.18, '#fcb5ef22'); edge.addColorStop(.7, '#7440d844'); edge.addColorStop(1, '#43cbec88');
  ctx.strokeStyle = edge; ctx.lineWidth = 2.2; ctx.stroke();
  ctx.globalAlpha = .72;
  ctx.strokeStyle = '#ffffff'; ctx.lineWidth = Math.max(2, b.r * .035); ctx.lineCap = 'round';
  ctx.beginPath(); ctx.arc(cx - rx * .2, cy - ry * .18, rx * .48, 3.55, 4.82); ctx.stroke();
  ctx.globalAlpha = 1;
  ctx.restore();
}

function draw() {
  ctx.clearRect(0, 0, width, height);
  ctx.save();
  if (shake > .1) ctx.translate((Math.random() - .5) * shake, (Math.random() - .5) * shake);
  for (const s of stars) {
    ctx.globalAlpha = s.a * (.72 + Math.sin(time * .001 * s.tw) * .28);
    ctx.fillStyle = '#e8dbff'; ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2); ctx.fill();
  }
  ctx.globalAlpha = 1;

  // Soft shadow beneath each slime piece.
  for (const b of blobs) {
    const g = ctx.createRadialGradient(b.x, b.y + b.r * .75, 0, b.x, b.y + b.r * .75, b.r * .9);
    g.addColorStop(0, '#13001999'); g.addColorStop(1, '#13001900');
    ctx.save(); ctx.scale(1, .28); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(b.x, (b.y + b.r * .75) / .28, b.r * .9, 0, Math.PI * 2); ctx.fill(); ctx.restore();
  }
  blobs.forEach(drawBlob);

  for (const m of motes) {
    ctx.globalAlpha = Math.max(0, m.life);
    ctx.fillStyle = m.size > 1.5 ? '#f39eea' : '#a6efff';
    ctx.beginPath(); ctx.arc(m.x, m.y, m.size, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore(); ctx.globalAlpha = 1;
}

function frame(now) {
  const dt = Math.min(2, (now - lastTime) / 16.67);
  lastTime = now; time = now;
  update(dt); draw(); requestAnimationFrame(frame);
}

canvas.addEventListener('pointerdown', onPointerDown);
canvas.addEventListener('pointermove', onPointerMove);
canvas.addEventListener('pointerup', onPointerUp);
canvas.addEventListener('pointercancel', onPointerUp);
resetButton.addEventListener('click', reset);
window.addEventListener('resize', resize);
resize();
requestAnimationFrame(frame);
