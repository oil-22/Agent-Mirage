"""Repeat only a failed development terminal request, preserving prior attempt."""
from pathlib import Path
import json
from remote import remote
r=Path(__file__).resolve().parent
receipt=r/'v3.0-completion-replay-launch.json';old=json.loads(receipt.read_text())
stage=json.loads((r/'v2-staging.json').read_text())
code='''import pathlib,json,hashlib
r=pathlib.Path(ROOT);assert not pathlib.Path('/proc/'+str(PID)).exists(),'Prior development check still running'
assert not(r/'summary.json').exists(),'Completed semantic result must be inspected, not retried unchanged'
files=list(r.rglob('*.json'))+list(r.rglob('*.jsonl'))+[pathlib.Path(LOG)]
print(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in files if p.is_file()}))
'''.replace('ROOT',repr(old['root'])).replace('PID',str(old['pid'])).replace('LOG',repr(old['log']))
hashes=json.loads(remote(code,host='4090'))
out=r/'replay-preservation'/Path(old['root']).name;out.mkdir(parents=True,exist_ok=False)
(out/'launch.json').write_bytes(receipt.read_bytes());(out/'source-hashes.json').write_text(json.dumps(hashes,indent=2))
code='''import pathlib,json,subprocess,time
release=pathlib.Path(RELEASE);base=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');out=base/('completion-history-'+str(time.time_ns()))
with out.with_suffix('.log').open('xb')as log:
 p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'completion_history_replay.py'),'--source',SOURCE,'--root',str(out),'--token-file',str(base/'transport.token')],cwd=release,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':p.pid,'root':str(out),'release':str(release),'source':SOURCE,'log':str(out.with_suffix('.log')),'technical_retry_of':OLD,'reason':'same full input after allocator-only service replacement; previous OOM preserved'}))
'''.replace('RELEASE',repr(stage['release'])).replace('SOURCE',repr(old['source'])).replace('OLD',repr(old['root']))
result=json.loads(remote(code,host='4090'));receipt.write_text(json.dumps(result,indent=2));print(json.dumps(result))
