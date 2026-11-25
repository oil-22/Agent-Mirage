"""Respect the user's repair-first decision; collect sealed new sources with owned locks."""
import base64,hashlib,io,json,time,zipfile
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent;PREP=BASE/'focus-history-repair-development';PREP.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
assert not(PREP/'source-current.json').exists()
old=BASE/'scoped-observability-development';ready=json.loads((old/'fullgui-ready-current.json').read_bytes())
decision={'approved':False,'proposal_sha256':ready['proposal_sha256'],'scope':'one-new-scoped-joint-stale-fullgui','user_authorization_text':'先修复焦点和历史推断问题','status':'REPAIR_FIRST_FULLGUI_NOT_AUTHORIZED'}
dp=old/'fullgui-decision-current.json'
if not dp.exists():dp.write_text(json.dumps(decision,ensure_ascii=False,indent=2),encoding='utf-8')
(PREP/'user-decision.json').write_text(json.dumps(decision,ensure_ascii=False,indent=2),encoding='utf-8')
raw=(BASE/'capture_focus_history_sources.py').read_bytes()
code=r'''
import base64,fcntl,hashlib,io,json,os,subprocess,time,zipfile
from pathlib import Path
assert os.getuid()==1015
b=Path('/data/researcher/mirage-defense-pilot-20261023');locks=[]
for name in ['scoped-observability-source.lock','scoped-observability-development.lock','native-direction-development.lock']:
 p=b/name;f=p.open('a');assert p.stat().st_uid==1015;fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
assert not(b/'scoped-fullgui-active-20261028.json').exists(),'User chose repair first'
active=b/'focus-history-source-active-20261028.json';assert not active.exists()
r=b/('focus-history-fresh-source-'+str(time.time_ns()));r.mkdir()
with active.open('x')as f:json.dump({'root':str(r),'phase':'source_capture_reserved','model_calls':0},f)
containers=json.loads(subprocess.check_output(['docker','inspect','qwen27_vwa_classifieds','qwen27_vwa_classifieds_db'],text=True))
for c,identity in zip(containers,['de6f56798c3c5a278a96d7afe6844e8be2c5673301e44e1c887eecc56118f0dd','e8fe8dfaa8010a5473c1ebf603859ba04d7d4ac1e8016b347ea8211c03a4c62c']):
 assert c['Id']==identity and c['Config']['Labels']['owner']=='whz-qwen27-vwa'and c['State']['Running']
 assert all(Path(p).stat().st_uid==1015 for p in c['Config']['Labels']['com.docker.compose.project.config_files'].split(','))
(r/'container-identity.json').write_text(json.dumps([{'id':c['Id'],'image':c['Image'],'labels':c['Config']['Labels'],'ports':c['HostConfig']['PortBindings']}for c in containers],indent=2))
assert containers[0]['HostConfig']['PortBindings']=={'9980/tcp':[{'HostIp':'192.0.2.10','HostPort':'29980'}]}
raw=base64.b64decode(SCRIPT);assert hashlib.sha256(raw).hexdigest()==SCRIPT_SHA;(r/'capture.py').write_bytes(raw)
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',OMP_NUM_THREADS='2')
with(r/'capture.log').open('xb')as log:
 p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python',str(r/'capture.py'),'--root',str(r)],env=env,stdout=log,stderr=subprocess.STDOUT,pass_fds=tuple(f.fileno()for f in locks))
 rc=p.wait(timeout=90)
files={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest()for p in r.rglob('*')if p.is_file()};(r/'source-seal.json').write_text(json.dumps(files,indent=2))
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED)as z:
 for n in list(files)+['source-seal.json']:z.writestr(n,(r/n).read_bytes())
print(json.dumps({'root':str(r),'returncode':rc,'files':files,'zip':base64.b64encode(buf.getvalue()).decode(),'model_calls':0,'no_site_reset':True}))
'''
row=json.loads(remote('SCRIPT='+repr(base64.b64encode(raw).decode())+'\nSCRIPT_SHA='+repr(sha(raw))+'\n'+code,host='4090',timeout=120))
out=PREP/('sources-'+str(time.time_ns()));out.mkdir()
with zipfile.ZipFile(io.BytesIO(base64.b64decode(row.pop('zip'))))as z:
 for n in z.namelist():(out/n).resolve().relative_to(out.resolve())
 z.extractall(out)
for n,h in row['files'].items():assert sha((out/n).read_bytes())==h,n
row.update(directory=str(out),source_seal_sha256=sha((out/'source-seal.json').read_bytes()))
(out/'receipt.json').write_text(json.dumps(row,indent=2));(PREP/'source-current.json').write_text(json.dumps(row,indent=2));print(json.dumps({k:v for k,v in row.items()if k!='files'}))
assert row['returncode']==0,'Preserve failed source attempt, do not relaunch'
