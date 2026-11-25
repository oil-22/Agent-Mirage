"""Restore only owned stopped site containers, then collect new read-only source frames."""
import base64,hashlib,io,json,time,zipfile
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent;PREP=BASE/'scoped-observability-development';PREP.mkdir(exist_ok=True)
assert not(PREP/'fresh-source-current.json').exists(),'New source already collected; do not repeat'
script=(BASE/'capture_scoped_readiness_sources.py').read_bytes()
code=r'''
import base64,fcntl,hashlib,io,json,os,socket,subprocess,time,urllib.request,zipfile
from pathlib import Path
assert os.getuid()==1015
base=Path('/data/researcher/mirage-defense-pilot-20261023');lock=(base/'scoped-observability-source.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
active=base/'scoped-observability-source-active-20261028.json';assert not active.exists()
root=base/('scoped-observability-fresh-source-'+str(time.time_ns()));root.mkdir()
with active.open('x')as f:json.dump({'root':str(root),'phase':'source_capture_reserved','model_calls':0},f)
containers=json.loads(subprocess.check_output(['docker','inspect','qwen27_vwa_classifieds','qwen27_vwa_classifieds_db'],text=True))
expected=['de6f56798c3c5a278a96d7afe6844e8be2c5673301e44e1c887eecc56118f0dd','e8fe8dfaa8010a5473c1ebf603859ba04d7d4ac1e8016b347ea8211c03a4c62c'];inspection=[]
for c,identity in zip(containers,expected):
 assert c['Id']==identity and c['Config']['Labels']['owner']=='whz-qwen27-vwa'
 labels=c['Config']['Labels'];assert labels['com.docker.compose.project']=='qwen27_vwa'
 paths=labels['com.docker.compose.project.config_files'].split(',')
 assert all(Path(p).stat().st_uid==1015 for p in paths)
 inspection.append({'id':c['Id'],'name':c['Name'],'state':c['State'],'labels':labels,'ports':c['HostConfig']['PortBindings'],'mounts':c['Mounts'],'image':c['Image'],'configuration_owner_uid':1015})
web,db=containers
assert web['HostConfig']['PortBindings']=={'9980/tcp':[{'HostIp':'192.0.2.10','HostPort':'29980'}]}
assert any(m.get('Name')=='qwen27_vwa_db_data' for m in db['Mounts'])
(root/'container-before.json').write_text(json.dumps(inspection,indent=2))
for c in containers:
 p=subprocess.run(['docker','logs','--tail','60',c['Id']],capture_output=True,text=True);(root/(c['Name'].lstrip('/')+'-before.log')).write_text(p.stdout+p.stderr)
if not web['State']['Running']:
 with socket.socket()as s:assert s.connect_ex(('192.0.2.10',29980))!=0
for c in [db,web]:
 if not c['State']['Running']:subprocess.run(['docker','start',c['Id']],check=True,capture_output=True,text=True)
for i in range(8):
 try:
  with urllib.request.urlopen('http://192.0.2.10:29980/',timeout=5)as r:assert r.status==200;r.read()
  break
 except Exception:
  if i==7:raise
  time.sleep(2)
raw=base64.b64decode(SCRIPT);assert hashlib.sha256(raw).hexdigest()==SCRIPT_SHA;(root/'capture.py').write_bytes(raw)
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',OMP_NUM_THREADS='2')
p=subprocess.run(['/data/researcher/vwa100-2026-10-09/venv/bin/python',str(root/'capture.py'),'--root',str(root)],env=env,capture_output=True,text=True,timeout=90)
(root/'capture-stdout.log').write_text(p.stdout);(root/'capture-stderr.log').write_text(p.stderr)
files={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest()for f in root.rglob('*')if f.is_file()}
(root/'source-seal.json').write_text(json.dumps(files,indent=2))
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED)as z:
 for n in list(files)+['source-seal.json']:z.writestr(n,(root/n).read_bytes())
print(json.dumps({'root':str(root),'returncode':p.returncode,'sha256':files,'zip':base64.b64encode(buf.getvalue()).decode(),'model_calls':0,'only_dedicated_site_restored':True,'no_reset_or_import':True}))
'''
row=json.loads(remote('SCRIPT='+repr(base64.b64encode(script).decode())+'\nSCRIPT_SHA='+repr(hashlib.sha256(script).hexdigest())+'\n'+code,host='4090',timeout=150))
out=PREP/('fresh-source-'+str(time.time_ns()));out.mkdir()
with zipfile.ZipFile(io.BytesIO(base64.b64decode(row.pop('zip'))))as z:
    for n in z.namelist():(out/n).resolve().relative_to(out.resolve())
    z.extractall(out)
for n,h in row['sha256'].items():assert hashlib.sha256((out/n).read_bytes()).hexdigest()==h,n
row['directory']=str(out);row['source_seal_sha256']=hashlib.sha256((out/'source-seal.json').read_bytes()).hexdigest()
(out/'collection-receipt.json').write_text(json.dumps(row,indent=2));(PREP/'fresh-source-current.json').write_text(json.dumps(row,indent=2))
print(json.dumps({k:v for k,v in row.items()if k!='sha256'}));assert row['returncode']==0,'Preserved failed source attempt; inspect before linked repair'
