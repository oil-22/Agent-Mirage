"""Read-only inspection and local artifact collection; never launches inference."""
import argparse,base64,hashlib,io,json,time,zipfile
from pathlib import Path
from remote import remote

BASE=Path(__file__).resolve().parent;PREP=BASE/'source-evidence-preview-development'
ap=argparse.ArgumentParser();ap.add_argument('--collect',action='store_true');ap.add_argument('--controls',action='store_true');ap.add_argument('--routing',action='store_true');a=ap.parse_args()
assert not(a.controls and a.routing)
launch=json.loads((PREP/('routing-launch.json'if a.routing else'controls-launch.json'if a.controls else'launch.json')).read_bytes())
code='ROOT='+repr(launch['root'])+'\nPID='+str(launch['pid'])+'\nCOLLECT='+repr(a.collect)+'\n'+r'''
import base64,hashlib,io,json,os,pathlib,subprocess,time,zipfile
root=pathlib.Path(ROOT);proc=pathlib.Path('/proc')/str(PID)
sha=lambda b:hashlib.sha256(b).hexdigest()
status=json.loads((root/'status.json').read_bytes()) if(root/'status.json').exists()else None
actual=None
inherited_locks=[]
if proc.exists():
 cmd=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode()
 actual={'uid':proc.stat().st_uid,'full_command':cmd,'belongs_to_attempt':str(root)in cmd and any(n in cmd for n in ['source_evidence_preview_dev.py','source_evidence_preview_controls.py','source_evidence_routing_diagnostic.py'])}
 if actual['belongs_to_attempt']:assert actual['uid']==1015
 if actual['belongs_to_attempt']:
  for f in(proc/'fd').iterdir():
   if str(f.resolve())=='/data/researcher/mirage-defense-pilot-20261023/source-evidence-preview-development.lock':
    info=(proc/'fdinfo'/f.name).read_text();assert 'FLOCK' in info and 'WRITE' in info
    inherited_locks.append({'fd':f.name,'target':str(f.resolve()),'fdinfo':info})
locks=subprocess.run(['lslocks','-n','-o','PID,PATH'],capture_output=True,text=True).stdout
events=[];head='0'*64
for line in(root/'journal/events.jsonl').read_text().splitlines():
 e=json.loads(line);got=e.pop('sha256');assert e['previous']==head and sha(json.dumps(e,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())==got
 head=got;e['sha256']=got;events.append(e)
responses=[{'case':e['data']['case'],'arm':e['data'].get('arm','preview'),'calls':e['data'].get('calls',[])}for e in events if e['kind']in {'development_actor_response','development_preview_response'}]
sealed=None
if(root/'terminal-sha256.json').exists():
 seal=json.loads((root/'terminal-sha256.json').read_bytes())
 for n,h in seal.items():assert sha((root/n).read_bytes())==h,n
 sealed={'manifest_sha256':sha((root/'terminal-sha256.json').read_bytes()),'verified_files':len(seal)}
out={'time':time.time(),'root':ROOT,'status':status,'actual_process':actual,'task_lock_lines':[l for l in locks.splitlines()if 'source-evidence-preview-development.lock'in l],
 'inherited_locks':inherited_locks,'events':len(events),'event_chain_head':head,'responses':responses,'seal':sealed,'log_tail':(root/'worker.log').read_text()[-2000:]}
if COLLECT:
 b=io.BytesIO()
 with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED)as z:
  for p in root.rglob('*'):
   if p.is_file()and not str(p.relative_to(root)).startswith(('images/','inputs/','release/')):z.write(p,str(p.relative_to(root)))
 out['artifacts_zip_base64']=base64.b64encode(b.getvalue()).decode()
print(json.dumps(out))
'''
result=json.loads(remote(code,host='4090',timeout=90))
if a.collect:
 raw=base64.b64decode(result.pop('artifacts_zip_base64'));folder=Path(launch['local_root'])/'collected'
 folder.mkdir(exist_ok=True)
 with zipfile.ZipFile(io.BytesIO(raw))as z:
  for n in z.namelist():assert not n.startswith('/')and '..'not in Path(n).parts
  z.extractall(folder)
 result['collected_local']=str(folder)
snapshot=PREP/('inspection-'+str(time.time_ns())+'.json');snapshot.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(PREP/('routing-current.json'if a.routing else'controls-current.json'if a.controls else'current.json')).write_text(json.dumps({'snapshot':str(snapshot),'sha256':hashlib.sha256(snapshot.read_bytes()).hexdigest(),**result},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items()if k!='responses'},ensure_ascii=False))
