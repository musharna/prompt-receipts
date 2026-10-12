const body = document.body;
const status = document.querySelector('#status-text');
const caption = document.querySelector('#stage-caption');
const pause = document.querySelector('#pause');
const adopt = document.querySelector('#adopt');
const toast = document.querySelector('#toast');
let idleTimer, paused = false;

function setNap(isNapping) {
  if (paused) return;
  body.classList.toggle('napping', isNapping);
  status.textContent = isNapping ? 'Taking a tiny nap' : 'Roaming happily';
  caption.textContent = isNapping ? 'shh… dreaming of snacks' : 'out for a little stroll';
}
function resetIdle() {
  setNap(false);
  clearTimeout(idleTimer);
  idleTimer = setTimeout(() => setNap(true), 4500);
}
['pointermove','pointerdown','keydown','touchstart'].forEach(event => window.addEventListener(event, resetIdle, {passive:true}));
resetIdle();

pause.addEventListener('click', () => {
  paused = !paused;
  body.classList.toggle('paused', paused);
  body.classList.remove('napping');
  pause.innerHTML = paused ? '<span class="pause-icon">▶</span> Resume roaming' : '<span class="pause-icon">Ⅱ</span> Pause roaming';
  status.textContent = paused ? 'Waiting for you' : 'Roaming happily';
  caption.textContent = paused ? 'patiently holding still' : 'out for a little stroll';
  if (!paused) resetIdle();
});
adopt.addEventListener('click', () => {
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2800);
});
document.querySelector('#settings').addEventListener('click', () => {
  toast.textContent = 'Settings coming soon — he already knows the important bit.';
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2800);
});
