(() => {
  const canvas = document.querySelector('#scene');
  const gl = canvas.getContext('webgl', { antialias:true, alpha:true });
  if (!gl) { canvas.outerHTML = '<p class="webgl-error">This terrarium needs WebGL enabled.</p>'; return; }

  const VS = `attribute vec3 aPosition; attribute vec3 aNormal;
    uniform mat4 uProjection,uView,uModel; uniform mat3 uNormal;
    varying vec3 vNormal,vWorld;
    void main(){ vec4 w=uModel*vec4(aPosition,1.0); vWorld=w.xyz; vNormal=normalize(uNormal*aNormal); gl_Position=uProjection*uView*w; }`;
  const FS = `precision mediump float; varying vec3 vNormal,vWorld; uniform vec4 uColor; uniform vec3 uLight; uniform float uGlass;
    void main(){ vec3 n=normalize(vNormal); float d=max(dot(n,normalize(uLight-vWorld)),0.0); float rim=pow(1.0-abs(dot(n,normalize(vec3(0.0,2.1,7.0)-vWorld))),2.2); vec3 c=uColor.rgb*(0.46+0.54*d); if(uGlass>0.5)c=mix(c,vec3(0.92,1.0,0.96),rim*.75); gl_FragColor=vec4(c,uColor.a); }`;
  function shader(type, src){ const s=gl.createShader(type); gl.shaderSource(s,src); gl.compileShader(s); if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(s)); return s; }
  const program=gl.createProgram(); gl.attachShader(program,shader(gl.VERTEX_SHADER,VS)); gl.attachShader(program,shader(gl.FRAGMENT_SHADER,FS)); gl.linkProgram(program); gl.useProgram(program);
  const loc={ pos:gl.getAttribLocation(program,'aPosition'), norm:gl.getAttribLocation(program,'aNormal'), proj:gl.getUniformLocation(program,'uProjection'), view:gl.getUniformLocation(program,'uView'), model:gl.getUniformLocation(program,'uModel'), normal:gl.getUniformLocation(program,'uNormal'), color:gl.getUniformLocation(program,'uColor'), light:gl.getUniformLocation(program,'uLight'), glass:gl.getUniformLocation(program,'uGlass') };
  gl.enable(gl.DEPTH_TEST); gl.enable(gl.CULL_FACE); gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);

  const M={
    identity:()=>[1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1],
    mul:(a,b)=>{const o=new Array(16).fill(0);for(let c=0;c<4;c++)for(let r=0;r<4;r++)for(let k=0;k<4;k++)o[c*4+r]+=a[k*4+r]*b[c*4+k];return o},
    translate:(x,y,z)=>[1,0,0,0,0,1,0,0,0,0,1,0,x,y,z,1],
    scale:(x,y,z)=>[x,0,0,0,0,y,0,0,0,0,z,0,0,0,0,1],
    rotX:a=>{let c=Math.cos(a),s=Math.sin(a);return[1,0,0,0,0,c,s,0,0,-s,c,0,0,0,0,1]},
    rotY:a=>{let c=Math.cos(a),s=Math.sin(a);return[c,0,-s,0,0,1,0,0,s,0,c,0,0,0,0,1]},
    rotZ:a=>{let c=Math.cos(a),s=Math.sin(a);return[c,s,0,0,-s,c,0,0,0,0,1,0,0,0,0,1]},
    compose:(p,r,s)=>M.mul(M.translate(...p),M.mul(M.rotY(r[1]||0),M.mul(M.rotX(r[0]||0),M.mul(M.rotZ(r[2]||0),M.scale(...s))))),
    perspective:(fov,asp,n,f)=>{let t=1/Math.tan(fov/2),q=1/(n-f);return[t/asp,0,0,0,0,t,0,0,0,0,(f+n)*q,-1,0,0,2*f*n*q,0]},
    lookAt:(e,t,u)=>{let z=norm(sub(e,t)),x=norm(cross(u,z)),y=cross(z,x);return[x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x,e),-dot(y,e),-dot(z,e),1]}
  };
  const sub=(a,b)=>a.map((v,i)=>v-b[i]), dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0), cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]], norm=a=>{let l=Math.hypot(...a)||1;return a.map(v=>v/l)};

  function mesh(vertices,normals,indices){
    const m={count:indices.length}; m.v=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,m.v);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(vertices),gl.STATIC_DRAW);
    m.n=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,m.n);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(normals),gl.STATIC_DRAW);
    m.i=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,m.i);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(indices),gl.STATIC_DRAW);return m;
  }
  function sphere(ru=20,rv=12){let v=[],n=[],i=[];for(let y=0;y<=rv;y++){let p=y/rv*Math.PI;for(let x=0;x<=ru;x++){let q=x/ru*Math.PI*2, a=Math.sin(p)*Math.cos(q),b=Math.cos(p),c=Math.sin(p)*Math.sin(q);v.push(a,b,c);n.push(a,b,c)}}for(let y=0;y<rv;y++)for(let x=0;x<ru;x++){let a=y*(ru+1)+x,b=a+ru+1;i.push(a,b,a+1,b,b+1,a+1)}return mesh(v,n,i)}
  function cylinder(seg=24,open=false){let v=[],n=[],i=[];for(let y=0;y<=1;y++)for(let j=0;j<=seg;j++){let a=j/seg*Math.PI*2,x=Math.cos(a),z=Math.sin(a);v.push(x,y-.5,z);n.push(x,0,z)}for(let j=0;j<seg;j++){let a=j,b=j+seg+1;i.push(a,b,a+1,b,b+1,a+1)}if(!open){for(let side of [-1,1]){let center=v.length/3;v.push(0,side*.5,0);n.push(0,side,0);let start=v.length/3;for(let j=0;j<=seg;j++){let a=j/seg*Math.PI*2;v.push(Math.cos(a),side*.5,Math.sin(a));n.push(0,side,0)}for(let j=0;j<seg;j++)side>0?i.push(center,start+j,start+j+1):i.push(center,start+j+1,start+j)}}return mesh(v,n,i)}
  function cone(seg=16){let v=[],n=[],i=[];for(let j=0;j<=seg;j++){let a=j/seg*Math.PI*2,x=Math.cos(a),z=Math.sin(a);v.push(x,-.5,z,0,.5,0);let nn=norm([x,1,z]);n.push(...nn,...nn);if(j<seg)i.push(j*2,j*2+2,j*2+1,j*2+2,j*2+3,j*2+1)}return mesh(v,n,i)}
  function torus(seg=32,tube=8){let v=[],n=[],i=[];for(let a=0;a<=seg;a++)for(let b=0;b<=tube;b++){let u=a/seg*Math.PI*2,w=b/tube*Math.PI*2,x=(1+.16*Math.cos(w))*Math.cos(u),y=.16*Math.sin(w),z=(1+.16*Math.cos(w))*Math.sin(u);v.push(x,y,z);n.push(Math.cos(w)*Math.cos(u),Math.sin(w),Math.cos(w)*Math.sin(u))}for(let a=0;a<seg;a++)for(let b=0;b<tube;b++){let q=a*(tube+1)+b,r=q+tube+1;i.push(q,r,q+1,r,r+1,q+1)}return mesh(v,n,i)}
  const geo={sphere:sphere(),cylinder:cylinder(),openCylinder:cylinder(32,true),cone:cone(),torus:torus()};
  const objects=[], glass=[];
  const add=(shape,p,s,c,r=[0,0,0],transparent=false)=> (transparent?glass:objects).push({shape,p,s,c,r});
  const cylBetween=(a,b,r,c)=>{let d=sub(b,a),len=Math.hypot(...d),mid=a.map((v,i)=>(v+b[i])/2), yaw=Math.atan2(d[0],d[2]),pitch=Math.acos(d[1]/len);add('cylinder',mid,[r,len,r],c,[pitch,yaw,0])};

  // Table shadow and jar contents
  add('sphere',[0,-2.32,0],[3.1,.08,1.55],[.32,.38,.28,.16]);
  add('cylinder',[0,-1.78,0],[2.25,.3,2.25],[.24,.17,.11,1]);
  add('cylinder',[0,-1.48,0],[2.28,.31,2.28],[.39,.27,.15,1]);
  add('cylinder',[0,-1.18,0],[2.3,.28,2.3],[.16,.12,.08,1]);
  add('cylinder',[0,-.92,0],[2.31,.28,2.31],[.37,.25,.13,1]);
  // Pebbles
  for(let k=0;k<32;k++){let a=k*2.399,r=.25+(k%7)/7*1.75;add('sphere',[Math.cos(a)*r,-1.92+((k%3)*.04),Math.sin(a)*r],[.17+(k%3)*.06,.1,.14+(k%2)*.05],k%2?[.48,.44,.35,1]:[.66,.61,.5,1],[0,a,0])}
  // Moss mounds
  const mossColors=[[.17,.39,.18,1],[.28,.5,.22,1],[.39,.58,.26,1],[.48,.62,.3,1]];
  for(let k=0;k<58;k++){let a=k*2.31,r=.25+(k%13)/13*1.86,x=Math.cos(a)*r,z=Math.sin(a)*r,y=-.76+.11*Math.sin(k*4);let q=.15+(k%5)*.035;add('sphere',[x,y,z],[q,.10+q*.35,q],mossColors[k%4])}
  // Rocks
  [[-1.45,-.6,.45,.45],[1.35,-.62,-.42,.36],[-.7,-.65,-1.3,.28]].forEach((q,k)=>add('sphere',[q[0],q[1],q[2]],[q[3],q[3]*.65,q[3]*.8],k===0?[.42,.43,.34,1]:[.55,.53,.42,1],[0,k,.2]));
  // Ferns: curved-looking stepped stalks and paired leaves
  function fern(x,z,scale,lean,color){
    for(let f=0;f<5;f++){let ang=(f-2)*.36+lean,base=[x,-.66,z], tip=[x+Math.sin(ang)*(.65+f*.05)*scale,-.25+(f%2)*.18*scale,z+Math.cos(ang)*(.5+f*.08)*scale];cylBetween(base,tip,.025*scale,[.13,.35,.17,1]);
      for(let j=1;j<6;j++){let t=j/6,cx=base[0]+(tip[0]-base[0])*t,cy=base[1]+(tip[1]-base[1])*t,cz=base[2]+(tip[2]-base[2])*t,sz=(.21*(1-t)+.05)*scale;for(let side of [-1,1]){let la=ang+side*1.25;add('sphere',[cx+Math.sin(la)*sz*.85,cy+.025,cz+Math.cos(la)*sz*.85],[sz,.025,sz*.38],color,[0,-la,.05*side])}}
    }
  }
  fern(-.78,-.12,1.25,-.35,[.21,.49,.24,1]); fern(.92,-.1,1.05,.42,[.28,.55,.27,1]); fern(.28,-1.08,.85,2.6,[.19,.43,.2,1]);
  // Tall maidenhair stem with coin leaves
  cylBetween([-.2,-.65,.2],[-.38,1.15,.05],.025,[.12,.31,.15,1]);
  for(let k=0;k<9;k++){let y=-.18+k*.16,a=k*2.3,x=-.3+Math.cos(a)*(.2+k*.02),z=.1+Math.sin(a)*(.18+k*.02);cylBetween([-.32,y-.03,.08],[x,y,z],.012,[.12,.31,.15,1]);add('sphere',[x,y,z],[.18,.025,.14],[.27,.53,.26,1],[0,-a,0])}
  // Ceramic deer body, neck, head, muzzle, legs, tail, ears
  const ceramic=[.84,.78,.66,1], glaze=[.96,.91,.78,1], dark=[.16,.13,.1,1];
  add('sphere',[-.22,-.28,.73],[.52,.34,.25],ceramic,[0,-.15,0]);
  cylBetween([.08,-.22,.7],[.23,.25,.71],.16,ceramic); add('sphere',[.28,.39,.69],[.25,.28,.22],glaze,[0,0,-.12]); add('sphere',[.42,.34,.7],[.18,.12,.16],glaze);
  [[-.52,-.45,.61],[-.05,-.48,.61],[-.43,-.43,.88],[.06,-.44,.87]].forEach(p=>{cylBetween(p,[p[0],-.83,p[2]],.055,ceramic);add('sphere',[p[0],-.84,p[2]],[.07,.04,.085],dark)});
  add('cone',[-.48,-.11,.72],[.13,.32,.13],ceramic,[0,0,-1.25]);
  add('cone',[.17,.68,.58],[.11,.28,.1],ceramic,[0,0,.15]);add('cone',[.35,.68,.8],[.11,.28,.1],ceramic,[0,0,-.15]);
  add('sphere',[.47,.4,.62],[.025,.025,.025],dark);add('sphere',[.47,.4,.78],[.025,.025,.025],dark);add('sphere',[.59,.34,.7],[.035,.025,.035],dark);
  // Antlers
  cylBetween([.2,.59,.66],[.08,.94,.62],.018,[.48,.36,.2,1]);cylBetween([.34,.6,.72],[.42,.96,.76],.018,[.48,.36,.2,1]);
  cylBetween([.12,.82,.63],[-.02,.91,.58],.014,[.48,.36,.2,1]);cylBetween([.39,.82,.75],[.55,.9,.82],.014,[.48,.36,.2,1]);
  // Jar cork base/top and glass last
  add('cylinder',[0,2.38,0],[2.16,.42,2.16],[.56,.39,.22,1]);
  for(let k=0;k<25;k++){let a=k*2.4,r=(k%5)/5*1.7;add('sphere',[Math.cos(a)*r,2.6,Math.sin(a)*r],[.035,.015,.035],[.34,.23,.14,1])}
  add('torus',[0,2.11,0],[2.23,.17,2.23],[.78,.9,.83,.43],[0,0,0],true);
  add('openCylinder',[0,.16,0],[2.38,4.12,2.38],[.72,.9,.82,.15],[0,0,0],true);
  add('torus',[0,-1.89,0],[2.34,.13,2.34],[.72,.88,.81,.24],[0,0,0],true);

  let yaw=-.32,pitch=.09,dist=9.2,target=[0,.05,0],desired={yaw,pitch,dist,target:[...target]},drag=false,last=[0,0],auto=true;
  const views={front:{yaw:-.32,pitch:.09,dist:9.2,target:[0,.05,0]},side:{yaw:1.57,pitch:.06,dist:9.2,target:[0,.05,0]},top:{yaw:-.3,pitch:1.03,dist:9,target:[0,-.05,0]},moss:{yaw:-.2,pitch:.28,dist:7.5,target:[0,-.6,0]},soil:{yaw:.35,pitch:.08,dist:7.8,target:[0,-1.25,0]},fern:{yaw:-.65,pitch:.14,dist:7.3,target:[-.25,.2,0]},deer:{yaw:-.72,pitch:.07,dist:6.7,target:[.05,-.05,.65]}};
  function setView(name){Object.assign(desired,views[name]||views.front);desired.target=[...(views[name]||views.front).target];auto=false;document.querySelectorAll('.view-nav [data-preset]').forEach(b=>b.classList.toggle('active',b.dataset.preset===name));document.querySelectorAll('.layer').forEach(b=>b.classList.toggle('active',b.dataset.focus===name))}
  function normalMat(m){return[m[0],m[1],m[2],m[4],m[5],m[6],m[8],m[9],m[10]]}
  function draw(o){const g=geo[o.shape],model=M.compose(o.p,o.r,o.s);gl.bindBuffer(gl.ARRAY_BUFFER,g.v);gl.vertexAttribPointer(loc.pos,3,gl.FLOAT,false,0,0);gl.enableVertexAttribArray(loc.pos);gl.bindBuffer(gl.ARRAY_BUFFER,g.n);gl.vertexAttribPointer(loc.norm,3,gl.FLOAT,false,0,0);gl.enableVertexAttribArray(loc.norm);gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,g.i);gl.uniformMatrix4fv(loc.model,false,new Float32Array(model));gl.uniformMatrix3fv(loc.normal,false,new Float32Array(normalMat(model)));gl.uniform4fv(loc.color,new Float32Array(o.c));gl.uniform1f(loc.glass,o.c[3]<.5?1:0);gl.drawElements(gl.TRIANGLES,g.count,gl.UNSIGNED_SHORT,0)}
  function resize(){let d=Math.min(devicePixelRatio,2),w=canvas.clientWidth,h=canvas.clientHeight;if(canvas.width!==w*d||canvas.height!==h*d){canvas.width=w*d;canvas.height=h*d;gl.viewport(0,0,canvas.width,canvas.height)}}
  function render(t){resize(); if(auto&&!drag)desired.yaw+=.0006; yaw+=(desired.yaw-yaw)*.07;pitch+=(desired.pitch-pitch)*.07;dist+=(desired.dist-dist)*.07;target=target.map((v,i)=>v+(desired.target[i]-v)*.07);let eye=[target[0]+dist*Math.cos(pitch)*Math.sin(yaw),target[1]+dist*Math.sin(pitch),target[2]+dist*Math.cos(pitch)*Math.cos(yaw)];gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.uniformMatrix4fv(loc.proj,false,new Float32Array(M.perspective(.58,canvas.width/canvas.height,.1,50)));gl.uniformMatrix4fv(loc.view,false,new Float32Array(M.lookAt(eye,target,[0,1,0])));gl.uniform3fv(loc.light,new Float32Array([-4,7,5]));gl.depthMask(true);objects.forEach(draw);gl.depthMask(false);gl.disable(gl.CULL_FACE);glass.forEach(draw);gl.enable(gl.CULL_FACE);gl.depthMask(true);requestAnimationFrame(render)}
  canvas.addEventListener('pointerdown',e=>{drag=true;auto=false;last=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId)});
  canvas.addEventListener('pointermove',e=>{if(!drag)return;desired.yaw-=(e.clientX-last[0])*.009;desired.pitch=Math.max(-.55,Math.min(1.15,desired.pitch+(e.clientY-last[1])*.007));last=[e.clientX,e.clientY]});
  canvas.addEventListener('pointerup',()=>drag=false);canvas.addEventListener('pointercancel',()=>drag=false);
  canvas.addEventListener('wheel',e=>{e.preventDefault();auto=false;desired.dist=Math.max(5.8,Math.min(12,desired.dist+e.deltaY*.008))},{passive:false});
  document.querySelectorAll('[data-preset]').forEach(b=>b.onclick=()=>setView(b.dataset.preset));document.querySelectorAll('[data-focus]').forEach(b=>b.onclick=()=>setView(b.dataset.focus));document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>setView(b.dataset.view));
  document.querySelector('#labels').onclick=e=>{e.currentTarget.classList.toggle('active');document.querySelectorAll('.hotspot,.scale-tag').forEach(x=>x.style.display=e.currentTarget.classList.contains('active')?'':'none')};
  // A tiny, generated woodland ambience; starts only after an explicit click.
  let audioCtx,ambient=false,osc;
  document.querySelector('#sound').onclick=e=>{ambient=!ambient;e.currentTarget.style.opacity=ambient?'1':'.5';if(ambient){audioCtx ||= new (window.AudioContext||window.webkitAudioContext)();osc=audioCtx.createOscillator();let gain=audioCtx.createGain();osc.type='sine';osc.frequency.value=174;gain.gain.value=.012;osc.connect(gain).connect(audioCtx.destination);osc.start()}else if(osc){osc.stop();osc=null}};
  requestAnimationFrame(render);
})();
