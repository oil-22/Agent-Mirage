"""Read-only evidence audit, no experiment restarts or label generation."""
import hashlib,json,time
from pathlib import Path
from remote import remote
R=Path(__file__).resolve().parent
code='''import pathlib,json,subprocess,hashlib,time
p=pathlib.Path('/home/researcher/mirage-defense-pilot-20261023')
H=lambda raw:hashlib.sha256(raw).hexdigest()
pause=json.loads((p/'pause-receipt.json').read_text());states={}
oldroot=pathlib.Path('/home/researcher/agent-mirage-mechanism-scale-20261020')
for name in ['internvl/status-history-full-bf16-v1.json','qwen9/status-plan-full-qwen9.json']:
 f=oldroot/name;states[name]=json.loads(f.read_text())
root=pathlib.Path(json.loads((p/'shadow-launch.json').read_text())['root']);complete=[];failures=[];journal=[]
for f in root.rglob('complete.json'):
 complete.append(dict(path=str(f),sha256=H(f.read_bytes()),data=json.loads(f.read_text())))
for f in root.rglob('failure.json'):failures.append(dict(path=str(f),data=json.loads(f.read_text())))
for f in root.rglob('events.jsonl'):
 prev='0'*64;count=0;valid=True
 for line in f.read_text().splitlines():
  ev=json.loads(line);saved=ev.pop('sha256');raw=json.dumps(ev,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
  valid=valid and H(raw)==saved and ev['previous']==prev and ev['seq']==count;prev=saved;count+=1
 journal.append(dict(path=str(f),events=count,hash_chain_valid=valid,head=prev))
out=dict(time=time.time(),pause=dict(snapshot=pause['snapshot'],phase=pause['phase'],queues=[dict(folder=x['folder'],parent=x['parent'],worker=x['worker'],signals=x['signals'],preserved_files=len(x['files']),prior_summary_markers=len(x['completion_markers']))for x in pause['queues']]),safe_worker_states=states,process_check=subprocess.check_output(['ps','-p','216086,239183,1270741,1269447','-o','pid,ppid,stat,etime,args'],text=True),gpus=subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.used,utilization.gpu','--format=csv,noheader'],text=True),shadow_launch=json.loads((p/'shadow-launch.json').read_text()),shadow_status=json.loads((root/'status.json').read_text()),runtime=json.loads((root/'runtime.json').read_text()),completed=complete,failures=failures,journal_checks=journal,semantic_labels=None)
print(json.dumps(out,ensure_ascii=False))
'''
data=json.loads(remote(code));data['local_dispatch']=json.loads((R/'dispatch-status.json').read_text(encoding='utf-8'))if(R/'dispatch-status.json').exists()else None
env=json.loads((R/'environment-launch.json').read_text());data['environment_preflight']=json.loads(remote(f"import pathlib;print((pathlib.Path({env['root']!r})/'status.json').read_text())",host='4090'))
path=R/('audit-'+str(time.time_ns())+'.json');path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');(R/'latest-audit.json').write_text(json.dumps({'file':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()},indent=2))
print(json.dumps({'file':str(path),'shadow':data['shadow_status'],'journal_hashes_valid':all(x['hash_chain_valid']for x in data['journal_checks']),'environment_preflight':data['environment_preflight']['phase'],'dispatch_phase':None if data['local_dispatch']is None else data['local_dispatch']['phase']},ensure_ascii=False,indent=2))
