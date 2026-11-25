"""Launch isolated real-image readiness controls after owned formal worker paused."""
import json
from pathlib import Path
from remote import remote
here=Path(__file__).resolve().parent;out=here/'v3.9-readiness-launch.json';assert not out.exists()
old=json.loads((here/'v3.8.3-vwa-resume.json').read_text());stage=json.loads((here/'v2-staging.json').read_text())
pause=json.loads((here/'v3.8.3-overblocking-pause.json').read_text())
code=r'''
import pathlib,json,ast,time,subprocess,hashlib,shutil
source=pathlib.Path(SOURCE);release=pathlib.Path(RELEASE);old=pathlib.Path(OLDRELEASE)
state=json.loads((source/'status.json').read_text());assert state['phase']=='paused_at_decision_boundary'
proc=pathlib.Path('/proc')/str(PID);assert not proc.exists()or(proc/'stat').read_text().split()[2]=='Z'
preserve=pathlib.Path(PRESERVED);active=pathlib.Path(state['attempt']);assert(active/'paused.json').exists()
final=preserve/'active-final';assert not final.exists();shutil.copytree(active,final)
(preserve/'active-final-hashes.json').write_text(json.dumps({str(p.relative_to(active)):hashlib.sha256(p.read_bytes()).hexdigest()for p in active.rglob('*')if p.is_file()},indent=2))
for name in ['defense/http_backend.py','defense/qwen_backend.py','defense/schema.py','native-vwa-request.json','plan80.json','inference_server.py']:
 assert(release/name).read_bytes()==(old/name).read_bytes(),name
before={};after={};exec((old/'defense/prompts.py').read_text(),before);exec((release/'defense/prompts.py').read_text(),after)
for key in ['EVIDENCE','SCREEN','VERIFY','POINT','ALIGN','COMPLETION','COMPLETION_RELATION','HISTORY_REPORT']:assert before[key]==after[key],key
def methods(p):
 c=next(n for n in ast.parse(p.read_text()).body if isinstance(n,ast.ClassDef)and n.name=='Controller')
 return{n.name:ast.dump(n,include_attributes=False)for n in c.body if isinstance(n,ast.FunctionDef)}
b=methods(old/'defense/core.py');a=methods(release/'defense/core.py')
for key in b:
 if key!='inspect':assert b[key]==a[key],key
bindings={n:hashlib.sha256((release/n).read_bytes()).hexdigest()for n in ['defense/core.py','defense/prompts.py','defense/schema.py','defense/http_backend.py','defense/qwen_backend.py','run_vwa_pilot.py','native-vwa-request.json','plan80.json']}
root=source.parent/('readiness-v39-'+str(time.time_ns()));log=root.with_suffix('.log')
with log.open('xb')as stream:
 child=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'readiness_regression.py'),'--source',str(source),'--root',str(root),'--token-file',str(source.parent/'transport.token')],cwd=release,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':child.pid,'root':str(root),'release':str(release),'log':str(log),'time':time.time(),'source':str(source),'bindings':bindings,'scope':'Readiness-only repair. Actor, main/point/focus/completion prompts, parser, raw images, schema, budgets, scoring unchanged. Seven real-image checks + one engineering check, no GUI.'}))
'''.replace('SOURCE',repr(old['root'])).replace('OLDRELEASE',repr(old['release'])).replace('RELEASE',repr(stage['release'])).replace('PID',str(old['pid'])).replace('PRESERVED',repr(pause['preservation']))
data=json.loads(remote(code,host='4090'));out.write_text(json.dumps(data,indent=2),encoding='utf-8');print(json.dumps(data))
