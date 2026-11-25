"""One new background CPU test with a recoverable exact process handle."""
import base64
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'full-gui-bounded-evidence-20261109-03'))
from remote_control import remote,save,sha

assert not(HERE/'native-CPU-linked02-submission-intent.json').exists()
root='/home/researcher/jev-defense-four-gpu-20261106/unicode-length-guard-20261109-17'
files={n:base64.b64encode((HERE/n).read_bytes()).decode()for n in ['unicode_length_guard.py','native_cpu_check_linked02.py']}
expected={n:sha(HERE/n)for n in files}
save(HERE/'native-CPU-linked02-submission-intent.json',{'time':time.time(),'once_only':True,'root':root,'source_SHA':expected,
     'new_model_GPU_calls':0,'ambiguous_observation_requires_inspection_not_resubmit':True})
code='ROOT='+repr(root)+'\nFILES='+repr(files)+'\nEXPECTED='+repr(expected)+'\n'+r'''
from pathlib import Path
import base64,hashlib,json,os,subprocess,time
r=Path(ROOT);assert os.getuid()==1033 and r.exists() and not (r/'attempt-02').exists();p0=r/'attempt-01';assert (p0/'seal.json').is_file() and (p0/'failure.json').is_file();old=json.loads((r/'launch.json').read_bytes());assert not Path('/proc',str(old['pid'])).exists()
p=r/'CPU-package-linked02';assert not p.exists();p.mkdir()
for name,encoded in FILES.items():
 raw=base64.b64decode(encoded);assert hashlib.sha256(raw).hexdigest()==EXPECTED[name]
 with(p/name).open('xb')as f:f.write(raw)
with(r/'source-seal-linked02.json').open('x')as f:json.dump(EXPECTED,f,indent=2)
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',TOKENIZERS_PARALLELISM='false',HF_HUB_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1')
command=['/opt/whz/conda-envs/webmall-vlm/bin/python','-u',str(p/'native_cpu_check_linked02.py'),'--output',str(r/'attempt-02')]
log=(r/'attempt-02.log').open('xb')
child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=env,cwd=str(p),start_new_session=True)
proc=Path('/proc',str(child.pid));tail=(proc/'stat').read_text().rsplit(')',1)[1].split()
value={'pid':child.pid,'uid':proc.stat().st_uid,'command':command,'start_ticks':tail[19],'time':time.time(),'CPU_only':True,'no_model_weights_loaded':True}
with(r/'launch-linked02.json').open('x')as f:json.dump(value,f,indent=2)
print(json.dumps(value))
'''
out,op=remote('3090',code,'launch-length17-native-CPU-linked02-test-only-repair',timeout=55)
save(HERE/'native-CPU-linked02-submission.json',{'result':json.loads(out),'operation':str(op)})
print(json.dumps({'result':json.loads(out),'operation':str(op)},ensure_ascii=False))
