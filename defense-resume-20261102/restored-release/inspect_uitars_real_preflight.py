"""Read-only real UI verifier preflight inspector, with recoverable active receipt."""
import hashlib,json,time
from pathlib import Path
from remote import remote
base=Path(__file__).resolve().parent/'uitars-verifier-preparation';receipt=base/('real-remaining-controls-launch.json'if(base/'real-remaining-controls-launch.json').exists()else'real-loader-retry-launch.json'if(base/'real-loader-retry-launch.json').exists()else'real-preflight-launch.json')
if(base/'real-final-controls-launch.json').exists():receipt=base/'real-final-controls-launch.json'
elif(base/'final-controls-static-proof.json').exists():
 probe=json.loads(remote("import pathlib;p=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023/uitars-real-final-controls-active.json');print(p.read_text()if p.exists()else'null')",host='4090',timeout=30))
 if probe is not None:
  receipt=base/'real-final-controls-launch.json';receipt.write_text(json.dumps(probe,indent=2),encoding='utf8')
if receipt.name not in {'real-final-controls-launch.json','real-remaining-controls-launch.json'}and(base/'remaining-controls-static-proof.json').exists():
 probe=json.loads(remote("import pathlib,json;p=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023/uitars-real-remaining-controls-active.json');print(p.read_text()if p.exists()else'null')",host='4090',timeout=30))
 if probe is not None:
  receipt=base/'real-remaining-controls-launch.json';receipt.write_text(json.dumps(probe,indent=2),encoding='utf8')
if receipt.name=='real-preflight-launch.json'and(base/'loader-repair-static-proof.json').exists():
 probe=json.loads(remote("import pathlib,json;p=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023/uitars-real-loader-retry-active.json');print(p.read_text()if p.exists()else'null')",host='4090',timeout=30))
 if probe is not None:
  receipt=base/'real-loader-retry-launch.json';receipt.write_text(json.dumps(probe,indent=2),encoding='utf8')
if not receipt.exists():
 data=json.loads(remote("import pathlib;print(pathlib.Path('/data/researcher/mirage-defense-pilot-20261023/uitars-real-preflight-active.json').read_text())",host='4090',timeout=30));receipt.write_text(json.dumps(data,indent=2),encoding='utf8')
launch=json.loads(receipt.read_bytes())
code=r'''
import pathlib,json,hashlib,time,subprocess
root=pathlib.Path(L['root']);p=pathlib.Path('/proc')/str(L['pid']);process=None
if p.exists():
 process={'uid':p.stat().st_uid,'command':[s.decode()for s in(p/'cmdline').read_bytes().split(b'\0')if s]}
 assert process['uid']==L['uid']and process['command']==L['command']
def read(n):
 p=root/n;return json.loads(p.read_bytes())if p.exists()else None
parent_verified=None
if L.get('retry_origin'):
 origin=L['retry_origin'];seal=pathlib.Path(origin['sealed_manifest']);assert hashlib.sha256(seal.read_bytes()).hexdigest()==origin['sealed_manifest_sha256']
 parent_verified=all(hashlib.sha256((pathlib.Path(origin['original_root'])/n).read_bytes()).hexdigest()==h and hashlib.sha256((pathlib.Path(origin['preserved_root'])/n).read_bytes()).hexdigest()==h for n,h in json.loads(seal.read_bytes()).items());assert parent_verified
if L.get('loader_failure_origin'):
 origin=L['loader_failure_origin'];seal=pathlib.Path(origin['sealed_manifest']);assert hashlib.sha256(seal.read_bytes()).hexdigest()==origin['sealed_manifest_sha256']
 assert all(hashlib.sha256((pathlib.Path(origin['original_root'])/n).read_bytes()).hexdigest()==h and hashlib.sha256((pathlib.Path(origin['preserved_root'])/n).read_bytes()).hexdigest()==h for n,h in json.loads(seal.read_bytes()).items())
manifest=read('final-artifacts-sha256.json');verified=None
if manifest:
 verified=all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in manifest.items())
 if not verified:
  preservation=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023')
  seals=list(preservation.glob('uitars-loader-failure-preserved-*/preservation.json'))
  matched=[json.loads(p.read_bytes())for p in seals if json.loads(p.read_bytes())['original_root']==str(root)]
  assert len(matched)==1
  origin=matched[0];seal=pathlib.Path(origin['sealed_manifest']);assert hashlib.sha256(seal.read_bytes()).hexdigest()==origin['sealed_manifest_sha256']
  parent_verified=all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in json.loads(seal.read_bytes()).items());assert parent_verified
generations=[]
for p in sorted(root.glob('*/format-*/generated-token-progress.jsonl')):
 lines=p.read_text().splitlines();last=json.loads(lines[-1])if lines else None
 generations.append({'case':p.parent.parent.name,'format':p.parent.name,'last':last})
log=root/'worker.log'
print(json.dumps({'time':time.time(),'root':str(root),'process':process,'status':read('status.json'),'summary':read('summary.json'),'results':read('results.json'),'failure':read('technical-failure.json'),'runtime':read('runtime.json'),'verified_weight_shards':len(read('weights-verified.json')or[]),'final_manifest_verified':verified,'final_manifest_sha256':hashlib.sha256((root/'final-artifacts-sha256.json').read_bytes()).hexdigest()if manifest else None,'generation_progress':generations[-3:],'log_tail':log.read_text(errors='replace')[-4000:],'gpu':subprocess.check_output(['nvidia-smi','--id=3','--query-gpu=index,memory.used,utilization.gpu','--format=csv,noheader']).decode()}))
'''
data=json.loads(remote('L='+repr(launch)+'\n'+code,host='4090',timeout=45));dest=base/('real-inspection-'+str(time.time_ns())+'.json');dest.write_text(json.dumps(data,indent=2),encoding='utf8')
(base/'real-preflight-current.json').write_text(json.dumps({'inspection':str(dest),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'status':data['status'],'root':data['root']},indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in data.items()if k not in {'results','summary','runtime'}}))
if data['results']:print(json.dumps([{'id':v['id'],'result':v['result'],'calls':len(v['attempts']),'peak_allocated_bytes':v['peak_allocated_bytes']}for v in data['results']]))
