"""Read-only inspection; a resource-wait state is not a failed model attempt."""
import hashlib
import json
import time
from pathlib import Path
from remote import remote

BASE=Path(__file__).resolve().parent;PREP=BASE/'uitars-verifier-preparation'
stage=json.loads((PREP/'dual-gpu-staging.json').read_bytes())
code='STAGE='+repr(stage)+'\n'+r'''
import pathlib,json,time,hashlib,pwd
base=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');active=base/'uitars-dual-gpu-active.json'
if not active.exists():
 print(json.dumps({'time':time.time(),'state':'not_launched_resource_wait','root':STAGE['root'],'model_calls':0,'terminal':False}));raise SystemExit(0)
launch=json.loads(active.read_bytes());root=pathlib.Path(launch['root']);assert root==pathlib.Path(STAGE['root'])
proc=pathlib.Path('/proc')/str(launch['pid']);process=None
if proc.exists():
 assert proc.stat().st_uid==1015
 cmd=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode();assert str(root)in cmd and 'uitars_dual_gpu_preflight.py'in cmd
 fds=[]
 for p in(proc/'fd').iterdir():
  try:fds.append(str(p.resolve()))
  except OSError:pass
 lock_rows=[]
 for path in launch['locks'].values():
  p=pathlib.Path(path);assert str(p)in fds
  inode=p.stat().st_ino;matches=[l for l in pathlib.Path('/proc/locks').read_text().splitlines()if str(inode)in l];assert matches
  lock_rows.append({'path':str(p),'inode':inode,'held':matches})
 process={'uid':proc.stat().st_uid,'full_command':cmd,'lock_rows':lock_rows}
record={'time':time.time(),'root':str(root),'process':process,'launch':launch,'files':{}}
for n in ['status.json','runtime.json','summary.json','technical-failure.json','weights-verified.json']:
 p=root/n
 if p.exists():
  raw=p.read_bytes();record['files'][n]={'sha256':hashlib.sha256(raw).hexdigest(),'data':json.loads(raw)}
case=root/'long-history-candidate';attempts=[]
for p in sorted(case.glob('format-*')):
 item={'format':p.name,'files':{}}
 for f in p.iterdir():
  if not f.is_file():continue
  raw=f.read_bytes();meta={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
  if f.name=='pre-inference-input.json':
   d=json.loads(raw);assert d['input_ids_sha256']==launch['authorization']['expected_input_ids_sha256']if p.name=='format-0'else True
   meta.update({k:d.get(k)for k in ['input_ids_sha256','tensor_shapes','image_grid_thw']})
  if f.name=='generation.json':
   d=json.loads(raw);meta.update(input_tokens=len(d['input_ids']),output_tokens=len(d['generated_ids']),hit_output_cap=d['hit_output_cap'],seconds=d['seconds'])
  if f.name=='raw-response.txt':meta['raw_reply']=raw.decode()
  item['files'][f.name]=meta
 attempts.append(item)
record['attempts']=attempts;record['terminal']=process is None and any(k in record['files']for k in ['summary.json','technical-failure.json'])
if process is None and(root/'final-artifacts-sha256.json').exists():
 raw=(root/'final-artifacts-sha256.json').read_bytes();bad=[]
 for n,h in json.loads(raw).items():
  if hashlib.sha256((root/n).read_bytes()).hexdigest()!=h:bad.append(n)
 record['final_manifest_sha256']=hashlib.sha256(raw).hexdigest();record['final_manifest_mismatches']=bad
record['log_tail']=(root/'worker.log').read_text(errors='replace')[-2200:]
print(json.dumps(record))
'''
record=json.loads(remote(code,host='4090',timeout=50))
out=PREP/('dual-gpu-inspection-'+str(time.time_ns())+'.json');out.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(PREP/'dual-gpu-current.json').write_text(json.dumps({'snapshot':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),**record},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'snapshot':str(out),'state':record.get('state'),'terminal':record.get('terminal'),'running':bool(record.get('process')),'phase':record.get('files',{}).get('status.json',{}).get('data',{}).get('phase'),'model_calls':record.get('files',{}).get('status.json',{}).get('data',{}).get('model_calls',record.get('model_calls'))}))
