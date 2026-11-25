import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
for host,root in [('3090','/home/researcher/jev-defense-four-gpu-20261106/online-three-service-group-1793985778592347799'),('4090','/data/researcher/jev-defense-four-gpu-20261106')]:
    code='''import json,hashlib
from pathlib import Path
r=Path(ROOT)
if HOST=='3090':
 names=['terminal-sha256.json','launcher-exit.json','primary/worker-exit.json','pplx_flash/worker-exit.json','primary/process.json','pplx_flash/process.json']
else:
 names=['gui-final-readiness-three-01/launch-spec.json','gui-outer-control-three-01/postexit-sha256.json','gui-outer-control-three-01/batch-postexit-sha256.json','gui-three-control-preparation-01/invocation.json','gui-batch-image-observer-three-01/status.json']
out={}
for n in names:
 p=r/n
 out[n]={'exists':p.is_file()}
 if p.is_file():
  raw=p.read_bytes();v=json.loads(raw)
  out[n].update(sha256=hashlib.sha256(raw).hexdigest(),value=v if 'sha256.json'not in n else {'entries':len(v)})
if HOST=='3090':out['top_names']=[p.name for p in r.iterdir()]
print(json.dumps(out))
'''
    print(host,remote('ROOT='+repr(root)+'\nHOST='+repr(host)+'\n'+code,host=host,timeout=45))
