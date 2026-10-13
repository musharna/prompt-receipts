/*
 * Pottery shop micro-animations.
 *
 *   PotteryAnim.success(el)  – fill el with a checkmark that draws in
 *   PotteryAnim.error(el)    – fill el with a cross that draws in, then shakes
 *   PotteryAnim.sparkle(el)  – add twinkling sparkles to el (e.g. a new item card)
 *
 * Automatic:
 *   .fav-btn                 – click toggles aria-pressed and pops the heart
 *   [data-sparkle]           – gets sparkles on page load
 */
(function () {
  'use strict';

  var CHECK_SVG =
    '<svg class="anim-check" viewBox="0 0 52 52" aria-hidden="true">' +
    '<circle class="anim-check__circle" cx="26" cy="26" r="24"/>' +
    '<path class="anim-check__tick" d="M14 27 L22 35 L38 19"/>' +
    '</svg>';

  var CROSS_SVG =
    '<svg class="anim-cross" viewBox="0 0 52 52" aria-hidden="true">' +
    '<circle class="anim-cross__circle" cx="26" cy="26" r="24"/>' +
    '<path class="anim-cross__line anim-cross__line--a" d="M18 18 L34 34"/>' +
    '<path class="anim-cross__line anim-cross__line--b" d="M34 18 L18 34"/>' +
    '</svg>';

  var STAR_SVG =
    '<svg viewBox="0 0 24 24" aria-hidden="true">' +
    '<path d="M12 0C12.6 7.4 16.6 11.4 24 12 16.6 12.6 12.6 16.6 12 24 11.4 16.6 7.4 12.6 0 12 7.4 11.4 11.4 7.4 12 0Z"/>' +
    '</svg>';

  // Positions are percentages of the host element; sizes in px.
  var SPARKLES = [
    { x: 10, y: 12, size: 14, delay: 0 },
    { x: 88, y: 10, size: 10, delay: 0.5 },
    { x: 80, y: 84, size: 16, delay: 1.0 },
    { x: 14, y: 86, size: 11, delay: 1.4 },
    { x: 50, y: 6,  size: 9,  delay: 0.8 }
  ];

  // Replacing innerHTML creates new nodes, so CSS animations restart from the beginning.
  function success(el) {
    el.innerHTML = CHECK_SVG;
  }

  function error(el) {
    el.innerHTML = CROSS_SVG;
  }

  function sparkle(el) {
    if (el.querySelector('.pot-sparkles')) return;

    var wrap = document.createElement('span');
    wrap.className = 'pot-sparkles';
    wrap.setAttribute('aria-hidden', 'true');

    SPARKLES.forEach(function (s) {
      var star = document.createElement('span');
      star.className = 'pot-sparkle';
      star.style.left = s.x + '%';
      star.style.top = s.y + '%';
      star.style.width = s.size + 'px';
      star.style.height = s.size + 'px';
      star.style.setProperty('--delay', s.delay + 's');
      star.innerHTML = STAR_SVG;
      wrap.appendChild(star);
    });

    el.appendChild(wrap);
  }

  // Favourite toggle. Delegated, so buttons added later also work.
  document.addEventListener('click', function (e) {
    var btn = e.target.closest && e.target.closest('.fav-btn');
    if (!btn) return;

    var on = btn.getAttribute('aria-pressed') !== 'true';
    btn.setAttribute('aria-pressed', String(on));

    if (on) {
      btn.classList.remove('is-popping');
      void btn.offsetWidth; // force reflow so the pop replays on rapid clicks
      btn.classList.add('is-popping');
    }
  });

  document.addEventListener('animationend', function (e) {
    var btn = e.target.closest && e.target.closest('.fav-btn');
    if (btn) btn.classList.remove('is-popping');
  });

  function initSparkles() {
    document.querySelectorAll('[data-sparkle]').forEach(sparkle);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSparkles);
  } else {
    initSparkles();
  }

  window.PotteryAnim = {
    success: success,
    error: error,
    sparkle: sparkle
  };
})();
