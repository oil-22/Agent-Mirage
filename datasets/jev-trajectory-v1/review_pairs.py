"""Derive visual review aids from original frames. Never alter model inputs."""
from collections import Counter, defaultdict
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
WORK=HERE.parents[1]/'.tmp/jev-trajectory-v1-review'
def readlines(p): return [json.loads(x) for x in p.read_bytes().splitlines() if x.strip()]

def scroll_proof(a,b,direction):
    # Match distinctive corners, then verify signed vertical translation in original pixels.
    orb=cv2.ORB_create(nfeatures=2200)
    ka,da=orb.detectAndCompute(a,None);kb,db=orb.detectAndCompute(b,None)
    if da is None or db is None:return None
    matches=[]
    for pair in cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(da,db,k=2):
        if len(pair)!=2:continue
        m,n=pair
        if m.distance>=0.65*n.distance:continue
        x,y=ka[m.queryIdx].pt; u,v=kb[m.trainIdx].pt
        dy=round(v-y)
        if abs(u-x)>1.8 or dy*(-1 if direction=='down' else 1)<25 or min(y,v)<52:continue
        matches.append((round(x),round(y),dy))
    if not matches:return None
    for move,_ in Counter(d for _,_,d in matches).most_common(4):
        anchors=[];grid=set()
        for x,y,d in matches:
            if abs(d-move)>1 or not 20<x<a.shape[1]-20 or not (25<y<a.shape[0]-25 and 25<y+move<b.shape[0]-25):continue
            cell=(x//64,y//42)
            if cell in grid:continue
            p=a[y-15:y+16,x-15:x+16]; q=b[y+move-15:y+move+16,x-15:x+16]
            if p.std()<18 or np.mean(np.abs(p.astype(float)-q))>3:continue
            # Reject repeating motifs at the same horizontal location.
            strip=b[:,x-15:x+16]
            sim=cv2.matchTemplate(strip,p,cv2.TM_CCOEFF_NORMED).ravel()
            if sim[y+move-15]<.96:continue
            sim[max(0,y+move-15-12):y+move-15+13]=-1
            if sim.max()>.91:continue
            anchors.append([x,y]);grid.add(cell)
        if len(anchors)>=5 and np.ptp([x for x,y in anchors])>=125 and np.ptp([y for x,y in anchors])>=35:
            return dict(displacement_y=move,distinct_anchor_cells=len(anchors),anchors=anchors)

def main():
    WORK.mkdir(parents=True,exist_ok=True)
    by=defaultdict(list)
    for r in readlines(HERE/'observations.jsonl'):
        if r['suite']=='gui':by[r['pair_id']].append(r)
    seen=set()
    old=HERE.parents[1]/'reports'
    reg=json.loads((old/'jev-verifier-finetune-20261122/known-regression-reference.json').read_bytes())
    for x in reg['offline']['requests']:seen.update(x['ordered_image_sha256'])
    for x in reg['live']['unique_input_groups']:
        seen.update(x['binding'][k] for k in ('candidate_image_sha256','previous_image_sha256'))
    for x in readlines(old/'jev-verifier-finetune-starter-20261125/examples.regression.jsonl'):
        seen.update([x['before_sha256'],x['candidate_sha256']])
    groups=defaultdict(list); proof={}
    arrays={}
    def array(h):
        if h not in arrays:arrays[h]=cv2.imread(str(HERE/'images'/(h+'.png')),cv2.IMREAD_GRAYSCALE)
        return arrays[h]
    for k,rs in sorted(by.items()):
        r=rs[0]; pre,cur=r['before_sha256'],r['candidate_sha256']
        if seen.intersection((pre,cur)):continue
        t=r['action']['type']
        if t=='scroll':
            p=scroll_proof(array(pre),array(cur),r['action']['direction'])
            if p:proof[k]=p
        groups[t].append((k,r))
    (HERE/'scroll-proof.json').write_text(json.dumps(proof,indent=1),encoding='utf-8')
    idx={}; font=ImageFont.truetype('arial.ttf',16)
    for t,items in groups.items():
        for start in range(0,len(items),5):
            sheet=Image.new('RGB',(1040,5*310),(244,245,246)); draw=ImageDraw.Draw(sheet)
            for num,(key,r) in enumerate(items[start:start+5],start):
                code=t[0].upper()+str(num+1).zfill(2);idx[code]=key
                action=r['action']; y=(num-start)*310
                title=code+'   '+json.dumps(action,ensure_ascii=False)+'    '+('pixel-translation verified' if key in proof else '')
                draw.text((6,y+2),title,fill='black',font=font)
                for j,h in enumerate((r['before_sha256'],r['candidate_sha256'])):
                    with Image.open(HERE/'images'/(h+'.png')) as im:
                        thumb=im.convert('RGB').resize((512,288),Image.Resampling.LANCZOS)
                    sheet.paste(thumb,(j*520,y+22))
                    if j==0 and t=='click':
                        x=action['x']*.512; yy=y+22+action['y']*.288
                        draw.ellipse((x-6,yy-6,x+6,yy+6),outline=(228,0,120),width=2)
            sheet.save(WORK/(t+str(start//5+1).zfill(2)+'.jpg'),quality=88)
    (HERE/'gui-review-index.json').write_text(json.dumps(idx,indent=1),encoding='utf-8')
    print('GUI groups:',{k:len(v) for k,v in groups.items()},'pixel-proven scrolls:',len(proof))
if __name__=='__main__':main()
