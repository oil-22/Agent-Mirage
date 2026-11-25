import json,pathlib,collections
from PIL import Image,ImageDraw
r=pathlib.Path('/data/researcher/attention-audit-20261102/campaign');p=json.loads((r/'plan.json').read_text());dest=r/'previews';dest.mkdir(exist_ok=True)
tasks=collections.defaultdict(list)
for s in p['sources']:tasks[s['task']].append(s)
for i,(task,ss) in enumerate(tasks.items()):
 sheet=Image.new('RGB',(1800,400),'white');d=ImageDraw.Draw(sheet)
 for k,s in enumerate(ss):
  h=s['image_sha256'];f=next((r/'assets').glob('*/'+h+'.*'));im=Image.open(f).convert('RGB');im.thumbnail((595,355));sheet.paste(im,(600*k,40));d.text((600*k,5),s['app']+' '+s['stage']+' step '+str(s['step']),fill='black')
 sheet.save(dest/f'T{i:02d}.png')
print('preview tasks',len(tasks))
old=pathlib.Path('/data/researcher/attention-audit-20261031/inputs');ms=list(old.glob('attention-experiment/**/crossmodel*/**/paired-*-buttons_only/input-metadata.json'));previous={json.loads(m.read_text()).get('task') for m in ms};now=set(tasks)
print('paired prior task overlap',len(now&previous),'new distinct IDs',sorted(now-previous))
