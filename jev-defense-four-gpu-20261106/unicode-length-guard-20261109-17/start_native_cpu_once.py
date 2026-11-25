"""One new background CPU test with a recoverable exact process handle."""
import base64
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'full-gui-bounded-evidence-20261109-03'))
from remote_control import remote,save,sha

assert not(HERE/'native-CPU-submission-intent.json').exists()
root='/home/researcher/jev-defense-four-gpu-20261106/unicode-length-guard-20261109-17'
files={n:base64.b64encode((HERE/n).read_bytes()).decode()for n in ['unicode_length_guard.py','native_cpu_check.py']}
expected={n:sha(HERE/n)for n in files}
save(HERE/'native-CPU-submission-intent.json',{'time':time.time(),'once_only':True,'root':root,'source_SHA':expected,
     'new_model_GPU_calls':0,'ambiguous_observation_requires_inspection_not_resubmit':True})
code='ROOT='+repr(root)+'\nFILES='+repr(files)+'\nEXPECTED='+repr(expected)+'\n'+r'''
from pathlib import Path
import base64,hashlib,json,os,subprocess,time
r=Path(ROOT);assert os.getuid()==1033 and not r.exists();r.mkdir()
p=r/'CPU-package';p.mkdir()
for name,encoded in FILES.items():
 raw=base64.b64decode(encoded);assert hashlib.sha256(raw).hexdigest()==EXPECTED[name]
 with(p/name).open('xb')as f:f.write(raw)
with(r/'source-seal.json').open('x')as f:json.dump(EXPECTED,f,indent=2)
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',TOKENIZERS_PARALLELISM='false',HF_HUB_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1')
command=['/opt/whz/conda-envs/webmall-vlm/bin/python','-u',str(p/'native_cpu_check.py'),'--output',str(r/'attempt-01')]
log=(r/'attempt-01.log').open('xb')
child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=env,cwd=str(p),start_new_session=True)
proc=Path('/proc',str(child.pid));tail=(proc/'stat').read_text().rsplit(')',1)[1].split()
value={'pid':child.pid,'uid':proc.stat().st_uid,'command':command,'start_ticks':tail[19],'time':time.time(),'CPU_only':True,'no_model_weights_loaded':True}
with(r/'launch.json').open('x')as f:json.dump(value,f,indent=2)
print(json.dumps(value))
'''
out,op=remote('3090',code,'launch-new-length17-native-CPU-test-once',timeout=55)
save(HERE/'native-CPU-submission.json',{'result':json.loads(out),'operation':str(op)})
print(json.dumps({'result':json.loads(out),'operation':str(op)},ensure_ascii=False))
