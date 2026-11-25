"""Read-only resource ownership and public task-source discovery."""
import json
import time
from pathlib import Path
from remote_util import HERE, remote, save, sha

RESOURCE = r'''
import json,os,sys,time
from pathlib import Path
p=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/flash-native-source-loop-20261116-linked11')
sys.path.insert(0,str(p/'flash'))
from resource_guard import gpu_snapshot
snapshot=gpu_snapshot()
base=Path('/data/researcher/jev-defense-four-gpu-20261106')
s=os.statvfs(base)
print(json.dumps({'time':time.time(),'uid':os.getuid(),'snapshot':snapshot,
 'all_eight_empty_with_23000MiB':not snapshot['compute']and all(snapshot['gpu'][i]['free_mib']>=23000 for i in range(8)),
 'free_disk_bytes':s.f_bavail*s.f_frsize,'new_GPU_lock_or_model_allocation':False}))
'''

SOURCES = r'''
import hashlib,json,os,time
from pathlib import Path
root=Path('/data/researcher/jev-defense-four-gpu-20261106/evaluation-source-preparation-20261109-01')
files=[]
for q in sorted(root.rglob('*')):
 if q.is_file() and 'PRIVATE-evaluator-configs'not in q.parts and q.stat().st_size<2*1024**2:
  row={'path':str(q),'bytes':q.stat().st_size}
  if q.suffix in['.json','.py','.md']:
   text=q.read_text(errors='replace')
   if q.suffix=='.py':
    row['source_location_lines']=[line for line in text.splitlines()if any(k in line.lower()for k in['zipfile','/data/','archive','evaluator_configs_v1','source_root'])]
   elif q.suffix=='.json':
    try:v=json.loads(text)
    except ValueError:v={}
    if isinstance(v,dict):row['location_metadata']={k:x for k,x in v.items()if isinstance(x,(str,int,bool))and any(n in k.lower()for n in['root','path','archive','source','zip','bundle'])}
  files.append(row)
private=root/'collection/PRIVATE-evaluator-configs'
candidates=[Path('/data/researcher/mirage-trace'),Path('/data/researcher/MultiModel/mirage-trace'),Path('/home/researcher/MultiModel/mirage-trace'),Path('/data/researcher/mirage-bench')]
print(json.dumps({'time':time.time(),'uid':os.getuid(),'source_directory_files':files,
 'existing_PRIVATE_config_filenames':[p.name for p in sorted(private.glob('*.json'))],
 'candidate_roots':{str(p):p.exists()for p in candidates},'private_answers_exported':False,'new_model_GUI_calls':0}))
'''

def main():
    root=HERE/('source-resource-inspection-'+str(time.time_ns()))
    root.mkdir()
    values={}
    for host,code,label in [('3090',RESOURCE,'resource'),('4090',SOURCES,'public-source-locations')]:
        raw,operation=remote(host,code,'scale10-'+label)
        values[label]={'operation':str(operation),'result':json.loads(raw)}
        save(root/(label+'.json'),values[label])
    (root/'source.py').write_bytes(Path(__file__).read_bytes())
    save(root/'seal.json',{p.name:sha(p)for p in root.iterdir()if p.is_file()})
    pointer={'root':str(root),'seal_sha256':sha(root/'seal.json')}
    temporary=HERE/('.inspection-'+str(time.time_ns()))
    save(temporary,pointer)
    temporary.replace(HERE/'source-resource-inspection-current.json')
    print(json.dumps({'root':str(root),**values}))

if __name__=='__main__':main()
