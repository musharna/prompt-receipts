import zlib, struct
def write_png(path, pixels):  # pixels: list of rows of (r,g,b)
    h=len(pixels); w=len(pixels[0])
    raw=b''.join(b'\x00'+bytes(c for p in row for c in p) for row in pixels)
    def chunk(t,d): return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    with open(path,'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))
def grid_png(path, grid, colours, cell=12):
    px=[]
    for row in grid:
        for k in range(cell):
            line=[]
            for ch in row:
                c=colours.get(ch,(255,255,255))
                for m in range(cell):
                    line.append((200,200,200) if (k==0 or m==0) else c)
            px.append(line)
    write_png(path,px)
