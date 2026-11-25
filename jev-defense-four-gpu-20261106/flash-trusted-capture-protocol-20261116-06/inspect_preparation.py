"""Read-only resource, dependency and exact native-source inspection."""
import json
import sys
import time
from remote_util import HERE, remote, save, sha

CODE = r'''
import hashlib,importlib.util,json,os,subprocess,time
from pathlib import Path
def identity(pid):
 p=Path('/proc',str(pid))
 try:
  s=(p/'stat').read_text().rsplit(')',1)[1].split()
  return {'pid':int(pid),'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace').strip(),'start_ticks':s[19],'state':s[0]}
 except (FileNotFoundError,ProcessLookupError):return None
compute=[]
for line in subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True).splitlines():
 if line.strip():
  uuid,pid,used=[v.strip()for v in line.split(',')];compute.append({'uuid':uuid,'used_mib':used,'identity':identity(pid)})
sources={}
if HOST=='4090':
 root=Path('/data/researcher/jev-defense-validation-20261103/runtime-stage-01')
 for rel in ['native/run_reddit_internvl_smoke.py','upstream/browser_env/envs.py','upstream/browser_env/processors.py','upstream/browser_env/actions.py','upstream/browser_env/utils.py']:
  p=root/rel;sources[str(p)]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
 envpython=root/'env/bin/python'
 dep=subprocess.run([str(envpython),'-B','-c',"import json,sys,importlib.util;print(json.dumps({'python':sys.version,'modules':{n:importlib.util.find_spec(n) is not None for n in ['cryptography','nacl','PIL','numpy','playwright','requests']}}))"],capture_output=True,text=True)
 assert dep.returncode==0,dep.stderr
 dependencies=json.loads(dep.stdout)
else:dependencies=None
disk=[]
for p in [Path('/home/researcher'),Path('/data/researcher')]:
 s=os.statvfs(p);disk.append({'path':str(p),'free_bytes':s.f_bavail*s.f_frsize})
print(json.dumps({'time':time.time(),'host':HOST,'uid':os.getuid(),'GPU':subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.total,memory.free','--format=csv,noheader,nounits'],text=True),'compute':compute,'native_sources':sources,'dependencies':dependencies,'disk':disk,'new_model_GUI_calls':0,'read_only':True}))
'''

if __name__ == '__main__':
    host = sys.argv[1]
    raw, operation = remote(host, 'HOST=' + repr(host) + '\n' + CODE, 'trusted-capture-preparation-readonly-' + host)
    value = json.loads(raw)
    path = HERE / ('resource-' + host + '-' + str(time.time_ns()) + '.json')
    save(path, {'operation': str(operation), 'operation_seal_sha256': sha(operation / 'seal.json'), 'result': value})
    print(json.dumps({'receipt': str(path), 'result': value}))
