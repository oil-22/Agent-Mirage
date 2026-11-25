"""Run a source-bound controller delta without any new model requests."""
import json
from pathlib import Path
from remote import remote
here=Path(__file__).resolve().parent;out=here/'v3.8.3-guard-launch.json';assert not out.exists()
stage=json.loads((here/'v2-staging.json').read_text());source=json.loads((here/'v3.8.2-history-launch.json').read_text())
previous=json.loads((here/'v3.7-scope-launch.json').read_text());formal=json.loads((here/'v3.6.2-online-oom-preservation.json').read_text())
preserved=json.loads((here/'v3.8.2-history-failure-preservation.json').read_text())
code=r'''import pathlib,json,hashlib,subprocess,time
base=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');release=pathlib.Path(RELEASE);old=pathlib.Path(OLDRELEASE)
assert pathlib.Path(PRESERVED).exists()
for name in ['defense/prompts.py','defense/schema.py','defense/qwen_backend.py','defense/http_backend.py','run_vwa_pilot.py','native-vwa-request.json','plan80.json','history_report_delta.py']:
 assert(release/name).read_bytes()==(old/name).read_bytes(),name
root=base/('history-guard-v383-'+str(time.time_ns()));log=root.with_suffix('.log')
with log.open('xb')as stream:p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'history_guard_delta.py'),'--replay-source',SOURCE,'--source',FORMAL,'--previous',PREVIOUS,'--root',str(root),'--token-file',str(base/'transport.token')],cwd=release,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':p.pid,'root':str(root),'log':str(log),'release':str(release),'time':time.time(),'scope':'No model HTTP calls; exact-input frozen responses for unchanged routes, comparison scope guard for changed routes'}))
'''.replace('OLDRELEASE',repr(source['release'])).replace('RELEASE',repr(stage['release'])).replace('PRESERVED',repr(preserved['preservation'])).replace('SOURCE',repr(source['root'])).replace('FORMAL',repr(formal['formal']['attempt']+'/events.jsonl')).replace('PREVIOUS',repr(previous['root']))
data=json.loads(remote(code,host='4090'));out.write_text(json.dumps(data,indent=2));print(json.dumps(data))
