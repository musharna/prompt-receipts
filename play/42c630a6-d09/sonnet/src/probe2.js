const O=require('./engine.js');const M=O.build(require(process.argv[2])[process.argv[3]]);const r=x=>Math.round(x*1000)/1000;
M.timeline.forEach((s,i)=>{const fs=s.endFaces;const xs=fs.flatMap(f=>f.p.map(q=>q[0])),ys=fs.flatMap(f=>f.p.map(q=>q[1])),zs=fs.flatMap(f=>f.p.map(q=>q[2]));console.log(i,s.title,fs.length,'x',r(Math.min(...xs)),r(Math.max(...xs)),'y',r(Math.min(...ys)),r(Math.max(...ys)),'z',r(Math.min(...zs)),r(Math.max(...zs)));
 if(process.argv[4]==String(i)) fs.forEach(f=>{const n=O.info(f);console.log('   f'+f.id,n.up?'UP':'DN','z',r(n.cz),'A',r(n.area),f.p.map(q=>'('+r(q[0])+','+r(q[1])+')').join(' '))})});
console.log('creases',M.creases.length,M.creases.map(c=>c.kind).join(''));
