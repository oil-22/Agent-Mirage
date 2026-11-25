"""Submit only the new finite eight-task initialization admission, once."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'full-gui-bounded-evidence-20261109-03'))
from remote_control import remote,save,sha


def main():
    assert not (HERE/'native-preflight-submission-intent.json').exists()
    source=HERE/'source-bindings-1794217976714587500/receipt.json'
    bindings=source.read_bytes()
    assert json.loads(bindings)['complete_GUI_launcher_ready']is False
    files={name:(HERE/name).read_bytes()for name in ['native_environment.py','native_task_preflight.py']}
    files['bindings-public.json']=bindings
    expected={name:hashlib.sha256(raw).hexdigest()for name,raw in files.items()}
    encoded={name:base64.b64encode(raw).decode()for name,raw in files.items()}
    root='/data/researcher/jev-defense-four-gpu-20261106/independent-native-bindings-20261109-19'
    save(HERE/'native-preflight-submission-intent.json',{'time':time.time(),'root':root,'source_SHA':expected,
         'once_only':True,'model_GPU_agent_scorer_calls':0,'browser_initializations_and_recaptures':8,
         'observation_timeout_requires_existing_handle_inspection_not_resubmission':True})
    code='ROOT='+repr(root)+'\nFILES='+repr(encoded)+'\nEXPECTED='+repr(expected)+'\n'+r'''
from pathlib import Path
import base64,hashlib,json,os,subprocess,time
r=Path(ROOT);assert os.getuid()==1015 and not r.exists();r.mkdir();package=r/'package';package.mkdir()
for name,encoded in FILES.items():
 raw=base64.b64decode(encoded);assert hashlib.sha256(raw).hexdigest()==EXPECTED[name]
 with(package/name).open('xb')as stream:stream.write(raw)
with(package/'source-seal.json').open('x')as stream:json.dump(EXPECTED,stream,indent=2)
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',TOKENIZERS_PARALLELISM='false',PYTHONDONTWRITEBYTECODE='1')
argv=['/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python','-B','-u',str(package/'native_task_preflight.py'),'--output',str(r/'attempt-01')]
log=(r/'attempt-01.log').open('xb');os.chmod(log.name,0o600)
child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=env,cwd=str(package),start_new_session=True)
p=Path('/proc',str(child.pid));tail=(p/'stat').read_text().rsplit(')',1)[1].split()
value={'time':time.time(),'pid':child.pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':tail[19],
       'source_SHA':EXPECTED,'GPU_model_agent_scorer_calls':0,'once_only':True}
assert value['command']==' '.join(argv)
with(r/'launch.json').open('x')as stream:json.dump(value,stream,indent=2)
print(json.dumps(value))
'''
    output,operation=remote('4090',code,'launch-eight-native-task-initializations-once-no-model',timeout=55)
    save(HERE/'native-preflight-submission.json',{'value':json.loads(output),'operation':str(operation)})
    print(json.dumps({'value':json.loads(output),'operation':str(operation)},ensure_ascii=False))


if __name__=='__main__':main()
