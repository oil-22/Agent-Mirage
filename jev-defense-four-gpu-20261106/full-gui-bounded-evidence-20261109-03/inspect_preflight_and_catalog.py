from remote_control import remote,ROOT4090
code='ROOT='+repr(ROOT4090)+'\n'+r'''
from pathlib import Path
import json,os,time
r=Path(ROOT);out={'read_only':True,'model_GUI_scorer_calls':0,'preflight_files':{}}
for name in ['environment-preflight/receipt.json','environment-preflight/initial.png','environment-preflight/same-live-recapture.png']:
 p=r/name
 if p.exists():out['preflight_files'][name]=json.loads(p.read_bytes())if p.suffix=='.json'else{'bytes':p.stat().st_size}
out['native_preflight_processes']=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  if p.stat().st_uid!=os.getuid():continue
  cmd=(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip()
  if 'environment_preflight.py'in cmd:out['native_preflight_processes'].append({'pid':int(p.name),'uid':p.stat().st_uid,'full_command':cmd})
 except(OSError,UnicodeError):pass
roots=[Path('/data/researcher/vwa100-2026-10-09'),
 Path('/data/researcher/jev-defense-validation-20261103/runtime-stage-01/upstream/config_files'),
 Path('/data/researcher/jev-defense-validation-20261103/runtime-stage-01/upstream/config_files/vwa'),
 Path('/data/researcher/jev-defense-validation-20261103/task-restore-1793683370167273452')]
out['public_task_catalog_discovery_names_only']={str(p):{'exists':p.exists(),'children':sorted(x.name for x in p.iterdir())[:60]if p.is_dir()else[]}for p in roots}
print(json.dumps(out,ensure_ascii=False))
'''
out,path=remote('4090',code,'read-only-preflight-and-public-catalog-discovery',timeout=45)
print(out)
