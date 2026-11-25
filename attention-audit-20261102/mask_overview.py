import json,pathlib,numpy as np
from PIL import Image,ImageDraw
r=pathlib.Path('/data/researcher/attention-audit-20261031');i=r/'inputs';assets=i/'mirage-trace/_shared/input-images/_embedded-input-images'
pp=list(i.glob('attention-experiment/**/crossmodel*/**/paired-*-buttons_only/input-metadata.json'))
for p in pp[:1]:
 d=json.loads(p.read_text());print('keys',list(d));print('images',d.get('images'));print('smallfields',{k:v for k,v in d.items() if len(str(v))<800})
out=Image.new('RGB',(1200,900),'white');draw=ImageDraw.Draw(out)
for k,p in enumerate(pp[1:7]):
 d=json.loads(p.read_text());images=d.get('images',[])
 if not images:continue
 h=images[-1]['sha256'];matches=list(assets.glob('*/'+h+'.*'))
 if not matches:print('MISSING',h);continue
 im=Image.open(matches[0]).convert('RGB');a=np.array(im);nonwhite=np.any(a<245,axis=-1)
 rows=np.flatnonzero(nonwhite.any(1));print(p.parent.name,im.size,'nonwhite rows',rows.min() if len(rows) else None,rows.max() if len(rows) else None)
 im.thumbnail((590,270));x=(k%2)*600;y=(k//2)*300;out.paste(im,(x,y+25));draw.text((x,y),p.parent.name,fill='black')
out.save(r/'mask-overview.png')
