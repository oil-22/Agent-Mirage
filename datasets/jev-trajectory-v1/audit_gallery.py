"""Deterministically select a stratified review and independent spot checks; never change the inputs."""
import json
from collections import defaultdict
from PIL import Image,ImageDraw,ImageFont
from archive_files import WORK
from export import canon,rows,sha
from screen_evidence import T
D=WORK/'archive-review'
def gallery(rs,tag):
    idx={};font=ImageFont.truetype('arial.ttf',14)
    for first in range(0,len(rs),12):
        canvas=Image.new('RGB',(948,760),'white');draw=ImageDraw.Draw(canvas)
        for i,(r,type_) in enumerate(rs[first:first+12]):
            identifier=tag+str(first+i+1).zfill(3);idx[identifier]=r['pair_id'];a=r['action']
            x=(i%2)*474;y=(i//2)*126
            t=identifier+'  '+str(a.get('text') or a.get('key') or a.get('direction') or a['type'])[:24]+'  '+type_[:29]
            draw.text((x+3,y+2),t,font=font,fill='black')
            for j,h in enumerate([r['before_sha256'],r['candidate_sha256']]):
                with Image.open(T/(h+'.png')) as raw:im=raw.convert('RGB')
                im.thumbnail((231,106));xx=x+j*235+(231-im.width)//2; yy=y+19
                if j==0 and a['type']=='click':
                    dx,dy=im.width*a['x']/1000,im.height*a['y']/1000;g=ImageDraw.Draw(im);g.ellipse((dx-4,dy-4,dx+4,dy+4),outline=(242,0,138),width=2)
                canvas.paste(im,(xx,yy))
        canvas.save(D/(tag+str(first//12+1).zfill(3)+'.jpg'),quality=93)
    (D/(tag+'-index.json')).write_bytes(canon(idx))
if __name__=='__main__':
    ds=rows(WORK/'archive-pair-reps.jsonl');rep={r['pair_id']:r for r in ds};lab=json.loads((WORK/'derived-labels.json').read_bytes());borders=json.loads((WORK/'field-borders.json').read_bytes());v={r['pair_id']:r for r in rows(WORK/'visual-features.jsonl')}
    qs=defaultdict(list);others=defaultdict(list)
    for k,r in rep.items():
        if k in lab or k in borders:
            typ=lab[k][1] if k in lab else 'focus_ring';qs[(typ,r['family'].split(':')[0])].append(r)
        elif r['action']['type'] in ('click','back','scroll') and .06<v[k]['change']<.85 and v[k]['tiles']>=6 and min(v[k]['edges'])>.017:
            others[(r['family'],r['action']['type'])].append(r)
    q=[]
    for (typ,site),g in sorted(qs.items()):
        g.sort(key=lambda r:sha(('spot'+r['pair_id']).encode()));q.extend((r,typ) for r in g[:(14 if typ=='rendered_navigation' else 4)])
    gallery(q,'Q')
    for g in others.values():g.sort(key=lambda r:sha(('review'+r['pair_id']).encode()))
    p=[]
    for level in range(100):
        for group,g in sorted(others.items()):
            if len(g)>level:p.append((g[level],group[0].split(':')[-1]))
        if len(p)>=144:break
    gallery(p[:144],'P')
    print('QA',len(q),'new visual reviews',len(p[:144]))
