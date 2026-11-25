"""Build a distinct fullGUI candidate; only CPU and zero-inference live environment checks."""
import base64,hashlib,io,json,shutil,subprocess,sys,time,zipfile
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent;PREP=BASE/'scoped-observability-development'
sha=lambda b:hashlib.sha256(b).hexdigest()
assert not(PREP/'fullgui-staging-current.json').exists()
parent=json.loads((PREP/'live-candidate-current.json').read_bytes());old=Path(parent['directory'])
for n,h in json.loads((old/'sha256.json').read_bytes()).items():assert sha((old/n).read_bytes())==h,n
out=PREP/('fullgui-stage-'+str(time.time_ns()));out.mkdir();release=out/'release'
shutil.copytree(old/'candidate-release',release,ignore=shutil.ignore_patterns('__pycache__'))
p=release/'defense/core.py';s=p.read_text(encoding='utf-8');needle="DEFENSE_VERSION='evidence-v3.9.9-bounded-point-evidence-recovery-20261027'";assert s.count(needle)==1
p.write_text(s.replace(needle,"DEFENSE_VERSION='evidence-v4.0-dev-scoped-direction-source-20261028'"),encoding='utf-8')
(release/'tests').mkdir()
excluded={'test_observation_readiness.py','test_reused_audit.py','test_scroll_source.py','test_uitars_device_placement.py'}
for f in (BASE/'tests').glob('test*.py'):
 if f.name not in excluded:shutil.copy2(f,release/'tests'/f.name)
# The old readiness tests assert exact OLD prompt identity and are retained in parent sources.
# New scoped integration tests cover that intentionally changed interface; no test altered.
commands=[[sys.executable,'-m','unittest','discover','-s','tests'],[sys.executable,'-m','unittest','test_native_direction_development','test_native_direction_feedback_origin','test_scoped_observability','test_scoped_controller_integration']]
testrows=[]
for cmd in commands:
 r=subprocess.run(cmd,cwd=release,capture_output=True,text=True);testrows.append({'command':cmd[1:],'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
(out/'cpu-results.json').write_text(json.dumps(testrows,indent=2))
assert all(x['returncode']==0 for x in testrows),'Preserved failed staging; inspect logs before linked repair'
manifest={str(p.relative_to(release)).replace('\\','/'):sha(p.read_bytes())for p in release.rglob('*')if p.is_file()and'__pycache__'not in str(p)}
(out/'release-sha256.json').write_text(json.dumps(manifest,indent=2))
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED)as z:
 for n,h in manifest.items():z.writestr('release/'+n,(release/n).read_bytes())
 z.writestr('release-sha256.json',(out/'release-sha256.json').read_bytes())
code=r'''
import base64,fcntl,hashlib,io,json,os,subprocess,time,zipfile
from pathlib import Path
assert os.getuid()==1015
b=Path('/data/researcher/mirage-defense-pilot-20261023');locks=[]
for n in ['scoped-fullgui-preparation.lock','scoped-observability-source.lock','scoped-observability-development.lock','native-direction-development.lock','scroll-validation-startup.lock']:
 p=b/n;f=p.open('a');assert p.stat().st_uid==1015;fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
active=b/'scoped-fullgui-preparation-active-20261028.json';assert not active.exists()
r=b/('scoped-fullgui-preparation-'+str(time.time_ns()));r.mkdir()
with active.open('x')as f:json.dump({'root':str(r),'model_calls':0,'phase':'reserved_zero_inference_preflight'},f)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(ARCHIVE)))as z:
 for n in z.namelist():(r/n).resolve().relative_to(r.resolve())
 z.extractall(r)
for n,h in json.loads((r/'release-sha256.json').read_bytes()).items():assert hashlib.sha256((r/'release'/n).read_bytes()).hexdigest()==h,n
containers=json.loads(subprocess.check_output(['docker','inspect','qwen27_vwa_classifieds','qwen27_vwa_classifieds_db'],text=True))
for c,identity in zip(containers,['de6f56798c3c5a278a96d7afe6844e8be2c5673301e44e1c887eecc56118f0dd','e8fe8dfaa8010a5473c1ebf603859ba04d7d4ac1e8016b347ea8211c03a4c62c']):
 assert c['Id']==identity and c['Config']['Labels']['owner']=='whz-qwen27-vwa' and c['State']['Running']
 assert all(Path(p).stat().st_uid==1015 for p in c['Config']['Labels']['com.docker.compose.project.config_files'].split(','))
(r/'container-identity.json').write_text(json.dumps([{'id':c['Id'],'image':c['Image'],'labels':c['Config']['Labels'],'ports':c['HostConfig']['PortBindings'],'mounts':c['Mounts']}for c in containers],indent=2))
assert containers[0]['HostConfig']['PortBindings']=={'9980/tcp':[{'HostIp':'192.0.2.10','HostPort':'29980'}]}
assert any(m.get('Name')=='qwen27_vwa_db_data'for m in containers[1]['Mounts'])
py='/data/researcher/vwa100-2026-10-09/venv/bin/python'
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset')
results=[]
for args in [['-m','unittest','discover','-s','tests'],['-m','unittest','test_native_direction_development','test_native_direction_feedback_origin','test_scoped_observability','test_scoped_controller_integration']]:
 p=subprocess.run([py]+args,cwd=r/'release',env=env,capture_output=True,text=True,timeout=60);results.append({'args':args,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
(r/'remote-cpu-tests.json').write_text(json.dumps(results,indent=2))
assert all(x['returncode']==0 for x in results),'Remote CPU failure preserved'
command=[py,'-u',str(r/'release/run_vwa_pilot.py'),'--root',str(r/'environment'),'--plan',str(r/'release/plan80.json'),'--token-file',str(b/'transport.token'),'--environment-preflight']
with(r/'environment-worker.log').open('xb')as log:
 p=subprocess.Popen(command,cwd=r/'release',env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,pass_fds=tuple(f.fileno()for f in locks))
 proc=Path('/proc')/str(p.pid);cmd=[x.decode()for x in(proc/'cmdline').read_bytes().split(b'\0')if x]
 assert proc.stat().st_uid==1015 and cmd==command
 held=[{'target':os.readlink(str(proc/'fd'/f.name)),'fdinfo':f.read_text()}for f in(proc/'fdinfo').iterdir()if'FLOCK'in f.read_text()]
 assert len(held)>=len(locks)
 (r/'actual-process.json').write_text(json.dumps({'uid':1015,'pid':p.pid,'command':cmd,'held_locks':held},indent=2))
 try:rc=p.wait(timeout=150)
 except subprocess.TimeoutExpired:
  # This exact newly spawned owned child only, preserve all artifacts before diagnosis.
  p.terminate();rc=p.wait(timeout=20)
state=json.loads((r/'environment/status.json').read_bytes())if(r/'environment/status.json').exists()else{}
row={'root':str(r),'returncode':rc,'status':state,'model_calls':0,'new_GPU_allocation':False,'formal_trial_started':False,'no_site_reset_or_fixture_import':True,'child_exited':p.poll()is not None,'source_package_sha256':hashlib.sha256((r/'release-sha256.json').read_bytes()).hexdigest()}
allfiles={str(f.relative_to(r)):hashlib.sha256(f.read_bytes()).hexdigest()for f in r.rglob('*')if f.is_file()and'__pycache__'not in str(f)}
(r/'terminal-sha256.json').write_text(json.dumps(allfiles,indent=2));row['terminal_manifest_sha256']=hashlib.sha256((r/'terminal-sha256.json').read_bytes()).hexdigest()
public_files=['container-identity.json','remote-cpu-tests.json','actual-process.json','environment-worker.log','terminal-sha256.json']
public_files += [n for n in ['environment/status.json','environment/initial.png','environment/real-recapture.png']if(r/n).exists()]
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED)as z:
 for n in public_files:z.writestr(n,(r/n).read_bytes())
row['zip']=base64.b64encode(buf.getvalue()).decode();row['public_file_sha256']={n:hashlib.sha256((r/n).read_bytes()).hexdigest()for n in public_files}
(r/'receipt.json').write_text(json.dumps({k:v for k,v in row.items()if k!='zip'},indent=2))
print(json.dumps(row))
'''
row=json.loads(remote('ARCHIVE='+repr(base64.b64encode(buf.getvalue()).decode())+'\n'+code,host='4090',timeout=260))
col=out/'environment-evidence';col.mkdir()
with zipfile.ZipFile(io.BytesIO(base64.b64decode(row.pop('zip'))))as z:
 for n in z.namelist():(col/n).resolve().relative_to(col.resolve())
 z.extractall(col)
for n,h in row['public_file_sha256'].items():assert sha((col/n).read_bytes())==h,n
(out/'environment-receipt.json').write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
pointer={'directory':str(out),'release':str(release),'release_manifest_sha256':sha((out/'release-sha256.json').read_bytes()),'environment_receipt_sha256':sha((out/'environment-receipt.json').read_bytes()),'remote_preparation_root':row['root'],'environment_returncode':row['returncode'],'environment_phase':row['status'].get('phase'),'model_calls':0,'formal_execution_authorized':False,'fullGUI_launcher_ready':False}
(PREP/'fullgui-staging-current.json').write_text(json.dumps(pointer,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(pointer,ensure_ascii=False))
assert row['returncode']==0 and row['status']['phase']=='environment_preflight_complete','Preserved failed environment attempt; linked repair required'
