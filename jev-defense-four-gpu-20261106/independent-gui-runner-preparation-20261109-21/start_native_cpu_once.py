"""Once-only background native CPU admission; no GPU/weights/model generation."""
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
    assert not(HERE/'native-CPU-submission-intent.json').exists()
    root='/home/researcher/jev-defense-four-gpu-20261106/independent-gui-runner-preparation-20261109-21'
    files={'complete_actor_history.py':(HERE/'prepared-source-linked03/complete_actor_history.py').read_bytes(),
           'native_history_wire_cpu.py':(HERE/'native_history_wire_cpu.py').read_bytes()}
    expected={name:hashlib.sha256(raw).hexdigest()for name,raw in files.items()}
    encoded={name:base64.b64encode(raw).decode()for name,raw in files.items()}
    save(HERE/'native-CPU-submission-intent.json',{'time':time.time(),'root':root,'source_SHA':expected,
             'once_only':True,'weights_GPU_model_GUI_scorer_calls':0,
             'timeout_requires_same_handle_inspection_never_resubmission':True})
    code='ROOT='+repr(root)+'\nFILES='+repr(encoded)+'\nEXPECTED='+repr(expected)+'\n'+r'''
from pathlib import Path
import base64,hashlib,json,os,subprocess,time
r=Path(ROOT);assert os.getuid()==1033 and not r.exists();r.mkdir();package=r/'package';package.mkdir()
for name,encoded in FILES.items():
 raw=base64.b64decode(encoded);assert hashlib.sha256(raw).hexdigest()==EXPECTED[name]
 with(package/name).open('xb')as stream:stream.write(raw)
with(package/'source-seal.json').open('x')as stream:json.dump(EXPECTED,stream,indent=2)
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',TOKENIZERS_PARALLELISM='false',PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
argv=['/opt/whz/conda-envs/webmall-vlm/bin/python','-B','-u',str(package/'native_history_wire_cpu.py'),'--output',str(r/'attempt-01')]
log=(r/'attempt-01.log').open('xb')
child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=env,cwd=str(package),start_new_session=True)
p=Path('/proc',str(child.pid));tail=(p/'stat').read_text().rsplit(')',1)[1].split()
value={'time':time.time(),'pid':child.pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':tail[19],
       'source_SHA':EXPECTED,'GPU_model_agent_scorer_calls':0,'once_only':True}
assert value['command']==' '.join(argv)
with(r/'launch.json').open('x')as stream:json.dump(value,stream,indent=2)
print(json.dumps(value))
'''
    output,operation=remote('3090',code,'launch-native-full-history21-CPU-once-no-weights',timeout=55)
    save(HERE/'native-CPU-submission.json',{'value':json.loads(output),'operation':str(operation)})
    print(output)


if __name__=='__main__':main()
