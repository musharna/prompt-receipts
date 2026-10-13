const canvas = document.getElementById('crystalCanvas');
const ctx = canvas.getContext('2d');
const viewport = document.getElementById('viewport');

const palettes = {
  quartz: { title:'Clear Quartz', sub:'Prismatic Cluster', culture:'QR-031 / GHOST GLASS', base:[190,214,207], edge:[238,250,246], glow:[170,215,208], sides:6 },
  amethyst: { title:'Amethyst', sub:'Geode Cluster', culture:'AM-024 / DREAM VIOLET', base:[101,51,128], edge:[221,185,238], glow:[165,109,199], sides:6 },
  citrine: { title:'Citrine', sub:'Sunstone Cluster', culture:'CT-018 / SOLAR HONEY', base:[191,112,28], edge:[255,222,135], glow:[236,165,59], sides:6 },
  fluorite: { title:'Fluorite', sub:'Cubic Matrix', culture:'FL-009 / DEEP MINT', base:[45,119,110], edge:[166,231,207], glow:[83,181,164], sides:4 }
};

const state = {
  mineral:'amethyst', yaw:-.48, pitch:.12, zoom:1, dragging:false, auto:true, paused:false,
  day:18.28, rate:1.2, temperature:42, saturation:78, last:performance.now(), crystals:[]
};

let seed = 84217;
function random(){ seed = (seed * 16807) % 2147483647; return (seed-1)/2147483646; }
function mix(a,b,t){ return a+(b-a)*t; }
function clamp(v,a,b){ return Math.max(a,Math.min(b,v)); }
function rgb(c,a=1){ return `rgba(${c[0]|0},${c[1]|0},${c[2]|0},${a})`; }

function createCluster(){
  seed = 84217 + Object.keys(palettes).indexOf(state.mineral)*919;
  state.crystals=[];
  const fluorite=state.mineral==='fluorite';
  const count=fluorite?25:36;
  for(let i=0;i<count;i++){
    const a=random()*Math.PI*2, radius=Math.pow(random(),.62)*1.7;
    const outer=radius/1.7;
    state.crystals.push({
      x:Math.cos(a)*radius, z:Math.sin(a)*radius*.72,
      y:-.18+random()*.18,
      h:(fluorite?.5:1.0)+random()*(fluorite?1.25:2.55)*(1-outer*.34),
      r:(fluorite?.22:.13)+random()*(fluorite?.26:.22),
      tiltX:(random()-.5)*(fluorite?.15:.34), tiltZ:(random()-.5)*(fluorite?.15:.34),
      rot:random()*Math.PI*2, age:.35+random()*.65, facets:fluorite?4:6,
      variant:random()
    });
  }
  state.crystals.sort((a,b)=>a.h-b.h);
  document.getElementById('facetCount').textContent = String(state.crystals.reduce((n,c)=>n+c.facets+ (fluorite?2:c.facets),0));
}

function rotate(p,c){
  let x=p.x, y=p.y, z=p.z;
  const tx=c.tiltX, tz=c.tiltZ;
  let yy=y*Math.cos(tx)-z*Math.sin(tx), zz=y*Math.sin(tx)+z*Math.cos(tx); y=yy;z=zz;
  let xx=x*Math.cos(tz)-y*Math.sin(tz); yy=x*Math.sin(tz)+y*Math.cos(tz); x=xx;y=yy;
  xx=x*Math.cos(c.rot)-z*Math.sin(c.rot); zz=x*Math.sin(c.rot)+z*Math.cos(c.rot);
  return {x:xx+c.x,y:y+c.y,z:zz+c.z};
}
function camera(p){
  const cy=Math.cos(state.yaw),sy=Math.sin(state.yaw),cp=Math.cos(state.pitch),sp=Math.sin(state.pitch);
  let x=p.x*cy-p.z*sy, z=p.x*sy+p.z*cy;
  let y=p.y*cp-z*sp; z=p.y*sp+z*cp;
  return {x,y,z};
}
function project(p,w,h){
  const z=6.7-p.z, f=Math.min(w,h)*1.18*state.zoom;
  return {x:w*.53+p.x*f/z,y:h*.62-p.y*f/z,z:p.z,s:f/z};
}
function normal(a,b,c){
  const u={x:b.x-a.x,y:b.y-a.y,z:b.z-a.z},v={x:c.x-a.x,y:c.y-a.y,z:c.z-a.z};
  const n={x:u.y*v.z-u.z*v.y,y:u.z*v.x-u.x*v.z,z:u.x*v.y-u.y*v.x};
  const l=Math.hypot(n.x,n.y,n.z)||1; return {x:n.x/l,y:n.y/l,z:n.z/l};
}

function crystalFaces(c,growth){
  const sides=c.facets, p=palettes[state.mineral], h=c.h*growth, r=c.r*(.72+.28*growth);
  const faces=[];
  if(sides===4){
    const levels=[-h*.18,h*.7], rings=[];
    levels.forEach(y=>{ const ring=[]; for(let i=0;i<4;i++){const a=Math.PI/4+i*Math.PI/2;ring.push(rotate({x:Math.cos(a)*r,y,z:Math.sin(a)*r},c));}rings.push(ring); });
    for(let i=0;i<4;i++) faces.push({pts:[rings[0][i],rings[0][(i+1)%4],rings[1][(i+1)%4],rings[1][i]],type:'side',v:i});
    faces.push({pts:rings[1],type:'cap',v:2});
  } else {
    const base=[], shoulder=[], tip=rotate({x:0,y:h,z:0},c);
    for(let i=0;i<sides;i++){
      const a=i/sides*Math.PI*2;
      base.push(rotate({x:Math.cos(a)*r,y:0,z:Math.sin(a)*r},c));
      shoulder.push(rotate({x:Math.cos(a)*r*.97,y:h*.72,z:Math.sin(a)*r*.97},c));
    }
    for(let i=0;i<sides;i++){
      const n=(i+1)%sides;
      faces.push({pts:[base[i],base[n],shoulder[n],shoulder[i]],type:'side',v:i});
      faces.push({pts:[shoulder[i],shoulder[n],tip],type:'tip',v:i});
    }
  }
  return faces;
}

function draw(now){
  const rect=viewport.getBoundingClientRect(), dpr=Math.min(devicePixelRatio,2);
  if(canvas.width!==Math.floor(rect.width*dpr)||canvas.height!==Math.floor(rect.height*dpr)){
    canvas.width=Math.floor(rect.width*dpr);canvas.height=Math.floor(rect.height*dpr);
  }
  ctx.setTransform(dpr,0,0,dpr,0,0); const w=rect.width,h=rect.height;
  const dt=Math.min((now-state.last)/1000,.05);state.last=now;
  if(!state.paused){ state.day+=dt*.025*state.rate; if(state.auto)state.yaw+=dt*.055; }
  ctx.clearRect(0,0,w,h);
  const bg=ctx.createRadialGradient(w*.56,h*.48,10,w*.56,h*.5,Math.max(w,h)*.72);
  bg.addColorStop(0,'#f1f2ed');bg.addColorStop(.55,'#e3e6df');bg.addColorStop(1,'#cfd4cc');ctx.fillStyle=bg;ctx.fillRect(0,0,w,h);
  // laboratory grid and halo
  ctx.save();ctx.globalAlpha=.18;ctx.strokeStyle='#7a857e';ctx.lineWidth=.5;
  for(let x=20;x<w;x+=42){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();}
  for(let y=20;y<h;y+=42){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}ctx.restore();
  const halo=ctx.createRadialGradient(w*.53,h*.58,0,w*.53,h*.58,Math.min(w,h)*.38);halo.addColorStop(0,rgb(palettes[state.mineral].glow,.18));halo.addColorStop(1,rgb(palettes[state.mineral].glow,0));ctx.fillStyle=halo;ctx.fillRect(0,0,w,h);

  // matrix stone beneath cluster
  const ground=[]; for(let i=0;i<20;i++){const a=i/20*Math.PI*2,rr=1.42+Math.sin(i*5.7)*.18;ground.push(project(camera({x:Math.cos(a)*rr,y:-.21,z:Math.sin(a)*rr*.67}),w,h));}
  ctx.beginPath();ground.forEach((q,i)=>i?ctx.lineTo(q.x,q.y):ctx.moveTo(q.x,q.y));ctx.closePath();
  const stone=ctx.createLinearGradient(0,h*.55,0,h*.82);stone.addColorStop(0,'#b9bcb4');stone.addColorStop(1,'#686f68');ctx.fillStyle=stone;ctx.fill();ctx.strokeStyle='rgba(48,56,51,.34)';ctx.stroke();

  const age=clamp(state.day/40,0,1), faces=[];
  for(const c of state.crystals){
    const g=clamp((age-(1-c.age)*.56)/(.44+c.age*.3),.02,1);
    for(const face of crystalFaces(c,g)){
      const cam=face.pts.map(camera), n=normal(cam[0],cam[1],cam[2]);
      if(n.z < -.05) continue;
      const pts=cam.map(v=>project(v,w,h));
      faces.push({...face,pts,n,depth:cam.reduce((s,v)=>s+v.z,0)/cam.length,variant:c.variant});
    }
  }
  faces.sort((a,b)=>a.depth-b.depth);
  const pal=palettes[state.mineral];
  ctx.lineJoin='round';
  for(const f of faces){
    const light=clamp(.46+f.n.x*-.28+f.n.y*.33+f.n.z*.12,0,1);
    const typeLift=f.type==='tip'?.18:f.type==='cap'?.11:0;
    const shimmer=Math.sin(f.v*2.1+state.yaw*2+f.variant*8)*.07;
    const t=clamp(light+typeLift+shimmer,0,1);
    const col=pal.base.map((v,i)=>mix(v,pal.edge[i],t));
    ctx.beginPath();f.pts.forEach((q,i)=>i?ctx.lineTo(q.x,q.y):ctx.moveTo(q.x,q.y));ctx.closePath();
    const grad=ctx.createLinearGradient(f.pts[0].x,f.pts[0].y,f.pts[f.pts.length-1].x,f.pts[f.pts.length-1].y);
    grad.addColorStop(0,rgb(col,.88));grad.addColorStop(.55,rgb(col.map(v=>v*1.07),.8));grad.addColorStop(1,rgb(pal.base,.9));
    ctx.fillStyle=grad;ctx.fill();ctx.strokeStyle=rgb(pal.edge,.44);ctx.lineWidth=.7;ctx.stroke();
    if(f.type!=='side'){
      ctx.save();ctx.globalCompositeOperation='screen';ctx.fillStyle=rgb(pal.edge,.08+t*.12);ctx.fill();ctx.restore();
    }
  }
  // foreground edge glow
  ctx.save();ctx.globalCompositeOperation='screen';ctx.filter='blur(16px)';ctx.fillStyle=rgb(pal.glow,.12);ctx.beginPath();ctx.ellipse(w*.53,h*.62,Math.min(w,h)*.18,Math.min(w,h)*.1,0,0,Math.PI*2);ctx.fill();ctx.restore();
  updateTelemetry();
  requestAnimationFrame(draw);
}

function updateTelemetry(){
  const day=Math.floor(state.day), secs=Math.floor((state.day-day)*86400), hh=String(Math.floor(secs/3600)).padStart(2,'0'), mm=String(Math.floor(secs%3600/60)).padStart(2,'0'), ss=String(secs%60).padStart(2,'0');
  document.getElementById('dayCount').textContent=`DAY ${day}`;document.getElementById('timeCount').textContent=`${hh}:${mm}:${ss}`;
  document.getElementById('timeProgress').style.width=`${clamp(state.day/40*100,0,100)}%`;
  document.getElementById('heightLabel').textContent=`${(32+state.day*2.8).toFixed(1)} mm`;
  document.getElementById('growthLabel').textContent=`+${(1.6+state.rate*1.8).toFixed(1)} mm / day`;
  document.getElementById('pressure').textContent=`${(1+state.temperature/1000).toFixed(2)} ATM`;
  document.getElementById('ph').textContent=(7.6-state.saturation/100).toFixed(2);
}

function updateRange(el){ const pct=(el.value-el.min)/(el.max-el.min)*100;el.style.setProperty('--pct',`${pct}%`); }
['temperature','saturation','growthRate'].forEach(id=>{const el=document.getElementById(id);updateRange(el);el.addEventListener('input',()=>{updateRange(el);if(id==='temperature'){state.temperature=+el.value;document.getElementById('tempOut').textContent=`${el.value}°C`;}if(id==='saturation'){state.saturation=+el.value;document.getElementById('satOut').textContent=`${el.value}%`;}if(id==='growthRate'){state.rate=+el.value/10;document.getElementById('rateOut').textContent=`${state.rate.toFixed(1)}×`;}});});

document.getElementById('mineralGrid').addEventListener('click',e=>{const b=e.target.closest('.mineral');if(!b)return;document.querySelectorAll('.mineral').forEach(x=>x.classList.remove('active'));b.classList.add('active');state.mineral=b.dataset.mineral;const p=palettes[state.mineral];document.getElementById('mineralTitle').innerHTML=`${p.title}<br><i>${p.sub}</i>`;document.getElementById('cultureName').textContent=p.culture;createCluster();});
document.getElementById('pauseButton').addEventListener('click',e=>{state.paused=!state.paused;const b=e.currentTarget;b.classList.toggle('paused',state.paused);b.querySelector('b').textContent=state.paused?'RESUME GROWTH':'PAUSE GROWTH';});
document.getElementById('resetButton').addEventListener('click',()=>{state.day=.1;createCluster();});
document.getElementById('autoRotate').addEventListener('click',e=>{state.auto=!state.auto;e.currentTarget.classList.toggle('active',state.auto);});
document.getElementById('fullButton').addEventListener('click',()=>document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen());
document.getElementById('snapshot').addEventListener('click',()=>{const link=document.createElement('a');link.download=`lithic-${state.mineral}-day-${Math.floor(state.day)}.png`;link.href=canvas.toDataURL('image/png');link.click();});

let lastX=0,lastY=0;
viewport.addEventListener('pointerdown',e=>{if(e.target.closest('button'))return;state.dragging=true;state.auto=false;document.getElementById('autoRotate').classList.remove('active');lastX=e.clientX;lastY=e.clientY;viewport.setPointerCapture(e.pointerId);viewport.classList.add('dragging');});
viewport.addEventListener('pointermove',e=>{if(!state.dragging)return;state.yaw+=(e.clientX-lastX)*.008;state.pitch=clamp(state.pitch+(e.clientY-lastY)*.006,-.55,.6);lastX=e.clientX;lastY=e.clientY;});
viewport.addEventListener('pointerup',()=>{state.dragging=false;viewport.classList.remove('dragging');});
viewport.addEventListener('wheel',e=>{e.preventDefault();state.zoom=clamp(state.zoom-e.deltaY*.0008,.65,1.55);},{passive:false});

// Tiny generated ambient tone; remains off until the user asks for it.
let audioCtx,osc,gain;
document.getElementById('soundButton').addEventListener('click',e=>{if(!audioCtx){audioCtx=new AudioContext();osc=audioCtx.createOscillator();gain=audioCtx.createGain();osc.type='sine';osc.frequency.value=84;gain.gain.value=.018;osc.connect(gain).connect(audioCtx.destination);osc.start();e.currentTarget.style.background='white';}else{const on=gain.gain.value>.001;gain.gain.setTargetAtTime(on?0:.018,audioCtx.currentTime,.15);e.currentTarget.style.background=on?'':'white';}});

createCluster();requestAnimationFrame(draw);
