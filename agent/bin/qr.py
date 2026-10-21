import struct, zlib, sys, time, os

PNG='/home/ubuntu/Napcat/opt/QQ/resources/app/app_launcher/napcat/cache/qrcode.png'

def decode(path):
    d=open(path,'rb').read()
    w,h,bd,ct,cm,fm,im=struct.unpack('>IIBBBBB', d[16:29])
    assert bd==1 and ct==0 and im==0
    idat=b''; i=8
    while i<len(d):
        ln=struct.unpack('>I',d[i:i+4])[0]; typ=d[i+4:i+8]
        if typ==b'IDAT': idat+=d[i+8:i+8+ln]
        i+=12+ln
    raw=zlib.decompress(idat); bpr=(w+7)//8
    rows=[]; prev=bytearray(bpr); p=0
    for y in range(h):
        ft=raw[p]; p+=1
        line=bytearray(raw[p:p+bpr]); p+=bpr
        if ft==1:
            for x in range(1,bpr): line[x]=(line[x]+line[x-1])&0xff
        elif ft==2:
            for x in range(bpr): line[x]=(line[x]+prev[x])&0xff
        elif ft==3:
            for x in range(bpr):
                left=line[x-1] if x else 0
                line[x]=(line[x]+((left+prev[x])>>1))&0xff
        elif ft==4:
            for x in range(bpr):
                a=line[x-1] if x else 0; b=prev[x]; c=prev[x-1] if x else 0
                pp=a+b-c; pa=abs(pp-a); pb=abs(pp-b); pc=abs(pp-c)
                pr=a if (pa<=pb and pa<=pc) else (b if pb<=pc else c)
                line[x]=(line[x]+pr)&0xff
        rows.append(bytes(line)); prev=line
    return w,h,rows

def render(path, border=4):
    w,h,rows=decode(path)
    def px(x,y): return (rows[y][x//8]>>(7-(x%8)))&1
    scale = 3 if w%3==0 else 1
    n=w//scale
    def mod(x,y): return 0 if px(x*scale+scale//2, y*scale+scale//2) else 1  # 1=black
    W=n+2*border; H=n+2*border
    g=[[0]*W for _ in range(H)]
    for y in range(n):
        for x in range(n):
            if mod(x,y): g[y+border][x+border]=1
    lines=[]
    for y in range(0,H,2):
        top=g[y]; bot=g[y+1] if y+1<H else [0]*W
        s=''
        for x in range(W):
            t,b=top[x],bot[x]
            s += '█' if (t and b) else ('▀' if t else ('▄' if b else ' '))
        lines.append(s)
    return '\n'.join(lines), W, H

if __name__=='__main__':
    args=[a for a in sys.argv[1:] if not a.startswith('--')]
    art,W,H=render(args[0] if args else PNG)
    if '--ansi' in sys.argv:
        art='\n'.join('\x1b[30;47m'+l+'\x1b[0m' for l in art.splitlines())
    sys.stderr.write(f'{W}x{H} modules\n')
    print(art)
