from ops import remote

code=r'''
from pathlib import Path
import hashlib,json
r=Path('/home/researcher/jev-defense-four-gpu-20261106/bounded-evidence-20261109-02/worker/auxiliary');out=[]
for p in sorted(r.glob('*/seal.json')):
 m=json.loads(p.read_bytes())
 for name,h in m.items():assert hashlib.sha256((p.parent/name).read_bytes()).hexdigest()==h,name
 out.append({'id':p.parent.name,'text':(p.parent/'raw-output.txt').read_text(),'failure':json.loads((p.parent/'contract-failure.json').read_bytes())if(p.parent/'contract-failure.json').exists()else None})
print(json.dumps(out,ensure_ascii=False))
'''
out,path=remote('3090',code,'read-committed-new-outputs',timeout=45);print(out)
