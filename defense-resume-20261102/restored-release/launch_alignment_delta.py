"""Launch one immutable development delta; preserve previous failed attempts."""
import json,time
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent
formal=json.loads((r/'v2-vwa-launch.json').read_text())
staged=json.loads((r/'v2-staging.json').read_text())
receipt=r/'v2.9-alignment-replay-launch.json'
if receipt.exists():
    old=json.loads(receipt.read_text())
    code='''import pathlib,json,hashlib
r=pathlib.Path(ROOT);assert not pathlib.Path('/proc/'+str(PID)).exists(),'Previous delta still running'
files=[pathlib.Path(LOG)]+list(r.rglob('*.json'))+list(r.rglob('*.jsonl'))
print(json.dumps({'root':str(r),'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in files if p.is_file()}}))
'''.replace('ROOT',repr(old['root'])).replace('PID',str(old['pid'])).replace('LOG',repr(old['log']))
    evidence=json.loads(remote(code,host='4090'))
    archive=r/'replay-preservation'/Path(old['root']).name
    archive.mkdir(parents=True,exist_ok=False)
    (archive/'launch.json').write_bytes(receipt.read_bytes())
    (archive/'source-hashes.json').write_text(json.dumps(evidence,indent=2))
code='''import pathlib,json,subprocess,time
old=pathlib.Path(OLD);state=json.loads((old/'status.json').read_text())
assert state['phase']=='paused_at_decision_boundary',state
assert not pathlib.Path('/proc/'+str(state['pid'])).exists(),'Live worker not released'
r=old.parent;release=pathlib.Path(RELEASE);out=r/('alignment-delta-'+str(time.time_ns()));source=pathlib.Path(state['attempt'])/'events.jsonl'
with out.with_suffix('.log').open('xb')as log:
 p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'target_alignment_replay.py'),'--source',str(source),'--parent-release',PARENT,'--root',str(out),'--token-file',str(r/'transport.token')],cwd=release,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':p.pid,'root':str(out),'release':str(release),'log':str(out.with_suffix('.log')),'parent_batch':str(old),'source':str(source)}))
'''.replace('OLD',repr(formal['root'])).replace('PARENT',repr(formal['release'])).replace('RELEASE',repr(staged['release']))
result=json.loads(remote(code,host='4090'));receipt.write_text(json.dumps(result,indent=2));print(json.dumps(result))
