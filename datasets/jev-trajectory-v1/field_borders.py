"""A local focus-ring witness: new colored rectangle around the clicked field in an otherwise stable view."""
from functools import lru_cache
import cv2,numpy as np
from archive_files import WORK
from export import rows,canon
from screen_evidence import paths

def witness(a,b,x,y):
    h,w=a.shape[:2];diff=(cv2.absdiff(a,b).max(2)>=27).astype(np.uint8)
    for c in cv2.findContours(diff,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0]:
        l,t,ww,hh=cv2.boundingRect(c)
        if not (40<=ww<.85*w and 17<=hh<=82 and l+2<=x<l+ww-2 and t+1<=y<t+hh-1):continue
        z=diff[t:t+hh,l:l+ww];n=int(z.sum())
        if n<80 or n<.38*int(diff.sum()):continue
        sides=[z[:4].any(0).mean(),z[-4:].any(0).mean(),z[:,:4].any(1).mean(),z[:,-4:].any(1).mean()]
        if min(sides)<.72 or z[4:-4,5:-5].mean()>.035:continue
        ring=z.astype(bool);ring[4:-4,4:-4]=False
        pre=a[t:t+hh,l:l+ww][ring].astype(np.int16);post=b[t:t+hh,l:l+ww][ring].astype(np.int16)
        satdiff=float(np.mean(post.max(1)-post.min(1))-np.mean(pre.max(1)-pre.min(1)))
        if satdiff<20:continue
        return dict(focus_box=[l,t,ww,hh],covered_sides=[round(float(t),3) for t in sides],saturation_gain=round(satdiff,2),other_pixels_changed=int(diff.sum())-n)
if __name__=='__main__':
    v={r['pair_id']:r for r in rows(WORK/'visual-features.jsonl')};p=paths();out={}
    @lru_cache(32)
    def img(h):return cv2.imdecode(np.frombuffer(p[h].read_bytes(),np.uint8),cv2.IMREAD_COLOR)
    for r in rows(WORK/'archive-pair-reps.jsonl'):
        k=r['pair_id'];a=r['action']
        if a['type']!='click' or r['suite']!='archive_vwa' or r['before_url_path']!=r['after_url_path'] or not 0<v[k]['change']<.045:continue
        i=img(r['before_sha256']);j=img(r['candidate_sha256']);h,w=i.shape[:2]
        ev=witness(i,j,round(a['x']*w/1000),round(a['y']*h/1000))
        if ev:out[k]=ev
    (WORK/'field-borders.json').write_bytes(canon(out));print('visible new focus ring',len(out))
