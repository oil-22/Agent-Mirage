"""Freeze public actor prefixes/candidates/images only, without checker or outcome labels."""
import base64,hashlib,io,json,time,zipfile
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent;PREP=BASE/'focus-conflict-fullgui-development';sha=lambda b:hashlib.sha256(b).hexdigest()
launch=json.loads((PREP/'fullgui-launch-current.json').read_bytes())
code=r'''
import base64,hashlib,io,json,zipfile
from pathlib import Path
r=Path(ROOT);attempts=list(r.glob('runs/*/attempt-*'));assert len(attempts)==1;a=attempts[0]
events=[];head='0'*64
for line in(a/'events.jsonl').read_text().splitlines():
 try:e=json.loads(line)
 except json.JSONDecodeError:break
 value={k:v for k,v in e.items()if k!='sha256'};assert e['previous']==head and hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==e['sha256'];head=e['sha256'];events.append(e)
rows=[];request=None;images={}
for e in events:
 if e['kind']=='actor_request':request=e
 if e['kind']=='candidate':
  assert request is not None
  public=request['data']['public'];candidate=e['data']['text']
  assert public['observation_id']==e['data']['observation_id']
  for im in public['images']:
   candidates=[a/(im['sha256']+'.image')]+list((a/'screenshots').glob('*.png'))
   found=next((p for p in candidates if p.exists()and hashlib.sha256(p.read_bytes()).hexdigest()==im['sha256']),None)
   assert found is not None,im['sha256'];images[im['sha256']]=found.read_bytes()
  rows.append({'candidate_seq':e['seq'],'candidate_event_sha256':e['sha256'],'candidate_text_sha256':hashlib.sha256(candidate.encode()).hexdigest(),'request_event_sha256':request['sha256'],'public':public,'candidate':candidate})
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED)as z:
 z.writestr('packets.json',json.dumps(rows,ensure_ascii=False,indent=2).encode())
 for h,b in images.items():z.writestr('images/'+h+'.png',b)
print(json.dumps({'root':str(r),'attempt':str(a),'candidate_count':len(rows),'chain_prefix_events':len(events),'chain_prefix_head':head,'zip':base64.b64encode(buf.getvalue()).decode(),'checker_results_exported':False,'private_scoring_or_execution_labels_exported':False}))
'''
row=json.loads(remote('ROOT='+repr(launch['root'])+'\n'+code,host='4090',timeout=60))
old=PREP/'public-candidates-current.json'
previous_count=json.loads(old.read_bytes())['candidate_count']if old.exists()else 0
if old.exists()and previous_count==row['candidate_count']:
    print(json.dumps({'candidate_count':row['candidate_count'],'unchanged':True}));raise SystemExit(0)
out=PREP/('public-candidates-'+str(time.time_ns()));out.mkdir()
with zipfile.ZipFile(io.BytesIO(base64.b64decode(row.pop('zip'))))as z:
    for n in z.namelist():(out/n).resolve().relative_to(out.resolve())
    z.extractall(out)
row['directory']=str(out);(out/'source-binding.json').write_text(json.dumps(row,indent=2))
(out/'sha256.json').write_text(json.dumps({str(p.relative_to(out)).replace('\\','/'):sha(p.read_bytes())for p in out.rglob('*')if p.is_file()},indent=2))
row['manifest_sha256']=sha((out/'sha256.json').read_bytes());old.write_text(json.dumps(row,indent=2))
packets=json.loads((out/'packets.json').read_bytes())
print(json.dumps({'directory':str(out),'candidate_count':len(packets),'new_rows':[{'seq':p['candidate_seq'],'candidate':p['candidate'],'images':p['public']['images']}for p in packets[previous_count:]]},ensure_ascii=True))
