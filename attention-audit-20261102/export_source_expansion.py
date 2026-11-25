import collections,copy,gzip,hashlib,json,pathlib,shutil
from PIL import Image,ImageDraw
r=pathlib.Path('/data/researcher/attention-audit-20261031');dest=pathlib.Path('/data/researcher/attention-audit-20261102/source-campaign');dest.mkdir(parents=True,exist_ok=True)
assets=r/'inputs/mirage-trace/_shared/input-images/_embedded-input-images';outassets=dest/'assets';outassets.mkdir(exist_ok=True)
choices=json.loads(pathlib.Path('/data/researcher/attention-audit-20261102/source-selection.json').read_text());corpus=r/'inputs/attention-experiment/_shared/mixed__all-configurations/agent-mirage-mechanism-scale-20261020/corpus/runs'
links={pathlib.PurePosixPath(n).stem:l for n,s,t,l in (json.loads(x) for x in gzip.open(r/'members.jsonl.gz','rt')) if '/_embedded-input-images/' in n and t=='1'}
def store(h):
 pp=list(assets.glob('*/'+h+'.*'))
 if not pp and h in links and (r/'inputs'/links[h]).is_file():pp=[r/'inputs'/links[h]]
 if not pp:return None
 p=pp[0];assert hashlib.sha256(p.read_bytes()).hexdigest()==h
 target=outassets/h[:2]/p.name;target.parent.mkdir(exist_ok=True)
 if not target.exists():shutil.copyfile(p,target)
 return 'archive-image://sha256/'+h
raw=[];audit=[];sheet=Image.new('RGB',(1800,((len(choices)+2)//3)*300),'white');draw=ImageDraw.Draw(sheet)
for ci,choice in enumerate(choices):
 trajectory=choice['trajectory'];base=corpus/trajectory;source=json.loads((base/'002.json').read_text());summary=json.loads((base/'summary_info.json').read_text())
 assert summary['condition']=='silent_drop' and source['injection_fired'] and source['delivered_sha256'] is None
 assert choice['claim'] in source['original_response']
 cap=store(source['capture_sha256']);audit.append({'trajectory':trajectory,'task':summary['task'],'source_claim':choice['claim'],'source_response':source['original_response'],'source_current_image_missing':True,'capture_restored':cap is not None,'capture_sha256':source['capture_sha256'],'ledger':source['ledger']})
 if cap:
  h=source['capture_sha256'];p=next(outassets.glob('*/'+h+'.*'));im=Image.open(p).convert('RGB');im.thumbnail((590,260));x=ci%3*600;y=ci//3*300;sheet.paste(im,(x,y+35));draw.text((x,y),str(summary['task'])+' | '+choice['claim'],fill='black')
 for step in [3,5,8]:
  path=base/f'{step:03d}.json';record=json.loads(path.read_text());request=copy.deepcopy(record['body'])
  for m in request['messages']:
   if isinstance(m['content'],list):
    for block in m['content']:
     if block.get('type')=='image_url':
      h=block['image_url']['url'].split(':')[-1].rsplit('/',1)[-1];url=store(h);assert url,('missing image',h);block['image_url']['url']=url
  assistants=[m for m in request['messages'] if m['role']=='assistant'];assert choice['claim'] in assistants[1]['content'];assert assistants[1]['content']==source['original_response']
  raw.append({'id':f"S{ci:02d}-{step:02d}",'task':summary['task'],'app':'VisualWebArena','trajectory':trajectory,'step':step,'stage':'followup','history':'full','condition':'original','source_step':2,'source_assistant_index':1,'source_claim':choice['claim'],'withdrawals':choice['withdrawals'],'shams':choice['shams'],'source_artifact':str(path.relative_to(r)),'source_artifact_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'request':request})
(dest/'raw.json').write_text(json.dumps(raw,ensure_ascii=False,indent=2));(dest/'selection-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2));sheet.save(dest/'source-captures.png')
print(json.dumps({'independent_tasks':len(choices),'snapshots':len(raw),'assets':len(list(outassets.glob('*/*'))),'capture_restored':sum(a['capture_restored'] for a in audit)}))
