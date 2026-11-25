"""Bind latest completed parent identities/seals; do not reread full raw tensors."""
import json
import sys
from remote_util import HERE, remote, save, sha


def main():
    host = sys.argv[1]; target = HERE / ('completed-parent-' + host + '.json')
    assert host in ['3090','4090'] and not target.exists()
    code = 'HOST=' + repr(host) + '\n' + r'''
import hashlib,json,os,time
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def identity(pid):
 p=Path('/proc',str(pid))
 if not p.exists():return None
 s=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
study='flash-trusted-capture-protocol-20261116-06'
p=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation')/study if HOST=='3090'else Path('/data/researcher/jev-defense-four-gpu-20261106')/study/'runtime'
o=Path('/data/researcher/jev-defense-four-gpu-20261106')/study/'model-attempt-01'
files={};processes=[]
paths=[p/'manifest.json']+([o/n for n in['launcher-process.json','primary/process.json','primary/status.json','primary/terminal.json','exit.json','released.json','postexit-seal.json']]+[p/'flash/service/process.json',p/'flash/service/terminal.json']if HOST=='3090'else[p/n for n in['batch/status.json','control/process.json','control/runner-process.json','control/exit.json','control/postexit-seal.json']])
for q in paths:
 v=json.loads(q.read_bytes());files[str(q)]={'sha256':sha(q)}
 if isinstance(v,dict)and all(k in v for k in['pid','uid','command','start_ticks']):
  a=identity(v['pid']);assert a is None or a['state']in['X','Z']or any(a[k]!=v[k]for k in['uid','command','start_ticks']);processes.append({'saved':v,'actual':a})
 if q.name=='status.json':assert v['phase']=='completed'and v['expected']==2
print(json.dumps({'host':HOST,'time':time.time(),'files':files,'processes':processes,'read_only':True,'new_model_GUI_calls':0}))
'''
    raw, op = remote(host, code, 'bind-latest-completed-source-parent-identities')
    save(target, {'operation': str(op), 'result': json.loads(raw)})
    print(json.dumps({'host': host, 'new_model_GUI_calls': 0, 'receipt': str(target), 'sha256': sha(target)}))


if __name__ == '__main__':
    main()
