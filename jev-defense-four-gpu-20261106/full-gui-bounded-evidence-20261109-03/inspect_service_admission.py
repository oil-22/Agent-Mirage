from remote_control import remote
code=r'''
from pathlib import Path
import json
b=Path('/home/researcher/jev-defense-four-gpu-20261106');name='full-gui-bounded-evidence-20261109-03';c=b/'resource-attempt-20261106-01';out={}
for p in c.glob(name+'*'):
 if p.is_file():out[p.name]=p.read_bytes()[-7000:].decode(errors='replace')
for p in(b/'runtime-preparation'/name/'prelaunch-failures').glob('*/failure.json'):out[str(p)]=p.read_text()
print(json.dumps(out))
'''
out,path=remote('3090',code,'inspect-service-admission-actual',timeout=45);print(out)
