import json
from ops import remote

code=r'''
from pathlib import Path
import json,os
b=Path('/home/researcher/jev-defense-four-gpu-20261106');c=b/'resource-attempt-20261106-01';out={}
for p in c.iterdir():
 if p.is_file()and('bounded' in p.name or p.suffix=='.log'):
  if 'bounded'in p.name:out[p.name]=p.read_bytes()[-6000:].decode(errors='replace')
for p in (c/'commands').glob('*bounded*'):out[str(p.relative_to(c))]=p.read_text()
r=b/'runtime-preparation/bounded-evidence-20261109-02/prelaunch-failures'
for p in r.glob('*/failure.json'):out[str(p)]=p.read_text()
print(json.dumps(out))
'''
out,path=remote('3090',code,'inspect-once-launch-admission',timeout=45)
print(out)
