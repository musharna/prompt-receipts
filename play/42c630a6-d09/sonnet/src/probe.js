// usage: node probe.js model.js -> prints geometry after each step
const O=require('./engine.js'); const m=require(process.argv[2]).crane||require(process.argv[2]); const M=O.build(m);
const r=x=>Math.round(x*1000)/1000;
M.timeline.forEach((s,i)=>{const fs=s.endFaces; const xs=fs.flatMap(f=>f.p.map(q=>q[0])), ys=fs.flatMap(f=>f.p.map(q=>q[1])), zs=fs.flatMap(f=>f.p.map(q=>q[2]));
 console.log(i,s.title,'faces',fs.length,'bbox x',r(Math.min(...xs)),r(Math.max(...xs)),'y',r(Math.min(...ys)),r(Math.max(...ys)),'z',r(Math.min(...zs)),r(Math.max(...zs)));
 if(process.argv[3]==String(i)||process.argv[3]=='all'){fs.forEach(f=>{const n=O.info(f);console.log('  f'+f.id,n.up?'UP':'DN','z',r(n.cz),'area',r(n.area),f.p.map(q=>'('+r(q[0])+','+r(q[1])+')').join(' '))})}});
console.log('creases',M.creases.map(c=>c.kind+JSON.stringify(c.a.map(r))+JSON.stringify(c.b.map(r))).join('\n'));
