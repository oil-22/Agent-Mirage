"""Immutable marked contradiction control, never an actual GUI trajectory."""
import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;receipt=r/'v3.1-completion-negative-launch.json'
assert not receipt.exists(),'Inspect existing control before another launch'
stage=json.loads((r/'v2-staging.json').read_text());old=json.loads((r/'v2.9-vwa-resume.json').read_text());positive=json.loads((r/'v3.0-completion-replay-launch.json').read_text())
baseline=old['completed_runs_reused'][0]['attempt']+'/events.jsonl'
code='''import pathlib,json,subprocess,time,hashlib
base=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');release=pathlib.Path(RELEASE)
source_hashes={p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()for p in [BASELINE,COMPLETION]}
out=base/('completion-negative-'+str(time.time_ns()));log=out.with_suffix('.log')
with log.open('xb')as stream:
 p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'completion_history_negative.py'),'--baseline',BASELINE,'--completion',COMPLETION,'--root',str(out),'--token-file',str(base/'transport.token')],cwd=release,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':p.pid,'root':str(out),'release':str(release),'log':str(log),'source_hashes':source_hashes,'scope':'marked counterfactual wrong-current-page control and native actor equivalence; no GUI actions'}))
'''.replace('RELEASE',repr(stage['release'])).replace('BASELINE',repr(baseline)).replace('COMPLETION',repr(positive['source']))
result=json.loads(remote(code,host='4090'));receipt.write_text(json.dumps(result,indent=2));print(json.dumps(result))
