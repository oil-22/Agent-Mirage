"""Freeze and launch exact-source repair checks; leave existing service untouched."""
import argparse,base64,hashlib,json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;ap=argparse.ArgumentParser();ap.add_argument('--version',choices=['v3.9.4','v3.9.5'],default='v3.9.5');args=ap.parse_args();version=args.version
out=r/(version+'-staging.json');assert not out.exists(),'Inspect existing development launch'
old=json.loads((r/'v3.9.3-vwa-resume.json').read_text());saved=json.loads((r/'v3.9.4-failure-preservation.json').read_text(encoding='utf8'))
checks=(r/('checks-'+version+'.txt')).read_text();assert ('Ran 114 tests'if version=='v3.9.5'else'Ran 112 tests')in checks and 'OK'in checks
previous=json.loads((r/'v3.9.4-staging.json').read_text())if version=='v3.9.5'else None
files={n:base64.b64encode((r/n).read_bytes()).decode()for n in ['defense/core.py','defense/prompts.py','factual_citation_replay.py']};ident=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()[:16]
code=r'''
import pathlib,json,hashlib,shutil,base64,ast,subprocess,time,py_compile,urllib.request,fcntl
root=pathlib.Path(OLD['root']);prior=pathlib.Path(OLD['release']);s=json.loads((root/'status.json').read_text())
gate=(root/'factual-repair-stage.lock').open('a');fcntl.flock(gate,fcntl.LOCK_EX|fcntl.LOCK_NB)
marker=root/(VERSION+'-development-launch.json');assert not marker.exists()
if PREVIOUS:
 assert not pathlib.Path('/proc',str(PREVIOUS['pid'])).exists()and pathlib.Path(PREVIOUS['root'],'summary.json').exists()
assert s['phase']=='technical_failure'and s['attempt']==SAVED['source']and not pathlib.Path('/proc',str(s['pid'])).exists()
assert hashlib.sha256((pathlib.Path(SAVED['source'])/'events.jsonl').read_bytes()).hexdigest()==SAVED['sha256']['events.jsonl']
release=prior.parent/IDENT
assert not release.exists();shutil.copytree(prior,release,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for n,b in FILES.items():(release/n).write_bytes(base64.b64decode(b))
for p in release.rglob('*.py'):py_compile.compile(str(p),doraise=True)
def funcs(p):
 t=ast.parse(p.read_text());out={}
 for n in t.body:
  if isinstance(n,ast.FunctionDef):out[n.name]=ast.dump(n,include_attributes=False)
  elif isinstance(n,ast.ClassDef):
   for f in n.body:
    if isinstance(f,ast.FunctionDef):out[n.name+'.'+f.name]=ast.dump(f,include_attributes=False)
 return out
b=funcs(prior/'defense/core.py');a=funcs(release/'defense/core.py')
assert set(a)-set(b)==({'historical_report_records','instruction_only_history_source'}if VERSION=='v3.9.5'else set())
assert all(a[k]==b[k]for k in b if k not in {'Controller.inspect','validate_verdict'})
ot=ast.parse((prior/'defense/core.py').read_text());nt=ast.parse((release/'defense/core.py').read_text())
ov=next(n for n in ot.body if isinstance(n,ast.FunctionDef)and n.name=='validate_verdict');nv=next(n for n in nt.body if isinstance(n,ast.FunctionDef)and n.name=='validate_verdict')
for loop in nv.body:
 if isinstance(loop,ast.For):loop.body=[n for n in loop.body if not(isinstance(n,ast.If)and any(isinstance(c,ast.Constant)and c.value=='Task or correction instructions cannot prove historical observations'for c in ast.walk(n)))]
assert ast.dump(nv,include_attributes=False)==ast.dump(ov,include_attributes=False),'Existing validator fences must remain exact'
names=['run_vwa_pilot.py','plan80.json','native-vwa-request.json','defense/schema.py','defense/qwen_backend.py','defense/http_backend.py','inference_server.py']
assert all((release/n).read_bytes()==(prior/n).read_bytes()for n in names)
before={};after={};exec((prior/'defense/prompts.py').read_text(),before);exec((release/'defense/prompts.py').read_text(),after)
assert all(before[k]==after[k]for k in before if not k.startswith('__'))
req=urllib.request.Request('http://192.0.2.11:18127',headers={'Authorization':'Bearer '+(root.parent/'transport.token').read_text().strip()});assert json.load(urllib.request.urlopen(req,timeout=10))['phase']=='ready'
dev=root.parent/('factual-citation-probe-'+str(time.time_ns()));log=dev.with_suffix('.log')
with log.open('xb')as f:p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'factual_citation_replay.py'),'--source',SAVED['source'],'--root',str(dev),'--token-file',str(root.parent/'transport.token')],cwd=release,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
bindings={n:hashlib.sha256((release/n).read_bytes()).hexdigest()for n in names+['defense/core.py','defense/prompts.py']}
result={'pid':p.pid,'root':str(dev),'release':str(release),'log':str(log),'time':time.time(),'source':SAVED['source'],'bindings':bindings,'scope':'Four real model controls, no GUI/actor. Existing native experiment and service unchanged.'}
marker.write_text(json.dumps(result,indent=2));print(json.dumps(result))
'''
code='OLD='+repr(old)+'\nSAVED='+repr(saved)+'\nFILES='+repr(files)+'\nIDENT='+repr(ident)+'\nVERSION='+repr(version)+'\nPREVIOUS='+repr(previous)+'\n'+code
d=json.loads(remote(code,host='4090'));out.write_text(json.dumps(d,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in d.items()if k!='bindings'}))
