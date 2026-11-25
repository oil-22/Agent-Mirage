"""Preserve a /proc fd enumeration race and collect the completed zero-call preflight."""
import base64, hashlib, io, json, time, zipfile
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent;PREP=BASE/'focus-history-fullgui-development'
sha=lambda b:hashlib.sha256(b).hexdigest()
assert not(PREP/'fullgui-staging-current.json').exists()
out=next(PREP.glob('fullgui-stage-*'));release=out/'release'
code=r'''
import base64,hashlib,io,json,os,zipfile,time
from pathlib import Path
b=Path('/data/researcher/mirage-defense-pilot-20261023');active=b/'focus-history-fullgui-preparation-active-20261029.json';r=Path(json.loads(active.read_bytes())['root'])
assert os.getuid()==1015
assert hashlib.sha256((r/'release-sha256.json').read_bytes()).hexdigest()==EXPECTED
for n,h in json.loads((r/'release-sha256.json').read_bytes()).items():assert hashlib.sha256((r/'release'/n).read_bytes()).hexdigest()==h,n
state=json.loads((r/'environment/status.json').read_bytes());assert state['phase']=='environment_preflight_complete'and state['model_calls']==0,state
workers=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  cmd=[s.decode()for s in(p/'cmdline').read_bytes().split(b'\0')if s]
  if str(r/'release/run_vwa_pilot.py')in cmd:workers.append({'pid':int(p.name),'uid':p.stat().st_uid,'command':cmd})
 except(FileNotFoundError,PermissionError,ProcessLookupError):pass
assert not workers,workers
row={'root':str(r),'returncode':0,'status':state,'model_calls':0,'new_GPU_allocation':False,'formal_trial_started':False,'no_site_reset_or_fixture_import':True,'child_exited':True,'source_package_sha256':EXPECTED,'reporter_recovery':'Parent failed enumerating a disappearing child /proc fdinfo after spawn. Child completed original zero-inference preflight; no preflight or model control rerun. Original logs/sources retained.'}
allfiles={str(f.relative_to(r)):hashlib.sha256(f.read_bytes()).hexdigest()for f in r.rglob('*')if f.is_file()and'__pycache__'not in str(f)}
assert not(r/'terminal-sha256.json').exists()
(r/'terminal-sha256.json').write_text(json.dumps(allfiles,indent=2));row['terminal_manifest_sha256']=hashlib.sha256((r/'terminal-sha256.json').read_bytes()).hexdigest()
files=['container-identity.json','remote-cpu-tests.json','environment-worker.log','terminal-sha256.json','environment/status.json','environment/initial.png','environment/real-recapture.png']
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED)as z:
 for n in files:z.writestr(n,(r/n).read_bytes())
row['zip']=base64.b64encode(buf.getvalue()).decode();row['public_file_sha256']={n:hashlib.sha256((r/n).read_bytes()).hexdigest()for n in files}
(r/'receipt.json').write_text(json.dumps({k:v for k,v in row.items()if k!='zip'},indent=2));print(json.dumps(row))
'''
row=json.loads(remote('EXPECTED='+repr(sha((out/'release-sha256.json').read_bytes()))+'\n'+code,host='4090',timeout=40))
col=out/'environment-evidence';col.mkdir()
with zipfile.ZipFile(io.BytesIO(base64.b64decode(row.pop('zip'))))as z:
 for n in z.namelist():(col/n).resolve().relative_to(col.resolve())
 z.extractall(col)
for n,h in row['public_file_sha256'].items():assert sha((col/n).read_bytes())==h,n
(out/'environment-receipt.json').write_text(json.dumps(row,indent=2),encoding='utf-8')
pointer={'directory':str(out),'release':str(release),'release_manifest_sha256':sha((out/'release-sha256.json').read_bytes()),'environment_receipt_sha256':sha((out/'environment-receipt.json').read_bytes()),'remote_preparation_root':row['root'],'environment_returncode':0,'environment_phase':row['status']['phase'],'model_calls':0,'formal_execution_authorized':True,'fullGUI_launcher_ready':False,'reporter_recovery':row['reporter_recovery']}
(PREP/'fullgui-staging-current.json').write_text(json.dumps(pointer,indent=2));print(json.dumps(pointer))
