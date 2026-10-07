/**
 * <blob-mascot> — a round, breathing, blinking blob that giggles when poked.
 *
 * Usage:
 *   <script type="module" src="blob-mascot.js"></script>
 *   <blob-mascot mood="happy"></blob-mascot>
 *
 * Attributes / properties
 *   mood     "idle" | "happy" | "sleepy" | "surprised"   (default "idle")
 *
 * Methods
 *   poke()   make it giggle from code (e.g. when a habit is checked off)
 *   blink()  force a blink
 *
 * Events
 *   "poke"   fired on every poke (bubbles, composed); detail: { mood }
 *
 * Theming (CSS custom properties on the element)
 *   --blob-color   body colour            (default #7DD3A8)
 *   --blob-ink     eyes / mouth / text    (default #2E2A3A)
 *   --blob-blush   cheeks / tongue        (default #FF8FA3)
 *   Size it with plain CSS `width` (it's always square).
 */

const NS = 'http://www.w3.org/2000/svg';
export const MOODS = ['idle', 'happy', 'sleepy', 'surprised'];
const GIGGLES = ['hee', 'hehe', 'tee hee', 'hihi', '♪'];
const BODY = 'M100 42C146 42 172 74 172 114C172 154 143 178 100 178C57 178 28 154 28 114C28 74 54 42 100 42Z';

const template = document.createElement('template');
template.innerHTML = /* html */ `
<style>
  :host {
    --blob-color: #7DD3A8;
    --blob-ink: #2E2A3A;
    --blob-blush: #FF8FA3;
    display: inline-block;
    width: 160px;
    aspect-ratio: 1;
    cursor: pointer;
    user-select: none;
    -webkit-user-select: none;
    touch-action: manipulation;
    -webkit-tap-highlight-color: transparent;
    border-radius: 24px;
    outline: none;
  }
  :host(:focus-visible) {
    outline: 3px solid color-mix(in srgb, var(--blob-ink) 35%, transparent);
    outline-offset: 4px;
  }
  svg { display: block; width: 100%; height: 100%; overflow: visible; }

  /* ---------- paint ---------- */
  .body   { fill: var(--blob-color); }
  .shade  { fill: url(#shade); stroke: rgb(0 0 0 / .08); stroke-width: 2; }
  .shine  { fill: #fff; opacity: .55; }
  .ink    { fill: var(--blob-ink); }
  .glint  { fill: #fff; }
  .white  { fill: #fff; stroke: var(--blob-ink); stroke-width: 2.5; }
  .tongue { fill: var(--blob-blush); }
  .line, .brows path {
    fill: none; stroke: var(--blob-ink); stroke-width: 4.5;
    stroke-linecap: round; stroke-linejoin: round;
  }
  .brows path { stroke-width: 3.5; }
  .shadow { fill: rgb(0 0 0 / .12); }

  /* ---------- face parts: one set per mood, cross-faded ---------- */
  .part { opacity: 0; transition: opacity .14s ease; }
  [data-face="idle"]      .f-idle,
  [data-face="happy"]     .f-happy,
  [data-face="sleepy"]    .f-sleepy,
  [data-face="surprised"] .f-surprised,
  [data-face="giggle"]    .f-giggle { opacity: 1; }

  .blush { fill: var(--blob-blush); opacity: .5; transition: opacity .3s ease; }
  [data-face="happy"]     .blush { opacity: .7; }
  [data-face="giggle"]    .blush { opacity: .9; }
  [data-face="sleepy"]    .blush { opacity: .25; }
  [data-face="surprised"] .blush { opacity: 0; }

  /* ---------- transform layers (all pivot on the blob's base) ---------- */
  .hop, .jolt, .squish, .wiggle, .breathe {
    transform-box: view-box;
    transform-origin: 100px 178px;
  }
  .shadow, .eyes-blink, .mouth-sleepy, .zzz text, .giggle-text {
    transform-box: fill-box;
    transform-origin: center;
  }

  /* breathing */
  .breathe { animation: breathe 3.6s ease-in-out infinite; }
  .shadow  { animation: shadow-breathe 3.6s ease-in-out infinite; }
  [data-mood="sleepy"] .breathe    { animation: breathe-deep 5.5s ease-in-out infinite; }
  [data-mood="sleepy"] .shadow     { animation-duration: 5.5s; }
  [data-mood="surprised"] .breathe { animation-duration: 2s; }
  [data-mood="surprised"] .shadow  { animation-duration: 2s; }

  @keyframes breathe {
    0%, 100% { transform: scale(1, 1); }
    50%      { transform: scale(.985, 1.03); }
  }
  @keyframes breathe-deep {
    0%, 100% { transform: scale(1.02, .975); }
    50%      { transform: scale(.98, 1.04); }
  }
  @keyframes shadow-breathe {
    0%, 100% { transform: scaleX(1); }
    50%      { transform: scaleX(.97); }
  }

  /* happy: little hops */
  [data-mood="happy"] .hop    { animation: hop 1.3s cubic-bezier(.45, 0, .55, 1) infinite; }
  [data-mood="happy"] .shadow { animation: shadow-hop 1.3s cubic-bezier(.45, 0, .55, 1) infinite; }
  @keyframes hop {
    0%, 100% { transform: translateY(0) scale(1.05, .95); }
    15%      { transform: translateY(0) scale(1, 1); }
    45%      { transform: translateY(-9px) scale(.97, 1.04); }
    70%      { transform: translateY(-9px) scale(1, 1); }
    90%      { transform: translateY(0) scale(1, 1); }
  }
  @keyframes shadow-hop {
    0%, 15%, 90%, 100% { transform: scaleX(1);   opacity: 1; }
    45%, 70%           { transform: scaleX(.82); opacity: .6; }
  }

  /* surprised: one-shot jump when the mood switches in */
  .jolting .jolt { animation: jolt .5s cubic-bezier(.3, .7, .4, 1); }
  @keyframes jolt {
    0%   { transform: none; }
    30%  { transform: translateY(-16px) scale(.94, 1.08); }
    60%  { transform: translateY(0) scale(1.07, .93); }
    80%  { transform: scale(.98, 1.02); }
    100% { transform: none; }
  }

  /* poke: squish while held, springy release */
  .squish { transition: transform .5s cubic-bezier(.34, 1.8, .5, 1); }
  .pressed .squish {
    transform: scale(1.1, .86);
    transition: transform .1s ease-out;
  }

  /* giggle: wiggle */
  [data-face="giggle"] .wiggle { animation: wiggle .32s linear infinite; }
  @keyframes wiggle {
    0%, 100% { transform: rotate(0); }
    25%      { transform: rotate(-5deg); }
    75%      { transform: rotate(5deg); }
  }

  /* blink */
  .eyes-blink { transition: transform 70ms ease-in; }
  .blinking .eyes-blink { transform: scaleY(.08); }

  /* sleepy: snore mouth + Zzz */
  [data-face="sleepy"] .mouth-sleepy { animation: snore 5.5s ease-in-out infinite; }
  @keyframes snore {
    0%, 100% { transform: scale(1); }
    50%      { transform: scale(1.5); }
  }
  .zzz { opacity: 0; transition: opacity .4s ease; }
  [data-face="sleepy"] .zzz { opacity: 1; }
  .zzz text { font: 800 16px/1 system-ui, sans-serif; fill: var(--blob-ink); opacity: 0; }
  [data-face="sleepy"] .zzz text { animation: zzz 3.6s ease-in-out infinite; }
  .zzz text:nth-child(2) { animation-delay: 1.2s !important; }
  .zzz text:nth-child(3) { animation-delay: 2.4s !important; }
  @keyframes zzz {
    0%   { opacity: 0;  transform: translate(0, 0) scale(.5); }
    20%  { opacity: .7; }
    100% { opacity: 0;  transform: translate(22px, -40px) scale(1.3); }
  }

  /* giggle words */
  .giggle-text {
    font: 700 15px/1 system-ui, sans-serif;
    fill: var(--blob-ink);
    text-anchor: middle;
    pointer-events: none;
    animation: float-up 1.1s ease-out forwards;
  }
  @keyframes float-up {
    0%   { opacity: 0; transform: translate(0, 6px) scale(.6); }
    20%  { opacity: 1; transform: translate(calc(var(--dx) * .3), -4px) scale(1.1) rotate(var(--rot)); }
    100% { opacity: 0; transform: translate(var(--dx), -30px) scale(1) rotate(var(--rot)); }
  }
  @keyframes fade-out {
    0%, 60% { opacity: 1; }
    100%    { opacity: 0; }
  }

  @media (prefers-reduced-motion: reduce) {
    .breathe, .shadow, .hop, .wiggle, .mouth-sleepy,
    [data-face] .breathe, [data-face] .shadow, [data-face] .hop,
    [data-face] .wiggle, [data-face] .mouth-sleepy,
    .jolting .jolt { animation: none !important; }
    [data-face="sleepy"] .zzz text { animation: none !important; opacity: .7; }
    .zzz text:nth-child(2) { transform: translate(8px, -12px); }
    .zzz text:nth-child(3) { transform: translate(16px, -24px); }
    .giggle-text { animation: fade-out 1.1s ease-out forwards; }
  }
</style>

<svg viewBox="0 0 200 200" data-mood="idle" data-face="idle" aria-hidden="true">
  <defs>
    <radialGradient id="shade" cx="38%" cy="28%" r="80%">
      <stop offset="0"   stop-color="#fff" stop-opacity=".35"/>
      <stop offset=".5"  stop-color="#fff" stop-opacity="0"/>
      <stop offset="1"   stop-color="#000" stop-opacity=".18"/>
    </radialGradient>
  </defs>

  <ellipse class="shadow" cx="100" cy="184" rx="58" ry="7"/>

  <g class="hop"><g class="jolt"><g class="squish"><g class="wiggle"><g class="breathe">
    <path class="body hit" d="${BODY}"/>
    <path class="shade hit" d="${BODY}"/>
    <ellipse class="shine" cx="68" cy="72" rx="13" ry="8" transform="rotate(-32 68 72)"/>

    <g class="face">
      <g class="blush">
        <ellipse cx="62"  cy="126" rx="10" ry="6"/>
        <ellipse cx="138" cy="126" rx="10" ry="6"/>
      </g>

      <g class="brows part f-surprised">
        <path d="M66 83Q78 74 90 83"/>
        <path d="M110 83Q122 74 134 83"/>
      </g>

      <!-- eyes that can blink -->
      <g class="eyes-blink">
        <g class="part f-idle">
          <ellipse class="ink" cx="78"  cy="106" rx="7.5" ry="9.5"/>
          <ellipse class="ink" cx="122" cy="106" rx="7.5" ry="9.5"/>
          <circle class="glint" cx="80.5"  cy="102" r="2.6"/>
          <circle class="glint" cx="124.5" cy="102" r="2.6"/>
        </g>
        <g class="part f-surprised">
          <circle class="white" cx="78"  cy="106" r="11"/>
          <circle class="white" cx="122" cy="106" r="11"/>
          <circle class="ink"   cx="78"  cy="107" r="5.5"/>
          <circle class="ink"   cx="122" cy="107" r="5.5"/>
          <circle class="glint" cx="80"  cy="104.5" r="1.8"/>
          <circle class="glint" cx="124" cy="104.5" r="1.8"/>
        </g>
      </g>

      <!-- eyes that don't blink -->
      <path class="part f-happy line"  d="M69 109Q78 97 87 109M113 109Q122 97 131 109"/>
      <path class="part f-giggle line" d="M71 99L85 106L71 113M129 99L115 106L129 113"/>
      <path class="part f-sleepy line" d="M69 105Q78 113 87 105M113 105Q122 113 131 105"/>

      <!-- mouths -->
      <path class="part f-idle line" d="M91 127Q100 135 109 127"/>
      <g class="part f-happy">
        <path class="ink" d="M86 124Q100 127 114 124Q112 143 100 143Q88 143 86 124Z"/>
        <ellipse class="tongue" cx="100" cy="138" rx="6" ry="3.5"/>
      </g>
      <g class="part f-giggle">
        <path class="ink" d="M82 121Q100 125 118 121Q116 148 100 148Q84 148 82 121Z"/>
        <ellipse class="tongue" cx="100" cy="141" rx="8" ry="4.5"/>
      </g>
      <ellipse class="part f-sleepy ink mouth-sleepy" cx="100" cy="130" rx="3.5" ry="3"/>
      <ellipse class="part f-surprised ink" cx="100" cy="134" rx="7" ry="9"/>
    </g>
  </g></g></g></g></g>

  <g class="zzz">
    <text x="150" y="60">z</text>
    <text x="150" y="60">z</text>
    <text x="150" y="60">Z</text>
  </g>
  <g class="fx"></g>
</svg>
`;

class BlobMascot extends HTMLElement {
  static observedAttributes = ['mood'];

  #svg;
  #fx;
  #timers = new Set();
  #giggleTimer = 0;
  #blinkTimer = 0;
  #giggling = false;
  #pressed = false;

  constructor() {
    super();
    const root = this.attachShadow({ mode: 'open' });
    root.append(template.content.cloneNode(true));
    this.#svg = root.querySelector('svg');
    this.#fx = root.querySelector('.fx');

    for (const hit of root.querySelectorAll('.hit')) {
      hit.addEventListener('pointerdown', this.#onPointerDown);
    }
    this.#svg.addEventListener('pointerup', this.#onPointerUp);
    this.#svg.addEventListener('pointercancel', this.#onPointerCancel);
    this.addEventListener('keydown', this.#onKeyDown);
  }

  get mood() {
    const m = this.getAttribute('mood');
    return MOODS.includes(m) ? m : 'idle';
  }
  set mood(value) {
    this.setAttribute('mood', value);
  }

  connectedCallback() {
    if (!this.hasAttribute('tabindex')) this.tabIndex = 0;
    if (!this.hasAttribute('role')) this.setAttribute('role', 'button');
    this.#render();
    this.#scheduleBlink();
  }

  disconnectedCallback() {
    for (const t of this.#timers) clearTimeout(t);
    this.#timers.clear();
    this.#giggling = false;
    this.#pressed = false;
    this.#svg.classList.remove('pressed', 'blinking', 'jolting');
  }

  attributeChangedCallback(_name, oldValue, newValue) {
    if (oldValue === newValue) return;
    this.#render();
    if (!this.isConnected) return;
    if (this.mood === 'surprised') this.#jolt();
    this.#scheduleBlink();
  }

  /** Make the blob giggle. */
  poke() {
    this.#giggling = true;
    this.#render();
    this.#clear(this.#giggleTimer);
    this.#giggleTimer = this.#later(() => {
      this.#giggling = false;
      this.#render();
    }, 1100);
    this.#spawnGiggle();
    this.dispatchEvent(new CustomEvent('poke', {
      bubbles: true,
      composed: true,
      detail: { mood: this.mood },
    }));
  }

  /** Close and reopen the eyes once. */
  blink() {
    this.#svg.classList.add('blinking');
    this.#later(() => this.#svg.classList.remove('blinking'), 140);
  }

  #render() {
    const mood = this.mood;
    this.#svg.dataset.mood = mood;
    this.#svg.dataset.face = this.#giggling ? 'giggle' : mood;
    this.setAttribute('aria-label', `Mascot, feeling ${mood}. Poke it!`);
  }

  #scheduleBlink() {
    this.#clear(this.#blinkTimer);
    this.#blinkTimer = this.#later(() => {
      // Sleepy eyes are already shut; happy ones are ^ ^ arcs.
      if (this.mood === 'idle' || this.mood === 'surprised') {
        this.blink();
        // Occasional double-blink, like a real face.
        if (Math.random() < 0.2) this.#later(() => this.blink(), 260);
      }
      this.#scheduleBlink();
    }, 2200 + Math.random() * 3800);
  }

  #jolt() {
    this.#svg.classList.remove('jolting');
    void this.#svg.getBoundingClientRect(); // restart the animation
    this.#svg.classList.add('jolting');
    this.#later(() => this.#svg.classList.remove('jolting'), 550);
  }

  #spawnGiggle() {
    while (this.#fx.childElementCount >= 6) this.#fx.firstElementChild.remove();

    const g = document.createElementNS(NS, 'g');
    const x = 55 + Math.random() * 90;
    const y = 30 + Math.random() * 14;
    g.setAttribute('transform', `translate(${x.toFixed(1)} ${y.toFixed(1)})`);

    const text = document.createElementNS(NS, 'text');
    text.setAttribute('class', 'giggle-text');
    text.textContent = GIGGLES[Math.floor(Math.random() * GIGGLES.length)];
    text.style.setProperty('--dx', `${((x - 100) * 0.4).toFixed(1)}px`);
    text.style.setProperty('--rot', `${((Math.random() - 0.5) * 24).toFixed(1)}deg`);

    g.append(text);
    this.#fx.append(g);
    const remove = () => g.remove();
    text.addEventListener('animationend', remove, { once: true });
    this.#later(remove, 1500); // in case animations are disabled
  }

  #onPointerDown = (e) => {
    if (e.button !== 0) return;
    this.#pressed = true;
    this.#svg.setPointerCapture(e.pointerId);
    this.#svg.classList.add('pressed');
  };

  #onPointerUp = () => {
    if (!this.#pressed) return;
    this.#pressed = false;
    this.#svg.classList.remove('pressed');
    this.poke();
  };

  #onPointerCancel = () => {
    this.#pressed = false;
    this.#svg.classList.remove('pressed');
  };

  #onKeyDown = (e) => {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    e.preventDefault();
    if (e.repeat) return;
    this.#svg.classList.add('pressed');
    this.#later(() => {
      this.#svg.classList.remove('pressed');
      this.poke();
    }, 110);
  };

  #later(fn, ms) {
    const id = setTimeout(() => {
      this.#timers.delete(id);
      fn();
    }, ms);
    this.#timers.add(id);
    return id;
  }

  #clear(id) {
    clearTimeout(id);
    this.#timers.delete(id);
  }
}

if (!customElements.get('blob-mascot')) {
  customElements.define('blob-mascot', BlobMascot);
}

export { BlobMascot };
