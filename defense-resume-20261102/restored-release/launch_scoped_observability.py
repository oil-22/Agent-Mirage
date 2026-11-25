"""Once-only new protocol diagnostic with shared inference-client ownership lock."""
import base64,hashlib,io,json,zipfile
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent;PREP=BASE/'scoped-observability-development'
assert not(PREP/'launch-current.json').exists(),'Inspect existing attempt; never duplicate'
stage=json.loads((PREP/'current.json').read_bytes());root=Path(stage['directory']);manifest=json.loads((root/'source-sha256.json').read_bytes())
assert not any('PRIVATE'in n for n in manifest)
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED)as z:
    for n,h in manifest.items():
        raw=(root/n).read_bytes();assert hashlib.sha256(raw).hexdigest()==h;z.writestr(n,raw)
    z.writestr('source-sha256.json',(root/'source-sha256.json').read_bytes())
code=r'''
import base64,fcntl,hashlib,io,json,os,subprocess,time,zipfile
from pathlib import Path
assert os.getuid()==1015
b=Path('/data/researcher/mirage-defense-pilot-20261023');lock=(b/'scoped-observability-development.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
# Also exclude a concurrent original direction worker without altering its immutable receipts.
client=(b/'native-direction-development.lock').open('a');fcntl.flock(client,fcntl.LOCK_EX|fcntl.LOCK_NB)
active=b/'scoped-observability-development-active-20261028.json';assert not active.exists()
r=b/('scoped-observability-real-preflight-'+str(time.time_ns()));r.mkdir()
with zipfile.ZipFile(io.BytesIO(base64.b64decode(ARCHIVE)))as z:
 for n in z.namelist():(r/n).resolve().relative_to(r.resolve());assert'PRIVATE'not in n
 z.extractall(r)
for n,h in json.loads((r/'source-sha256.json').read_bytes()).items():assert hashlib.sha256((r/n).read_bytes()).hexdigest()==h,n
py='/data/researcher/vwa100-2026-10-09/venv/bin/python'
tests=subprocess.run([py,'-m','unittest','test_native_direction_development','test_native_direction_feedback_origin','test_scoped_observability','test_scoped_controller_integration'],cwd=r/'release',capture_output=True,text=True,timeout=60)
(r/'remote-cpu-tests.json').write_text(json.dumps({'returncode':tests.returncode,'stdout':tests.stdout,'stderr':tests.stderr},indent=2));assert tests.returncode==0,tests.stderr
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset')
native=subprocess.run([py,'-c','from run_reddit_internvl_smoke import parse,action; action(parse(\'<action>{"type":"wait"}</action>\'))'],cwd='/data/researcher/vwa100-2026-10-09',env=env,capture_output=True,text=True,timeout=30)
(r/'native-import-preflight.json').write_text(json.dumps({'returncode':native.returncode,'stdout':native.stdout,'stderr':native.stderr},indent=2));assert native.returncode==0,native.stderr
command=[py,'-u',str(r/'release/run_scoped_observability.py'),'--root',str(r)]
row={'root':str(r),'phase':'reserved_before_spawn','uid':1015,'time':time.time(),'max_calls':24,'private_expectations_transferred':False,'GUI_execution':False,'formal_trial':False,'source_manifest_sha256':hashlib.sha256((r/'source-sha256.json').read_bytes()).hexdigest()}
with active.open('x')as f:json.dump(row,f,indent=2)
with(r/'worker.log').open('xb')as f:p=subprocess.Popen(command,cwd=r/'release',env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(lock.fileno(),client.fileno()))
row.update(phase='launched',pid=p.pid,command=command);(r/'launch.json').write_text(json.dumps(row,indent=2));tmp=active.with_suffix('.tmp');tmp.write_text(json.dumps(row,indent=2));tmp.replace(active);print(json.dumps(row))
'''
row=json.loads(remote('ARCHIVE='+repr(base64.b64encode(buf.getvalue()).decode())+'\n'+code,host='4090',timeout=100));(root/'launch.json').write_text(json.dumps(row,indent=2));row['local_root']=str(root);(PREP/'launch-current.json').write_text(json.dumps(row,indent=2));print(json.dumps(row))
