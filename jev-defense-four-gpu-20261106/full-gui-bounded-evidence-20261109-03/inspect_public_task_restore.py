from remote_control import remote
code=r'''
from pathlib import Path
import hashlib,json,os,time
r=Path('/data/researcher/jev-defense-four-gpu-20261106/evaluation-source-preparation-20261109-01');out={'read_only':True,'models_GUI_calls':0}
launch=json.loads((r/'once-only-launch.json').read_bytes());record=launch['identity'];p=Path('/proc',str(record['pid']))
if p.exists():
 actual={'pid':record['pid'],'uid':p.stat().st_uid,'full_command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),
 'start_ticks':(p/'stat').read_text().rsplit(')',1)[1].split()[19]}
 assert actual==record;out['actual_process']=actual
else:out['actual_process_exited']=True
c=r/'collection'
for name in ['receipt.json','failure.json']:
 p=c/name
 if p.exists():out[name]=json.loads(p.read_bytes())
progress=sorted(c.glob('source-progress-*.json'))
if progress:out['progress']=json.loads(progress[-1].read_bytes())
if(c/'public-task-catalog.json').exists():
 seal=json.loads((c/'seal.json').read_bytes())
 for n,h in seal.items():assert hashlib.sha256((c/n).read_bytes()).hexdigest()==h,n
 out['public_catalog_sha256']=hashlib.sha256((c/'public-task-catalog.json').read_bytes()).hexdigest()
 out['all_original_sources_SHA_verified']=len(seal)
 out['public_catalog']=json.loads((c/'public-task-catalog.json').read_bytes())
print(json.dumps(out,ensure_ascii=False))
'''
out,path=remote('4090',code,'inspect-public-catalog-restoration',timeout=60);print(out)
