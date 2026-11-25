"""Freeze minimal controller/prompt repair without restarting the model service."""
import argparse,base64,hashlib,json,re
from pathlib import Path
from remote import remote
ap=argparse.ArgumentParser();ap.add_argument('--version',choices=['v3.9.3'],default='v3.9.3');args=ap.parse_args()
r=Path(__file__).resolve().parent;out=r/(args.version+'-staging.json');assert not out.exists()
old=json.loads((r/'v3.9-vwa-launch.json').read_text());preserve=json.loads((r/'v3.9.1-failure-preservation.json').read_text(encoding='utf8'))
checks=(r/('checks-'+args.version+'.txt')).read_text();assert 'Ran 108 tests'in checks and 'OK'in checks
previous=json.loads((r/'v3.9.2-staging.json').read_text())
files={n:base64.b64encode((r/n).read_bytes()).decode()for n in ['defense/core.py','defense/prompts.py','navigation_citation_replay.py']}
ident=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()[:16]
code=r'''
import pathlib,base64,json,hashlib,shutil,ast,py_compile,time,subprocess
prior=pathlib.Path(OLD['release']);root=pathlib.Path(OLD['root']);s=json.loads((root/'status.json').read_text())
assert s['phase']=='technical_failure'and not pathlib.Path('/proc',str(s['pid'])).exists()
if PREVIOUS is not None:
 assert not pathlib.Path('/proc',str(PREVIOUS['pid'])).exists(),'Previous development calls are still running'
 assert pathlib.Path(PREVIOUS['root'],'summary.json').exists()
assert pathlib.Path(PRESERVE['preservation'],'failed-attempt-sha256.json').exists()
release=prior.parent/IDENT
if not release.exists():
 shutil.copytree(prior,release,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 for n,b in FILES.items():(release/n).write_bytes(base64.b64decode(b))
else:
 for n,b in FILES.items():assert(release/n).read_bytes()==base64.b64decode(b)
for p in release.rglob('*.py'):py_compile.compile(str(p),doraise=True)
changed=[]
for p in prior.rglob('*'):
 if p.is_file()and '__pycache__'not in p.parts and p.suffix!='.pyc':
  n=str(p.relative_to(prior))
  if p.read_bytes()!=(release/n).read_bytes():changed.append(n)
assert sorted(changed)==['defense/core.py','defense/prompts.py'],changed
before={};after={};exec((prior/'defense/prompts.py').read_text(),before);exec((release/'defense/prompts.py').read_text(),after)
assert all(before[k]==after[k]for k in before if not k.startswith('__'))
def functions(path):
 t=ast.parse(path.read_text());d={}
 for n in t.body:
  if isinstance(n,(ast.FunctionDef,ast.ClassDef)):
   if isinstance(n,ast.ClassDef)and n.name=='Controller':
    for m in n.body:
     if isinstance(m,ast.FunctionDef):d['Controller.'+m.name]=ast.dump(m,include_attributes=False)
   else:d[n.name]=ast.dump(n,include_attributes=False)
 return d
b=functions(prior/'defense/core.py');a=functions(release/'defense/core.py')
assert all(b[k]==a[k]for k in b if k not in {'Controller.inspect','validate_verdict'})
# The existing validator remains exact except for the explicit back-history source fence.
old_tree=ast.parse((prior/'defense/core.py').read_text());new_tree=ast.parse((release/'defense/core.py').read_text())
vf=next(n for n in new_tree.body if isinstance(n,ast.FunctionDef)and n.name=='validate_verdict')
vf.body=[n for n in vf.body if not(isinstance(n,ast.If)and any(isinstance(c,ast.Constant)and isinstance(c.value,str)and c.value.startswith('Native back history citation')for c in ast.walk(n)))]
old_vf=next(n for n in old_tree.body if isinstance(n,ast.FunctionDef)and n.name=='validate_verdict')
assert ast.dump(vf,include_attributes=False)==ast.dump(old_vf,include_attributes=False)
names=['defense/core.py','defense/prompts.py','defense/schema.py','defense/qwen_backend.py','defense/http_backend.py','run_vwa_pilot.py','native-vwa-request.json','plan80.json']
bindings={n:hashlib.sha256((release/n).read_bytes()).hexdigest()for n in names}
dev=root.parent/('navigation-citation-probe-'+str(time.time_ns()));log=dev.with_suffix('.log')
with log.open('xb')as stream:
 p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'navigation_citation_replay.py'),'--source',PRESERVE['source'],'--root',str(dev),'--token-file',str(root.parent/'transport.token')],cwd=release,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':p.pid,'root':str(dev),'release':str(release),'log':str(log),'source':PRESERVE['source'],'bindings':bindings,'changed':changed,'time':time.time(),'scope':'Three actual model calls, exact failed back plus false-price and pure-WAIT controls. No GUI. Existing inference service/schema/actor unchanged.'}))
'''
values={'OLD':old,'PRESERVE':preserve,'FILES':files,'IDENT':ident,'PREVIOUS':previous}
code=re.sub(r'\b(?:OLD|PRESERVE|FILES|IDENT|PREVIOUS)\b',lambda m:repr(values[m.group()]),code)
compile(code,'stage-navigation','exec');data=json.loads(remote(code,host='4090'));out.write_text(json.dumps(data,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in data.items()if k!='bindings'}))
