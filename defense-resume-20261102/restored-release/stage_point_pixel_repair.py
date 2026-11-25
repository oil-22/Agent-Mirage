"""Immutable isolated point-reader protocol development; no formal queue launch."""
import base64,hashlib,json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;out=r/'v3.9.8-staging.json';assert not out.exists()
old=json.loads((r/'v3.9.7-scroll-validation-launch.json').read_bytes())
saved=json.loads((r/'v3.9.8-failure-preservation.json').read_bytes())
older=json.loads((r/'v3.9.6-failure-preservation.json').read_bytes())
checks=(r/'checks-v3.9.8.txt').read_text();assert 'Ran 126 tests' in checks and 'OK' in checks
files={n:base64.b64encode((r/n).read_bytes()).decode()for n in ['defense/core.py','defense/prompts.py','point_pixel_replay.py']}
ident=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()[:16]
code=r'''
import pathlib,json,hashlib,shutil,base64,ast,subprocess,time,py_compile,urllib.request,fcntl,pwd,os
root=pathlib.Path(OLD['root']);prior=pathlib.Path(OLD['release']);s=json.loads((root/'status.json').read_bytes())
gate=(root/'point-pixel-stage.lock').open('a');fcntl.flock(gate,fcntl.LOCK_EX|fcntl.LOCK_NB)
marker=root/'v3.9.8-development-launch.json';assert not marker.exists()
assert os.getuid()==1015 and s['phase']=='technical_failure'and s['attempt']==SAVED['source']and not pathlib.Path('/proc',str(s['pid'])).exists()
assert hashlib.sha256((pathlib.Path(SAVED['source'])/'events.jsonl').read_bytes()).hexdigest()==SAVED['sha256']['events.jsonl']
release=prior.parent/IDENT;assert not release.exists();shutil.copytree(prior,release,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for n,b in FILES.items():(release/n).write_bytes(base64.b64decode(b))
for p in release.rglob('*.py'):py_compile.compile(str(p),doraise=True)
def protected(source):
 t=ast.parse(source);defs={}
 for n in ast.walk(t):
  if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))and n.name!='inspect':defs[n.name]=ast.dump(n,include_attributes=False)
 return defs
assert protected((prior/'defense/core.py').read_text())==protected((release/'defense/core.py').read_text()),'All core functions except inspect must be exact'
def constants(p):
 ns={};exec(compile(p.read_text(),str(p),'exec'),ns);return {k:v for k,v in ns.items()if k.isupper()}
a=constants(prior/'defense/prompts.py');b=constants(release/'defense/prompts.py');assert all(b[k]==v for k,v in a.items())and set(b)-set(a)=={'POINT_PIXEL'}
names=['run_vwa_pilot.py','plan80.json','native-vwa-request.json','defense/schema.py','defense/qwen_backend.py','defense/http_backend.py','inference_server.py']
assert all((release/n).read_bytes()==(prior/n).read_bytes()for n in names)
token=(root.parent/'transport.token').read_text().strip()
health=json.load(urllib.request.urlopen(urllib.request.Request('http://192.0.2.11:18127',headers={'Authorization':'Bearer '+token}),timeout=15));assert health['phase']=='ready'
dev=root.parent/('point-pixel-probe-'+str(time.time_ns()));log=dev.with_suffix('.log')
command=['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'point_pixel_replay.py'),'--source',SAVED['source'],'--older-source',OLDER['source'],'--root',str(dev),'--token-file',str(root.parent/'transport.token')]
with log.open('xb')as f:p=subprocess.Popen(command,cwd=release,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
bindings={n:hashlib.sha256((release/n).read_bytes()).hexdigest()for n in names+list(FILES)}
record={'pid':p.pid,'uid':os.getuid(),'root':str(dev),'release':str(release),'log':str(log),'time':time.time(),'command':command,'source':SAVED['source'],'older_source':OLDER['source'],'bindings':bindings,'scope':'Eight predeclared real-model controls on two original failure screenshots; one call per control, no GUI/actor. All validators and native conditions unchanged; only isolated point-reader pixel transport and prompt.'}
with marker.open('x')as f:json.dump(record,f,indent=2)
print(json.dumps(record))
'''
d=json.loads(remote('OLD='+repr(old)+'\nSAVED='+repr(saved)+'\nOLDER='+repr(older)+'\nFILES='+repr(files)+'\nIDENT='+repr(ident)+'\n'+code,host='4090',timeout=60));out.write_text(json.dumps(d,indent=2));print(json.dumps({k:v for k,v in d.items()if k!='bindings'}))
