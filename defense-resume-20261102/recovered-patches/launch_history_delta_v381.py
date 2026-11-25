"""Fresh history-grammar attempt after preserved failure and service controls."""
import json
from pathlib import Path
from remote import remote
here=Path(__file__).resolve().parent;receipt=here/'v3.8.1-history-launch.json';assert not receipt.exists()
stage=json.loads((here/'v2-staging.json').read_text());previous=json.loads((here/'v3.7-scope-launch.json').read_text())
failed=json.loads((here/'v3.8-history-launch.json').read_text());preserved=json.loads((here/'v3.8-history-failure-preservation.json').read_text(encoding='utf-8'))
formal=json.loads((here/'v3.6.2-online-oom-preservation.json').read_text())
capacity=json.loads((here/'v9-capacity-progress.json').read_text());assert capacity['summary']['passed']
code=r'''import pathlib,json,time,subprocess,hashlib,types
base=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');release=pathlib.Path(RELEASE);previous=pathlib.Path(PREVIOUS)
proc=pathlib.Path('/proc')/str(FAILEDPID);assert not proc.exists()or(proc/'stat').read_text().split()[2]=='Z'
assert pathlib.Path(PRESERVED).exists()
oldrelease=pathlib.Path(OLDRELEASE);newns={};oldns={};exec((release/'defense/prompts.py').read_text(),newns);exec((oldrelease/'defense/prompts.py').read_text(),oldns)
for key in ['EVIDENCE','SCREEN','VERIFY','POINT','ALIGN','COMPLETION','COMPLETION_RELATION']:assert oldns[key]==newns[key],key
for name in ['defense/http_backend.py','native-vwa-request.json','plan80.json']:assert(release/name).read_bytes()==(oldrelease/name).read_bytes(),name
oldschema={};newschema={};exec((oldrelease/'defense/schema.py').read_text(),oldschema);exec((release/'defense/schema.py').read_text(),newschema)
for images in [[],[None],21*[None]]:
 for candidate in [None,'candidate text',{'mode':'point_probe'}]:
  view=types.SimpleNamespace(observation_id='test',images=images,messages=[{'role':'user','content':'Task'},{'role':'assistant','content':'History'}])
  assert oldschema['judge_schema'](view,candidate)==newschema['judge_schema'](view,candidate)
source=pathlib.Path(SOURCE);out=base/('history-report-v381-'+str(time.time_ns()));log=out.with_suffix('.log')
with log.open('xb')as stream:p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'history_report_delta.py'),'--source',str(source),'--previous',str(previous),'--root',str(out),'--token-file',str(base/'transport.token')],cwd=release,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':p.pid,'root':str(out),'release':str(release),'log':str(log),'time':time.time(),'previous':str(previous),'previous_summary_sha256':hashlib.sha256((previous/'summary.json').read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'default_schema_equivalence':True,'scope':'New history-only schema/source syntax controls; unchanged hash-bound visual/main requests reused. No GUI or independent Mirage labels'}))
'''.replace('OLDRELEASE',repr(previous['release'])).replace('RELEASE',repr(stage['release'])).replace('PREVIOUS',repr(previous['root'])).replace('FAILEDPID',str(failed['pid'])).replace('PRESERVED',repr(preserved['preservation'])).replace('SOURCE',repr(formal['formal']['attempt']+'/events.jsonl'))
data=json.loads(remote(code,host='4090'));receipt.write_text(json.dumps(data,indent=2));print(json.dumps(data))
