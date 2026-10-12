const fs=require('fs');
const html=fs.readFileSync(process.argv[2],'utf8');
const phys=html.split('//<physics>')[1].split('//</physics>')[0];
const pal=`const paletteColour=()=>[1,2,3];`;
const body=pal+phys+`
w=1280;h=720;s=20;floorY=670;
initSlime(340);
function comps(){const seen=new Uint8Array(N);let c=0,sizes=[];for(let i=0;i<N;i++){if(seen[i])continue;c++;let st=[i],n=0;seen[i]=1;while(st.length){const a=st.pop();n++;for(let j=0;j<N;j++){if(seen[j])continue;if(Math.hypot(px[a]-px[j],py[a]-py[j])<1.9*s){seen[j]=1;st.push(j)}}}sizes.push(n)}return sizes.sort((a,b)=>b-a)}
function stats(){let x0=1e9,x1=-1e9,y0=1e9,y1=-1e9,bad=0,sp=0;for(let i=0;i<N;i++){if(!isFinite(px[i]))bad++;x0=Math.min(x0,px[i]);x1=Math.max(x1,px[i]);y0=Math.min(y0,py[i]);y1=Math.max(y1,py[i]);sp=Math.max(sp,Math.hypot(vx[i],vy[i]))}return {bbox:[Math.round(x1-x0),Math.round(y1-y0)],bad,maxv:sp.toFixed(2),comps:comps().slice(0,6).join(',')}}
const run=n=>{for(let k=0;k<n;k++)step(1/3)};
run(900);console.log('settled',stats());
// grab centre-ish and pull far right fast
let cx=0,cy=0;for(let i=0;i<N;i++){cx+=px[i];cy+=py[i]}cx/=N;cy/=N;
grabAt(1,cx,cy);const g=grabs.get(1);console.log('grabbed',g.items.length);
for(let f=0;f<120;f++){g.tx=cx+f*7;g.ty=cy-f*1.5;run(3);if(f%30==29)console.log('pull',f,stats())}
g.tx=cx+900;g.ty=cy-100;
for(let f=0;f<60;f++){run(3)}console.log('pulled far',stats());
grabs.clear();run(600);console.log('released',stats());
// push the pieces together: grab the largest-left and drag back
let mx=0;for(let i=0;i<N;i++)mx+=px[i];mx/=N;
grabAt(2,px[0],py[0]);const g2=grabs.get(2);
for(let f=0;f<200;f++){g2.tx=mx;g2.ty=floorY-30;run(3)}
grabs.clear();run(300);console.log('after squish together',stats());
`;
new Function(body)();
