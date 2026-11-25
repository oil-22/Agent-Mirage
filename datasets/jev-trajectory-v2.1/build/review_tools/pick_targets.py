"""Triage only; an unchanged thumbnail does not assign a label."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'datasets/jev-trajectory-v2.1/build'))
from matched_controls import *
from PIL import ImageStat
def main():
    rows=[r for r in lines(W/'review-index.jsonl') if r['review_code'][0]=='K']
    matched={r['pair_id'] for r in lines(W/'matched.jsonl')}
    old=list(lines(V2/'manifest.jsonl'));old=[r for r in old if r['split']=='val' and r['action']['type']=='click' and imagepath_or_none(r['before_sha256'])]
    pool=[]; omit=Counter()
    for r in rows:
        a=r['action'];x,y=(round(a['x']*.144),round(a['y']*.320))
        if r['pair_id'] in matched or not (3<x<141 and 19<y<303):continue
        b=r['before'];e=r['candidate'];ba=den(b);z=tiny(b)
        if diff(b,e)[0]>.009:continue
        # Require some local texture near the pointer in addition to native receipts.
        if (cv2.Canny(z,60,140)[max(0,y-5):y+6,max(0,x-7):x+8]>0).sum()<4:continue
        if any(distance(a,v['action'])<82 and diff(b,v['before'])[0]<.024 and diff(e,v['candidate'])[0]<.024 for v in pool):continue
        pool.append(r)
    print('to visually inspect',len(pool))
    for j in range(0,len(pool),15):
        batch=pool[j:j+15];cw,ch=360,203
        sheet=Image.new('RGB',(cw*3,ch*math.ceil(len(batch)/3)),'#e9ecee');d=ImageDraw.Draw(sheet)
        for i,r in enumerate(batch):
            a=r['action'];x0=cw*(i%3);y0=ch*(i//3);d.text((x0+1,y0),r['review_code']+' '+short(a)+' '+r['family'][:19],font=font(12),fill='black')
            ix,iy=int(a['x']*1.08),int(a['y']*2.4);l=max(0,min(1080-680,ix-340));t=max(0,min(2400-224,iy-112))
            for c,h in enumerate((r['before'],r['candidate'])):
                im=Image.fromarray(tiny(h)[:,:,::-1]).resize((80,178),Image.Resampling.BILINEAR);xx=x0+c*81;yy=y0+21;sheet.paste(im,(xx,yy))
                if c==0:
                    cx=xx+80*a['x']/1000;cy=yy+178*a['y']/1000;d.ellipse((cx-4,cy-4,cx+4,cy+4),outline='#e41361',width=2)
                patch=whole(h).crop((l,t,l+680,t+224)).resize((195,64),Image.Resampling.LANCZOS);xx=x0+163;yy=y0+26+c*86;sheet.paste(patch,(xx,yy))
                if c==0:
                    cx=xx+(ix-l)*195/680;cy=yy+(iy-t)*64/224;d.ellipse((cx-4,cy-4,cx+4,cy+4),outline='#e41361',width=1)
        sheet.save(W/'sheets'/('Z'+str(j//15+1).zfill(2)+'.jpg'),quality=94)
def imagepath_or_none(h):
    try:return imagepath(h).exists()
    except KeyError:return False
if __name__=='__main__':main()
