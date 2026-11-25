"""Read-only binding of the immutable ten-trajectory completed parent."""
import json
import time
from remote_util import HERE,remote,save,sha

CODE=r'''
import hashlib,json,os,time
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def identity(pid):
 p=Path('/proc',str(pid))
 if not p.exists():return None
 s=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
study='flash-native-source-loop-20261116-linked11'
p=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation')/study if HOST=='3090'else Path('/data/researcher/jev-defense-four-gpu-20261106')/study/'runtime'
o=Path('/data/researcher/jev-defense-four-gpu-20261106')/study/'model-attempt-01'
assert sha(p/'manifest.json')=='c6b18f57e714100a2449a4c18a8f04de9cde014d95c587b711e72630db143e70'
files={};processes=[]
paths=[p/'manifest.json']+([o/n for n in ['launcher-process.json','lease.json','primary/process.json','primary/status.json','primary/terminal.json','exit.json','released.json','postexit-seal.json']]+[p/'flash/service/process.json',p/'flash/service/terminal.json']if HOST=='3090'else[p/n for n in ['batch/status.json','control/process.json','control/runner-process.json','control/exit.json','control/postexit-seal.json','control/batch-terminal-seal.json']])
if HOST=='4090':
 paths+=list((p/'batch/runs').glob('*/attempt-*/terminal.json'))+list((p/'batch/runs').glob('*/attempt-*/seal.json'))
 for q in(p/'batch').rglob('*process*.json'):
  if q not in paths:paths.append(q)
for q in paths:
 v=json.loads(q.read_bytes());files[str(q)]={'sha256':sha(q)}
 if isinstance(v,dict)and all(k in v for k in ['pid','uid','command','start_ticks']):
  a=identity(v['pid']);assert a is None or a['state']in['X','Z']or any(a[k]!=v[k]for k in ['uid','command','start_ticks'])
  processes.append({'saved':v,'actual':a})
 if q.name=='status.json':assert v['phase']=='completed'and v['expected']==10
 if q.name=='released.json':assert v['fresh_lease_locks_closed']==17
print(json.dumps({'host':HOST,'time':time.time(),'files':files,'processes':processes,
 'completed_parent_manifest_sha256':sha(p/'manifest.json'),'old_all_ten_terminal':True,
 'read_only':True,'new_model_GUI_calls':0}))
'''

def main():
 for host in ['3090','4090']:
  dest=HERE/('completed-scale-parent-'+host+'.json');assert not dest.exists()
  raw,op=remote(host,'HOST='+repr(host)+'\n'+CODE,'bind-completed-scale-parent-'+host)
  v=json.loads(raw);save(dest,{'operation':str(op),'result':v})
  print(json.dumps({'host':host,'files_bound':len(v['files']),'exited_identities':len(v['processes']),'sha256':sha(dest)}))

if __name__=='__main__':main()
