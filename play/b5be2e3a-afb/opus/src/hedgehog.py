import math
W,H=52,46
g=[['.']*W for _ in range(H)]
def inell(x,y,cx,cy,rx,ry): return ((x-cx)/rx)**2+((y-cy)/ry)**2<=1
def setc(x,y,c):
    if 0<=x<W and 0<=y<H: g[y][x]=c
RIM=23
# saucer
for y in range(H):
    for x in range(W):
        if inell(x+.5,y+.5,26,39.5,23,4): g[y][x]='W'
for y in range(H):
    for x in range(W):
        if g[y][x]=='W' and y>=40 and inell(x+.5,y+.5,26,39.5,23,4) and not inell(x+.5,y-1.5,26,39.5,23,4): pass
# saucer shading lower rim
for y in range(H):
    for x in range(W):
        if g[y][x]=='W' and y>=41: g[y][x]='c'
# handle ring
for y in range(H):
    for x in range(W):
        if x>=38 and inell(x+.5,y+.5,40,29,6.5,6) and not inell(x+.5,y+.5,40,29,2.6,2.4): g[y][x]='C'
# cup body (lower half ellipse)
for y in range(RIM,H):
    for x in range(W):
        if inell(x+.5,y+.5,25,RIM,16,15) and y<=36: g[y][x]='C'
# cup foot
for y in range(36,39):
    for x in range(20,31): g[y][x]='C'
# hedgehog spines dome
for y in range(0,RIM+1):
    for x in range(W):
        if inell(x+.5,y+.5,27,RIM-1,13,12.5): g[y][x]='B'
# head / face
for y in range(0,RIM+1):
    for x in range(W):
        if inell(x+.5,y+.5,14,19,6.5,4.5): g[y][x]='F'
# snout
for y in range(0,RIM+1):
    for x in range(W):
        if inell(x+.5,y+.5,9,20,4,2.6): g[y][x]='F'
# cup rim band (gold) across top
for x in range(W):
    if inell(x+.5,RIM+.5,25,RIM,16,15): g[RIM][x]='Y'
# paws on rim
for px in (10,14):
    for x,y in [(px,RIM-1),(px+1,RIM-1),(px+2,RIM-1),(px,RIM),(px+1,RIM),(px+2,RIM)]: setc(x,y,'F')
    for x in (px,px+1,px+2): pass
# outlines: hedgehog D, cup N
def outline(cs,oc,ys=range(H),against='.'):
    pts=[]
    for y in ys:
        for x in range(W):
            if g[y][x] in cs:
                for dx,dy in((1,0),(-1,0),(0,1),(0,-1)):
                    xx,yy=x+dx,y+dy
                    if not(0<=xx<W and 0<=yy<H) or g[yy][xx] in against:
                        pts.append((x,y));break
    for x,y in pts: g[y][x]=oc
outline('BF','D',range(0,RIM))
outline('W','N',range(36,H)); outline('c','N'); outline('C','N',range(RIM,H),'.Wc')
for px in (10,14):
    for x in (px,px+1,px+2): setc(x,RIM+1,'D')
for x in range(W):
    col=[y for y in range(RIM) if g[y][x]=='D']
    if col and x%3==0 and x>17:
        y=min(col)
        if y>0 and g[y-1][x]=='.' and g[y][x-1]=='D': setc(x,y-1,'D')
# spine texture: light tips in a staggered pattern
for y in range(H):
    for x in range(W):
        if g[y][x]=='B' and (x+2*y)%5==0: g[y][x]='L'
        elif g[y][x]=='B' and (x+2*y)%5==1 and y%2==0: g[y][x]='D'
# face details
for x,y in [(12,17),(13,18),(14,18),(15,17)]: setc(x,y,'D')   # closed eye
for x,y in [(16,20),(17,20)]: setc(x,y,'P')                 # cheek
for x,y in [(5,19),(5,20),(6,19),(6,20)]: setc(x,y,'D')     # nose
setc(4,20,'D')
# ear
for x,y in [(15,14),(16,14),(15,15),(16,15)]: setc(x,y,'P')
for x,y in [(14,14),(15,13),(16,13),(17,14),(17,15)]: setc(x,y,'D')

# polka dots on cup (white plus shapes)
for cx,cy in [(16,27),(25,30),(34,27),(20,34),(30,34),(11,31)]:
    if g[cy][cx]=='C':
        for x,y in [(cx,cy),(cx+1,cy),(cx,cy+1),(cx+1,cy+1)]:
            if g[y][x]=='C': g[y][x]='W'
# shine on cup
for x,y in [(36,25),(37,26),(37,27)]:
    if g[y][x]=='C': setc(x,y,'c')
# Zzz
def Z(x0,y0,s):
    for i in range(s): setc(x0+i,y0,'Z'); setc(x0+i,y0+s-1,'Z')
    for i in range(1,s-1): setc(x0+s-1-i,y0+i,'Z')
Z(41,9,5); Z(45,3,4); Z(49,0,3)
grid=[''.join(r) for r in g]
# trim empty rows/cols
while grid and set(grid[0])=={'.'}: grid.pop(0)
while grid and set(grid[-1])=={'.'}: grid.pop()
l=min(len(r)-len(r.lstrip('.')) for r in grid); r_=max(len(r.rstrip('.')) for r in grid)
grid=[r[l:r_] for r in grid]
COLOURS={'D':(74,52,38),'B':(140,90,55),'L':(205,165,115),'F':(236,204,162),'P':(232,150,160),
 'C':(110,155,205),'c':(190,215,240),'W':(255,255,255),'N':(40,60,110),'Y':(214,170,60),'Z':(130,130,140)}
if __name__=='__main__':
    for r in grid: print(r)
    print(len(grid[0]),'x',len(grid))
    from png import grid_png; grid_png('/tmp/hh.png',grid,COLOURS,14)
