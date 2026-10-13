const fs=require('fs');const html=fs.readFileSync(__dirname+'/../origami.html','utf8');
const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]);
let calls=0;const ctx=new Proxy({}, {get:(t,k)=>k==='canvas'?{}:(...a)=>{calls++}, set:()=>true});
const els={};const mk=id=>els[id]||(els[id]={id,style:{},dataset:{},classList:{toggle(){}},setAttribute(){},addEventListener(){},getContext:()=>ctx,width:760,height:760,set innerHTML(v){this._h=v},get innerHTML(){return this._h},textContent:'',value:0});
const window={};global.window=window;global.document={getElementById:mk,querySelectorAll:()=>[]};global.requestAnimationFrame=()=>{};
for(const s of scripts)(0,eval)(s);
const A=window.__origami;
for(const k of ['crane','frog','sailboat','swan','waterbomb']){A.load(k);const M=A.BUILT[k];
 const svg=A.cpSVG(k,300);
 // draw every step at several progress values
 for(let i=0;i<M.timeline.length;i++)for(const t of [0,.3,.6,1]){const fr=window.Origami.frame(M,i,t);for(const f of fr.faces)for(const q of f.p)if(q.some(v=>!isFinite(v)))throw new Error('NaN '+k+i)}
 console.log(k,'steps',M.timeline.length,'creases',(svg.match(/<line/g)||[]).length,'draw calls ok');}
els.cv.width=760;A.draw();console.log('canvas calls',calls);
