"""Contact sheets for visually distinct scene changes; sample makes no label decision."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'datasets/jev-trajectory-v2.1/build'))
from matched_controls import *
rr=lines(W/'review-index.jsonl')
for g in ('J','C','A'):
    rows=[r for r in rr if r['review_code'][0]==g]
    reps,pa,pb=[],[],[]
    for r in rows:
        a,b=ft(r['before']),ft(r['candidate'])
        if pa:
            mask=(np.abs(np.array(pa)-a).mean(1)<4.8) & (np.abs(np.array(pb)-b).mean(1)<4.8)
            if any(distance(r['action'],q['action'])<100 for ix,q in enumerate(reps) if mask[ix]):continue
        pa.append(a);pb.append(b);reps.append(r)
    print(g,len(reps))
    for j in range(0,len(reps),25):
        bb=reps[j:j+25];cw,ch=201,195
        sheet=Image.new('RGB',(5*cw,math.ceil(len(bb)/5)*ch),'#eff2f2');sd=ImageDraw.Draw(sheet)
        for i,r in enumerate(bb):
            px=i%5*cw;py=i//5*ch;a=r['action']
            sd.text((px+1,py),r['review_code']+' '+short(a),font=font(12),fill='black')
            for c,h in enumerate([r['before'],r['candidate']]):
                im=Image.fromarray(tiny(h)[:,:,::-1]).resize((80,177),Image.Resampling.BILINEAR);xx=px+97*c;yy=py+17;sheet.paste(im,(xx,yy))
                if c==0 and a['type']=='click':
                    x=xx+80*a['x']/1000;y=yy+177*a['y']/1000;sd.ellipse((x-3,y-3,x+3,y+3),outline='#ed1059',width=2)
        sheet.save(W/'sheets'/('U'+g+str(j//25+1).zfill(2)+'.jpg'),quality=94)
for k in ('T031','T033'):
    z=next(r for r in rr if r['review_code']==k);sheet=Image.new('RGB',(1000,490),'silver')
    for i,h in enumerate((z['before'],z['candidate'])):
        im=whole(h);sheet.paste(im.crop((0,0,1080,700)).resize((500,324),Image.Resampling.LANCZOS),(500*i,0))
        sheet.paste(im.crop((0,1470,1080,1820)).resize((500,162),Image.Resampling.LANCZOS),(500*i,327))
    sheet.save(W/'sheets'/(k+'-detail.png'))
