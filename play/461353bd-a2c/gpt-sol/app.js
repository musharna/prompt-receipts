const canvas = document.querySelector('#toy-canvas');
const ctx = canvas.getContext('2d');
const stage = document.querySelector('#stage');
const bubbleGrid = document.querySelector('#bubble-grid');
const tabs = [...document.querySelectorAll('.toy-tab')];
const resetButton = document.querySelector('.reset-button');
const soundButton = document.querySelector('.sound-toggle');
const numberEl = document.querySelector('.material-number');
const titleEl = document.querySelector('.card-copy h2');
const instructionEl = document.querySelector('.instruction');
const labelEl = document.querySelector('.stage-label');
const countEl = document.querySelector('#counter-value');
const countLabel = document.querySelector('#counter-label');

const toys = {
  wax: { index:'01 / 04', title:'Hardened candle wax', instruction:'Press anywhere. Hold for a deeper crack.', label:'PRESS TO CRACK', count:'cracks made' },
  soap: { index:'02 / 04', title:'Sun-dried soap bar', instruction:'Drag slowly to carve. Tap to crunch a corner.', label:'DRAG TO CARVE', count:'shavings made' },
  slime: { index:'03 / 04', title:'Lavender cloud slime', instruction:'Poke, pull and squish. It always comes back.', label:'POKE & STRETCH', count:'squishes made' },
  bubbles: { index:'04 / 04', title:'A fresh sheet of bubble wrap', instruction:'Tap each bubble—or glide across a whole row.', label:'POP THE BUBBLES', count:'bubbles popped' }
};

let current = 'wax';
let count = 0;
let soundOn = true;
let audio;
let pointer = { down:false, x:0, y:0, start:0 };
let cracks = [];
let crumbs = [];
let soapCuts = [];
let slime = { x:0, y:0, vx:0, vy:0, pullX:0, pullY:0, pulling:false, ripples:[] };

function fitCanvas() {
  const rect = stage.getBoundingClientRect();
  const dpr = Math.min(devicePixelRatio || 1, 2);
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  draw();
}

function audioContext() {
  if (!audio) audio = new (window.AudioContext || window.webkitAudioContext)();
  if (audio.state === 'suspended') audio.resume();
  return audio;
}

function noiseBurst(duration=.08, volume=.08, filter=1500, type='bandpass') {
  if (!soundOn) return;
  const ac = audioContext();
  const length = Math.floor(ac.sampleRate * duration);
  const buffer = ac.createBuffer(1, length, ac.sampleRate);
  const data = buffer.getChannelData(0);
  for (let i=0; i<length; i++) data[i] = (Math.random()*2-1) * Math.pow(1-i/length, 2);
  const src = ac.createBufferSource();
  const filt = ac.createBiquadFilter();
  const gain = ac.createGain();
  filt.type = type; filt.frequency.value = filter; filt.Q.value = 1.5;
  gain.gain.setValueAtTime(volume, ac.currentTime);
  gain.gain.exponentialRampToValueAtTime(.0001, ac.currentTime + duration);
  src.buffer = buffer; src.connect(filt).connect(gain).connect(ac.destination); src.start();
}

function tone(freq=180, duration=.08, volume=.05, slide=.6) {
  if (!soundOn) return;
  const ac = audioContext();
  const osc = ac.createOscillator();
  const gain = ac.createGain();
  osc.type = 'sine'; osc.frequency.setValueAtTime(freq, ac.currentTime); osc.frequency.exponentialRampToValueAtTime(freq*slide, ac.currentTime+duration);
  gain.gain.setValueAtTime(volume, ac.currentTime); gain.gain.exponentialRampToValueAtTime(.0001, ac.currentTime+duration);
  osc.connect(gain).connect(ac.destination); osc.start(); osc.stop(ac.currentTime+duration);
}

function playSound(kind, strength=1) {
  if (kind==='wax') { noiseBurst(.045+.05*strength, .075, 2600); tone(120, .05, .025, .4); }
  if (kind==='soap') { noiseBurst(.035, .045, 4100, 'highpass'); if(Math.random()>.65) tone(520, .025, .015, .7); }
  if (kind==='slime') { tone(105 + Math.random()*35, .16, .06, .55); noiseBurst(.12, .025, 500, 'lowpass'); }
  if (kind==='bubbles') { noiseBurst(.025, .07, 3200); tone(320 + Math.random()*90, .035, .035, .25); }
}

function roundedRect(x,y,w,h,r) {
  ctx.beginPath(); ctx.roundRect(x,y,w,h,r); ctx.closePath();
}

function drawWax(w,h) {
  const sw=Math.min(w*.55, 510), sh=Math.min(h*.62, 315), x=(w-sw)/2, y=(h-sh)/2;
  ctx.save();
  ctx.shadowColor='rgba(89,59,39,.2)'; ctx.shadowBlur=34; ctx.shadowOffsetY=19;
  roundedRect(x,y,sw,sh,10); ctx.fillStyle='#d6aa82'; ctx.fill();
  ctx.shadowColor='transparent';
  const grad=ctx.createLinearGradient(x,y,x+sw,y+sh); grad.addColorStop(0,'#efd5ba'); grad.addColorStop(.55,'#dfbd9d'); grad.addColorStop(1,'#c99a73');
  roundedRect(x,y,sw,sh,10); ctx.fillStyle=grad; ctx.fill();
  ctx.strokeStyle='rgba(119,75,48,.13)'; ctx.lineWidth=1; ctx.stroke();
  ctx.globalAlpha=.25;
  for(let i=0;i<50;i++){ const px=x+Math.random()*sw, py=y+Math.random()*sh; ctx.fillStyle=i%3?'#fff5e8':'#a87655'; ctx.fillRect(px,py,Math.random()*1.5+.3,Math.random()*1.5+.3); }
  ctx.globalAlpha=1;
  cracks.forEach(c=>{
    ctx.strokeStyle=`rgba(100,62,41,${c.alpha})`; ctx.lineWidth=c.width; ctx.lineCap='round'; ctx.lineJoin='round';
    c.lines.forEach(line=>{ctx.beginPath(); line.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y)); ctx.stroke();});
    ctx.fillStyle='rgba(101,64,43,.22)'; ctx.beginPath(); ctx.arc(c.x,c.y,4+c.force*4,0,Math.PI*2); ctx.fill();
  });
  crumbs.forEach(p=>{ctx.fillStyle=p.color; ctx.save();ctx.translate(p.x,p.y);ctx.rotate(p.r);ctx.fillRect(-p.s/2,-p.s/2,p.s,p.s*.65);ctx.restore();});
  ctx.restore();
}

function createCrack(x,y,force) {
  const lines=[]; const branches=5+Math.floor(force*4);
  for(let i=0;i<branches;i++){
    let a=(Math.PI*2/branches)*i+Math.random()*.65, len=22+Math.random()*35+force*28;
    const pts=[{x,y}]; let px=x,py=y;
    for(let j=0;j<4;j++){a+=(Math.random()-.5)*.55;px+=Math.cos(a)*len/4;py+=Math.sin(a)*len/4;pts.push({x:px,y:py});}
    lines.push(pts);
    if(Math.random()>.45){ const p=pts[2], ba=a+(Math.random()>.5?1:-1)*.85; lines.push([p,{x:p.x+Math.cos(ba)*len*.28,y:p.y+Math.sin(ba)*len*.28}]); }
  }
  cracks.push({x,y,lines,alpha:.45+force*.25,width:.75+force*.4,force});
  for(let i=0;i<3+force*6;i++){let a=Math.random()*Math.PI*2,d=8+Math.random()*22;crumbs.push({x:x+Math.cos(a)*d,y:y+Math.sin(a)*d,s:2+Math.random()*4,r:Math.random()*3,color:Math.random()>.5?'#bd8a65':'#e5c4a5'});}
  count++; updateCounter(); playSound('wax',force);
}

function drawSoap(w,h) {
  const sw=Math.min(w*.52,480),sh=Math.min(h*.59,300),x=(w-sw)/2,y=(h-sh)/2;
  ctx.save();ctx.shadowColor='rgba(52,73,42,.18)';ctx.shadowBlur=35;ctx.shadowOffsetY=20;
  roundedRect(x,y,sw,sh,32);ctx.fillStyle='#8ea27e';ctx.fill();ctx.shadowColor='transparent';
  const g=ctx.createLinearGradient(x,y,x+sw,y+sh);g.addColorStop(0,'#ccdabd');g.addColorStop(.55,'#b6c9a8');g.addColorStop(1,'#8fa781');roundedRect(x,y,sw,sh,32);ctx.fillStyle=g;ctx.fill();
  ctx.strokeStyle='rgba(52,82,49,.12)';ctx.lineWidth=2;ctx.stroke();
  ctx.globalAlpha=.17;ctx.strokeStyle='#fff';ctx.lineWidth=1;for(let i=0;i<16;i++){ctx.beginPath();ctx.moveTo(x+20,y+30+i*15);ctx.quadraticCurveTo(x+sw*.5,y+22+i*16,x+sw-20,y+30+i*14);ctx.stroke();}ctx.globalAlpha=1;
  roundedRect(x+sw*.34,y+sh*.38,sw*.32,sh*.24,12);ctx.strokeStyle='rgba(64,91,56,.22)';ctx.stroke();
  ctx.fillStyle='rgba(64,91,56,.34)';ctx.font='500 11px DM Mono';ctx.textAlign='center';ctx.fillText('SLOW',x+sw/2,y+sh*.53);
  soapCuts.forEach(c=>{
    ctx.strokeStyle='rgba(65,88,55,.38)';ctx.lineWidth=c.size;ctx.lineCap='round';ctx.beginPath();c.points.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));ctx.stroke();
    ctx.strokeStyle='rgba(245,250,235,.48)';ctx.lineWidth=Math.max(1,c.size*.35);ctx.translate(0,-1);ctx.stroke();ctx.translate(0,1);
  });
  crumbs.forEach(p=>{ctx.fillStyle=p.color;ctx.beginPath();ctx.ellipse(p.x,p.y,p.s,p.s*.35,p.r,0,Math.PI*2);ctx.fill();});
  ctx.restore();
}

function carveSoap(x,y) {
  let cut=soapCuts.at(-1);
  if(!cut || !pointer.down) return;
  const last=cut.points.at(-1); if(Math.hypot(x-last.x,y-last.y)<7)return;
  cut.points.push({x,y});
  const a=Math.atan2(y-last.y,x-last.x)+Math.PI/2;
  crumbs.push({x:x+Math.cos(a)*(5+Math.random()*10),y:y+Math.sin(a)*(5+Math.random()*10),s:2+Math.random()*5,r:a,color:Math.random()>.4?'#a9bd99':'#d4e0c8'});
  if(cut.points.length%3===0){count++;updateCounter();playSound('soap');}
}

function drawSlime(w,h) {
  const cx=w/2+slime.vx, cy=h/2+slime.vy; const pull=slime.pulling;
  ctx.save();ctx.shadowColor='rgba(81,55,104,.2)';ctx.shadowBlur=35;ctx.shadowOffsetY=18;
  const g=ctx.createRadialGradient(cx-60,cy-70,8,cx,cy,220);g.addColorStop(0,'#e9d9f1');g.addColorStop(.45,'#c6a8d8');g.addColorStop(1,'#9c7db6');
  ctx.beginPath();
  if(pull){
    const a=Math.atan2(slime.pullY-cy,slime.pullX-cx), d=Math.min(210,Math.hypot(slime.pullX-cx,slime.pullY-cy));
    const px=Math.cos(a+Math.PI/2),py=Math.sin(a+Math.PI/2),rx=155,ry=118;
    ctx.moveTo(cx+px*ry,cy+py*ry);ctx.bezierCurveTo(cx+Math.cos(a)*rx,cy+Math.sin(a)*rx,slime.pullX+px*24,slime.pullY+py*24,slime.pullX,slime.pullY);ctx.bezierCurveTo(slime.pullX-px*24,slime.pullY-py*24,cx+Math.cos(a)*rx,cy+Math.sin(a)*rx,cx-px*ry,cy-py*ry);ctx.bezierCurveTo(cx-Math.cos(a)*rx,cy-Math.sin(a)*rx,cx-px*ry,cy-py*ry,cx+px*ry,cy+py*ry);
  } else {
    for(let i=0;i<=24;i++){const a=i/24*Math.PI*2,r=153+Math.sin(a*3+performance.now()*.001)*5+Math.sin(a*5)*4;const x=cx+Math.cos(a)*r,y=cy+Math.sin(a)*r*.76;i?ctx.lineTo(x,y):ctx.moveTo(x,y);}
  }
  ctx.closePath();ctx.fillStyle=g;ctx.fill();ctx.shadowColor='transparent';
  ctx.strokeStyle='rgba(86,54,111,.14)';ctx.lineWidth=2;ctx.stroke();
  ctx.fillStyle='rgba(255,255,255,.32)';ctx.beginPath();ctx.ellipse(cx-55,cy-54,42,15,-.45,0,Math.PI*2);ctx.fill();
  slime.ripples.forEach(r=>{ctx.strokeStyle=`rgba(255,255,255,${r.life*.38})`;ctx.lineWidth=2;ctx.beginPath();ctx.arc(r.x,r.y,(1-r.life)*40+4,0,Math.PI*2);ctx.stroke();r.life-=.025;});
  slime.ripples=slime.ripples.filter(r=>r.life>0);
  ctx.restore();
}

function draw() {
  const {width:w,height:h}=canvas.getBoundingClientRect(); ctx.clearRect(0,0,w,h);
  if(current==='wax') drawWax(w,h);
  if(current==='soap') drawSoap(w,h);
  if(current==='slime') drawSlime(w,h);
}

function animate(){ if(current==='slime'){ if(!slime.pulling){slime.vx*=.88;slime.vy*=.88;} draw(); } requestAnimationFrame(animate); }

function pointFromEvent(e){const r=canvas.getBoundingClientRect();return{x:e.clientX-r.left,y:e.clientY-r.top};}

canvas.addEventListener('pointerdown',e=>{
  const p=pointFromEvent(e);pointer={down:true,x:p.x,y:p.y,start:performance.now()};canvas.setPointerCapture(e.pointerId);stage.classList.add('used');
  if(current==='soap') soapCuts.push({points:[p],size:3+Math.random()*2});
  if(current==='slime'){slime.pulling=true;slime.pullX=p.x;slime.pullY=p.y;slime.ripples.push({...p,life:1});count++;updateCounter();playSound('slime');}
});
canvas.addEventListener('pointermove',e=>{
  if(!pointer.down)return;const p=pointFromEvent(e);
  if(current==='soap')carveSoap(p.x,p.y);
  if(current==='slime'){slime.pullX=p.x;slime.pullY=p.y;}
  pointer.x=p.x;pointer.y=p.y;draw();
});
function release(e){
  if(!pointer.down)return;const p=pointFromEvent(e);const held=Math.min(1.8,(performance.now()-pointer.start)/700);
  if(current==='wax')createCrack(p.x,p.y,.35+held*.65);
  if(current==='soap' && soapCuts.at(-1).points.length===1){ for(let i=0;i<9;i++)crumbs.push({x:p.x+(Math.random()-.5)*45,y:p.y+(Math.random()-.5)*35,s:2+Math.random()*6,r:Math.random()*3,color:'#a9bd99'});count++;updateCounter();playSound('soap');}
  if(current==='slime'){slime.pulling=false;slime.vx=(p.x-canvas.clientWidth/2)*.07;slime.vy=(p.y-canvas.clientHeight/2)*.07;}
  pointer.down=false;draw();
}
canvas.addEventListener('pointerup',release);canvas.addEventListener('pointercancel',release);

function makeBubbles(){
  bubbleGrid.innerHTML='';
  for(let i=0;i<60;i++){const b=document.createElement('button');b.className='bubble';b.type='button';b.setAttribute('aria-label',`Pop bubble ${i+1}`);b.addEventListener('pointerenter',()=>{if(pointer.down)popBubble(b)});b.addEventListener('pointerdown',e=>{pointer.down=true;e.preventDefault();popBubble(b)});b.addEventListener('click',()=>popBubble(b));bubbleGrid.append(b);}
}
function popBubble(b){if(b.classList.contains('popped'))return;b.classList.add('popped');stage.classList.add('used');count++;updateCounter();playSound('bubbles');}
document.addEventListener('pointerup',()=>pointer.down=false);

function updateCounter(){countEl.textContent=count;}
function reset(){count=0;cracks=[];crumbs=[];soapCuts=[];slime={x:0,y:0,vx:0,vy:0,pullX:0,pullY:0,pulling:false,ripples:[]};stage.classList.remove('used');makeBubbles();updateCounter();draw();}
function selectToy(name){
  current=name;const t=toys[name];tabs.forEach(tab=>tab.classList.toggle('active',tab.dataset.toy===name));numberEl.textContent=t.index;titleEl.textContent=t.title;instructionEl.innerHTML=`<span aria-hidden="true">↘</span> ${t.instruction}`;labelEl.textContent=t.label;countLabel.textContent=t.count;canvas.setAttribute('aria-label',`Interactive ${t.title}`);stage.classList.toggle('bubbles',name==='bubbles');reset();
}

tabs.forEach(t=>t.addEventListener('click',()=>selectToy(t.dataset.toy)));
resetButton.addEventListener('click',reset);
soundButton.addEventListener('click',()=>{soundOn=!soundOn;soundButton.setAttribute('aria-pressed',soundOn);soundButton.lastChild.textContent=soundOn?' sound on':' sound off';if(soundOn)tone(260,.08,.025,1.4);});
new ResizeObserver(fitCanvas).observe(stage);
makeBubbles();fitCanvas();animate();
