const canvas = document.querySelector('#fog');
const ctx = canvas.getContext('2d');
const sound = document.querySelector('.sound');
const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
let width, height, cols, rows, cell, frame = 0, paused = reduced.matches;

const chars = '·,.:;~*+=-';
const palette = [
  [58, 43, 209],   // violet
  [229, 64, 82],   // red
  [249, 147, 37],  // amber
  [25, 157, 146],  // teal
  [218, 48, 145]   // magenta
];

function resize() {
  const ratio = Math.min(devicePixelRatio || 1, 2);
  width = innerWidth; height = innerHeight;
  cell = width < 600 ? 10 : 12;
  cols = Math.ceil(width / cell); rows = Math.ceil(height / cell);
  canvas.width = width * ratio; canvas.height = height * ratio;
  canvas.style.width = width + 'px'; canvas.style.height = height + 'px';
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.font = `${cell}px "DM Mono", monospace`;
  ctx.textBaseline = 'middle';
}

const wave = (x, y, t, phase) =>
  Math.sin(x * .055 + t * .42 + phase) +
  Math.sin(y * .07 - t * .27 + phase * 2) +
  Math.sin((x + y) * .032 + t * .2) +
  Math.sin(Math.hypot(x - cols * .52, y - rows * .48) * .13 - t * .33);

function draw() {
  if (paused) return;
  frame += .016;
  ctx.clearRect(0, 0, width, height);
  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < cols; x++) {
      const n = wave(x, y, frame, 0) / 4;
      if (n < -.05) continue;
      const band = (wave(x, y, frame, 2.4) + 4) / 8;
      const color = palette[Math.min(palette.length - 1, Math.floor(band * palette.length))];
      const alpha = Math.pow(Math.max(0, n), 1.25) * .72;
      const index = Math.min(chars.length - 1, Math.floor(Math.max(0,n) * chars.length * 1.55));
      ctx.fillStyle = `rgba(${color[0]},${color[1]},${color[2]},${alpha})`;
      ctx.fillText(chars[index], x * cell, y * cell + cell / 2);
    }
  }
  requestAnimationFrame(draw);
}

sound.addEventListener('click', () => {
  paused = !paused;
  sound.setAttribute('aria-pressed', String(!paused));
  sound.lastChild.textContent = paused ? ' Atmosphere: off' : ' Atmosphere: on';
  if (!paused) draw();
});
reduced.addEventListener('change', event => { paused = event.matches; if (!paused) draw(); });
addEventListener('resize', resize);
resize();
if (!paused) draw();
