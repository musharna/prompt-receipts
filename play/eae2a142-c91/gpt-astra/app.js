(() => {
  const $ = (id) => document.getElementById(id);
  const isPet = new URLSearchParams(location.search).has('pet');
  const defaults = { color: 'peach', pace: 2, autoNap: true, napDelay: 30 };
  let settings = { ...defaults };
  try { settings = { ...defaults, ...JSON.parse(localStorage.getItem('miso-settings') || '{}') }; } catch {}
  const colors = {
    peach: ['#f3b39c', '#ec9989', '#f9cbb2', '#df897d'],
    rose: ['#e2a7b6', '#ca879e', '#f4c9cf', '#bf7794'],
    sage: ['#becaa6', '#9aaa8b', '#dce2c3', '#899d7e'],
    lavender: ['#c3b6db', '#a396c1', '#e1d3ee', '#a087b7'],
    cloud: ['#dad9ce', '#b7b8ad', '#f1eee0', '#aeb4ac']
  };
  const stage = $('pet-stage');
  if (isPet) { document.body.classList.add('desktop-pet-mode'); document.body.append(stage); }
  let sleeping = false, manualSleep = false, paused = false, lastActivity = Date.now();
  let x = 38, direction = 1, lastFrame = 0, bubbleTimer, toastTimer, loveTimer, snackTimer;
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  function paintSettings() {
    if (!colors[settings.color]) settings.color = 'peach';
    ['body', 'dark', 'light', 'gill'].forEach((key, i) => document.documentElement.style.setProperty('--pet-' + key, colors[settings.color][i]));
    document.querySelectorAll('.swatch').forEach(b => { const selected = b.dataset.color === settings.color; b.classList.toggle('selected', selected); b.setAttribute('aria-pressed', selected); });
    $('color-name').textContent = settings.color[0].toUpperCase() + settings.color.slice(1);
    $('pace').value = settings.pace;
    $('pace').style.background = `linear-gradient(to right,#b4bc9e ${(settings.pace - 1) * 25}%,#e9e9df ${(settings.pace - 1) * 25}%)`;
    $('pace-label').textContent = ['Nice and slow', 'Easy does it', 'Feeling curious', 'Places to be', 'Tiny adventurer'][settings.pace - 1];
    $('nap-toggle').classList.toggle('on', settings.autoNap);
    $('nap-toggle').setAttribute('aria-checked', settings.autoNap);
    $('nap-delay').value = settings.napDelay;
    $('nap-delay').disabled = !settings.autoNap;
  }
  function save() {
    try { localStorage.setItem('miso-settings', JSON.stringify(settings)); } catch {}
    window.miso?.setSettings(settings);
    paintSettings();
  }
  function say(message, duration = 2800) {
    clearTimeout(bubbleTimer); $('pet-bubble').textContent = message; $('pet-bubble').style.opacity = 1;
    bubbleTimer = setTimeout(() => $('pet-bubble').style.opacity = 0, duration);
  }
  function toast(message) { clearTimeout(toastTimer); $('toast').textContent = message; $('toast').classList.add('visible'); toastTimer = setTimeout(() => $('toast').classList.remove('visible'), 3500); }
  function renderState() {
    stage.classList.toggle('sleeping', sleeping);
    $('pet').classList.toggle('walking', !sleeping && !paused && !reducedMotion);
    $('status-text').textContent = sleeping ? 'Dreaming of little things' : paused ? 'Happily staying close' : 'Happily wandering';
    $('sleep-button').innerHTML = `<svg class="icon"><use href="#i-${sleeping ? 'sun' : 'moon'}"/></svg>${sleeping ? 'Rise and shine' : 'Time for a nap'}`;
    $('pause-button').innerHTML = `<span class="pause-icon">${paused ? '▷' : 'Ⅱ'}</span>${paused ? 'Off you wander' : 'Stay a while'}`;
    $('pause-button').setAttribute('aria-pressed', paused);
    $('sleep-button').setAttribute('aria-pressed', sleeping);
  }
  function sleep(value, manual = false) {
    sleeping = value; manualSleep = value && manual;
    if (!value) lastActivity = Date.now();
    renderState();
    say(value ? 'a little rest…' : 'hello again.');
  }
  function petMiso() {
    if (sleeping) sleep(false);
    clearTimeout(loveTimer); stage.classList.remove('loved'); void stage.offsetWidth; stage.classList.add('loved');
    say(['you’re my favorite.', 'oh, hi there.', 'a little company ♡', 'happy to be here.'][Math.floor(Math.random() * 4)]);
    loveTimer = setTimeout(() => stage.classList.remove('loved'), 1600);
  }
  function snack() {
    sleep(false); say('a snack? for me? ♡', 3500); stage.classList.add('loved');
    clearTimeout(snackTimer); snackTimer = setTimeout(() => { stage.classList.remove('loved'); say('that was lovely.'); }, 3600);
  }
  document.querySelectorAll('.swatch').forEach(b => b.addEventListener('click', () => { settings.color = b.dataset.color; save(); }));
  $('pace').addEventListener('input', e => { settings.pace = Number(e.target.value); save(); });
  $('nap-toggle').addEventListener('click', () => { settings.autoNap = !settings.autoNap; if (!settings.autoNap && sleeping && !manualSleep) sleep(false); save(); });
  $('nap-delay').addEventListener('change', e => { settings.napDelay = Number(e.target.value); lastActivity = Date.now(); save(); });
  $('pet').addEventListener('click', () => { petMiso(); window.miso?.action('pet'); });
  $('treat-button').addEventListener('click', () => { snack(); window.miso?.action('snack'); });
  $('sleep-button').addEventListener('click', () => { sleep(!sleeping, true); window.miso?.action(sleeping ? 'sleep' : 'wake'); });
  $('pause-button').addEventListener('click', () => { paused = !paused; renderState(); say(paused ? 'right here with you.' : 'a little exploring.'); window.miso?.action(paused ? 'pause' : 'wander'); });
  function activity() { lastActivity = Date.now(); if (sleeping && !manualSleep && !isPet) sleep(false); }
  document.addEventListener('pointermove', activity, { passive: true });
  document.addEventListener('keydown', activity);
  function tick(now) {
    const delta = Math.min((now - lastFrame) / 1000 || 0, .05); lastFrame = now;
    if (!isPet) {
      if (settings.autoNap && !sleeping && Date.now() - lastActivity > settings.napDelay * 1000) sleep(true);
      if (!sleeping && !paused && !reducedMotion) {
        const max = Math.max(0, $('scene').clientWidth - stage.clientWidth);
        x += direction * delta * (3 + settings.pace * 3);
        if (x >= max) { x = max; direction = -1; } else if (x <= 0) { x = 0; direction = 1; }
        stage.style.left = x + 'px';
        $('pet').querySelector('svg').style.transform = direction < 0 ? 'scaleX(-1)' : '';
      }
    }
    requestAnimationFrame(tick);
  }
  const dialog = $('info-dialog');
  $('about-button').addEventListener('click', () => {
    $('dialog-content').innerHTML = '<h2>A small friend named Miso.</h2><p>Miso is an axolotl with a very simple schedule: a little exploring, a little snacking, and plenty of rest.</p><p>Click your little friend for a moment of affection. Leave your mouse alone and Miso will drift off. Move it again, and your buddy wakes up with you.</p><p class="dialog-note">Your preferences stay on this computer. No account, no notifications, no pressure.</p>';
    dialog.showModal();
  });
  $('adopt-button').addEventListener('click', async () => {
    if (window.miso) { await window.miso.adopt(); toast('Miso is making a home on your desktop.'); return; }
    $('dialog-content').innerHTML = '<h2>A little home on your desktop.</h2><p>You’re trying Miso in a browser. To let your friend wander above your real taskbar, run the included desktop app from this project folder:</p><pre>npm install\nnpm start</pre><p class="dialog-note">Requires Node.js and a graphical desktop. Then click “Bring Miso to my desktop” in the app. Right-click your desktop Miso to open settings or say goodbye.</p>';
    dialog.showModal();
  });
  document.querySelector('.dialog-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', e => { if (e.target === dialog) { const rect = dialog.getBoundingClientRect(); if (e.clientX < rect.left || e.clientX > rect.right || e.clientY < rect.top || e.clientY > rect.bottom) dialog.close(); } });
  if (window.miso) {
    window.miso.onSettings(value => { settings = { ...defaults, ...value }; paintSettings(); });
    window.miso.onState(state => {
      if (!isPet) return;
      const changed = sleeping !== state.sleeping;
      sleeping = state.sleeping; paused = state.paused;
      $('pet').querySelector('svg').style.transform = state.direction < 0 ? 'scaleX(-1)' : '';
      renderState(); if (changed) say(sleeping ? 'a little rest…' : 'hello again.');
    });
    window.miso.onAction(action => { if (!isPet) return; if (action === 'snack') snack(); if (action === 'pet') petMiso(); });
    window.miso.getSettings().then(value => { settings = { ...defaults, ...value }; paintSettings(); });
    if (isPet) {
      document.addEventListener('contextmenu', e => { e.preventDefault(); window.miso.menu(); });
      document.addEventListener('pointerdown', () => window.miso.action('wake'));
    }
  }
  function updateClock() { $('taskbar-time').innerHTML = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + '<span>a good day to go slow</span>'; }
  updateClock(); setInterval(updateClock, 60000);
  paintSettings(); renderState(); say('oh, hi there.', 5000);
  x = isPet ? 0 : $('scene').clientWidth * .39;
  requestAnimationFrame(tick);
})();
