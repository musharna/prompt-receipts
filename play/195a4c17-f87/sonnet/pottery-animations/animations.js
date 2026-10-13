// Pottery shop micro-animations: markup helpers. No dependencies.

const NS = 'http://www.w3.org/2000/svg';

// Replay-safe: returns fresh markup each call so animations restart.
export function successIcon() {
  return `<svg class="anim-icon anim-success" viewBox="0 0 52 52" role="img" aria-label="Success">
    <circle class="ring" cx="26" cy="26" r="23" pathLength="1"/>
    <path class="tick" d="M15 27 l8 8 l15 -17" pathLength="1"/>
  </svg>`;
}

export function errorIcon() {
  return `<svg class="anim-icon anim-error" viewBox="0 0 52 52" role="img" aria-label="Error">
    <circle class="ring" cx="26" cy="26" r="23" pathLength="1"/>
    <path class="bar-a" d="M18 18 L34 34" pathLength="1"/>
    <path class="bar-b" d="M34 18 L18 34" pathLength="1"/>
  </svg>`;
}

// Usage: showIcon(el, 'success') after checkout succeeds, 'error' if payment fails.
export function showIcon(el, kind) {
  el.innerHTML = kind === 'success' ? successIcon() : errorIcon();
}

// Turns every <button class="heart-btn"> into a toggle with a pop + burst.
// Dispatches a bubbling "favourite-change" event with detail { favourited }.
export function initHearts(root = document) {
  root.querySelectorAll('.heart-btn').forEach((btn) => {
    if (!btn.querySelector('svg')) {
      btn.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true">
        <path class="heart-shape" d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
      </svg>` + Array.from({ length: 6 }, (_, i) => `<i class="burst" style="--a:${i * 60}deg"></i>`).join('');
    }
    if (!btn.hasAttribute('aria-pressed')) btn.setAttribute('aria-pressed', 'false');
    if (!btn.hasAttribute('aria-label')) btn.setAttribute('aria-label', 'Favourite');

    btn.addEventListener('click', () => {
      const on = btn.getAttribute('aria-pressed') !== 'true';
      btn.setAttribute('aria-pressed', String(on));
      btn.classList.remove('is-popping');
      if (on) {
        void btn.offsetWidth; // restart animation
        btn.classList.add('is-popping');
      }
      btn.dispatchEvent(new CustomEvent('favourite-change', { bubbles: true, detail: { favourited: on } }));
    });
  });
}

// Adds scattered twinkling sparkles to every .sparkle-wrap (e.g. wrap a "New" product image).
export function initSparkles(root = document) {
  const spots = [[8, 12], [82, 8], [90, 55], [15, 78], [50, 90], [60, 25]];
  const star = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 0 C13 8 16 11 24 12 C16 13 13 16 12 24 C11 16 8 13 0 12 C8 11 11 8 12 0Z"/></svg>`;
  root.querySelectorAll('.sparkle-wrap').forEach((wrap) => {
    if (wrap.querySelector('.sparkle')) return;
    spots.forEach(([x, y], i) => {
      const s = document.createElement('span');
      s.className = 'sparkle';
      s.style.cssText = `left:${x}%;top:${y}%;--s:${12 + (i % 3) * 5}px;--d:${(i * 0.4).toFixed(1)}s`;
      s.innerHTML = star;
      wrap.appendChild(s);
    });
  });
}
