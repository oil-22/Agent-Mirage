"""Explicit sequential staging and once-only submits; never resumes old jobs."""
import argparse,base64,hashlib,io,json,os,secrets,shutil,sys,time,zipfile
from pathlib import Path
from remote_control import HERE,BASE,ROOT3090,ROOT4090,remote,save,sha
RUNTIME=HERE/'runtime-package'
REMOTE_PACKAGE='/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/full-gui-single-evidence-20261108-01'

def payload(package):
    f=io.BytesIO()
    with zipfile.ZipFile(f,'w',zipfile.ZIP_DEFLATED) as z:
        for p in package.rglob('*'):
            if p.is_file():z.writestr(p.relative_to(package).as_posix(),p.read_bytes())
    return base64.b64encode(f.getvalue()).decode()

def stage():
    assert not (RUNTIME/'manifest.json').exists()
    code=r'''
from pathlib import Path
import base64,hashlib,json
b=Path('/data/researcher/jev-defense-validation-20261103')
p=b/'native-vwa-request.recovered.json'
print(json.dumps({'actor_template_base64':base64.b64encode(p.read_bytes()).decode(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))
'''
    raw,target=remote('4090',code,'original-actor-template')
    v=json.loads(raw);(RUNTIME/'actor-template.json').write_bytes(base64.b64decode(v['actor_template_base64']))
    assert sha(RUNTIME/'actor-template.json')==v['sha256']
    ref=json.loads((RUNTIME/'auxiliary-identity-reference.json').read_bytes())
    lease=BASE/'resource-attempt-20261106-01/lease.json'
    token=secrets.token_urlsafe(48).encode();(RUNTIME/'private.token').write_bytes(token)
    # Token travels only within SSH staging; never printed, embedded in source, or exposed in public manifests.
    m={'schema':'new-single-image-full-GUI-pilot-v1','authorized_finite_joint_development':True,
        'authorization':'User explicitly requested 运行完整的gui实验 on 2026-11-08',
        'expected_holder':ref['expected_holder'],'lease_sha256':sha(lease),
        'outputs':ROOT3090,'GUI_output':ROOT4090+'/batch','model_url':'http://192.0.2.11:19138',
        'auth_token_sha256':hashlib.sha256(token).hexdigest(),
        'source_condition_tradeoffs':'One fallible image-only auxiliary; no task/history/candidate to it. Exact latest original main validator. No full long-history fit or semantic efficacy guarantee.',
        'files':{p.relative_to(RUNTIME).as_posix():sha(p) for p in sorted(RUNTIME.rglob('*')) if p.is_file() and p.name!='private.token'}}
    m['worker_source_sha256']=sha(RUNTIME/'gpu_server.py');save(RUNTIME/'manifest.json',m)
    encoded=payload(RUNTIME)
    for host,path,interpreter in [('3090',REMOTE_PACKAGE,'/opt/whz/conda-envs/webmall-vlm/bin/python'),
                                 ('4090',ROOT4090,'/data/researcher/venvs/qwen35-9b-full-20261019/bin/python')]:
        code='TARGET='+repr(path)+'\nMANIFEST_SHA='+repr(sha(RUNTIME/'manifest.json'))+'\n'+r'''
from pathlib import Path
import base64,hashlib,io,json,os,zipfile
r=Path(TARGET);assert not r.exists();r.mkdir(parents=True)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD))) as z:
 for n in z.namelist():assert (r/n).resolve().is_relative_to(r.resolve())
 z.extractall(r)
(r/'private.token').chmod(0o600)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(r/'manifest.json')==MANIFEST_SHA
m=json.loads((r/'manifest.json').read_bytes())
for n,h in m['files'].items():assert sha(r/n)==h,n
assert sha(r/'private.token')==m['auth_token_sha256']
print(json.dumps({'root':str(r),'uid':os.getuid(),'manifest_sha256':MANIFEST_SHA,'files_verified':len(m['files']),'model_GUI_calls':0}))
'''
        out,operation=remote(host,code,'stage-package-'+host,timeout=80,interpreter=interpreter,
            private_prefix='PAYLOAD='+repr(encoded)+'\n')
        save(HERE/('stage-'+host+'.json'),{'result':json.loads(out),'evidence':str(operation)})
    save(HERE/'freeze.json',{'manifest_sha256':sha(RUNTIME/'manifest.json'),'plan_sha256':sha(RUNTIME/'plan.json'),
        'new_GUI_trajectories':4,'max_steps':50,'actor_per_trajectory':70,'judge_per_trajectory':140,
        'auxiliary_per_enabled_trajectory':60,'complete_images_history_and_BF16':True,'semantic_efficacy':None})
    print(json.dumps({'staged_both_hosts':True,'manifest_sha256':sha(RUNTIME/'manifest.json'),'model_GUI_calls':0}))

def preflight():
    code='import runpy,sys\nsys.path.insert(0,'+repr(ROOT4090)+')\nrunpy.run_path('+repr(ROOT4090+'/environment_preflight.py')+',run_name="__main__")\n'
    out,target=remote('4090',code,'native-same-live-environment',timeout=180,
        interpreter='/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python')
    print(out)

def service():
    assert not (HERE/'service-submission.json').exists()
    msha=sha(RUNTIME/'manifest.json')
    argv=['/opt/whz/conda-envs/webmall-vlm/bin/python',REMOTE_PACKAGE+'/launch_gui_service_once.py',
          '--manifest',REMOTE_PACKAGE+'/manifest.json','--manifest-sha256',msha,'--output',ROOT3090]
    command={'action':'launch','argv':argv,'script_sha256':sha(RUNTIME/'launch_gui_service_once.py')}
    code='COMMAND='+repr(command)+'\nOUTPUT='+repr(ROOT3090)+'\n'+r'''
from pathlib import Path
import hashlib,json,os,socket,subprocess,time
b=Path('/home/researcher/jev-defense-four-gpu-20261106');assert os.getuid()==1033
assert not Path(OUTPUT).exists()
p=Path(COMMAND['argv'][1]);assert hashlib.sha256(p.read_bytes()).hexdigest()==COMMAND['script_sha256']
lease=json.loads((b/'resource-attempt-20261106-01/lease.json').read_bytes());h=lease['holder'];p=Path('/proc',str(h['pid']))
assert p.stat().st_uid==h['uid'] and (p/'stat').read_text().rsplit(')',1)[1].split()[19]==h['start_ticks']
assert (p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip()==h['command']
for row in lease['lock_records']:
 fd=p/'fd'/str(row['fd']);info=(p/'fdinfo'/str(row['fd'])).read_text()
 assert os.readlink(fd)==row['path'] and fd.stat().st_ino==row['inode'] and 'WRITE '+str(h['pid']) in info
target={r['uuid'] for r in lease['gpu']}
gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
for row in gpu.splitlines():
 i,u,f=[x.strip() for x in row.split(',')]
 if int(i) in [4,5,6,7]:assert u in target and int(f)>=23000
compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
assert not any(v.split(',')[0].strip() in target for v in compute.splitlines() if v.strip())
with socket.socket() as s:s.bind(('192.0.2.11',19138))
commands=b/'resource-attempt-20261106-01/commands'
assert all(p.with_suffix('.claimed').exists() for p in commands.glob('*.json'))
path=commands/'full-gui-single-evidence-20261108-01.json';temp=commands/('.new-fullGUI-'+str(os.getpid())+'.tmp')
raw=json.dumps(COMMAND,ensure_ascii=False,indent=2).encode()
with temp.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
os.link(temp,path);temp.unlink()
print(json.dumps({'submitted_once':True,'command_file':str(path),'output':OUTPUT,'manifest_sha256':COMMAND['argv'][5],'time':time.time()}))
'''
    out,target=remote('3090',code,'submit-service-once',timeout=55)
    save(HERE/'service-submission.json',{'manifest_sha256':msha,'result':json.loads(out),'evidence':str(target)})
    print(out)

def gui():
    assert not (HERE/'GUI-submission.json').exists()
    msha=sha(RUNTIME/'manifest.json')
    code='ROOT='+repr(ROOT4090)+'\nMSHA='+repr(msha)+'\n'+r'''
from pathlib import Path
import hashlib,json,os,subprocess,time
r=Path(ROOT);assert os.getuid()==1015
assert hashlib.sha256((r/'manifest.json').read_bytes()).hexdigest()==MSHA
assert json.loads((r/'environment-preflight/receipt.json').read_bytes())['status']=='passed'
assert not (r/'control').exists() and not (r/'batch').exists()
claim=r/'background';claim.mkdir(exist_ok=False)
argv=['/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python','-B','-u',str(r/'gui_outer.py'),'--manifest-sha256',MSHA]
with (claim/'outer.log').open('xb') as log:
 child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,cwd=str(r),env={**os.environ,'CUDA_VISIBLE_DEVICES':'','PYTHONDONTWRITEBYTECODE':'1'},start_new_session=True)
p=Path('/proc',str(child.pid));tail=(p/'stat').read_text().rsplit(')',1)[1].split()
v={'pid':child.pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':tail[19]}
assert v['command']==' '.join(argv)
(claim/'launch.json').write_text(json.dumps({'identity':v,'argv':argv,'once_only':True,'manifest_sha256':MSHA,'time':time.time()},indent=2))
print(json.dumps({'submitted_once':True,'identity':v,'root':ROOT,'manifest_sha256':MSHA}))
'''
    out,target=remote('4090',code,'submit-full-GUI-once',timeout=55,
        interpreter='/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python')
    save(HERE/'GUI-submission.json',{'manifest_sha256':msha,'result':json.loads(out),'evidence':str(target)})
    print(out)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['stage','preflight','service','gui']);a=p.parse_args()
    {'stage':stage,'preflight':preflight,'service':service,'gui':gui}[a.action]()
