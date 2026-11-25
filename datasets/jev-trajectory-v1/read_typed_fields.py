"""Check if the actual typed string became readable in a changed region of the paired PNGs."""
import json,re,unicodedata
from collections import Counter
import cv2,numpy as np
from rapidocr_onnxruntime import RapidOCR
from archive_files import WORK
from screen_evidence import paths
from export import rows,canon

def norm(s):return ''.join(c for c in unicodedata.normalize('NFKC',s).casefold() if c.isalnum())
if __name__=='__main__':
    rr=[r for r in rows(WORK/'archive-pair-reps.jsonl') if r['action']['type']=='type']; ps=paths()
    engine=RapidOCR(intra_op_num_threads=1,inter_op_num_threads=1,use_text_det=False,use_angle_cls=False)
    def image(h):return cv2.imdecode(np.frombuffer(ps[h].read_bytes(),np.uint8),cv2.IMREAD_COLOR)
    def read(im):
        if min(im.shape[:2])<2:return '',0.
        out,_=engine(im)
        return (out[0][1],float(out[0][2])) if out else ('',0.)
    f=WORK/'typed-reading.jsonl';seen={r['pair_id'] for r in rows(f)} if f.exists() else set()
    with f.open('ab') as fp:
        for r in rr:
            pid=r['pair_id']
            if pid in seen:continue
            q=norm(r['action']['text']);yes=None
            if len(q)>=2 and r['before_sha256']!=r['candidate_sha256']:
                a,b=[image(r[k]) for k in ('before_sha256','candidate_sha256')];h,w=a.shape[:2]
                mask=(cv2.absdiff(a,b).max(2)>35).astype(np.uint8)
                if h>w:mask[:int(.04*h)]=0;mask[int(.965*h):]=0
                fat=cv2.dilate(mask,cv2.getStructuringElement(cv2.MORPH_RECT,(17,3)))
                rect=[]
                for c in cv2.findContours(fat,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0]:
                    x,y,ww,hh=cv2.boundingRect(c)
                    if 7<=hh<=74 and 8<=ww<=min(950,w*.9):rect.append((x,y,ww,hh))
                rect.sort(key=lambda b:b[2]*b[3],reverse=True)
                for x,y,ww,hh in rect[:8]:
                    for pad in [1,12]:
                        l=max(0,x-pad);t=max(0,y-3);rrr=min(w,x+ww+pad);bb=min(h,y+hh+3)
                        ac,sc=read(b[t:bb,l:rrr]);before=''
                        if sc<.85 or q not in norm(ac):continue
                        before,_=read(a[t:bb,l:rrr])
                        if norm(ac).count(q)>norm(before).count(q):
                            yes=dict(box=[l,t,rrr,bb],after=ac,before=before,confidence=round(sc,3));break
                    if yes:break
            fp.write(canon(dict(pair_id=pid,match=yes))+b'\n');fp.flush()
    print('Newly visible typed string:',sum(bool(r['match']) for r in rows(f)),flush=True)
