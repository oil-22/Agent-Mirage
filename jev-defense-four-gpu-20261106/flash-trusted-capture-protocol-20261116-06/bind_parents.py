"""Small fresh bindings of old terminal receipts; no repeated full raw audits."""
import json
import sys
from remote_util import HERE, remote, save

CODE = r'''
import hashlib,json,os,time
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def identity(pid):
 p=Path('/proc',str(pid))
 if not p.exists():return None
 s=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':int(pid),'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
files={};processes=[]
for study,expected in [('flash-four-injection-defense-20261115-04',8),('buttons-native-trigger-supplement-20261116-05',2)]:
 package=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation'if HOST=='3090'else'/data/researcher/jev-defense-four-gpu-20261106')/study
 out=Path('/data/researcher/jev-defense-four-gpu-20261106')/study
 paths=[package/'manifest.json']+([out/n for n in ['launcher-process.json','primary/process.json','primary/status.json','primary/terminal.json','exit.json','postexit-seal.json']]+[package/'flash/service/process.json',package/'flash/service/terminal.json']if HOST=='3090'else[package/n for n in ['batch/status.json','control/process.json','control/runner-process.json','control/exit.json','control/postexit-seal.json']])
 for p in paths:
  v=json.loads(p.read_bytes());files[str(p)]={'sha256':sha(p)}
  if isinstance(v,dict)and all(k in v for k in ['pid','uid','command','start_ticks']):
   a=identity(v['pid']);same=a is not None and a['state']not in ['Z','X']and all(a[k]==v[k]for k in ['pid','uid','command','start_ticks']);assert not same
   processes.append({'saved':v,'actual':a})
  if p.name=='status.json':assert v['phase']=='completed'and v['expected']==expected
if HOST=='3090':
 p=Path('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/released.json');assert sha(p)=='2fb82487654ad92ca6c8f8fa324aa07643259a47bfc3d371c09cdf6eca98aa10';files[str(p)]={'sha256':sha(p)}
print(json.dumps({'host':HOST,'time':time.time(),'files':files,'processes':processes,'read_only':True,'new_model_GUI_calls':0}))
'''

if __name__ == '__main__':
    host = sys.argv[1]
    assert not (HERE / ('prior-' + host + '.json')).exists()
    raw, op = remote(host, 'HOST=' + repr(host) + '\n' + CODE, 'bind-prior-terminals-new-protocol-' + host)
    value = json.loads(raw)
    save(HERE / ('prior-' + host + '.json'), {'operation': str(op), 'result': value})
    print(json.dumps({'host': host, 'small_bound_terminal_files': len(value['files']), 'old_identities_verified_exited': len(value['processes'])}))
