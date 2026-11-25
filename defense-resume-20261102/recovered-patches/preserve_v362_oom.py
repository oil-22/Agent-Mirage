"""Preserve this exact completed technical failure on both hosts before repair."""
import json
from pathlib import Path
from remote import remote

here = Path(__file__).resolve().parent
output = here / 'v3.6.2-online-oom-preservation.json'
assert not output.exists()
launch = json.loads((here / 'v3.6.2-vwa-resume.json').read_text(encoding='utf-8'))
service = json.loads((here / 'v7-service-launch.json').read_text(encoding='utf-8'))
code = '''import pathlib,json,time,hashlib,shutil,subprocess
root=pathlib.Path(ROOT);state=json.loads((root/'status.json').read_text())
assert state['phase']=='technical_failure'
proc=pathlib.Path('/proc')/str(PID)
assert not proc.exists()or(proc/'stat').read_text().split()[2]=='Z'
attempt=pathlib.Path(state['attempt']);assert(attempt/'technical-failure.json').exists()
dest=root/'preservation'/('v362-online-oom-'+str(time.time_ns()));dest.mkdir()
shutil.copytree(attempt,dest/'attempt')
paths=[root/'status.json',pathlib.Path(LOG)]
for p in paths:shutil.copy2(p,dest/p.name)
hashes={str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest()for p in dest.rglob('*')if p.is_file()}
(dest/'hashes.json').write_text(json.dumps(hashes,indent=2))
failure=json.loads((attempt/'technical-failure.json').read_text())
print(json.dumps({'root':str(dest),'attempt':str(attempt),'files':len(hashes),'manifest_sha256':hashlib.sha256((dest/'hashes.json').read_bytes()).hexdigest(),'outcome':failure.get('outcome'),'official_reward':failure.get('official_reward'),'scoring_status':failure.get('scoring_status')}))
'''.replace('ROOT', repr(launch['root'])).replace('PID', str(launch['pid'])).replace('LOG', repr(launch['log']))
formal = json.loads(remote(code, host='4090'))
code = '''import pathlib,json,time,hashlib,shutil,subprocess
root=pathlib.Path(ROOT);request=root/'requests'/'1792911523173290976'
assert 'OutOfMemoryError'in(request/'failure.json').read_text()
dest=root.parent/('v362-service-oom-'+str(time.time_ns()));dest.mkdir()
shutil.copytree(request,dest/'failed-request')
for name in ['runtime.json','status.json','worker.log']:shutil.copy2(root/name,dest/name)
gpu=subprocess.check_output(['nvidia-smi','--id=0,1,2,3','--query-gpu=index,memory.used,memory.free','--format=csv'],text=True)
(dest/'gpu-memory.txt').write_text(gpu)
hashes={str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest()for p in dest.rglob('*')if p.is_file()}
(dest/'hashes.json').write_text(json.dumps(hashes,indent=2))
runtime=json.loads((root/'runtime.json').read_text());counts={}
for k,v in runtime['device_map'].items():counts[v]=counts.get(v,0)+1
print(json.dumps({'root':str(dest),'request':str(request),'request_sha256':hashlib.sha256((request/'request.json').read_bytes()).hexdigest(),'manifest_sha256':hashlib.sha256((dest/'hashes.json').read_bytes()).hexdigest(),'gpu_memory':gpu,'device_map':runtime['device_map']}))
'''.replace('ROOT', repr(service['root']))
model = json.loads(remote(code, host='3090'))
data = {'formal': formal, 'service': model, 'scope': 'preserved technical OOM; not completed model result or Mirage-negative'}
output.write_text(json.dumps(data, indent=2), encoding='utf-8')
print(json.dumps(data))
