"""Read the exact once-only command/claim/launcher evidence, never resubmit."""
import json
import time
from orchestrate import admitted, remote, COMMON, save, sha, HERE, PACKAGE, REMOTE_PACKAGE, OUTPUT

def main():
    admitted()
    source='PACKAGE='+repr(REMOTE_PACKAGE)+'\nOUTPUT='+repr(OUTPUT)+'\n'+COMMON+r'''
base=Path('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01')
name='remaining28-source-reference-gui-20261110-40'
out={'time':time.time(),'remote_read_only':True,'new_model_GUI_calls':0,'files':{},'prelaunch_failures':[]}
for path in[base/'commands'/(name+'.json'),base/'commands'/(name+'.claimed'),base/(name+'-launch.json')]:
 if path.is_file():out['files'][str(path)]={'sha256':sha(path),'value':json.loads(path.read_bytes())}
record=base/(name+'-launch.json')
if record.exists():
 r=json.loads(record.read_bytes());out['launcher_actual']=identity(r['pid'])
 exitfile=base/('child-'+str(r['pid'])+'-exit.json')
 if exitfile.exists():out['child_exit']=json.loads(exitfile.read_bytes())
for p in[base/(name+'.log'),base/'holder.log']:
 if p.exists():out['files'][str(p)]={'bytes':p.stat().st_size,'sha256':sha(p),'tail':p.read_bytes()[-4000:].decode(errors='replace')}
for p in sorted((Path(PACKAGE)/'prelaunch-failures').glob('*/failure.json')):
 out['prelaunch_failures'].append({'path':str(p),'sha256':sha(p),'value':json.loads(p.read_bytes())})
out['output_exists']=Path(OUTPUT).exists()
print(json.dumps(out))
'''
    raw, operation=remote('3090',source,'inspect-exact-approved28-command-claim-prelaunch-no-resubmit',timeout=55)
    result=json.loads(raw);out=HERE/('submission-evidence-'+str(time.time_ns()));out.mkdir()
    save(out/'evidence.json',result);save(out/'operation.json',dict(operation=str(operation)))
    save(out/'seal.json',{p.name:sha(p)for p in out.iterdir()if p.is_file()})
    print(json.dumps(dict(evidence=str(out),result=result)))

if __name__=='__main__':main()
