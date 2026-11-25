"""Freeze and once-only launch the new finite real repair preflight."""
from pathlib import Path
import argparse
import ast
import base64
import hashlib
import io
import json
import os
import shutil
import zipfile
from ops import HERE,BASE,ROOT,PACKAGE,remote,save,sha

def freeze():
    source=HERE/'runtime-package';dest=HERE/'controls-package'
    assert not dest.exists();dest.mkdir()
    for name in ['release','control-inputs','grammar-vendor']:
        shutil.copytree(source/name,dest/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in ['model_runtime.py','resource_gate.py','preflight_support.py','aux_identity_support.py','four_gpu_contract.py',
                 'primary-reference.json','auxiliary-identity-reference.json','controls-plan.json','bounded_schema.py','native_format_bridge.py']:
        shutil.copy2(source/name,dest/name)
    shutil.copy2(HERE/'controls_worker.py',dest/'controls_worker.py')
    launcher=(BASE/'full-gui-single-evidence-20261108-01/runtime-package/launch_gui_service_once.py').read_text(encoding='utf8')
    launcher=launcher.replace('full-gui-single-evidence-20261108-01','bounded-evidence-20261109-02').replace('launch_gui_service_once.py','launch_controls_once.py').replace('gpu_server.py','controls_worker.py').replace('GUI_is_external_and_bound_to_plan','no_GUI_in_control_batch')
    (dest/'launch_controls_once.py').write_text(launcher,encoding='utf8',newline='\n')
    for p in dest.rglob('*.py'):ast.parse(p.read_text(encoding='utf8'),filename=str(p))
    check=HERE/'CPU-native-tokenizer-linked04-result.json'
    assert json.loads(check.read_bytes())['result']['returncode']==0
    lease=BASE/'resource-attempt-20261106-01/lease.json';l=json.loads(lease.read_bytes())
    m={'schema':'new-bounded-source-evidence-controls-v1','authorized_finite_joint_development':True,
       'authorization':'User sustained goal: 做实验做到防御有效果为止; new structural-only auxiliary condition',
       'expected_holder':l['holder'],'lease_sha256':sha(lease),'output':ROOT,'no_old_terminal_resume':True,
       'condition_and_tradeoffs_sha256':sha(HERE/'condition-and-tradeoffs.json'),'source_bindings_sha256':sha(HERE/'source-bindings.json'),
       'source_first_PRIVATE_expectation_seal_sha256':sha(HERE/'PRIVATE-source-first-expectations-seal.json'),
       'PRIVATE_expectations_excluded_from_worker':True,'native_CPU_receipt_sha256':sha(check),
       'worker_source_sha256':sha(dest/'controls_worker.py'),
       'files':{p.relative_to(dest).as_posix():sha(p)for p in sorted(dest.rglob('*'))if p.is_file()}}
    save(dest/'manifest.json',m)
    save(HERE/'controls-freeze.json',{'manifest_sha256':sha(dest/'manifest.json'),'plan_sha256':sha(dest/'controls-plan.json'),
         'auxiliary_cap':6,'main_cap':0,'format_retries':0,'actor_GUI_scorer_paid':0,'formal_efficacy':False})
    print(json.dumps({'frozen':str(dest),'manifest_sha256':sha(dest/'manifest.json'),'model_calls':0}))


def stage():
    dest=HERE/'controls-package';msha=sha(dest/'manifest.json')
    blob=io.BytesIO()
    with zipfile.ZipFile(blob,'w',zipfile.ZIP_DEFLATED)as z:
        for p in sorted(dest.rglob('*')):
            if p.is_file():z.writestr(p.relative_to(dest).as_posix(),p.read_bytes())
    code='TARGET='+repr(PACKAGE)+'\nMSHA='+repr(msha)+'\n'+r'''
from pathlib import Path
import base64,hashlib,io,json,os,zipfile
r=Path(TARGET);r.mkdir(parents=True,exist_ok=False)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD)))as z:
 for n in z.namelist():assert(r/n).resolve().is_relative_to(r.resolve())
 z.extractall(r)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(r/'manifest.json')==MSHA
m=json.loads((r/'manifest.json').read_bytes())
for n,h in m['files'].items():assert sha(r/n)==h,n
assert not any('PRIVATE'in p.name or p.name=='private.token'for p in r.rglob('*'))
print(json.dumps({'staged':str(r),'uid':os.getuid(),'files_SHA_verified':len(m['files']),'model_calls':0,'manifest_sha256':MSHA}))
'''
    out,target=remote('3090',code,'stage-new-controls',timeout=90,private_prefix='PAYLOAD='+repr(base64.b64encode(blob.getvalue()).decode())+'\n')
    save(HERE/'controls-stage.json',{'result':json.loads(out),'operation':str(target)});print(out)

def launch():
    dest=HERE/'controls-package';assert not(HERE/'controls-launch.json').exists()
    argv=['/opt/whz/conda-envs/webmall-vlm/bin/python',PACKAGE+'/launch_controls_once.py','--manifest',PACKAGE+'/manifest.json',
          '--manifest-sha256',sha(dest/'manifest.json'),'--output',ROOT]
    command={'action':'launch','argv':argv,'script_sha256':sha(dest/'launch_controls_once.py')}
    code='COMMAND='+repr(command)+'\nOUTPUT='+repr(ROOT)+'\n'+r'''
from pathlib import Path
import hashlib,json,os,subprocess,time
b=Path('/home/researcher/jev-defense-four-gpu-20261106');assert os.getuid()==1033
assert not Path(OUTPUT).exists()
p=Path(COMMAND['argv'][1]);assert hashlib.sha256(p.read_bytes()).hexdigest()==COMMAND['script_sha256']
lease_path=b/'resource-attempt-20261106-01/lease.json';lease=json.loads(lease_path.read_bytes());h=lease['holder'];p=Path('/proc',str(h['pid']))
assert p.stat().st_uid==h['uid']and(p/'stat').read_text().rsplit(')',1)[1].split()[19]==h['start_ticks']
assert(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip()==h['command']
for row in lease['lock_records']:
 fd=p/'fd'/str(row['fd']);info=(p/'fdinfo'/str(row['fd'])).read_text()
 assert os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']and'WRITE '+str(h['pid'])in info
target={r['uuid']for r in lease['gpu']}
gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
for row in gpu.splitlines():
 i,u,f=[x.strip()for x in row.split(',')]
 if int(i)in[4,5,6,7]:assert u in target and int(f)>=23000
compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
assert not any(v.split(',')[0].strip()in target for v in compute.splitlines()if v.strip())
commands=b/'resource-attempt-20261106-01/commands'
assert all(p.with_suffix('.claimed').exists()for p in commands.glob('*.json'))
path=commands/'bounded-evidence-20261109-02.json';temp=commands/('.new-bounded-'+str(os.getpid())+'.tmp')
with temp.open('xb')as f:f.write(json.dumps(COMMAND,ensure_ascii=False,indent=2).encode());f.flush();os.fsync(f.fileno())
os.link(temp,path);temp.unlink()
print(json.dumps({'submitted_once':True,'command_file':str(path),'output':OUTPUT,'manifest_sha256':COMMAND['argv'][5],'actual_owned_locks':9,'actual_free_GPU_min_MiB':23000,'time':time.time()}))
'''
    out,target=remote('3090',code,'submit-new-controls-once',timeout=55)
    save(HERE/'controls-launch.json',{'result':json.loads(out),'operation':str(target)});print(out)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','stage','launch']);a=p.parse_args()
    {'freeze':freeze,'stage':stage,'launch':launch}[a.action]()
