"""Explicit sequential staging and once-only submits; never resumes old jobs."""
import argparse,base64,hashlib,io,json,os,secrets,shutil,sys,time,zipfile
from pathlib import Path
from remote_control import HERE,BASE,ROOT3090,ROOT4090,remote,save,sha
RUNTIME=HERE/'runtime-package'
REMOTE_PACKAGE='/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/full-history-gui-development-20261109-23'

def payload(package):
    f=io.BytesIO()
    with zipfile.ZipFile(f,'w',zipfile.ZIP_DEFLATED) as z:
        for p in package.rglob('*'):
            if p.is_file():z.writestr(p.relative_to(package).as_posix(),p.read_bytes())
    return base64.b64encode(f.getvalue()).decode()


def stage():
    assert not (RUNTIME/'manifest.json').exists()
    inputs=json.loads((HERE/'stage-inputs.json').read_bytes())
    review=Path(inputs['semantic_review']);audit=Path(inputs['technical_audit'])
    cpu=Path(inputs['CPU_integration'])
    reviewed=json.loads(review.read_bytes());audited=json.loads(audit.read_bytes())
    assert audited['passed'] and audited['fresh_auxiliary_calls']==0 and audited['actual_main_model_calls']<=28
    assert reviewed['all_actual_replies_reviewed'] and reviewed['allow_new_GUI_development']
    assert reviewed['trajectory_reduction_established'] is False
    assert json.loads(cpu.read_bytes())['passed']
    for name,h in json.loads((HERE/'source-seal.json').read_bytes()).items():assert sha(RUNTIME/name)==h,name
    expected=json.loads((RUNTIME/'auxiliary-identity-reference.json').read_bytes())['expected_holder']
    token=secrets.token_urlsafe(48).encode()
    with (RUNTIME/'private.token').open('xb')as stream:stream.write(token)
    admission={'admit_new_GUI_development':True,'formal_release_or_semantic_pass':False,
       'known_semantic_failures_not_relabelled_as_passes':True,
       'full_history_capacity_beyond_actual_inputs_not_established':True,
       'technical_audit_sha256':sha(audit),'semantic_review_sha256':sha(review),'CPU_integration_sha256':sha(cpu),
       'exact_tradeoff':json.loads((RUNTIME/'plan.json').read_bytes())['source_condition_tradeoff'],
       'authorization':'Existing sustained user goal; new finite matched GUI development, original per-track budgets'}
    save(RUNTIME/'admission.json',admission)
    lease=BASE/'resource-attempt-20261106-01/lease.json'
    m={'schema':'complete-main-history-32-track-GUI-development-v1','authorized_finite_joint_development':True,
       'expected_holder':expected,'lease_sha256':sha(lease),'outputs':ROOT3090,'GUI_output':ROOT4090+'/batch',
       'model_url':'http://192.0.2.11:19138','auth_token_sha256':hashlib.sha256(token).hexdigest(),
       'native_bindings_sha256':sha(RUNTIME/'native-bindings-public.json'),
       'source_condition_tradeoffs':admission['exact_tradeoff'],'technical_audit_sha256':sha(audit),
       'semantic_review_sha256':sha(review),'CPU_integration_sha256':sha(cpu),
       'actual_auxiliary':'Qwen/Qwen3.5-9B','decision_adapter_loaded':False,
       'tracks':32,'per_trajectory_caps':{'steps':50,'actor':70,'judge':140,'auxiliary':60},
       'worker_source_sha256':sha(RUNTIME/'gpu_server.py'),
       'files':{p.relative_to(RUNTIME).as_posix():sha(p)for p in sorted(RUNTIME.rglob('*'))if p.is_file()and p.name!='private.token'}}
    save(RUNTIME/'manifest.json',m)
    encoded=payload(RUNTIME)
    for host,path,interpreter in [('3090',REMOTE_PACKAGE,'/opt/whz/conda-envs/webmall-vlm/bin/python'),
                                ('4090',ROOT4090,'/data/researcher/venvs/qwen35-9b-full-20261019/bin/python')]:
        code='TARGET='+repr(path)+'\nMANIFEST_SHA='+repr(sha(RUNTIME/'manifest.json'))+'\n'+r"""
from pathlib import Path
import base64,hashlib,io,json,os,zipfile
r=Path(TARGET);assert not r.exists();r.mkdir(parents=True)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD)))as archive:
 for name in archive.namelist():assert(r/name).resolve().is_relative_to(r.resolve())
 archive.extractall(r)
(r/'private.token').chmod(0o600)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(r/'manifest.json')==MANIFEST_SHA
m=json.loads((r/'manifest.json').read_bytes())
for name,h in m['files'].items():assert sha(r/name)==h,name
assert sha(r/'private.token')==m['auth_token_sha256']
for p in r.rglob('*.py'):compile(p.read_text(),str(p),'exec')
print(json.dumps({'root':str(r),'uid':os.getuid(),'manifest_sha256':MANIFEST_SHA,'files_verified':len(m['files']),'new_model_GUI_scorer_calls':0}))
"""
        out,op=remote(host,code,'stage-new-package-'+host,timeout=55,interpreter=interpreter,private_prefix='PAYLOAD='+repr(encoded)+'\n')
        save(HERE/('stage-'+host+'.json'),{'result':json.loads(out),'operation':str(op)})
    save(HERE/'freeze.json',{'manifest_sha256':sha(RUNTIME/'manifest.json'),'plan_sha256':sha(RUNTIME/'plan.json'),
       'new_GUI_tracks':32,'tasks':8,'paired_comparisons':16,'old_queues_or_completed_controls_resumed':False,
       'per_track_steps_actor_judge_auxiliary':[50,70,140,60],'formal_efficacy_established':False})
    print(json.dumps({'staged_both_hosts':True,'manifest_sha256':sha(RUNTIME/'manifest.json'),'new_model_GUI_calls':0}))


def preflight():
    code='import runpy,sys\nsys.path.insert(0,'+repr(ROOT4090)+')\nrunpy.run_path('+repr(ROOT4090+'/environment_preflight.py')+',run_name="__main__")\n'
    out,target=remote('4090',code,'native-same-live-environment',timeout=180,
        interpreter='/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python')
    value=json.loads(out);assert value['status']=='passed'
    save(HERE/'environment-admission.json',{'passed':True,'result':value,'operation':str(target),'new_model_GUI_scorer_calls':0})
    print(out)

def service():
    assert not (HERE/'service-submission.json').exists() and not (HERE/'service-submission-intent.json').exists()
    assert json.loads((RUNTIME/'admission.json').read_bytes())['admit_new_GUI_development']
    assert json.loads((HERE/'environment-admission.json').read_bytes())['passed']
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
path=commands/'full-history-gui-development-20261109-23.json';temp=commands/('.new-fullGUI-'+str(os.getpid())+'.tmp')
raw=json.dumps(COMMAND,ensure_ascii=False,indent=2).encode()
with temp.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
os.link(temp,path);temp.unlink()
print(json.dumps({'submitted_once':True,'command_file':str(path),'output':OUTPUT,'manifest_sha256':COMMAND['argv'][5],'time':time.time()}))
'''
    save(HERE/'service-submission-intent.json',{'manifest_sha256':msha,'time':time.time(),'no_duplicate_after_observation_timeout':True})
    out,target=remote('3090',code,'submit-service-once',timeout=55)
    save(HERE/'service-submission.json',{'manifest_sha256':msha,'result':json.loads(out),'evidence':str(target)})
    print(out)

def gui():
    assert not (HERE/'GUI-submission.json').exists() and not (HERE/'GUI-submission-intent.json').exists()
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
    save(HERE/'GUI-submission-intent.json',{'manifest_sha256':msha,'time':time.time(),'no_duplicate_after_observation_timeout':True})
    out,target=remote('4090',code,'submit-full-GUI-once',timeout=55,
        interpreter='/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python')
    save(HERE/'GUI-submission.json',{'manifest_sha256':msha,'result':json.loads(out),'evidence':str(target)})
    print(out)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['stage','preflight','service','gui']);a=p.parse_args()
    {'stage':stage,'preflight':preflight,'service':service,'gui':gui}[a.action]()
