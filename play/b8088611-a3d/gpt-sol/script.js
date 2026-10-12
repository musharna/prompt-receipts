const canvas = document.querySelector("#fog");
const context = canvas.getContext("2d", { alpha: false });
const toggle = document.querySelector("#motion-toggle");
const toggleIcon = toggle.querySelector(".control-icon");
const toggleLabel = toggle.querySelector(".control-label");

const glyphRamp = "  .·:;+*%#@";
const palette = [
  [76, 214, 205],
  [96, 126, 224],
  [176, 74, 224],
  [225, 74, 147],
];

let width = 0;
let height = 0;
let columns = 0;
let rows = 0;
let cellWidth = 13;
let cellHeight = 16;
let pixelRatio = 1;
let frame = 0;
let lastFrame = 0;
let isPaused = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
let pointer = { x: 0, y: 0, targetX: 0, targetY: 0 };

function resize() {
  width = window.innerWidth;
  height = window.innerHeight;
  pixelRatio = Math.min(window.devicePixelRatio || 1, 2);

  canvas.width = Math.round(width * pixelRatio);
  canvas.height = Math.round(height * pixelRatio);
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);

  cellWidth = width < 600 ? 11 : 13;
  cellHeight = width < 600 ? 14 : 16;
  columns = Math.ceil(width / cellWidth) + 1;
  rows = Math.ceil(height / cellHeight) + 1;
  draw(performance.now());
}

function mix(a, b, amount) {
  return a + (b - a) * amount;
}

function smoothNoise(x, y, time) {
  const broad = Math.sin(x * 1.18 + time * 0.18 + Math.sin(y * 0.72 - time * 0.11));
  const folded = Math.sin(y * 1.64 - time * 0.13 + Math.cos(x * 0.83 + time * 0.08));
  const detail = Math.sin((x + y) * 2.31 + time * 0.06) * 0.3;
  return (broad + folded + detail + 2.3) / 4.6;
}

function colorAt(amount, glow) {
  const position = Math.max(0, Math.min(0.999, amount)) * (palette.length - 1);
  const index = Math.floor(position);
  const local = position - index;
  const start = palette[index];
  const end = palette[Math.min(index + 1, palette.length - 1)];
  const lift = glow * 18;

  return [
    Math.min(255, mix(start[0], end[0], local) + lift),
    Math.min(255, mix(start[1], end[1], local) + lift),
    Math.min(255, mix(start[2], end[2], local) + lift),
  ];
}

function draw(timestamp = 0) {
  context.fillStyle = "#08080b";
  context.fillRect(0, 0, width, height);
  context.font = `${width < 600 ? 10 : 11}px "Courier New", monospace`;
  context.textAlign = "center";
  context.textBaseline = "middle";

  pointer.x += (pointer.targetX - pointer.x) * 0.025;
  pointer.y += (pointer.targetY - pointer.y) * 0.025;

  const time = timestamp * 0.001;
  const driftX = pointer.x * 0.85;
  const driftY = pointer.y * 0.5;

  for (let row = -1; row < rows; row += 1) {
    for (let column = -1; column < columns; column += 1) {
      const px = column * cellWidth;
      const py = row * cellHeight;
      const nx = (px / width) * 4.1 + driftX;
      const ny = (py / height) * 3.1 + driftY;

      const cloud = smoothNoise(nx, ny, time);
      const veil = smoothNoise(nx * 0.53 + 4.2, ny * 0.6 - 2.1, time * 0.72);
      const edgeFade = Math.min(1, py / (height * 0.18)) * Math.min(1, (height - py) / (height * 0.13));
      const density = Math.pow(Math.max(0, cloud * 0.72 + veil * 0.44 - 0.36), 1.28) * edgeFade;

      if (density < 0.12) continue;

      const glyphIndex = Math.min(glyphRamp.length - 1, Math.floor(density * glyphRamp.length));
      const glyph = glyphRamp[glyphIndex];
      const colorFlow = (Math.sin(nx * 0.82 - ny * 0.28 + time * 0.09) + 1) / 2;
      const [red, green, blue] = colorAt(colorFlow, density);
      const alpha = Math.min(0.76, density * 0.68);

      context.fillStyle = `rgba(${red}, ${green}, ${blue}, ${alpha})`;
      context.fillText(glyph, px, py);
    }
  }

  // A soft vignette preserves contrast behind the main type.
  const vignette = context.createRadialGradient(
    width * 0.5,
    height * 0.46,
    Math.min(width, height) * 0.15,
    width * 0.5,
    height * 0.5,
    Math.max(width, height) * 0.72,
  );
  vignette.addColorStop(0, "rgba(8, 8, 11, 0.02)");
  vignette.addColorStop(1, "rgba(8, 8, 11, 0.58)");
  context.fillStyle = vignette;
  context.fillRect(0, 0, width, height);
}

function animate(timestamp) {
  if (!isPaused && timestamp - lastFrame > 42) {
    draw(timestamp);
    lastFrame = timestamp;
  }
  frame = requestAnimationFrame(animate);
}

function updateToggle() {
  toggle.setAttribute("aria-pressed", String(isPaused));
  toggleIcon.textContent = isPaused ? "▶" : "Ⅱ";
  toggleLabel.textContent = isPaused ? "Play atmosphere" : "Pause atmosphere";
}

window.addEventListener("resize", resize);
window.addEventListener("pointermove", (event) => {
  pointer.targetX = (event.clientX / width - 0.5) * 0.34;
  pointer.targetY = (event.clientY / height - 0.5) * 0.25;
});

window.addEventListener("visibilitychange", () => {
  if (document.hidden) lastFrame = performance.now();
});

toggle.addEventListener("click", () => {
  isPaused = !isPaused;
  updateToggle();
  if (isPaused) draw(lastFrame);
});

resize();
updateToggle();
frame = requestAnimationFrame(animate);

window.addEventListener("beforeunload", () => cancelAnimationFrame(frame));
