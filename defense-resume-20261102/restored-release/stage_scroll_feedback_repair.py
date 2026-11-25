"""Immutable feedback-only repair, unchanged actor/validators/budgets and service."""
import base64,hashlib,json
from pathlib import Path
from remote import remote

r=Path(__file__).resolve().parent
out=r/'v3.9.7-staging.json';assert not out.exists(),'Inspect prior development, never duplicate'
preserve=json.loads((r/'v3.9.7-scroll-failure-preservation.json').read_bytes())
files={n:base64.b64encode((r/n).read_bytes()).decode()for n in ['defense/core.py','scroll_feedback_replay.py']}
ident=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()[:16]
code=r'''
import pathlib,hashlib,json,base64,ast,shutil,subprocess,time,os,urllib.request
base=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');prior=pathlib.Path(SAVED['release'])
assert hashlib.sha256((prior/'defense/core.py').read_bytes()).hexdigest()==SAVED['core_sha256']
release=prior.parent/IDENT;assert not release.exists()
shutil.copytree(prior,release,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for n,b in FILES.items():(release/n).write_bytes(base64.b64decode(b))
before=ast.parse((prior/'defense/core.py').read_text());after=ast.parse((release/'defense/core.py').read_text())
oldfunc={n.name:n for n in before.body if isinstance(n,ast.FunctionDef)};newfunc={n.name:n for n in after.body if isinstance(n,ast.FunctionDef)}
assert set(newfunc)-set(oldfunc)=={'pending_action_patch'}
for n in oldfunc:
 if n!='correction_message':assert ast.dump(oldfunc[n],include_attributes=False)==ast.dump(newfunc[n],include_attributes=False),n
bc=next(n for n in before.body if isinstance(n,ast.ClassDef)and n.name=='Controller');ac=next(n for n in after.body if isinstance(n,ast.ClassDef)and n.name=='Controller')
bm={n.name:n for n in bc.body if isinstance(n,ast.FunctionDef)};am={n.name:n for n in ac.body if isinstance(n,ast.FunctionDef)}
for n in bm:
 if n!='decide':assert ast.dump(bm[n],include_attributes=False)==ast.dump(am[n],include_attributes=False),n
def action_feedback_if(fn):return next(n for n in ast.walk(fn)if isinstance(n,ast.If)and isinstance(n.test,ast.Name)and n.test.id=='action_bad')
action_feedback_if(am['decide']).body=action_feedback_if(bm['decide']).body
assert ast.dump(bm['decide'],include_attributes=False)==ast.dump(am['decide'],include_attributes=False)
names=['run_vwa_pilot.py','plan80.json','native-vwa-request.json','defense/prompts.py','defense/schema.py','defense/qwen_backend.py','defense/http_backend.py','inference_server.py']
assert all((release/n).read_bytes()==(prior/n).read_bytes()for n in names)
service=json.load(urllib.request.urlopen(urllib.request.Request('http://192.0.2.11:18127',headers={'Authorization':'Bearer '+(base/'transport.token').read_text().strip()}),timeout=15));assert service['phase']=='ready'and not service['actor_grammar']if 'actor_grammar'in service else service['phase']=='ready'
dev=base/('scroll-feedback-probe-'+str(time.time_ns()));log=dev.with_suffix('.log')
command=['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'scroll_feedback_replay.py'),'--source-root',str(base/'vwa-v39-1792930297029784133'),'--root',str(dev),'--token-file',str(base/'transport.token')]
with log.open('xb')as stream:p=subprocess.Popen(command,cwd=release,env=dict(os.environ,CUDA_VISIBLE_DEVICES=''),stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
record={'time':time.time(),'pid':p.pid,'root':str(dev),'release':str(release),'log':str(log),'command':command,'source_preservation':SAVED['preservation'],'only_changes':['feedback formatting','source-bound rejected proposal feedback','version'],'unchanged_sha256':{n:hashlib.sha256((release/n).read_bytes()).hexdigest()for n in names},'new_core_sha256':hashlib.sha256((release/'defense/core.py').read_bytes()).hexdigest(),'validators_unchanged_ast':True,'native_actor_and_service_unchanged':True,'scope':'Two real actor regenerations plus three verifier controls. No GUI, no official score.'}
(base/'scroll-feedback-development-active.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
'''
record=json.loads(remote('SAVED='+repr(preserve)+'\nFILES='+repr(files)+'\nIDENT='+repr(ident)+'\n'+code,host='4090',timeout=60))
out.write_text(json.dumps(record,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in record.items()if k!='unchanged_sha256'}))
