"""Make review-only contact sheets of unchanged-target candidates, keyed to source triplets."""
import collections,hashlib,json,math,sys
from functools import lru_cache
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageOps
from archive_files import WORK
from screen_evidence import paths,T
from export import rows,canon,sha
D=WORK/'archive-review';D.mkdir(exist_ok=True)
def font(n):return ImageFont.truetype('arial.ttf',n)
def signatures(ps):
    f=WORK/'content-sha.json';out=json.loads(f.read_bytes()) if f.exists() else {}
    for h,p in ps.items():
        if h in out:continue
        with Image.open(p) as im:
            assert im.format=='PNG';w,ht=im.size;im=im.convert('RGB')
            # Desktop: no ignored pixels. Android: only the OS status and system navigation strips.
            area=im.crop((0,round(ht*.04),w,round(ht*.968))) if ht>w else im
            out[h]=[sha(canon(list(area.size))+area.tobytes()),w,ht]
    f.write_bytes(canon(out));return out
def fits(g,r,sz):
    a=r['action']
    for entry in g:
        b=entry['action']
        if a['type']!='click':
            if a==b:return True
        elif math.hypot((a['x']-b['x'])*sz[0]/1000,(a['y']-b['y'])*sz[1]/1000)<=6:return True
    return False
def card(r,ps,ident,kind):
    c=Image.new('RGB',(286,155),'white');dr=ImageDraw.Draw(c)
    a=r['action'];s=r['family'].split(':')[-1]; title=ident+'  '+(a.get('text') or a.get('key') or a.get('direction') or a['type'])
    dr.text((3,1),title[:36],font=font(15),fill='black')
    # A public source thumbnail and the actual target area in the two original PNGs.
    pre,post=r['before_sha256'],r['candidate_sha256']
    with Image.open(ps[pre]) as im, Image.open(ps[post]) as jm:
        w,h=im.size; x=round(a.get('x',500)*w/1000);y=round(a.get('y',500)*h/1000)
        orig=im.convert('RGB'); after=jm.convert('RGB')
        if a['type']=='click':
            target=ImageDraw.Draw(orig);rad=max(9,round(w*.012));target.ellipse((x-rad,y-rad,x+rad,y+rad),outline=(255,0,153),width=max(3,w//260))
        orig.thumbnail((147,123));c.paste(orig,((147-orig.width)//2,23))
        if a['type']=='click':
            cw,ch=round(w*.205),round(w*.095);x0=max(0,min(w-cw,x-cw//2));y0=max(0,min(h-ch,y-ch//2))
            for bb,yy in ((im,22),(jm,81)):
                crop=bb.crop((x0,y0,x0+cw,y0+ch)).convert('RGB')
                crop=crop.resize((134,57),Image.Resampling.LANCZOS)
                lx=(x-x0)*134/cw;ly=(y-y0)*57/ch
                g=ImageDraw.Draw(crop);g.ellipse((lx-4,ly-4,lx+4,ly+4),outline=(255,0,153),width=1)
                c.paste(crop,(149,yy))
        else:
            after.thumbnail((133,119));c.paste(after,(150+(133-after.width)//2,23))
    dr.text((3,140),s[:29],font=font(11),fill=(80,80,80));return c
def sheets(rs,kind,ps):
    alias={}
    for start in range(0,len(rs),24):
        canvas=Image.new('RGB',(286*4,155*6),(235,235,235))
        for i,r in enumerate(rs[start:start+24]):
            ident=kind+str(start+i+1).zfill(4);c=card(r,ps,ident,kind);alias[ident]=r['pair_id']
            canvas.paste(c,(i%4*286,i//4*155))
        canvas.save(D/(kind+str(start//24+1).zfill(3)+'.jpg'),quality=88)
    (D/(kind+'-index.json')).write_bytes(canon(alias));return len(rs)
if __name__=='__main__':
    rr=rows(WORK/'archive-pair-reps.jsonl');ps=paths();sig=signatures(ps)
    if '--signatures' in sys.argv:print(len(sig));sys.exit()
    groups=collections.defaultdict(list);select=[]
    for r in sorted(rr,key=lambda r:(r['family'],r['before_sha256'],r['pair_id'])):
        a=r['action'];x=r['before_sha256'];y=r['candidate_sha256'];ks,w,h=sig[x];kt=sig[y][0]
        if ks!=kt or a['type'] not in ('click','type','press','back'):continue
        b=groups[ks,kt,a['type']]
        if fits(b,r,(w,h)):continue
        b.append(r);select.append(r)
    select.sort(key=lambda r:(r['family'],r['action']['type'],sig[r['before_sha256']][0],r['action'].get('y',0),r['pair_id']))
    print('Reviewing representative unchanged targets:',len(select),flush=True)
    print(sheets(select,'N',ps))
