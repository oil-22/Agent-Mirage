"""New single-trajectory condition, gated by an explicit decision on the sealed proposal."""
import argparse,hashlib,json
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent;PREP=BASE/'scoped-observability-development'
sha=lambda b:hashlib.sha256(b).hexdigest()

def validate_decision(value,proposal_sha256):
    if not isinstance(value,dict) or value.get('approved') is not True:raise ValueError('Explicit human decision required')
    if value.get('proposal_sha256')!=proposal_sha256:raise ValueError('Decision must bind this exact proposal')
    if value.get('scope')!='one-new-scoped-joint-stale-fullgui':raise ValueError('Only one new trajectory allowed')
    if not isinstance(value.get('user_authorization_text'),str)or not value['user_authorization_text'].strip():raise ValueError('Preserve actual human authorization text')
    return value

def main(decision_path):
    ready=json.loads((PREP/'fullgui-ready-current.json').read_bytes())
    proposal=Path(ready['proposal']);assert sha(proposal.read_bytes())==ready['proposal_sha256']
    decision=validate_decision(json.loads(decision_path.read_bytes()),ready['proposal_sha256'])
    assert not(PREP/'fullgui-launch-current.json').exists(),'Existing launch or reservation must be inspected, never duplicated'
    stage=json.loads((PREP/'fullgui-staging-current.json').read_bytes());local=Path(stage['directory']);release=local/'release'
    manifest=(local/'release-sha256.json').read_bytes();assert sha(manifest)==stage['release_manifest_sha256']==ready['release_manifest_sha256']
    for n,h in json.loads(manifest).items():assert sha((release/n).read_bytes())==h,n
    code=r'''
import fcntl,hashlib,json,os,subprocess,time
from pathlib import Path
assert os.getuid()==1015
b=Path('/data/researcher/mirage-defense-pilot-20261023');locks=[]
for n in ['scoped-fullgui-launch.lock','scoped-observability-source.lock','scoped-observability-development.lock','native-direction-development.lock','scroll-validation-startup.lock']:
 p=b/n;f=p.open('a');assert p.stat().st_uid==1015;fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
active=b/'scoped-fullgui-active-20261028.json';assert not active.exists(),'Inspect existing active receipt; no duplicate'
staged=Path(STAGE);staged.resolve().relative_to(b.resolve());release=staged/'release'
assert hashlib.sha256((staged/'release-sha256.json').read_bytes()).hexdigest()==MANIFEST_SHA
for n,h in json.loads((staged/'release-sha256.json').read_bytes()).items():
 p=release/n;p.resolve().relative_to(release.resolve());assert p.stat().st_uid==1015 and hashlib.sha256(p.read_bytes()).hexdigest()==h,n
state=json.loads((staged/'environment/status.json').read_bytes());assert state['phase']=='environment_preflight_complete'and state['model_calls']==0
for path,h in READY['runtime_source_bindings'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==h,path
containers=json.loads(subprocess.check_output(['docker','inspect','qwen27_vwa_classifieds','qwen27_vwa_classifieds_db'],text=True))
for c,identity in zip(containers,['de6f56798c3c5a278a96d7afe6844e8be2c5673301e44e1c887eecc56118f0dd','e8fe8dfaa8010a5473c1ebf603859ba04d7d4ac1e8016b347ea8211c03a4c62c']):
 assert c['Id']==identity and c['Config']['Labels']['owner']=='whz-qwen27-vwa'and c['State']['Running']
 assert all(Path(p).stat().st_uid==1015 for p in c['Config']['Labels']['com.docker.compose.project.config_files'].split(','))
assert containers[0]['HostConfig']['PortBindings']=={'9980/tcp':[{'HostIp':'192.0.2.10','HostPort':'29980'}]}
# Verify the resumed service UID, full command and actual flock ownership on3090 separately
# with inspect_resumed_defense_service.py immediately before invoking this launcher.
py='/data/researcher/vwa100-2026-10-09/venv/bin/python'
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset')
r=b/('scoped-joint-stale-fullgui-'+str(time.time_ns()));r.mkdir()
command=[py,'-u',str(release/'run_vwa_pilot.py'),'--root',str(r),'--plan',str(release/'plan80.json'),'--token-file',str(b/'transport.token'),'--only-runs','vwa--classifieds_112--stale_replace--joint']
row={'root':str(r),'release':str(release),'command':command,'uid':1015,'phase':'reserved_before_spawn','proposal_sha256':PROPOSAL_SHA,'decision_sha256':DECISION_SHA,'source_manifest_sha256':MANIFEST_SHA,'scope':'one-new-scoped-joint-stale-fullgui','max_actor_calls':70,'max_verifier_calls':140,'max_steps':50,'no_auto_retry':True,'formal_efficacy_claim':False,'time':time.time()}
with active.open('x')as f:json.dump(row,f,indent=2)
(r/'human-decision.json').write_text(json.dumps(DECISION,ensure_ascii=False,indent=2))
(r/'preparation-binding.json').write_text(json.dumps(READY,ensure_ascii=False,indent=2))
with(r/'worker.log').open('xb')as log:p=subprocess.Popen(command,cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=tuple(f.fileno()for f in locks))
proc=Path('/proc')/str(p.pid);actual=[x.decode()for x in(proc/'cmdline').read_bytes().split(b'\0')if x];assert proc.stat().st_uid==1015 and actual==command
held=[{'target':os.readlink(str(proc/'fd'/f.name)),'fdinfo':f.read_text()}for f in(proc/'fdinfo').iterdir()if'FLOCK'in f.read_text()];assert len(held)>=len(locks)
row.update(pid=p.pid,phase='launched',actual_command=actual,held_locks=held)
(r/'launch.json').write_text(json.dumps(row,indent=2));tmp=active.with_suffix('.tmp');tmp.write_text(json.dumps(row,indent=2));tmp.replace(active);print(json.dumps(row))
'''
    import subprocess,sys
    health=subprocess.run([sys.executable,str(BASE/'inspect_resumed_defense_service.py')],capture_output=True,text=True,check=True)
    (local/'prelaunch-service-check.json').write_text(health.stdout,encoding='utf-8')
    code='STAGE='+repr(stage['remote_preparation_root'])+'\nMANIFEST_SHA='+repr(ready['release_manifest_sha256'])+'\nREADY='+repr(ready)+'\nPROPOSAL_SHA='+repr(ready['proposal_sha256'])+'\nDECISION_SHA='+repr(sha(decision_path.read_bytes()))+'\nDECISION='+repr(decision)+'\n'+code
    row=json.loads(remote(code,host='4090',timeout=90));(PREP/'fullgui-launch-current.json').write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(row))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--decision-file',type=Path,required=True);main(p.parse_args().decision_file)
