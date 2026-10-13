// ascii.js model name stepIndex  -> crude top-down view (topmost face colour: '#' colored(back) '.' white(top))
const O=require('./engine.js');const mods=Object.assign({},require('./m_simple.js'),require('./m_crane.js'));
const M=O.build(mods[process.argv[2]]);const si=+process.argv[3];const fs=M.timeline[si].endFaces;
const xs=fs.flatMap(f=>f.p.map(q=>q[0])),ys=fs.flatMap(f=>f.p.map(q=>q[1]));
const x0=Math.min(...xs)-.02,x1=Math.max(...xs)+.02,y0=Math.min(...ys)-.02,y1=Math.max(...ys)+.02;const W=60,H=Math.round(W*(y1-y0)/(x1-x0)*.5);
const inside=(p,pt)=>{let c=false;for(let i=0,j=p.length-1;i<p.length;j=i++){if((p[i][1]>pt[1])!=(p[j][1]>pt[1])&&pt[0]<(p[j][0]-p[i][0])*(pt[1]-p[i][1])/(p[j][1]-p[i][1])+p[i][0])c=!c}return c};
const sorted=fs.map(f=>({f,i:O.info(f)})).sort((a,b)=>a.i.cz-b.i.cz);
let out='';for(let r=0;r<H;r++){let line='';for(let c=0;c<W;c++){const pt=[x0+(c+.5)/W*(x1-x0),y1-(r+.5)/H*(y1-y0)];let ch=' ';for(const s of sorted){if(inside(s.f.p,pt))ch=s.i.up?'.':'#'}line+=ch}out+=line+'\n'}
console.log(out);console.log('x',x0.toFixed(2),x1.toFixed(2),'y',y0.toFixed(2),y1.toFixed(2));
