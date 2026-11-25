import base64
import json
from remote_control import HERE,remote,save,sha

package='/data/researcher/jev-defense-four-gpu-20261106/evaluation-source-preparation-20261109-01'
source=HERE/'restore_public_task_catalog_worker.py'
code='ROOT='+repr(package)+'\nSHA='+repr(sha(source))+'\n'+r'''
from pathlib import Path
import base64,hashlib,json,os,subprocess,time
r=Path(ROOT);r.mkdir(exist_ok=False);p=r/'restore_public_task_catalog_worker.py'
p.write_bytes(base64.b64decode(PAYLOAD));assert hashlib.sha256(p.read_bytes()).hexdigest()==SHA
argv=['/data/researcher/venvs/qwen35-9b-full-20261019/bin/python','-B','-u',str(p),'--output',str(r/'collection')]
with(r/'worker.log').open('xb')as log:
 child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
   env={**os.environ,'CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2','PYTHONDONTWRITEBYTECODE':'1'},start_new_session=True)
proc=Path('/proc',str(child.pid));identity={'pid':child.pid,'uid':proc.stat().st_uid,
 'full_command':(proc/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),
 'start_ticks':(proc/'stat').read_text().rsplit(')',1)[1].split()[19]}
assert identity['uid']==1015 and identity['full_command']==' '.join(argv)
result={'identity':identity,'argv':argv,'root':str(r),'CPU_cores_for_decompression':2,'model_GUI_calls':0,'no_automatic_retry':True,'time':time.time()}
(r/'once-only-launch.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result))
'''
out,path=remote('4090',code,'restore-independent-public-task-sources-once',timeout=45,
    private_prefix='PAYLOAD='+repr(base64.b64encode(source.read_bytes()).decode())+'\n')
save(HERE/'public-task-source-launch.json',{'result':json.loads(out),'operation':str(path),'source_sha256':sha(source)})
print(out)
