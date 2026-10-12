const canvas = document.querySelector('#fog');
const ctx = canvas.getContext('2d');
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
let width, height, cols, rows, fontSize, dpr;

function resize() {
  dpr = Math.min(devicePixelRatio || 1, 2);
  width = innerWidth; height = innerHeight;
  fontSize = width < 700 ? 12 : 15;
  cols = Math.ceil(width / (fontSize * .62));
  rows = Math.ceil(height / fontSize) + 2;
  canvas.width = width * dpr; canvas.height = height * dpr;
  canvas.style.width = `${width}px`; canvas.style.height = `${height}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
addEventListener('resize', resize); resize();

const chars = ' .·:;+=xX#%@';
function noise(x, y, t) {
  return (Math.sin(x * .12 + t * .42) + Math.sin(y * .19 - t * .25) + Math.sin((x + y) * .055 + t * .2) + Math.sin(x * .025 - y * .08 + t * .31)) / 4;
}
function frame(ms) {
  const t = (ms || 0) / 1000;
  ctx.fillStyle = '#08090e'; ctx.fillRect(0, 0, width, height);
  ctx.font = `${fontSize}px "DM Mono", monospace`; ctx.textBaseline = 'top';
  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < cols; x++) {
      const n = noise(x, y, t);
      const density = (n + 1) / 2;
      if (density < .39) continue;
      const hue = 100 + Math.sin(x * .03 + t * .12) * 55 + y * .45;
      const light = 48 + density * 23;
      ctx.fillStyle = `hsla(${hue}, ${70 + density * 20}%, ${light}%, ${.08 + density * .24})`;
      ctx.fillText(chars[Math.min(chars.length - 1, Math.floor(density * chars.length))], x * fontSize * .62, y * fontSize);
    }
  }
  if (!reduceMotion) requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
