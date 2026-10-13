const NS = 'http://www.w3.org/2000/svg';

const models = [
  {
    id:'crane', number:'01', name:'Classic crane', difficulty:'Challenge', level:'challenge', time:'12\nMIN', accent:'#ed8b72',
    description:'The club classic. Begin with a bird base, then shape the neck, tail, wings and head.',
    steps:['Begin color-side down. Fold both diagonals, then unfold.','Turn over. Fold in half both ways, then unfold.','Collapse the four corners into a square base.','Petal-fold the front and back into a long diamond.','Inside-reverse fold two points up for the neck and tail.','Reverse-fold the beak, then lower both wings.'],
    frames:[
      `<polygon class="paper-shape" points="130,28 232,130 130,232 28,130"/><path class="fold-line" d="M28 130h204M130 28v204"/><path class="fold-arrow" d="M58 66Q130 105 199 67"/>`,
      `<rect class="paper-shape" x="52" y="52" width="156" height="156"/><path class="fold-line" d="m52 52 156 156M208 52 52 208"/><path class="fold-arrow" d="M44 130q45-55 86-5"/>`,
      `<polygon class="paper-shape" points="130,35 213,118 130,221 47,118"/><path class="paper-detail" d="M47 118h166M130 35v186"/><path class="fold-arrow" d="M68 113q60-42 119 0"/>`,
      `<polygon class="paper-shape" points="130,20 190,130 130,240 70,130"/><path class="paper-detail" d="M70 130h120M130 20v220M70 130l60 38 60-38"/><path class="fold-line" d="M91 130 130 54l39 76"/>`,
      `<path class="paper-shape" d="M36 151 119 87l12 72 17-108 22 116 55 27-74-8-19 51-16-63Z"/><path class="paper-detail" d="m36 151 80 23m15-15 20 27m19-19 55 27"/><path class="fold-arrow" d="M160 106q24-25 45 2"/>`,
      `<path class="paper-shape" d="M25 145 106 91l26 61 31-101 17 108 61 27-84-7-26 57-25-62Z"/><path class="paper-detail" d="m25 145 81 29 26-22 25 27 84 7M163 51l24 17"/>`
    ],
    cp:`<path class="v" d="M20 20l220 220M240 20 20 240M130 20v220M20 130h220"/><path class="m" d="M20 75h220M20 185h220M75 20v220M185 20v220M75 75l110 110M185 75 75 185M75 185l110-110M185 185 75 75"/><path class="v" d="m20 75 55-55m110 0 55 55M20 185l55 55m110 0 55-55"/>`
  },
  {
    id:'frog', number:'02', name:'Jumping frog', difficulty:'Medium', level:'medium', time:'8\nMIN', accent:'#9fcb89', sheet:'rectangle',
    description:'A springy little crowd-pleaser made from a half-sheet rectangle. Press its back and release to make it leap.',
    steps:['Fold the rectangle in half, then reopen.','Crease both top diagonals to make an X.','Pinch the X inward to form a triangle point.','Fold the triangle corners up for front legs.','Fold both long sides toward the center.','Z-fold the lower section to make the springy back legs.'],
    frames:[
      `<rect class="paper-shape" x="75" y="25" width="110" height="210"/><path class="fold-line" d="M75 130h110"/><path class="fold-arrow" d="M205 188q-42-36-18-78"/>`,
      `<rect class="paper-shape" x="75" y="25" width="110" height="210"/><path class="fold-line" d="m75 25 110 105M185 25 75 130"/><path class="fold-arrow" d="M56 74q37-26 59 5"/>`,
      `<path class="paper-shape" d="m75 130 55-105 55 105v105H75Z"/><path class="paper-detail" d="m75 130 55 29 55-29M130 25v134"/>`,
      `<path class="paper-shape" d="m75 130 55-105 55 105v105H75Z"/><path class="paper-detail" d="m75 130 55 29 55-29M130 25v134M75 130l34-34m76 34-34-34"/><path class="fold-arrow" d="M86 113q16-31 35-5"/>`,
      `<path class="paper-shape" d="m95 131 35-106 35 106 20 104H75Z"/><path class="paper-detail" d="m95 131 35 28 35-28M130 25v134M75 235l55-33 55 33"/>`,
      `<path class="paper-shape" d="M50 184 87 151l7-65 36-61 36 61 7 65 37 33-49 5 22 43-53-23-53 23 22-43Z"/><path class="paper-detail" d="m50 184 49 5 31 20 31-20 49-5M94 86l36 28 36-28"/><circle cx="113" cy="105" r="3"/><circle cx="147" cy="105" r="3"/>`
    ],
    cp:`<path class="v" d="M65 130h130M65 75h130M65 185h130M65 20l65 110M195 20l-65 110M65 130l65 110M195 130l-65 110"/><path class="m" d="m65 185 65-55 65 55M97 20v220M163 20v220M97 75l66 110M163 75l-66 110"/>`
  },
  {
    id:'boat', number:'03', name:'Sailboat', difficulty:'Easy', level:'easy', time:'4\nMIN', accent:'#f0c94f',
    description:'A breezy beginner model with one tall sail and a hull that stands on its own.',
    steps:['Fold the square in half diagonally.','Fold the triangle in half and reopen.','Bring the right corner down to shape the sail.','Fold the lower point upward for the hull.','Reverse the little point behind the boat.','Open the base slightly so your sailboat stands.'],
    frames:[
      `<rect class="paper-shape" x="48" y="48" width="164" height="164"/><path class="fold-line" d="m48 212 164-164"/><path class="fold-arrow" d="M69 73q60 6 112 77"/>`,
      `<polygon class="paper-shape" points="48,212 212,48 212,212"/><path class="fold-line" d="M130 130 212 212"/><path class="fold-arrow" d="M200 75q-50 17-45 72"/>`,
      `<path class="paper-shape" d="M48 212 128 50l29 126 55 36Z"/><path class="paper-detail" d="m128 50 29 126 55 36M48 212l109-36"/>`,
      `<path class="paper-shape" d="M48 205 128 42l29 127 55 36-82 20Z"/><path class="paper-detail" d="m128 42 29 127 55 36M48 205l109-36 55 36"/><path class="fold-arrow" d="M105 227q11-34 42-36"/>`,
      `<path class="paper-shape" d="M41 202 128 34l31 134 60 34-25 25H72Z"/><path class="paper-detail" d="M128 34v193m31-59 60 34M41 202l31 25"/>`,
      `<path class="paper-shape" d="M39 198 128 31v167h91l-26 30H70Z"/><path class="paper-detail" d="M128 31v197M39 198h180"/>`
    ],
    cp:`<path class="v" d="M20 20l220 220M240 20 20 240M130 20v220M20 130h220"/><path class="m" d="M20 185h220M75 20l55 110 55-110M20 240l55-55 55 55 55-55 55 55"/>`
  },
  {
    id:'swan', number:'04', name:'Elegant swan', difficulty:'Medium', level:'medium', time:'7\nMIN', accent:'#d5c6e6',
    description:'A graceful model built from a kite fold, with a long neck and a tiny reverse-folded beak.',
    steps:['Fold the square diagonally, then reopen.','Fold two edges inward to make a kite.','Fold the long point upward along the center.','Fold the whole model in half away from you.','Pull the neck upward and flatten its new crease.','Reverse-fold the tip for a head and lower the wings.'],
    frames:[
      `<polygon class="paper-shape" points="130,25 235,130 130,235 25,130"/><path class="fold-line" d="M130 25v210"/><path class="fold-arrow" d="M55 91q36 10 65 46"/>`,
      `<polygon class="paper-shape" points="130,25 182,130 130,235 78,130"/><path class="paper-detail" d="M130 25v210M78 130h104"/><path class="fold-arrow" d="M45 128q38-30 75-3"/>`,
      `<polygon class="paper-shape" points="130,18 182,147 130,235 78,147"/><path class="paper-detail" d="M130 18v217M78 147h104"/><path class="fold-arrow" d="M109 204q-18-48 17-72"/>`,
      `<path class="paper-shape" d="m44 180 86-162 22 137 64 39-88 13Z"/><path class="paper-detail" d="m44 180 84 27 24-52 64 39"/>`,
      `<path class="paper-shape" d="m39 187 92-48 7-112 18 111 69 57-89 17Z"/><path class="paper-detail" d="m39 187 97 25 20-74 69 57"/><path class="fold-arrow" d="M125 99q-30-43 5-70"/>`,
      `<path class="paper-shape" d="m34 185 98-47 8-100 34-20-20 39 5 80 70 58-92 17Z"/><path class="paper-detail" d="m34 185 103 27 22-75 70 58m-89-157 14 19"/>`
    ],
    cp:`<path class="v" d="M20 20l220 220M240 20 20 240M130 20v220M20 130h220M20 75l110 55 110-55M20 185l110-55 110 55"/><path class="m" d="M75 20l55 110 55-110M75 240l55-110 55 110M75 75l110 110M185 75 75 185"/>`
  },
  {
    id:'waterbomb', number:'05', name:'Waterbomb', difficulty:'Easy', level:'easy', time:'6\nMIN', accent:'#77b9d6',
    description:'A clever inflatable cube. Make the base, lock the flaps, then blow gently into the opening.',
    steps:['Fold the square in half both ways, then reopen.','Turn over. Fold both diagonals, then reopen.','Pinch the sides inward to collapse a triangle base.','Fold the lower corners up to meet the top.','Fold side points inward and tuck the flaps into pockets.','Blow gently into the small opening to inflate.'],
    frames:[
      `<rect class="paper-shape" x="45" y="45" width="170" height="170"/><path class="fold-line" d="M45 130h170M130 45v170"/><path class="fold-arrow" d="M65 237q65-44 128 0"/>`,
      `<rect class="paper-shape" x="45" y="45" width="170" height="170"/><path class="fold-line" d="m45 45 170 170M215 45 45 215"/><path class="fold-arrow" d="M32 101q43-28 76 7"/>`,
      `<polygon class="paper-shape" points="130,35 225,210 35,210"/><path class="paper-detail" d="M130 35v175M35 210l95-53 95 53"/>`,
      `<polygon class="paper-shape" points="130,35 225,210 35,210"/><path class="paper-detail" d="M130 35v175M35 210l95-53 95 53M35 210l95-92 95 92"/><path class="fold-arrow" d="M59 196q15-48 57-60"/>`,
      `<polygon class="paper-shape" points="130,38 216,130 130,222 44,130"/><path class="paper-detail" d="m44 130 86 35 86-35M130 38v184"/><path class="fold-arrow" d="M74 122q23-29 51-5"/>`,
      `<path class="paper-shape" d="M58 85 130 42l72 43 18 104-90 32-90-32Z"/><path class="paper-detail" d="M58 85l72 41 72-41m-72 41v95M40 189l90-63 90 63"/><path class="fold-arrow" d="M130 244v-31"/>`
    ],
    cp:`<path class="v" d="M20 20l220 220M240 20 20 240M130 20v220M20 130h220M20 75h220M20 185h220M75 20v220M185 20v220"/><path class="m" d="M20 75l55-55 55 55 55-55 55 55M20 185l55 55 55-55 55 55 55-55M75 75l110 110M185 75 75 185"/>`
  }
];

const template = document.querySelector('#modelTemplate');
const list = document.querySelector('#modelList');
const players = new Map();

function svgShell(content, label='Folding diagram') {
  return `<svg viewBox="0 0 260 260" role="img" aria-label="${label}"><defs><marker id="arrowhead" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0 0 6 3 0 6" fill="none" stroke="#ed6a52" stroke-width="1.5"/></marker></defs><g class="diagram">${content}</g></svg>`;
}

function patternSvg(model) {
  const sheet = model.sheet === 'rectangle' ? '<rect class="sheet" x="65" y="20" width="130" height="220"/>' : '<rect class="sheet" x="20" y="20" width="220" height="220"/>';
  return `<svg viewBox="0 0 260 260" role="img" aria-label="${model.name} crease pattern">${sheet}${model.cp}<circle cx="130" cy="130" r="2.5"/></svg>`;
}

function updatePlayer(model, card, state, animate=true) {
  const stage = card.querySelector('.stage');
  if (!animate) stage.style.setProperty('--no-animation', '1');
  stage.innerHTML = svgShell(model.frames[state.step], `${model.name}, step ${state.step + 1}`);
  card.querySelector('.step-count').textContent = `${String(state.step + 1).padStart(2,'0')} / ${String(model.steps.length).padStart(2,'0')}`;
  card.querySelector('.instruction').textContent = model.steps[state.step];
  card.querySelectorAll('.progress i').forEach((dot, i) => dot.classList.toggle('done', i <= state.step));
}

function stop(model, card, state) {
  clearInterval(state.timer); state.timer = null;
  card.querySelector('.play-button').classList.remove('playing');
  card.querySelector('.play-icon').textContent = '▶';
  card.querySelector('.play-label').textContent = state.step === model.steps.length - 1 ? 'Replay fold' : 'Watch fold';
}

models.forEach(model => {
  const card = template.content.firstElementChild.cloneNode(true);
  card.id = model.id; card.dataset.level = model.level; card.style.setProperty('--accent', model.accent);
  card.querySelector('.card-index').textContent = `${model.number} / ${model.id.toUpperCase()}`;
  card.querySelector('h3').textContent = model.name;
  card.querySelector('.difficulty').textContent = `${model.difficulty} model`;
  card.querySelector('.time').innerHTML = model.time.replace('\n','<br>');
  card.querySelector('.description').textContent = model.description;
  card.querySelector('.pattern').innerHTML = patternSvg(model);
  card.querySelector('.progress').innerHTML = model.steps.map(() => '<i></i>').join('');
  const state = {step:0, timer:null}; players.set(model.id, state);
  updatePlayer(model, card, state);
  card.querySelector('.previous').addEventListener('click', () => { stop(model,card,state); state.step = (state.step - 1 + model.steps.length) % model.steps.length; updatePlayer(model,card,state); });
  card.querySelector('.next').addEventListener('click', () => { stop(model,card,state); state.step = (state.step + 1) % model.steps.length; updatePlayer(model,card,state); });
  card.querySelector('.play-button').addEventListener('click', () => {
    if (state.timer) return stop(model,card,state);
    if (state.step === model.steps.length - 1) { state.step = 0; updatePlayer(model,card,state); }
    const button = card.querySelector('.play-button'); button.classList.add('playing'); button.querySelector('.play-icon').textContent = 'Ⅱ'; button.querySelector('.play-label').textContent = 'Pause';
    state.timer = setInterval(() => {
      if (state.step >= model.steps.length - 1) return stop(model,card,state);
      state.step++; updatePlayer(model,card,state);
    }, 1700);
  });
  card.querySelector('.download-button').addEventListener('click', () => downloadPattern(model));
  list.appendChild(card);
});

document.querySelectorAll('.filter').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('.filter').forEach(b => b.classList.toggle('active', b === button));
  document.querySelectorAll('.model-card').forEach(card => card.hidden = button.dataset.filter !== 'all' && card.dataset.level !== button.dataset.filter);
}));

function downloadPattern(model) {
  const style = `<style>.sheet{fill:white;stroke:#173c35;stroke-width:2}.v{stroke:#327ba8;stroke-width:1.35;stroke-dasharray:6 5;fill:none}.m{stroke:#ed6a52;stroke-width:1.35;stroke-dasharray:9 3 2 3;fill:none}circle{fill:#173c35}</style>`;
  const sheet = model.sheet === 'rectangle' ? '<rect class="sheet" x="65" y="20" width="130" height="220"/>' : '<rect class="sheet" x="20" y="20" width="220" height="220"/>';
  const source = `<svg xmlns="${NS}" viewBox="0 0 260 260">${style}${sheet}${model.cp}<circle cx="130" cy="130" r="2.5"/></svg>`;
  const blob = new Blob([source], {type:'image/svg+xml'}); const url = URL.createObjectURL(blob); const a = document.createElement('a');
  a.href = url; a.download = `fold-lab-${model.id}-crease-pattern.svg`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}

document.querySelector('#printAll').addEventListener('click', () => window.print());
