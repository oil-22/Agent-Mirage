"""Read-only one-call capacity diagnostic; never launches or repeats a model request."""
import hashlib,json,time
from pathlib import Path
from remote import remote
prep=Path(__file__).resolve().parent/'uitars-verifier-preparation';receipt=prep/'real-memory-diagnostic-launch.json'
if not receipt.exists():
 receipt.write_text(remote("import pathlib;print(pathlib.Path('/data/researcher/mirage-defense-pilot-20261023/uitars-real-memory-diagnostic-active.json').read_text())",host='4090',timeout=30),encoding='utf8')
launch=json.loads(receipt.read_bytes())
code=r'''
import pathlib,json,hashlib,subprocess,time
r=pathlib.Path(L['root']);p=pathlib.Path('/proc')/str(L['pid']);process=None
if p.exists():
 process={'uid':p.stat().st_uid,'command':[x.decode()for x in(p/'cmdline').read_bytes().split(b'\0')if x]}
 assert process['uid']==L['uid']and process['command']==L['command']
def read(n):
 p=r/n;return json.loads(p.read_bytes())if p.exists()else None
origin=L['retry_origin'];seal=pathlib.Path(origin['sealed_manifest']);assert hashlib.sha256(seal.read_bytes()).hexdigest()==origin['sealed_manifest_sha256']
assert all(hashlib.sha256((pathlib.Path(origin['original_root'])/n).read_bytes()).hexdigest()==h and hashlib.sha256((pathlib.Path(origin['preserved_root'])/n).read_bytes()).hexdigest()==h for n,h in json.loads(seal.read_bytes()).items())
m=read('final-artifacts-sha256.json');verified=None
if m:
 verified=all(hashlib.sha256((r/n).read_bytes()).hexdigest()==h for n,h in m.items());assert verified
input_receipt=read('long-history-candidate/format-0/pre-inference-input.json');binding=None
if input_receipt:
 cpu=next(c for c in read('cpu-result.json')['rows']if c['id']=='long-history-candidate')
 binding=input_receipt['input_ids_sha256']==cpu['input_ids_sha256'];assert binding
 input_receipt={k:v for k,v in input_receipt.items()if k!='input_ids'}
f=read('technical-failure.json');log=r/'worker.log';progress=r/'long-history-candidate/format-0/generated-token-progress.jsonl';last=None
if progress.exists():
 lines=progress.read_text().splitlines();last=json.loads(lines[-1])if lines else None
print(json.dumps({'time':time.time(),'root':str(r),'process':process,'status':read('status.json'),'failure':f,'runtime':read('runtime.json'),'results':read('results.json'),'summary':read('summary.json'),'actual_pre_inference_input':input_receipt,'input_ids_match_frozen_cpu':binding,'parent_seal_verified':True,'final_manifest_verified':verified,'final_manifest_sha256':hashlib.sha256((r/'final-artifacts-sha256.json').read_bytes()).hexdigest()if m else None,'last_generation_progress':last,'log_tail':log.read_text(errors='replace')[-1800:],'gpu':subprocess.check_output(['nvidia-smi','--id=3','--query-gpu=index,memory.used,utilization.gpu','--format=csv,noheader']).decode()}))
'''
d=json.loads(remote('L='+repr(launch)+'\n'+code,host='4090',timeout=45));path=prep/('memory-inspection-'+str(time.time_ns())+'.json');path.write_text(json.dumps(d,indent=2),encoding='utf8')
(prep/'real-memory-diagnostic-current.json').write_text(json.dumps({'inspection':str(path),'inspection_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'root':d['root'],'status':d['status']},indent=2),encoding='utf8')
compact={k:v for k,v in d.items()if k not in {'runtime','summary','results','failure','actual_pre_inference_input'}}
if d['failure']:compact['failure']={k:v[-1400:]if k=='traceback'else v for k,v in d['failure'].items()}
if d['actual_pre_inference_input']:compact['input']={k:v for k,v in d['actual_pre_inference_input'].items()if k!='generation_config'}
print(json.dumps(compact))
