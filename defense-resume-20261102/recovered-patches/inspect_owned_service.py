"""Read-only owned service progress; excludes request bodies and auth material."""
import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;receipt=r/'v9-service-launch.json'
if not receipt.exists():receipt=r/'v8-service-launch.json'
if not receipt.exists():receipt=r/'v7-service-launch.json'
launch=json.loads(receipt.read_text())
code=r'''
import pathlib,json,time,subprocess
root=pathlib.Path(ROOT);paths=sorted((root/'requests').glob('*'))[-2:];rows=[]
for p in paths:
 row={'request':p.name,'age':round(time.time()-p.stat().st_mtime)}
 for n in ['generation-progress.json','progress.json','failure.json','response.json']:
  q=p/n
  if q.exists():
   v=json.loads(q.read_text())
   row[n]={k:v[k]for k in ['phase','input_tokens','output_tokens','generated_tokens','seconds','error']if k in v}
 row['files']=[q.name for q in p.iterdir()]
 q=p/'generated-token-progress.jsonl'
 if q.exists():
  lines=q.read_text().splitlines()
  if lines:
   last=json.loads(lines[-1]);row['token_progress']={k:v for k,v in last.items()if k not in {'text','token_ids','input_ids','generated_ids'}}
 rows.append(row)
print(json.dumps({'status':json.loads((root/'status.json').read_text()),'requests':rows,'process':subprocess.check_output(['ps','-p',str(PID),'-o','pid,stat,etime'],text=True)},ensure_ascii=False))
'''.replace('ROOT',repr(launch['root'])).replace('PID',repr(launch['pid']))
print(remote(code,host='3090'))
