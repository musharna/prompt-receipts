import math, html
import hedgehog, mitten

def lum(rgb): r,g,b=[c/255 for c in rgb]; return 0.299*r+0.587*g+0.114*b
def hexc(rgb): return '#%02x%02x%02x'%rgb
FONT="font-family='DejaVu Sans, Segoe UI Symbol, Arial Unicode MS, sans-serif'"

# ---------------- Cross stitch ----------------
XS_KEY=[  # code, symbol, DMC, name
 ('D','●','838','Very dark brown (outlines, eye, nose)'),
 ('B','✕','801','Dark coffee brown (prickles)'),
 ('L','▲','436','Tan (prickle tips)'),
 ('F','○','738','Very light tan (face & paws)'),
 ('P','♥','3326','Light rose (ear & cheek)'),
 ('C','—','334','Medium baby blue (teacup)'),
 ('c','=','3325','Light baby blue (shine & saucer edge)'),
 ('W','·','Blanc','White (spots & saucer)'),
 ('N','◆','336','Navy (cup & saucer outline)'),
 ('Y','★','729','Old gold (cup rim)'),
 ('Z','Z','414','Dark grey (the Zzz)'),
]
def xs_svg(grid, cols, cell=22):
    h=len(grid); w=len(grid[0]); m=34
    W=w*cell+2*m; H=h*cell+2*m
    sym={k:s for k,s,_,_ in XS_KEY}
    o=[f"<svg viewBox='0 0 {W} {H}' xmlns='http://www.w3.org/2000/svg' {FONT}>"]
    o.append(f"<rect width='{W}' height='{H}' fill='white'/>")
    for y,row in enumerate(grid):
        for x,ch in enumerate(row):
            if ch=='.': continue
            rgb=cols[ch]; px=m+x*cell; py=m+y*cell
            o.append(f"<rect x='{px}' y='{py}' width='{cell}' height='{cell}' fill='{hexc(rgb)}'/>")
            tc='#fff' if lum(rgb)<0.5 else '#222'
            o.append(f"<text x='{px+cell/2}' y='{py+cell/2}' font-size='{cell*0.62:.1f}' fill='{tc}' text-anchor='middle' dominant-baseline='central'>{sym[ch]}</text>")
    for x in range(w+1):
        sw=2.2 if (x%10==0 or x==w) else 0.6; col='#222' if sw>1 else '#999'
        o.append(f"<line x1='{m+x*cell}' y1='{m}' x2='{m+x*cell}' y2='{m+h*cell}' stroke='{col}' stroke-width='{sw}'/>")
        if x%10==0 and x>0:
            for yy in (m-8, m+h*cell+18): o.append(f"<text x='{m+x*cell}' y='{yy}' font-size='15' text-anchor='middle' fill='#333'>{x}</text>")
    for y in range(h+1):
        sw=2.2 if (y%10==0 or y==h) else 0.6; col='#222' if sw>1 else '#999'
        o.append(f"<line x1='{m}' y1='{m+y*cell}' x2='{m+w*cell}' y2='{m+y*cell}' stroke='{col}' stroke-width='{sw}'/>")
        if y%10==0 and y>0:
            o.append(f"<text x='{m-6}' y='{m+y*cell+5}' font-size='15' text-anchor='end' fill='#333'>{y}</text>")
            o.append(f"<text x='{m+w*cell+6}' y='{m+y*cell+5}' font-size='15' fill='#333'>{y}</text>")
    # centre arrows
    cx=m+(w//2)*cell+cell/2; cy=m+(h//2)*cell+cell/2
    for pts in [(cx-9,2,cx+9,2,cx,16),(cx-9,H-2,cx+9,H-2,cx,H-16),(2,cy-9,2,cy+9,16,cy),(W-2,cy-9,W-2,cy+9,W-16,cy)]:
        o.append("<polygon points='%s' fill='#c0392b'/>"%' '.join(f'{v:.1f}' for v in pts))
    o.append("</svg>"); return '\n'.join(o)

# ---------------- Knitting ----------------
MC=(35,50,95); CC=(245,238,220)
def knit_svg(chart, cell=26):
    h=len(chart); w=len(chart[0]); ml=40; mr=40; mt=20; mb=40
    W=w*cell+ml+mr; H=h*cell+mt+mb
    o=[f"<svg viewBox='0 0 {W} {H}' xmlns='http://www.w3.org/2000/svg' {FONT}>","<rect width='100%' height='100%' fill='white'/>"]
    for i,row in enumerate(chart):
        for x,ch in enumerate(row):
            px=ml+x*cell; py=mt+i*cell
            o.append(f"<rect x='{px}' y='{py}' width='{cell}' height='{cell}' fill='{hexc(CC if ch=='X' else MC)}' stroke='#8a8a8a' stroke-width='0.8'/>")
            if ch=='X': o.append(f"<circle cx='{px+cell/2}' cy='{py+cell/2}' r='{cell*0.18}' fill='none' stroke='#b9ad90' stroke-width='1.2'/>")
    o.append(f"<rect x='{ml}' y='{mt}' width='{w*cell}' height='{h*cell}' fill='none' stroke='#111' stroke-width='2.5'/>")
    for i in range(h):
        rn=h-i; py=mt+i*cell+cell/2+5
        o.append(f"<text x='{ml+w*cell+8}' y='{py}' font-size='14' fill='#222'>{rn}</text>")
        if rn%5==0: o.append(f"<line x1='{ml}' y1='{mt+i*cell}' x2='{ml+w*cell}' y2='{mt+i*cell}' stroke='#e0a100' stroke-width='2'/>")
    for x in range(w):
        sn=w-x
        o.append(f"<text x='{ml+x*cell+cell/2}' y='{mt+h*cell+20}' font-size='13' text-anchor='middle' fill='#222'>{sn}</text>")
    # arrow showing reading direction
    y=mt+h*cell+34; o.append(f"<text x='{ml+w*cell}' y='{y}' font-size='12' text-anchor='end' fill='#c0392b'>start here, read ← right to left</text>")
    o.append("</svg>"); return '\n'.join(o)

# ---------------- Crochet ----------------
BROWN='#5b3a1e'; GOLD='#c98a00'
def pol(r,a): a=math.radians(a-90); return (r*math.cos(a), r*math.sin(a))
def stitch(base, top, kind, col, sw=2.4, gap=7):
    (x1,y1),(x2,y2)=base,top
    dx,dy=x2-x1,y2-y1; L=math.hypot(dx,dy); ux,uy=dx/L,dy/L; nx,ny=-uy,ux
    o=[]
    if kind!='ch' and gap:
        x1,y1=x1+ux*gap,y1+uy*gap; dx,dy=x2-x1,y2-y1
    if kind=='ch':
        cx,cy=(x1+x2)/2,(y1+y2)/2; ang=math.degrees(math.atan2(dy,dx))
        return [f"<ellipse cx='{cx:.1f}' cy='{cy:.1f}' rx='{min(L/2*0.9,6):.1f}' ry='{min(max(3.2,L*0.22),3.6):.1f}' transform='rotate({ang:.1f} {cx:.1f} {cy:.1f})' fill='none' stroke='{col}' stroke-width='{sw*0.8}'/>"]
    o.append(f"<line x1='{x1:.1f}' y1='{y1:.1f}' x2='{x2:.1f}' y2='{y2:.1f}' stroke='{col}' stroke-width='{sw}' stroke-linecap='round'/>")
    b=6
    o.append(f"<line x1='{x2-nx*b:.1f}' y1='{y2-ny*b:.1f}' x2='{x2+nx*b:.1f}' y2='{y2+ny*b:.1f}' stroke='{col}' stroke-width='{sw}' stroke-linecap='round'/>")
    slashes={'htr':[], 'tr':[0.5], 'dtr':[0.4,0.62]}[kind]
    for f in slashes:
        mx,my=x1+dx*f,y1+dy*f; s=4.5
        o.append(f"<line x1='{mx-nx*s-ux*3:.1f}' y1='{my-ny*s-uy*3:.1f}' x2='{mx+nx*s+ux*3:.1f}' y2='{my+ny*s+uy*3:.1f}' stroke='{col}' stroke-width='{sw*0.8}' stroke-linecap='round'/>")
    return o
def chain_stack(base, top, col, n=3):
    (x1,y1),(x2,y2)=base,top; o=[]
    L=math.hypot(x2-x1,y2-y1); f=6/L; x1,y1=x1+(x2-x1)*f,y1+(y2-y1)*f
    for i in range(n):
        a=(x1+(x2-x1)*i/n, y1+(y2-y1)*i/n); b=(x1+(x2-x1)*(i+1)/n, y1+(y2-y1)*(i+1)/n)
        o+=stitch(a,b,'ch',col)
    return o
def dot(p,col,r=4): return f"<circle cx='{p[0]:.1f}' cy='{p[1]:.1f}' r='{r}' fill='{col}'/>"
def crochet_svg():
    R=[16,52,92,134]; o=[]
    S=200
    bands=['#f6efe4','#ffffff','#f6efe4']
    o.append(f"<circle cx='0' cy='0' r='{R[3]+75}' fill='#fffdf5'/>")
    for i in (2,1,0): o.append(f"<circle cx='0' cy='0' r='{R[i+1]}' fill='{bands[i]}'/>")
    o.append(f"<circle cx='0' cy='0' r='{R[0]}' fill='none' stroke='{BROWN}' stroke-width='2.4'/>")
    # round 1: 12 sts
    th=[i*30 for i in range(12)]
    for i,a in enumerate(th):
        if i==0: o+=chain_stack(pol(R[0],a),pol(R[1],a),BROWN)
        else: o+=stitch(pol(R[0],a),pol(R[1],a),'tr',BROWN)
    o.append(dot(pol(R[1]+3,-9),BROWN))
    # round 2: 24 sts
    r2=[]
    for i,a in enumerate(th):
        for d in (-7.5,7.5): r2.append((a,a+d))
    r2=r2[1:]+r2[:1]  # start on the +side so the ch3 sits in the same st as the join
    for j,(b,t) in enumerate(r2):
        if j==0: o+=chain_stack(pol(R[1],b),pol(R[2],t),BROWN)
        else: o+=stitch(pol(R[1],b),pol(R[2],t),'tr',BROWN)
    o.append(dot(pol(R[2]+3,r2[0][1]-6),BROWN))
    # round 3: ch3 + tr in same st? -> pattern: ch3, 2tr in next, *tr in next, 2tr in next*
    r3=[]; tops=[]
    for k,(b,t) in enumerate(r2):
        n=1 if k%2==0 else 2
        if n==1: r3.append((t,t-2.5))
        else: r3+= [(t,t-2.5+10*0+5),(t,t+7.5)]
    # simple even spread: recompute tops so 36 sts are 10 deg apart
    start=r2[0][1]-2.5
    r3=[(b, start+10*idx) for idx,(b,_) in enumerate(r3)]
    for j,(b,t) in enumerate(r3):
        if j==0: o+=chain_stack(pol(R[2],b),pol(R[3],t),BROWN)
        else: o+=stitch(pol(R[2],b),pol(R[3],t),'tr',BROWN)
    o.append(dot(pol(R[3]+3,r3[0][1]-5),BROWN))
    # round 4: petals
    A=[t for _,t in r3]
    for p in range(12):
        s0,s1,s2=A[3*p],A[3*p+1],A[3*p+2]
        o.append(dot(pol(R[3]+5,s0),GOLD,4.5))
        c=(s1+s2)/2
        for st,(kind,off,h) in zip([s1]*3,[('htr',-12,24),('tr',-7.5,40),('dtr',-2.8,56)]):
            o+=stitch(pol(R[3],st),pol(R[3]+h,c+off),kind,GOLD)
        o+=stitch(pol(R[3]+60,c-2.2),pol(R[3]+60,c+2.2),'ch',GOLD)
        for st,(kind,off,h) in zip([s2]*3,[('dtr',2.8,56),('tr',7.5,40),('htr',12,24)]):
            o+=stitch(pol(R[3],st),pol(R[3]+h,c+off),kind,GOLD)
    # round labels
    for i,(r,txt) in enumerate([(R[0]+18,'1'),(R[1]+20,'2'),(R[2]+21,'3'),(R[3]+40,'4')]):
        a=-25 if i<3 else A[0]-1
        x,y=pol(r,a- (0 if i<3 else 0))
        o.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='11' fill='#fff' stroke='#c0392b' stroke-width='1.8'/><text x='{x:.1f}' y='{y+5:.1f}' font-size='14' font-weight='bold' text-anchor='middle' fill='#c0392b'>{txt}</text>")
    return f"<svg viewBox='{-S-20} {-S-20} {2*S+40} {2*S+40}' xmlns='http://www.w3.org/2000/svg' {FONT}>"+'\n'.join(o)+"</svg>"

def legend_svg(kind, col, label):
    o=[]
    if kind=='ch': o=stitch((14,30),(14,8),'ch',col)
    elif kind=='sl': o=[dot((14,19),col,5)]
    elif kind=='ring': o=[f"<circle cx='14' cy='19' r='9' fill='none' stroke='{col}' stroke-width='2.4'/>"]
    else: o=stitch((14,34),(14,4),kind,col)
    return f"<svg width='30' height='38' viewBox='0 0 28 38'>{''.join(o)}</svg>"

# ---------------- HTML ----------------
def build():
    g=hedgehog.grid; cols=hedgehog.COLOURS
    counts={k:sum(r.count(k) for r in g) for k in cols}
    xs_rows=''.join(
        f"<tr><td class='sw' style='background:{hexc(cols[k])};color:{'#fff' if lum(cols[k])<0.5 else '#222'}'>{s}</td><td><b>{d}</b></td><td>{html.escape(n)}</td><td class='num'>{counts[k]}</td></tr>"
        for k,s,d,n in XS_KEY)
    kn=mitten.CHART
    leg=lambda k,c,l: f"<tr><td>{legend_svg(k,c,l)}</td><td>{l}</td></tr>"
    crochet_leg=''.join([
        leg('ring',BROWN,'Magic ring (or ch 4 and join into a ring)'),
        leg('ch',BROWN,'Chain (ch)'),
        leg('sl',BROWN,'Slip stitch (sl st)'),
        leg('htr',BROWN,'Half treble (htr) &nbsp;<span class=us>US: half double crochet, hdc</span>'),
        leg('tr',BROWN,'Treble (tr) &nbsp;<span class=us>US: double crochet, dc</span>'),
        leg('dtr',BROWN,'Double treble (dtr) &nbsp;<span class=us>US: treble, tr</span>'),
    ])
    return f"""<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8">
<title>Three charts for Gran: hedgehog cross-stitch, snowflake mittens, sunflower coaster</title>
<style>
 @page {{ size: A4; margin: 12mm; }}
 body {{ font-family: Georgia, 'Times New Roman', serif; font-size: 15pt; line-height: 1.45; color:#222; max-width: 190mm; margin: 0 auto; padding: 8mm; }}
 h1 {{ font-size: 24pt; margin: 0 0 2mm; }}
 h2 {{ font-size: 17pt; margin: 5mm 0 1mm; }}
 .page {{ page-break-after: always; break-after: page; padding-bottom: 10mm; }}
 .page:last-child {{ page-break-after: auto; }}
 svg {{ width: 100%; height: auto; display:block; }}
 table {{ border-collapse: collapse; width:100%; font-size: 13pt; }}
 td, th {{ border: 1px solid #bbb; padding: 3px 7px; vertical-align: middle; text-align:left; }}
 td.sw {{ width: 34px; text-align:center; font-size: 17pt; font-family: 'DejaVu Sans','Segoe UI Symbol',sans-serif; }}
 td.num {{ text-align:right; }}
 .facts {{ background:#f6efe4; border-radius:6px; padding: 3mm 5mm; margin: 2mm 0 4mm; }}
 .us {{ color:#777; font-size: 11pt; }}
 ol li, ul li {{ margin-bottom: 1.5mm; }}
 .tip {{ border-left: 5px solid #c0392b; padding-left: 4mm; margin: 3mm 0; }}
 .two {{ display:flex; gap:6mm; align-items:flex-start; }} .two > * {{ flex:1; }}
 @media print {{ body {{ padding:0; }} }}
</style></head><body>

<div class="page">
<h1>Hedgehog asleep in a teacup</h1>
<div class="facts"><b>Cross-stitch.</b> {len(g[0])} stitches wide × {len(g)} stitches tall.
On <b>11-count Aida</b> (big holes, easy on the eyes) it comes out about {len(g[0])/11*2.54:.1f} × {len(g)/11*2.54:.1f} cm; use 3 strands of thread.
On 14-count Aida it's about {len(g[0])/14*2.54:.1f} × {len(g)/14*2.54:.1f} cm; use 2 strands. Cut your fabric at least 8 cm bigger all round.</div>
{xs_svg(g,cols)}
<p style="font-size:12pt">One square = one cross. Empty squares are left as bare fabric. The red arrows point to the middle of the design; start stitching there so it ends up centred. The thick lines are every 10 squares, to help you keep your place.</p>
</div>

<div class="page">
<h2>Thread key (DMC stranded cotton, one skein of each is plenty)</h2>
<table><tr><th>Symbol</th><th>DMC</th><th>Colour</th><th>Stitches</th></tr>{xs_rows}</table>
<h2>Handy reminders</h2>
<ul>
<li>Fold the fabric in half both ways to find the middle, and start there (where the red arrows meet).</li>
<li>Make all the top stitches of your crosses lean the same way. It looks much neater.</li>
<li>Do one colour at a time. Where a colour is spread out (like the white spots), finish your thread off rather than carrying it more than 3 or 4 squares across the back, or it will show through.</li>
<li>The outlines are ordinary full crosses, so there's no backstitch to do.</li>
</ul>
</div>

<div class="page">
<h1>Snowflake mittens</h1>
<div class="facts"><b>Stranded colourwork, knitted in the round.</b> Two colours of DK wool: about 50 g of <b>navy</b> (main colour) and 25 g of <b>cream</b> (contrast).
4 mm double-pointed needles or a short circular for magic loop, plus 3.5 mm needles for the cuff. Tension: 24 stitches to 10 cm over the pattern.
Makes an adult medium mitten (20 cm around the hand). <b>Make two.</b></div>
<div class="two">
<div style="flex:1.25">{knit_svg(kn)}</div>
<div style="font-size:13pt">
<p><b>Navy square</b> = knit with navy.<br><b>Cream square</b> (with a little ring) = knit with cream.</p>
<p>The chart is <b>24 stitches wide</b>. Each round you work it <b>twice</b> (48 stitches).</p>
<p>Read every row from <b>right to left</b>, starting at the bottom (row 1) and working up. Every round is a knit round.</p>
<p>A gold line sits above rows 5, 10, 15, 20, 25 and 30 to help you keep your place.</p>
<p>Wherever one colour isn't used, it never goes more than <b>5 stitches</b> along the back, so there are no long loops to catch.</p>
</div></div>
</div>

<div class="page">
<h2>Making the mittens</h2>
<ol>
<li><b>Cuff.</b> With 3.5 mm needles and navy, cast on 44 stitches. Join into a round without twisting. Work k2, p2 rib for 6 cm.</li>
<li>Change to 4 mm needles. <b>Next round:</b> *knit 11, make 1*, 4 times (48 sts). Put a marker at the start of the round.</li>
<li><b>Hand.</b> Join in cream and work rows 1 to 31 of the chart, doing the 24 stitches twice each round.</li>
<li><b>Thumb hole (on row 10).</b> On this round, knit the thumb stitches with a piece of scrap yarn in a different colour, slip those stitches back onto the left needle, and knit them again in the chart pattern.
 <ul><li><b>Right mitten:</b> use stitches 25 to 32 (the first 8 stitches of the second repeat).</li>
     <li><b>Left mitten:</b> use stitches 41 to 48 (the last 8 stitches of the round).</li></ul></li>
<li>After row 31, break the cream and carry on in navy until the mitten reaches the tip of the little finger.</li>
<li><b>Top.</b> Put a second marker after stitch 24.<br>
 <b>Decrease round:</b> *knit 1, slip-slip-knit, knit to 3 stitches before the marker, knit 2 together, knit 1*, twice (4 stitches gone).<br>
 Do the decrease round <b>every other round</b> until 32 stitches are left, then <b>every round</b> until 12 are left. Break the yarn, thread it through the last 12 stitches and pull it snug.</li>
<li><b>Thumb.</b> Carefully pull out the scrap yarn and slip the 8 stitches below and the 8 above onto needles. With navy, knit round them, picking up 1 extra stitch at each corner to close the gap (18 sts).
 Knit plain rounds until the thumb reaches about halfway up your thumbnail. Then <b>knit 2 together</b> all round (9 sts), break the yarn, thread it through and pull it tight.</li>
<li>Darn in the ends and give them a gentle steam to even out the stitches.</li>
</ol>
<p class="tip">Keep the strands at the back loose. Spread the stitches on the right needle out to their full width before you change colour, and the fabric won't pucker.</p>
</div>

<div class="page">
<h1>Sunflower coaster</h1>
<div class="facts"><b>Crochet, worked in rounds, right side always facing you.</b> DK cotton in <b>brown</b> and <b>sunflower yellow</b> (small amounts of each), 4 mm hook. It comes out about 11 cm across.<br>
<b>UK terms</b> are used. American names are shown in grey in the key.</div>
<div class="two">
<div style="flex:1.35">{crochet_svg()}</div>
<div><table>{crochet_leg}</table>
<p style="font-size:12pt">The circled red numbers are the round numbers. Brown symbols are worked in brown yarn and gold symbols in yellow. Each round starts at the stack of chain ovals and ends with a slip stitch (the dot).</p></div>
</div>
</div>

<div class="page">
<h2>Sunflower coaster: written out round by round</h2>
<p><b>With brown:</b></p>
<ol>
<li><b>Round 1:</b> Make a magic ring. Chain 3 (this counts as your first treble), then 11 trebles into the ring. Pull the ring tight. Slip stitch into the top of the chain-3. <i>(12 stitches)</i></li>
<li><b>Round 2:</b> Chain 3, 1 treble in the same place. Then <b>2 trebles in every stitch</b> all the way round. Slip stitch into the top of the chain-3. <i>(24 stitches)</i></li>
<li><b>Round 3:</b> Chain 3, 2 trebles in the next stitch. *1 treble in the next stitch, 2 trebles in the next stitch*; repeat from * to * all the way round. Slip stitch into the top of the chain-3. <i>(36 stitches)</i> Fasten off the brown.</li>
</ol>
<p><b>With yellow:</b></p>
<ol start="4">
<li><b>Round 4 (the petals):</b> Join the yellow with a slip stitch into any stitch.
 *In the next stitch work <b>1 half treble, 1 treble, 1 double treble</b>. Chain 1. In the following stitch work <b>1 double treble, 1 treble, 1 half treble</b>. Slip stitch into the next stitch.* That's one petal.
 Repeat from * to * all the way round <i>(12 petals)</i>. The last slip stitch goes into the same stitch as the join. Fasten off.</li>
</ol>
<p>Darn in the ends on the back. If the petals curl, pin the coaster out flat, spray it with a little water and leave it to dry.</p>
<p class="tip">If the middle starts to cup like a bowl, your trebles are a bit tight, so go up half a hook size. If it ripples, go down half a size.</p>
</div>

</body></html>"""

if __name__=='__main__':
    open('../charts-for-gran.html','w',encoding='utf-8').write(build())
    open('/tmp/crochet.svg','w').write(crochet_svg())
    print('written')
