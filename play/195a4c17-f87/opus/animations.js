/* Pottery shop micro-animations – small helpers, no dependencies. */
(function () {
  "use strict";

  const SVG_NS = "http://www.w3.org/2000/svg";

  // Restart a CSS animation by toggling a class (forces a reflow in between).
  function replay(el, className) {
    el.classList.remove(className);
    void el.offsetWidth;
    el.classList.add(className);
  }

  /* ------------------------------------------------------------------
     Status icons
     ------------------------------------------------------------------ */
  const ICONS = {
    success:
      '<circle class="ring" cx="26" cy="26" r="23" pathLength="1" transform="rotate(-90 26 26)"/>' +
      '<path class="mark" d="M15 27 l7 7 l15 -16" pathLength="1"/>',
    error:
      '<circle class="ring" cx="26" cy="26" r="23" pathLength="1" transform="rotate(-90 26 26)"/>' +
      '<path class="mark" d="M18 18 L34 34" pathLength="1"/>' +
      '<path class="mark" d="M34 18 L18 34" pathLength="1"/>',
  };

  /**
   * Render (or re-render) an animated status icon into `el`.
   * @param {HTMLElement} el
   * @param {"success"|"error"} type
   * @param {string} [label] accessible label, e.g. "Order placed"
   */
  function showStatus(el, type, label) {
    el.className = "status-icon status-icon--" + type;
    el.setAttribute("role", "img");
    el.setAttribute("aria-label", label || (type === "success" ? "Success" : "Error"));
    el.innerHTML =
      '<svg viewBox="0 0 52 52" aria-hidden="true" focusable="false">' + ICONS[type] + "</svg>";
    replay(el, "is-playing");
  }

  /* ------------------------------------------------------------------
     Favourite heart
     ------------------------------------------------------------------ */
  const HEART_SVG =
    '<svg class="heart" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
    '<path d="M12 21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.8 4.5c2.1 0 3.6 1.1 5.2 3 1.6-1.9 3.1-3 5.2-3 3.8 0 5.9 3.9 4.4 7.3C19.5 16.4 12 21 12 21z"/>' +
    "</svg>";

  const prefersReducedMotion = () =>
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function burst(btn) {
    if (prefersReducedMotion()) return;
    const count = 8;
    for (let i = 0; i < count; i++) {
      const dot = document.createElement("span");
      dot.className = "burst-dot";
      dot.style.setProperty("--angle", (360 / count) * i + "deg");
      dot.addEventListener("animationend", () => dot.remove(), { once: true });
      btn.appendChild(dot);
    }
  }

  /**
   * Turn every `.fav-btn` inside `root` into a toggle.
   * Fires a bubbling "favouritechange" event with detail { favourited }.
   */
  function initFavourites(root = document) {
    root.querySelectorAll(".fav-btn").forEach((btn) => {
      if (btn.dataset.favInit) return;
      btn.dataset.favInit = "1";
      if (!btn.querySelector(".heart")) btn.insertAdjacentHTML("afterbegin", HEART_SVG);
      if (!btn.hasAttribute("aria-pressed")) btn.setAttribute("aria-pressed", "false");
      if (!btn.hasAttribute("aria-label")) btn.setAttribute("aria-label", "Favourite");

      btn.addEventListener("click", () => {
        const on = btn.getAttribute("aria-pressed") !== "true";
        btn.setAttribute("aria-pressed", String(on));
        if (on) {
          replay(btn, "is-popping");
          burst(btn);
        } else {
          btn.classList.remove("is-popping");
        }
        btn.dispatchEvent(
          new CustomEvent("favouritechange", { bubbles: true, detail: { favourited: on } })
        );
      });
    });
  }

  /* ------------------------------------------------------------------
     Sparkles
     ------------------------------------------------------------------ */
  const STAR_PATH = "M12 0 C13 8 16 11 24 12 C16 13 13 16 12 24 C11 16 8 13 0 12 C8 11 11 8 12 0Z";

  function makeSparkle() {
    const s = document.createElement("span");
    s.className = "sparkle";
    s.setAttribute("aria-hidden", "true");
    const svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    const p = document.createElementNS(SVG_NS, "path");
    p.setAttribute("d", STAR_PATH);
    svg.appendChild(p);
    s.appendChild(svg);
    return s;
  }

  const rand = (min, max) => min + Math.random() * (max - min);

  /**
   * Add twinkling sparkles to each `.sparkle-host` inside `root`.
   * Count can be set per element with data-sparkles="6".
   * Sparkles hug the edges/corners so they don't cover the product photo.
   */
  function initSparkles(root = document) {
    root.querySelectorAll(".sparkle-host").forEach((host) => {
      if (host.dataset.sparkleInit) return;
      host.dataset.sparkleInit = "1";
      const count = parseInt(host.dataset.sparkles, 10) || 5;

      for (let i = 0; i < count; i++) {
        const s = makeSparkle();
        // Alternate between the four edges, randomised along each one.
        const edge = i % 4;
        const along = rand(5, 95) + "%";
        const inset = rand(-4, 10) + "%";
        if (edge === 0) { s.style.top = inset;    s.style.left = along; }
        if (edge === 1) { s.style.right = inset;  s.style.top = along; }
        if (edge === 2) { s.style.bottom = inset; s.style.left = along; }
        if (edge === 3) { s.style.left = inset;   s.style.top = along; }

        s.style.setProperty("--size", Math.round(rand(10, 20)) + "px");
        s.style.setProperty("--dur", rand(1.4, 2.4).toFixed(2) + "s");
        s.style.setProperty("--delay", rand(0, 2).toFixed(2) + "s");
        host.appendChild(s);
      }
    });
  }

  /* ------------------------------------------------------------------ */
  window.PotteryAnim = { showStatus, initFavourites, initSparkles };

  document.addEventListener("DOMContentLoaded", () => {
    initFavourites();
    initSparkles();
  });
})();
