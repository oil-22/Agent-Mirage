"""Read only capacity-development progress, including raw verdict for local review."""
import json
from pathlib import Path
from remote import remote
here=Path(__file__).resolve().parent
launch=json.loads((here/'v8-capacity-replay-launch.json').read_text())
code='''import pathlib,json,time,subprocess,hashlib
root=pathlib.Path(ROOT);p=root/'summary.json';progress=root/'progress.json'
cases={}
for path in root.glob('*/response.json'):
 body=json.loads(path.read_text());cases[path.parent.name]={k:v for k,v in body.items()if k!='text'}
print(json.dumps({'time':time.time(),'summary':json.loads(p.read_text())if p.exists()else None,'progress':json.loads(progress.read_text())if progress.exists()else None,'summary_sha256':hashlib.sha256(p.read_bytes()).hexdigest()if p.exists()else None,'responses':cases,'log_tail':pathlib.Path(LOG).read_text()[-1200:],'gpu_memory':subprocess.check_output(['nvidia-smi','--id=0,1,2,3,4,5,6,7','--query-gpu=index,memory.used,memory.free','--format=csv'],text=True)}))
'''.replace('ROOT',repr(launch['root'])).replace('LOG',repr(launch['log']))
data=json.loads(remote(code,host='3090'))
(here/'v8-capacity-replay-progress.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print(json.dumps(data))
