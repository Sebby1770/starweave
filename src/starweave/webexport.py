"""A self-contained, dependency-free web explorer for Starweave.

``explorer_html()`` returns a single HTML file (no build step, no network) that
ports the generator to the browser: type a phrase and watch the poster grow,
set a second phrase and morph between them, and see how the *words* steer the
art (vowel ratio, brightness, turbulence). It mirrors the Python pipeline —
seed -> hashed RNG streams -> semantic knobs -> layered scene -> palette blend
for the morph — so it behaves like the real thing, in a page you can open or host.
"""

from __future__ import annotations

_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Starweave — seed-space explorer</title>
<style>
  :root{color-scheme:dark}
  *{box-sizing:border-box}
  body{margin:0;background:#06070d;color:#e2e8f0;
    font-family:"Avenir Next",Inter,"Segoe UI",system-ui,sans-serif}
  .wrap{max-width:820px;margin:0 auto;padding:28px 20px 56px}
  h1{margin:0;font-size:22px;letter-spacing:.5px;font-weight:800}
  .sub{color:#94a3b8;font-size:13px;margin:4px 0 22px}
  .row{display:flex;flex-wrap:wrap;gap:12px;align-items:flex-end;margin-bottom:14px}
  label{display:flex;flex-direction:column;gap:5px;font-size:12px;color:#94a3b8}
  input[type=text],select{background:#0b0d16;color:#e2e8f0;border:1px solid #232a3a;
    border-radius:9px;padding:9px 11px;font:inherit;font-size:14px;min-width:170px}
  input[type=range]{accent-color:#22d3ee}
  button{background:#1a2233;color:#e2e8f0;border:1px solid #2c3650;border-radius:9px;
    padding:9px 14px;font:inherit;font-size:13px;cursor:pointer;display:inline-flex;gap:7px;align-items:center}
  button:hover{background:#222d44}
  .stage{border-radius:14px;overflow:hidden;line-height:0;box-shadow:0 14px 40px rgba(0,0,0,.45)}
  .ctrl{display:flex;align-items:center;gap:12px;margin:14px 0 8px}
  .ctrl input[type=range]{flex:1}
  .lbl{font-size:12px;color:#94a3b8;min-width:150px;text-align:right;font-variant-numeric:tabular-nums}
  .reading{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
  .chip{background:#0b0d16;border:1px solid #1c2333;border-radius:999px;padding:5px 11px;font-size:12px;color:#9fb0c7}
  .chip b{color:#e2e8f0;font-weight:600}
  .foot{margin-top:24px;font-size:12px;color:#64748b}
  a{color:#67e8f9}
</style>
</head>
<body>
<div class="wrap">
  <h1>starweave</h1>
  <div class="sub">A phrase becomes a deterministic little universe. Type, morph, and watch the words steer the sky.</div>
  <div class="row">
    <label>seed a<input id="sa" type="text" value="the long quiet between stars" autocomplete="off" size="30"></label>
    <label>seed b (morph target)<input id="sb" type="text" value="ember tide at the world's edge" autocomplete="off" size="30"></label>
    <button id="shuffle" title="random phrase"><i>↻</i> shuffle</button>
    <button id="tune" title="play the seed's tune"><i>♪</i> play tune</button>
    <button id="dl" title="download SVG"><i>↓</i> save svg</button>
  </div>
  <div class="ctrl">
    <button id="play">▶ play</button>
    <input id="t" type="range" min="0" max="100" value="0" step="1">
    <span class="lbl" id="tlbl">t = 0.00</span>
  </div>
  <div class="stage" id="poster"></div>
  <div class="reading" id="reading"></div>
  <div class="foot">Deterministic: the same phrase always grows the same poster. A browser port of
    <a href="https://github.com/Sebby1770/starweave">Sebby1770/starweave</a> — the CLI also emits animated SVGs and galleries.</div>
</div>
<script>
(function(){
  var $=function(id){return document.getElementById(id);};
  function xfnv1a(s){var h=2166136261>>>0;for(var i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);}return h>>>0;}
  function mul(a){return function(){a|=0;a=a+0x6D2B79F5|0;var t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
  function rng(seed,name){return mul(xfnv1a(seed+'|'+name));}
  function clamp(x){return Math.max(0,Math.min(1,x));}
  function lerp(a,b,t){return a+(b-a)*t;}
  var PAL={
    aurora:{mood:'serene',bg:['#09111f','#101a38'],neb:['#2dd4bf','#7c3aed','#f0abfc','#38bdf8'],star:['#f8fafc','#bfdbfe','#ccfbf1','#fef3c7'],planet:['#14b8a6','#818cf8','#f472b6','#fde68a'],acc:['#22d3ee','#a78bfa','#fb7185']},
    ember:{mood:'turbulent',bg:['#120b16','#24101d'],neb:['#f97316','#ef4444','#f59e0b','#ec4899'],star:['#fff7ed','#fed7aa','#fecaca','#fef9c3'],planet:['#fb923c','#f43f5e','#facc15','#c084fc'],acc:['#f97316','#fb7185','#fbbf24']},
    midnight:{mood:'glacial',bg:['#050816','#101827'],neb:['#2563eb','#4f46e5','#0ea5e9','#64748b'],star:['#eff6ff','#dbeafe','#c7d2fe','#e0f2fe'],planet:['#38bdf8','#6366f1','#94a3b8','#a5b4fc'],acc:['#60a5fa','#818cf8','#67e8f9']},
    solar:{mood:'radiant',bg:['#08100d','#162116'],neb:['#fbbf24','#22c55e','#84cc16','#f97316'],star:['#fff7ed','#ecfccb','#fde68a','#dcfce7'],planet:['#eab308','#22c55e','#fb923c','#bef264'],acc:['#facc15','#4ade80','#fb923c']},
    glacier:{mood:'glacial',bg:['#04141c','#082630'],neb:['#22d3ee','#38bdf8','#5eead4','#a5f3fc'],star:['#ecfeff','#cffafe','#e0f2fe','#f0fdfa'],planet:['#06b6d4','#0ea5e9','#2dd4bf','#7dd3fc'],acc:['#22d3ee','#5eead4','#7dd3fc']},
    synthwave:{mood:'turbulent',bg:['#170b2e','#2a0b3d'],neb:['#f000b8','#7c3aed','#22d3ee','#fb7185'],star:['#fdf4ff','#c4b5fd','#a5f3fc','#fbcfe8'],planet:['#f000b8','#22d3ee','#a855f7','#fde047'],acc:['#f000b8','#22d3ee','#fde047']},
    verdant:{mood:'serene',bg:['#04140d','#0a2417'],neb:['#22c55e','#10b981','#84cc16','#34d399'],star:['#f0fdf4','#dcfce7','#ecfccb','#d1fae5'],planet:['#16a34a','#10b981','#65a30d','#4ade80'],acc:['#4ade80','#a3e635','#34d399']},
    rose:{mood:'serene',bg:['#1a0712','#2c0d22'],neb:['#fb7185','#e879f9','#f0abfc','#fda4af'],star:['#fff1f2','#ffe4e6','#fae8ff','#fce7f3'],planet:['#f43f5e','#d946ef','#fb7185','#f9a8d4'],acc:['#fb7185','#e879f9','#fda4af']},
    gilded:{mood:'radiant',bg:['#16120a','#241a0c'],neb:['#f59e0b','#d97706','#fbbf24','#b45309'],star:['#fffbeb','#fef3c7','#fde68a','#fef9c3'],planet:['#eab308','#f59e0b','#d97706','#fcd34d'],acc:['#fbbf24','#fcd34d','#f59e0b']},
    noir:{mood:'glacial',bg:['#0a0a0b','#16181d'],neb:['#334155','#475569','#1e293b','#64748b'],star:['#f8fafc','#e2e8f0','#cbd5e1','#94a3b8'],planet:['#e2e8f0','#94a3b8','#cbd5e1','#64748b'],acc:['#e2e8f0','#94a3b8','#f8fafc']}
  };
  var BIAS={serene:{turbulence:0.6,brightness:1.0,density:0.9},turbulent:{turbulence:1.5,brightness:1.1,density:1.2},
    glacial:{turbulence:0.5,brightness:0.85,density:0.8},radiant:{turbulence:1.1,brightness:1.3,density:1.05},balanced:{turbulence:1,brightness:1,density:1}};
  var PN=Object.keys(PAL);
  function pickPal(s){return PAL[PN[xfnv1a('starweave-palette|'+s)%PN.length]];}
  function semantics(text){
    var low=(text||'').toLowerCase(),letters=low.replace(/[^a-z]/g,''),n=letters.length||1,vc=0;
    for(var i=0;i<letters.length;i++)if('aeiou'.indexOf(letters[i])>=0)vc++;
    var vr=vc/n,words=low.split(/\s+/).filter(Boolean);
    var avg=words.length?words.reduce(function(a,w){return a+w.length;},0)/words.length:letters.length;
    return {vowel_ratio:vr,avg_word:avg,brightness:clamp(0.35+vr),turbulence:clamp(0.25+(1-vr)*0.85),density:clamp(0.35+Math.min(avg,9)/12)};
  }
  function knobs(seed,pal){
    var r=rng(seed,'knobs'),bias=BIAS[pal.mood]||BIAS.balanced,sem=semantics(seed);
    function mix(rv,key){return clamp(0.45*clamp(rv*bias[key])+0.55*sem[key]);}
    return {turb:mix(0.25+r()*0.6,'turbulence'),bright:mix(0.55+r()*0.4,'brightness'),dens:mix(0.5+r()*0.45,'density'),sem:sem};
  }
  function feats(s){var r=rng(s,'features');return {moon:r()<0.6,rings:r()<0.72};}
  function lh(a,b,t){a=a.slice(1);b=b.slice(1);var o='#';for(var i=0;i<6;i+=2){var x=parseInt(a.substr(i,2),16),y=parseInt(b.substr(i,2),16),v=Math.round(x+(y-x)*t);o+=('0'+v.toString(16)).slice(-2);}return o;}
  function la(A,B,t){var n=Math.min(A.length,B.length),o=[];for(var i=0;i<n;i++)o.push(lh(A[i],B[i],t));return o;}
  function blend(A,B,t){return {bg:la(A.bg,B.bg,t),neb:la(A.neb,B.neb,t),star:la(A.star,B.star,t),planet:la(A.planet,B.planet,t),acc:la(A.acc,B.acc,t)};}
  var ADJ=['Drifting','Ember','Hollow','Silent','Gilded','Veiled','Frozen','Luminous','Wandering','Distant'],
      NOU=['Lattice','Crown','Spindle','Harbor','Lantern','Meridian','Cradle','Atlas','Anchor','Threshold'],
      GRK=['Sigma','Theta','Omega','Lyra','Vega','Astra','Vesper','Caelum'];
  function cat(s){var r=rng(s,'name');return r()<0.5?(GRK[(r()*GRK.length)|0]+' '+NOU[(r()*NOU.length)|0]):('The '+ADJ[(r()*ADJ.length)|0]+' '+NOU[(r()*NOU.length)|0]);}
  function ch(r,a){return a[(r()*a.length)|0];}
  function f(n){return Math.round(n*10)/10;}
  function esc(t){return (''+t).slice(0,60).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
  function poster(struct,pal,kn,ft,title,tag){
    var W=820,H=460,s=[];
    s.push('<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 820 460" role="img"><title>'+esc(title)+'</title>');
    s.push('<defs><linearGradient id="swbg" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stop-color="'+pal.bg[0]+'"/><stop offset="1" stop-color="'+pal.bg[1]+'"/></linearGradient></defs>');
    s.push('<rect width="820" height="460" fill="url(#swbg)"/>');
    var rn=rng(struct,'neb'),nc=Math.round(6+7*kn.dens);
    s.push('<g style="mix-blend-mode:screen">');
    for(var i=0;i<nc;i++){s.push('<ellipse cx="'+f(rn()*W)+'" cy="'+f(rn()*H)+'" rx="'+f(W*(0.08+rn()*0.16))+'" ry="'+f(H*(0.07+rn()*0.14))+'" fill="'+ch(rn,pal.neb)+'" opacity="'+(0.1+0.18*kn.turb).toFixed(2)+'"/>');}
    s.push('</g>');
    var rs=rng(struct,'stars'),ns=Math.round(150+170*kn.dens),pts=[];
    s.push('<g>');
    for(var j=0;j<ns;j++){var x=rs()*W,y=rs()*H,rad=0.4+rs()*1.9,o2=Math.min(1,0.35+rs()*0.5*kn.bright);pts.push([x,y,rad,o2]);s.push('<circle cx="'+f(x)+'" cy="'+f(y)+'" r="'+rad.toFixed(2)+'" fill="'+ch(rs,pal.star)+'" opacity="'+o2.toFixed(2)+'"/>');}
    s.push('</g>');
    pts.sort(function(a,b){return b[2]*b[3]-a[2]*a[3];});var br=pts.slice(0,34);
    var rc=rng(struct,'cons');for(var k=br.length-1;k>0;k--){var m=(rc()*(k+1))|0,tm=br[k];br[k]=br[m];br[m]=tm;}
    s.push('<g fill="none" opacity="0.42" stroke-linecap="round" stroke-linejoin="round">');
    for(var g=0;g<30;g+=6){var grp=br.slice(g,g+6);if(grp.length<3)continue;var d='';for(var p=0;p<grp.length;p++){d+=(p?'L':'M')+f(grp[p][0])+' '+f(grp[p][1])+' ';}s.push('<path d="'+d+'" stroke="'+pal.acc[(g/6)%pal.acc.length]+'" stroke-width="1.2"/>');}
    s.push('</g>');
    var rp=rng(struct,'planets');
    for(var q=0;q<4;q++){var ang=rp()*6.283,dx=W*(0.12+rp()*0.3),dy=H*(0.08+rp()*0.24),px=W*0.5+Math.cos(ang)*dx,py=H*0.5+Math.sin(ang)*dy,prad=Math.min(W,H)*(0.02+rp()*0.034),pf=ch(rp,pal.planet);
      s.push('<circle cx="'+f(px)+'" cy="'+f(py)+'" r="'+f(prad)+'" fill="'+pf+'" opacity="0.96"/>');
      s.push('<circle cx="'+f(px-prad*0.3)+'" cy="'+f(py-prad*0.25)+'" r="'+f(prad*0.38)+'" fill="#ffffff" opacity="0.16"/>');
      if(ft.rings&&q%2===0){s.push('<ellipse cx="'+f(px)+'" cy="'+f(py)+'" rx="'+f(prad*1.85)+'" ry="'+f(prad*0.4)+'" fill="none" stroke="'+ch(rp,pal.acc)+'" stroke-width="1.4" opacity="0.72" transform="rotate('+f(-18+rp()*36)+' '+f(px)+' '+f(py)+')"/>');}}
    if(ft.moon){var rm=rng(struct,'moon'),mx=W*(0.66+rm()*0.18),my=H*(0.15+rm()*0.2),mr=Math.min(W,H)*(0.07+rm()*0.05);
      s.push('<circle cx="'+f(mx)+'" cy="'+f(my)+'" r="'+f(mr)+'" fill="'+pal.star[0]+'" opacity="0.95"/>');
      s.push('<circle cx="'+f(mx+mr*0.35)+'" cy="'+f(my-mr*0.1)+'" r="'+f(mr*0.92)+'" fill="'+pal.bg[1]+'" opacity="0.25"/>');
      for(var c=0;c<5;c++){var a2=rm()*6.283,dd=rm()*mr*0.6;s.push('<circle cx="'+f(mx+Math.cos(a2)*dd)+'" cy="'+f(my+Math.sin(a2)*dd)+'" r="'+f(mr*(0.05+rm()*0.12))+'" fill="'+pal.bg[0]+'" opacity="0.3"/>');}}
    s.push('<text x="34" y="46" fill="'+pal.acc[0]+'" font-family="Avenir Next,Inter,sans-serif" font-size="13" letter-spacing="3" opacity="0.85">STARWEAVE · '+esc(tag.toUpperCase())+'</text>');
    s.push('<text x="34" y="420" fill="#f8fafc" font-family="Avenir Next,Inter,sans-serif" font-size="34" font-weight="800">'+esc(title)+'</text>');
    s.push('</svg>');
    return s.join('');
  }
  var lastSvg='',timer=null;
  function render(){
    var sa=$('sa').value||'starweave',sb=$('sb').value.trim(),t=parseInt($('t').value,10)/100;
    var palA=pickPal(sa),kA=knobs(sa,palA),ftA=feats(sa),pal,kn;
    if(sb){var palB=pickPal(sb),kB=knobs(sb,palB);pal=blend(palA,palB,t);kn={turb:lerp(kA.turb,kB.turb,t),bright:lerp(kA.bright,kB.bright,t),dens:kA.dens};}
    else{pal=palA;kn=kA;t=0;}
    lastSvg=poster(sa,pal,kn,ftA,sa,cat(sa));
    $('poster').innerHTML=lastSvg;
    var who=!sb?'':(t<=0?' · a':(t>=1?' · b':' · a→b'));
    $('tlbl').textContent='t = '+t.toFixed(2)+who;
    var sem=kA.sem;
    $('reading').innerHTML=
      '<span class="chip">vowels <b>'+Math.round(sem.vowel_ratio*100)+'%</b></span>'+
      '<span class="chip">brightness <b>'+kn.bright.toFixed(2)+'</b></span>'+
      '<span class="chip">turbulence <b>'+kn.turb.toFixed(2)+'</b></span>'+
      '<span class="chip">density <b>'+kn.dens.toFixed(2)+'</b></span>'+
      '<span class="chip">catalogue <b>'+esc(cat(sa))+'</b></span>';
  }
  function stop(){if(timer){clearInterval(timer);timer=null;}$('play').textContent='▶ play';}
  function play(){var dir=1;timer=setInterval(function(){var v=parseInt($('t').value,10)+dir*2.5;if(v>=100){v=100;dir=-1;}else if(v<=0){v=0;dir=1;}$('t').value=v;render();},45);$('play').textContent='❚❚ pause';}
  var POOL=['the long quiet between stars','ember tide','glacial drift','late night code','deep field','tidal lock','midnight compiler','solar flare','aurora oasis','a cold meridian'];
  $('sa').addEventListener('input',function(){stop();render();});
  $('sb').addEventListener('input',function(){stop();render();});
  $('t').addEventListener('input',function(){stop();render();});
  $('play').addEventListener('click',function(){timer?stop():play();});
  $('shuffle').addEventListener('click',function(){$('sa').value=POOL[(Math.random()*POOL.length)|0];$('t').value=0;stop();render();});
  // --- sonification: the same World scores a tune (mirrors sonify.py) ---
  var SCALES={serene:[0,2,4,7,9],radiant:[0,2,4,5,7,9,11],turbulent:[0,2,3,5,7,9,10],glacial:[0,3,5,7,10],balanced:[0,2,3,5,7,8,10]};
  var actx=null;
  function rri(r,n){return Math.floor(r()*n);}
  function playTune(){
    var sa=$('sa').value||'starweave',palA=pickPal(sa),kA=knobs(sa,palA);
    var scale=SCALES[palA.mood]||SCALES.balanced;
    if(actx){try{actx.close();}catch(e){}}
    actx=new (window.AudioContext||window.webkitAudioContext)();
    if(actx.resume)actx.resume();
    var r=rng(sa,'music'),root=130.81*Math.pow(2,(rri(r,5)-2)/12),bpm=78+kA.turb*64,beat=60/bpm,seconds=8,type=kA.bright<0.5?'triangle':'sine';
    function note(freq,start,dur,amp){var o=actx.createOscillator(),g=actx.createGain();o.type=type;o.frequency.value=freq;o.connect(g);g.connect(actx.destination);var t0=actx.currentTime+start;g.gain.setValueAtTime(0.0001,t0);g.gain.linearRampToValueAtTime(amp,t0+0.012);g.gain.exponentialRampToValueAtTime(0.0001,t0+dur);o.start(t0);o.stop(t0+dur+0.03);}
    var durs=[0.5,0.5,1,1,1,2],octs=[0,12,12,24],t=0;
    while(t<seconds){var d=beat*durs[rri(r,durs.length)];if(r()<0.12){t+=d;continue;}var semis=scale[rri(r,scale.length)]+octs[rri(r,octs.length)];note(root*Math.pow(2,semis/12),t,d*0.92,0.16*(0.6+0.4*kA.bright));t+=d;}
    t=0;while(t<seconds){note(root/2,t,beat*1.8,0.13);t+=beat*2;}
  }
  $('tune').addEventListener('click',playTune);
  $('dl').addEventListener('click',function(){var b=new Blob([lastSvg],{type:'image/svg+xml'});var u=URL.createObjectURL(b);var a=document.createElement('a');a.href=u;a.download='starweave-'+($('sa').value||'poster').replace(/[^a-z0-9]+/gi,'-').slice(0,40)+'.svg';a.click();URL.revokeObjectURL(u);});
  render();
})();
</script>
</body>
</html>
"""


def explorer_html() -> str:
    """Return the complete standalone explorer page."""

    return _HTML
