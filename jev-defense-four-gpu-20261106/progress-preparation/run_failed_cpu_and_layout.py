import base64
from pathlib import Path
import sys
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
base=Path(__file__).resolve().parent
files={'reconstruct_failed_and_layout_cpu.py':base64.b64encode((base/'reconstruct_failed_and_layout_cpu.py').read_bytes()).decode(),
    'original_capacity_cpu_helpers.py':base64.b64encode((base.parent/'runtime-preparation/dependency-repair-01/audit_real_capacity.py').read_bytes()).decode()}
code='FILES='+repr(files)+'\n'+'''
import base64,json,os,subprocess,time
from pathlib import Path
base=Path('/home/researcher/jev-defense-four-gpu-20261106')
prep=base/'failed-input-CPU-preparation'/str(time.time_ns());prep.mkdir(parents=True)
for name,encoded in FILES.items():
 with(prep/name).open('xb')as handle:handle.write(base64.b64decode(encoded))
root=base/'failed-input-CPU-layout-audits'/prep.name
command=['/opt/whz/conda-envs/webmall-vlm/bin/python',str(prep/'reconstruct_failed_and_layout_cpu.py'),
 '--root',str(root),'--preservation',str(base/'failed-gui-service-preservation/1793982653388639508'),
 '--helper',str(prep/'original_capacity_cpu_helpers.py')]
result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=dict(os.environ,
 CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1'))
(prep/'stdout.txt').write_bytes(result.stdout);(prep/'stderr.txt').write_bytes(result.stderr)
print(json.dumps({'preparation':str(prep),'CPU_root':str(root),'exit_code':result.returncode,
 'stdout':result.stdout.decode(),'stderr_tail':result.stderr.decode()[-6000:]}))
'''
print(remote(code,timeout=240))
