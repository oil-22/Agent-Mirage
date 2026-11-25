"""Read existing PNGs; measure visible content, local edits and signed scroll translations."""
from collections import Counter,defaultdict
from functools import lru_cache
from pathlib import Path
import hashlib,json,math
import cv2,numpy as np
from PIL import Image
from archive_files import HERE,WORK,BLOB,content_id
from export import rows,canon,sha
cv2.setNumThreads(1)
T=WORK/'thumbs'
def paths():
    al=json.loads((WORK/'archive-images-aliases.json').read_bytes())
    return {p.rsplit('/',1)[-1][:-4]:BLOB/content_id(o) for p,o in al.items()}
def cache(h,p):
    f=T/(h+'.png')
    if f.exists():return
    raw=p.read_bytes()
    assert sha(raw)==h
    im=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR)
    assert raw.startswith(b'\x89PNG') and im is not None
    height,width=im.shape[:2]
    assert width*height<=4194304
    fac=min(400/width,480/height)
    t=cv2.resize(im,(round(width*fac),round(height*fac)),interpolation=cv2.INTER_AREA)
    assert cv2.imwrite(str(f),t)
@lru_cache(256)
def thumb(h):return cv2.imread(str(T/(h+'.png')))
def core(t):
    h,w=t.shape[:2]
    return t[round(h*.041):round(h*.968)] if h>w else t
def scrollevidence(a,b,direction):
    x=cv2.cvtColor(a,cv2.COLOR_BGR2GRAY);y=cv2.cvtColor(b,cv2.COLOR_BGR2GRAY);h,w=x.shape
    found=defaultdict(list)
    for cy in np.linspace(19,h-20,12,dtype=int):
        for cx in np.linspace(18,w-19,9,dtype=int):
            ref=x[cy-8:cy+9,cx-9:cx+10]
            if np.std(ref)<18:continue
            s=cv2.matchTemplate(y[:,cx-9:cx+10],ref,cv2.TM_CCOEFF_NORMED).ravel(); by=int(s.argmax()); quality=float(s[by])
            dy=by-(cy-8)
            if quality<.96 or dy*(-1 if direction=='down' else 1)<8:continue
            residual=np.mean(np.abs(ref.astype(np.int16)-y[by:by+17,cx-9:cx+10]))
            if residual>5.7:continue
            s[max(0,by-6):by+7]=-1
            if float(s.max())>.86:continue
            found[dy].append((int(cx),int(cy)))
    for off in sorted(found,key=lambda k:-sum(len(found.get(k+i,())) for i in (-1,0,1))):
        pts=[p for i in (-1,0,1) for p in found.get(off+i,())]
        if len(pts)>=5 and np.ptp([x for x,y in pts])>=.18*w and np.ptp([y for x,y in pts])>=.065*h:
            return dict(dy=int(off),anchors=pts[:12],total=len(pts))
def measure(r):
    a=thumb(r['before_sha256']);b=thumb(r['candidate_sha256']);assert a.shape==b.shape
    h,w=a.shape[:2];ma=core(a);mb=core(b);mh,mw=ma.shape[:2]
    diff=cv2.absdiff(ma,mb).max(2);mask=diff>=22;fullmask=cv2.absdiff(a,b).max(2)>=22
    def frac(v):return round(float(v.mean()),5)
    def area(z):return frac(cv2.Canny(z,50,130)>0)
    tile=cv2.resize(mask.astype(np.float32),(8,8),interpolation=cv2.INTER_AREA)
    edit=np.where(fullmask)
    v=dict(change=frac(mask),core_mad=round(float(diff.mean()),4),mean1=round(float(ma.mean()),2),mean2=round(float(mb.mean()),2),
           tiles=int((tile>.065).sum()),coverage=[int((tile>.065).any(axis=ax).sum()) for ax in (0,1)],
           edges=[area(ma),area(mb)],size=[w,h])
    if len(edit[0]):
        v['bbox']=[int(edit[1].min()),int(edit[0].min()),int(edit[1].max()),int(edit[0].max())]
    if r['action']['type']=='click':
        x=int(r['action']['x']*w/1000);y=int(r['action']['y']*h/1000); patch=a[max(0,y-8):y+9,max(0,x-12):x+13]
        v['click_edge']=area(patch);v['target_change']=frac(fullmask[max(0,y-10):y+11,max(0,x-18):x+19])
    if r['action']['type']=='scroll' and .002<v['change']:
        proof=scrollevidence(ma,mb,r['action']['direction'])
        if proof:v['scroll_translation']=proof
    return v
if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--only-ready',action='store_true');args=ap.parse_args()
    T.mkdir(exist_ok=True);ps=paths();rr=rows(WORK/'archive-pair-reps.jsonl')
    for h,p in ps.items():
        if not p.is_file() and args.only_ready:continue
        cache(h,p)
    f=WORK/'visual-features.jsonl'; old={r['pair_id']:r for r in rows(f)} if f.exists() else {}
    with f.open('ab') as out:
        for i,r in enumerate(rr):
            if r['pair_id'] in old or not all((T/(h+'.png')).exists() for h in (r['before_sha256'],r['candidate_sha256'])):continue
            v=dict(pair_id=r['pair_id'],**measure(r));out.write(canon(v)+b'\n')
    n=sum(1 for _ in f.open('rb'));print('verified thumbnails',len(list(T.glob('*.png'))),'measured candidates',n,flush=True)
