const pet = document.querySelector('#petWrap');
const thought = document.querySelector('#thought');
const moodText = document.querySelector('#moodText');
const statusText = document.querySelector('#statusText');
const statusIcon = document.querySelector('#statusIcon');
const settingsPanel = document.querySelector('#settingsPanel');
const idleRange = document.querySelector('#idleRange');
const idleValue = document.querySelector('#idleValue');
const followToggle = document.querySelector('#followToggle');

let idleDelay = Number(idleRange.value) * 1000;
let idleTimer;
let strollTimer;
let lastX = window.innerWidth * .58;
let isNapping = false;
let isMuted = false;

function chirp() {
  if (isMuted) return;
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    const audio = new AudioContext();
    const gain = audio.createGain();
    const oscillator = audio.createOscillator();
    oscillator.type = 'sine';
    oscillator.frequency.setValueAtTime(540, audio.currentTime);
    oscillator.frequency.exponentialRampToValueAtTime(760, audio.currentTime + .12);
    gain.gain.setValueAtTime(.0001, audio.currentTime);
    gain.gain.exponentialRampToValueAtTime(.055, audio.currentTime + .02);
    gain.gain.exponentialRampToValueAtTime(.0001, audio.currentTime + .18);
    oscillator.connect(gain).connect(audio.destination);
    oscillator.start();
    oscillator.stop(audio.currentTime + .2);
    oscillator.addEventListener('ended', () => audio.close());
  } catch (_) { /* Audio is a small optional flourish. */ }
}

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

function setPetPosition(x, quick = false) {
  const safeX = clamp(x, 115, window.innerWidth - 115);
  pet.classList.toggle('right-facing', safeX < lastX);
  if (quick) pet.style.transitionDuration = '1.5s';
  else pet.style.transitionDuration = '';
  pet.style.left = `${safeX}px`;
  lastX = safeX;
}

function showThought(message) {
  thought.textContent = message;
  thought.classList.add('show');
  window.clearTimeout(showThought.timer);
  showThought.timer = window.setTimeout(() => thought.classList.remove('show'), 2300);
}

function wakeUp(withGreeting = false) {
  if (isNapping) {
    isNapping = false;
    pet.classList.remove('napping');
    moodText.textContent = 'Bright-eyed & curious';
    statusIcon.textContent = '✦';
    statusText.textContent = 'Mochi is awake again';
    if (withGreeting) showThought('oh! hello ♡');
  }
  window.clearTimeout(idleTimer);
  idleTimer = window.setTimeout(goToSleep, idleDelay);
}

function goToSleep() {
  isNapping = true;
  pet.classList.add('napping');
  thought.classList.remove('show');
  moodText.textContent = 'Dreaming of bubbles';
  statusIcon.textContent = '☾';
  statusText.textContent = 'Mochi curled up for a nap';
}

function stroll() {
  if (!isNapping) {
    const margin = Math.max(120, window.innerWidth * .09);
    const next = margin + Math.random() * (window.innerWidth - margin * 2);
    setPetPosition(next);
    const messages = ['Mochi is out for a stroll', 'Tiny feet, big adventure', 'Exploring the taskbar...'];
    statusText.textContent = messages[Math.floor(Math.random() * messages.length)];
  }
  strollTimer = window.setTimeout(stroll, 5000 + Math.random() * 3500);
}

let pointerThrottle = 0;
document.addEventListener('pointermove', (event) => {
  wakeUp(false);
  if (!followToggle.checked || Date.now() - pointerThrottle < 900) return;
  pointerThrottle = Date.now();
  if (event.clientY > window.innerHeight * .52) setPetPosition(event.clientX, true);
});

document.addEventListener('pointerdown', (event) => {
  if (!settingsPanel.contains(event.target) && !event.target.closest('#settingsButton')) {
    settingsPanel.classList.remove('open');
    settingsPanel.setAttribute('aria-hidden', 'true');
    document.querySelector('#settingsButton').setAttribute('aria-expanded', 'false');
  }
  wakeUp(false);
});

pet.addEventListener('click', () => {
  const wasNapping = isNapping;
  wakeUp(true);
  showThought(wasNapping ? 'five more minutes...' : ['hi friend! ♡', 'boop!', 'let’s wander!'][Math.floor(Math.random() * 3)]);
  moodText.textContent = 'Happy to see you';
  chirp();
});

document.querySelector('#settingsButton').addEventListener('click', () => {
  const open = settingsPanel.classList.toggle('open');
  settingsPanel.setAttribute('aria-hidden', String(!open));
  document.querySelector('#settingsButton').setAttribute('aria-expanded', String(open));
});
document.querySelector('#closeSettings').addEventListener('click', () => {
  settingsPanel.classList.remove('open');
  document.querySelector('#settingsButton').setAttribute('aria-expanded', 'false');
});
document.querySelector('#wakeButton').addEventListener('click', () => {
  wakeUp(true);
  setPetPosition(window.innerWidth * .72, true);
  settingsPanel.classList.remove('open');
  document.querySelector('#settingsButton').setAttribute('aria-expanded', 'false');
});
document.querySelector('#soundButton').addEventListener('click', (event) => {
  isMuted = !isMuted;
  event.currentTarget.classList.toggle('muted', isMuted);
});
idleRange.addEventListener('input', () => {
  idleDelay = Number(idleRange.value) * 1000;
  idleValue.textContent = `${idleRange.value} seconds`;
  wakeUp(false);
});
window.addEventListener('resize', () => setPetPosition(lastX, true));

function updateClock() {
  const now = new Date();
  const time = now.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  const date = now.toLocaleDateString([], { month: 'numeric', day: 'numeric', year: 'numeric' });
  document.querySelector('#clock').innerHTML = `${time}<br><small>${date}</small>`;
  const hour = now.getHours();
  document.querySelector('#greeting').innerHTML = `${hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'}! <span>♡</span>`;
}

updateClock();
window.setInterval(updateClock, 30000);
wakeUp(false);
window.setTimeout(stroll, 1600);
window.setTimeout(() => showThought('oh! hello ♡'), 700);

if ('serviceWorker' in navigator && location.protocol.startsWith('http')) {
  navigator.serviceWorker.register('./sw.js').catch(() => {});
}
