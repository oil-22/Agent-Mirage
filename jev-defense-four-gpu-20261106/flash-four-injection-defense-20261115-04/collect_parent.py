"""Bind old completed native/GUI terminals and verify their processes exited."""
import json
import sys
from remote_util import HERE, remote, save

CODE = r'''
import hashlib,json,os,time
from pathlib import Path
study='flash-late-corruption-defense-20261115-02'
p=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation'if HOST=='3090'else'/data/researcher/jev-defense-four-gpu-20261106')/study
out=Path('/data/researcher/jev-defense-four-gpu-20261106')/study
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
def identity(pid):
 q=Path('/proc',str(pid))
 if not q.exists():return None
 s=(q/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':q.stat().st_uid,'command':(q/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
names=['launcher-process.json','primary/process.json','primary/status.json','primary/terminal.json','exit.json','postexit-seal.json']if HOST=='3090'else['batch/status.json','control/process.json','control/runner-process.json','control/exit.json','control/postexit-seal.json','control/batch-terminal-seal.json']
files={};processes=[]
for name in names+(['flash/service/process.json','flash/service/terminal.json']if HOST=='3090'else[]):
 q=(p if name.startswith('flash/')else out)/name
 assert q.is_file(),str(q)
 raw=q.read_bytes();v=json.loads(raw);files[name]={'sha256':sha(q)}
 if not name.endswith('seal.json'):files[name]['value']=v
 if isinstance(v,dict)and all(k in v for k in ['pid','uid','command','start_ticks']):
  a=identity(v['pid']);same=a is not None and a['state']not in ['Z','X']and all(a[k]==v[k]for k in ['pid','uid','command','start_ticks'])
  assert not same,'Completed old worker is still active'
  processes.append({'saved':v,'actual':a,'same':same})
phase='primary/status.json'if HOST=='3090'else'batch/status.json'
assert files[phase]['value']['phase']=='completed'and files[phase]['value']['expected']==12
print(json.dumps({'time':time.time(),'host':HOST,'package':str(p),'output':str(out),'manifest_sha256':sha(p/'manifest.json'),'files':files,'processes':processes,'old_terminals_immutable':True,'new_model_GUI_calls':0}))
'''


def main():
    host = sys.argv[1]
    path = HERE / ('prior-' + host + '.json')
    assert not path.exists()
    raw, operation = remote(host, 'HOST=' + repr(host) + '\n' + CODE, 'bind-completed-native-parent-' + host)
    value = json.loads(raw)
    save(path, {'operation': str(operation), 'result': value})
    print(json.dumps({'host': host, 'parent_files': len(value['files']),
                      'old_processes_verified_exited': len(value['processes'])}))


if __name__ == '__main__':
    main()
