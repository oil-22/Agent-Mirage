"""Read immutable terminal receipts and actual identities after the parent audit."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent/'flash-late-corruption-defense-20261115-02'
spec = importlib.util.spec_from_file_location('parent_readonly', PRIOR/'control.py')
parent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parent)

def main():
    assert (PRIOR/'completed-publication-current.json').exists()
    assert (PRIOR/'completed-group-audit-current.json').exists()
    m = parent.manifest()
    for host in ['3090', '4090']:
        target = HERE/('prior-'+host+'.json')
        assert not target.exists()
        code = 'P='+repr(m['package'+host])+'\nO='+repr(m['output3090'])+'\nHOST='+repr(host)+'\n'+r'''
import hashlib,json,os,time
from pathlib import Path
p=Path(P);o=Path(O);base=o if HOST=='3090'else p
names=['primary/status.json','primary/terminal.json','exit.json','postexit-seal.json','launcher-process.json','primary/process.json','flash/service/process.json']if HOST=='3090'else['batch/status.json','control/exit.json','control/postexit-seal.json','control/batch-terminal-seal.json','control/process.json','control/runner-process.json']
files={};processes=[]
for name in names:
 q=(p if name.startswith('flash/')else base)/name
 raw=q.read_bytes();v=json.loads(raw)
 files[name]={'sha256':hashlib.sha256(raw).hexdigest()}
 if name not in ['postexit-seal.json','control/postexit-seal.json','control/batch-terminal-seal.json']:files[name]['value']=v
 if all(k in v for k in ['pid','uid','command','start_ticks']):
  proc=Path('/proc',str(v['pid']));actual=None
  if proc.exists():
   s=(proc/'stat').read_text().rsplit(')',1)[1].split();actual={'pid':v['pid'],'uid':proc.stat().st_uid,'command':(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
  same=actual is not None and actual['state']not in ['Z','X']and all(actual[k]==v[k]for k in ['uid','command','start_ticks'])
  assert not same,'Parent worker still live'
  processes.append({'saved':v,'current':actual,'same_live':same})
phase=files['primary/status.json'if HOST=='3090'else'batch/status.json']['value']
assert phase['phase']=='completed'and phase['expected']==phase.get('done',phase.get('completed'))==12
print(json.dumps({'time':time.time(),'host':HOST,'uid':os.getuid(),'package':str(p),'output':str(o),'files':files,'processes':processes,'expected_trajectories':12,'all_twelve_terminal':True,'new_model_GUI_calls':0}))
'''
        raw, operation = parent.remote(host, code, 'new-mask-parent-twelve-completion-readonly')
        parent.save(target, {'operation': str(operation), 'result': json.loads(raw)})
        print(json.dumps({'host': host, 'parent_all12_terminal_and_identities_exited': True}))

if __name__ == '__main__':
    main()
