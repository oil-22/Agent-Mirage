"""Once-only isolated source-bound repair diagnostic, no actor or GUI execution."""
import base64,hashlib,io,json,zipfile
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent;PREP=BASE/'focus-conflict-repair-development'
assert not(PREP/'launch-current.json').exists(),'Never duplicate or restart a completed diagnostic'
stage=json.loads((PREP/'current.json').read_bytes());root=Path(stage['directory']);manifest=json.loads((root/'source-sha256.json').read_bytes())
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED)as z:
 for n,h in manifest.items():
  raw=(root/n).read_bytes();assert hashlib.sha256(raw).hexdigest()==h and'PRIVATE'not in n;z.writestr(n,raw)
 z.writestr('source-sha256.json',(root/'source-sha256.json').read_bytes())
code=r'''
import base64,fcntl,hashlib,io,json,os,subprocess,time,zipfile
from pathlib import Path
assert os.getuid()==1015
b=Path('/data/researcher/mirage-defense-pilot-20261023');locks=[]
for name in ['focus-history-repair-development.lock','native-direction-development.lock','scoped-fullgui-launch.lock','scoped-observability-source.lock','scoped-observability-development.lock','scroll-validation-startup.lock']:
 p=b/name;f=p.open('a');assert p.stat().st_uid==1015;fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
active=b/'focus-conflict-repair-active-20261029.json';assert not active.exists()
r=b/('focus-conflict-repair-preflight-'+str(time.time_ns()));r.mkdir()
with zipfile.ZipFile(io.BytesIO(base64.b64decode(ARCHIVE)))as z:
 for n in z.namelist():(r/n).resolve().relative_to(r.resolve());assert'PRIVATE'not in n
 z.extractall(r)
for n,h in json.loads((r/'source-sha256.json').read_bytes()).items():assert hashlib.sha256((r/n).read_bytes()).hexdigest()==h,n
py='/data/researcher/vwa100-2026-10-09/venv/bin/python'
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset')
tests=[]
for args in [['-m','unittest','discover','-s','tests'],['-m','unittest','test_native_direction_development','test_native_direction_feedback_origin','test_scoped_observability','test_scoped_controller_integration','test_focus_history_scope','test_current_only_history_scope','test_current_scope_controller','test_focus_history_conflict_scope']]:
 p=subprocess.run([py]+args,cwd=r/'release',env=env,capture_output=True,text=True,timeout=60);tests.append({'args':args,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
(r/'remote-cpu-tests.json').write_text(json.dumps(tests,indent=2));assert all(x['returncode']==0 for x in tests),tests
command=[py,'-u',str(r/'release/run_focus_conflict_repair.py'),'--root',str(r)]
row={'root':str(r),'phase':'reserved_before_spawn','uid':1015,'time':time.time(),'max_calls':24,'private_expectations_transferred':False,'GUI_execution':False,'formal_trial':False,'source_manifest_sha256':hashlib.sha256((r/'source-sha256.json').read_bytes()).hexdigest(),'command':command}
with active.open('x')as f:json.dump(row,f,indent=2)
with(r/'worker.log').open('xb')as f:p=subprocess.Popen(command,cwd=r/'release',env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=tuple(f.fileno()for f in locks))
proc=Path('/proc')/str(p.pid);cmd=[x.decode()for x in(proc/'cmdline').read_bytes().split(b'\0')if x];assert proc.stat().st_uid==1015 and cmd==command
held=[]
for f in(proc/'fdinfo').iterdir():
 try:
  info=f.read_text()
  if'FLOCK'in info:held.append({'target':os.readlink(str(proc/'fd'/f.name)),'fdinfo':info})
 except FileNotFoundError:pass
assert all(any(x['target']==f.name for x in held)for f in locks)
row.update(phase='launched',pid=p.pid,held_locks=held);(r/'launch.json').write_text(json.dumps(row,indent=2));tmp=active.with_suffix('.tmp');tmp.write_text(json.dumps(row,indent=2));tmp.replace(active);print(json.dumps(row))
'''
row=json.loads(remote('ARCHIVE='+repr(base64.b64encode(buf.getvalue()).decode())+'\n'+code,host='4090',timeout=90));(root/'launch.json').write_text(json.dumps(row,indent=2));row['local_root']=str(root);(PREP/'launch-current.json').write_text(json.dumps(row,indent=2));print(json.dumps({k:v for k,v in row.items()if k!='held_locks'}))
