"""Freeze narrowly scoped coordinate prompt repair and run seven isolated controls."""
import base64,hashlib,json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;out=r/'v3.9.6-staging.json';assert not out.exists(),'Inspect existing staging worker'
old=json.loads((r/'v3.9.5-site-recovery-resume.json').read_text());saved=json.loads((r/'v3.9.6-failure-preservation.json').read_text(encoding='utf8'))
checks=(r/'checks-v3.9.6.txt').read_text();assert'Ran 116 tests'in checks and'OK'in checks
files={n:base64.b64encode((r/n).read_bytes()).decode()for n in ['defense/core.py','point_units_replay.py']};ident=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()[:16]
code=r'''
import pathlib,json,hashlib,shutil,base64,ast,subprocess,time,py_compile,urllib.request,fcntl
root=pathlib.Path(OLD['root']);prior=pathlib.Path(OLD['release']);s=json.loads((root/'status.json').read_text())
gate=(root/'point-units-stage.lock').open('a');fcntl.flock(gate,fcntl.LOCK_EX|fcntl.LOCK_NB)
marker=root/'v3.9.6-development-launch.json';assert not marker.exists()
assert s['phase']=='technical_failure'and s['attempt']==SAVED['source']and not pathlib.Path('/proc',str(s['pid'])).exists()
assert hashlib.sha256((pathlib.Path(SAVED['source'])/'events.jsonl').read_bytes()).hexdigest()==SAVED['sha256']['events.jsonl']
release=prior.parent/IDENT;assert not release.exists();shutil.copytree(prior,release,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for n,b in FILES.items():(release/n).write_bytes(base64.b64decode(b))
for p in release.rglob('*.py'):py_compile.compile(str(p),doraise=True)
before=ast.parse((prior/'defense/core.py').read_text());after=ast.parse((release/'defense/core.py').read_text())
def strip(t,patched=False):
 for n in t.body:
  if isinstance(n,ast.Assign)and any(isinstance(x,ast.Name)and x.id=='DEFENSE_VERSION'for x in n.targets):n.value=ast.Constant('VERSION')
  if isinstance(n,ast.ClassDef)and n.name=='Controller':
   for f in n.body:
    if isinstance(f,ast.FunctionDef)and f.name=='inspect'and patched:
     f.body=[x for x in f.body if not(isinstance(x,ast.If)and ast.dump(x.test,include_attributes=False)==ast.dump(ast.parse("phase=='point'",mode='eval').body,include_attributes=False))]
 return ast.dump(t,include_attributes=False)
assert strip(before)==strip(after,True),'Only point prompt branch and version may change; validators/actor/native behavior must remain exact'
names=['run_vwa_pilot.py','plan80.json','native-vwa-request.json','defense/prompts.py','defense/schema.py','defense/qwen_backend.py','defense/http_backend.py','inference_server.py']
assert all((release/n).read_bytes()==(prior/n).read_bytes()for n in names)
req=urllib.request.Request('http://192.0.2.11:18127',headers={'Authorization':'Bearer '+(root.parent/'transport.token').read_text().strip()});assert json.load(urllib.request.urlopen(req,timeout=10))['phase']=='ready'
dev=root.parent/('point-units-probe-'+str(time.time_ns()));log=dev.with_suffix('.log')
with log.open('xb')as f:p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'point_units_replay.py'),'--source',SAVED['source'],'--root',str(dev),'--token-file',str(root.parent/'transport.token')],cwd=release,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
bindings={n:hashlib.sha256((release/n).read_bytes()).hexdigest()for n in names+['defense/core.py']}
result={'pid':p.pid,'root':str(dev),'release':str(release),'log':str(log),'time':time.time(),'source':SAVED['source'],'bindings':bindings,'scope':'Seven predeclared real-model point/identity/WAIT controls, no GUI/actor. Only point coordinate prompt changed; native condition and service unchanged.'}
marker.write_text(json.dumps(result,indent=2));print(json.dumps(result))
'''
d=json.loads(remote('OLD='+repr(old)+'\nSAVED='+repr(saved)+'\nFILES='+repr(files)+'\nIDENT='+repr(ident)+'\n'+code,host='4090'));out.write_text(json.dumps(d,indent=2));print(json.dumps({k:v for k,v in d.items()if k!='bindings'}))
