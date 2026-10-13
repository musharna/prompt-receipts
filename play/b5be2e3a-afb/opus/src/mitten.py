# rows listed TOP first; 24-st repeat; X = contrast (cream), . = main (navy)
def floats(r):
    if len(set(r))==1: return 0
    rr=r+r; best=0; i=0
    # longest cyclic run of same char
    n=len(r); run=1
    for i in range(1,2*n):
        run = run+1 if rr[i]==rr[i-1] else 1
        best=max(best,min(run,n))
    return best
FLAKE=[
"X.....X.....X",
".....XXX.....",
"..XX..X..XX..",
"..XXX.X.XXX..",
"...XXX.XXX...",
".X..XX.XX..X.",
"XXX...X...XXX",
".X..XX.XX..X.",
"...XXX.XXX...",
"..XXX.X.XXX..",
"..XX..X..XX..",
".....XXX.....",
"X.....X.....X",
]
GAP=[
".....X.....",
".X.......X.",
"...........",
"...........",
"...........",
"....X.X....",
".....X.....",
"....X.X....",
"...........",
"...........",
"...........",
".X.......X.",
".....X.....",
]

def fix(row, lo=13, hi=24, maxrun=5):
    # add contrast dots (symmetric about the gap centre) until no float is longer than maxrun
    r=list(row)
    for _ in range(10):
        n=len(r); s=''.join(r)
        if floats(s)<=maxrun: break
        best=None
        for c in range(lo,hi):
            if r[c]=='X' or r[lo+hi-1-c]=='X': continue
            t=r[:]; t[c]='X'; t[lo+hi-1-c]='X'
            sc=(floats(''.join(t)), abs(c-(lo+hi-1)/2))
            if best is None or sc<best[0]: best=(sc,c)
        c=best[1]; r[c]='X'; r[lo+hi-1-c]='X'
    return ''.join(r)
STAR=["...X...X","..XXX...",".XX.XX..","..XXX...","...X...X"]  # 8-st small star repeat
rows=[]
rows.append("X..X"*6)
rows.append(".XX."*6)
rows.append("X..X"*6)
rows.append("."*24)
rows+= [STAR[i]*3 for i in range(5)]
rows.append("."*24)
rows.append("X.X."*6)
rows.append("."*24)
rows+= [fix(FLAKE[i]+GAP[i]) for i in range(13)]
rows.append("."*24)
rows.append("X.X."*6)
rows.append("."*24)
rows.append("X..X"*6)
rows.append(".XX."*6)
rows.append("X..X"*6)
CHART=rows  # top first
if __name__=='__main__':
    for i,r in enumerate(CHART):
        print(f"{len(CHART)-i:2d} {r} {r} run={floats(r)}")
    print(len(CHART[0]),len(CHART))
    from png import grid_png; grid_png('/tmp/mit.png',[r*2 for r in CHART],{'X':(245,240,225),'.':(35,50,95)},14)
