"""Retry the preserved transport-only control failure, after other calls finish."""
import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;receipt=r/'v3.2-completion-negative-launch.json'
assert not receipt.exists(),'Inspect existing attempt; never duplicate'
old=json.loads((r/'v3.1-completion-negative-launch.json').read_text())
prior=json.loads((r/'v3.2-state-repair-launch.json').read_text())
stage=json.loads((r/'v2-staging.json').read_text())
preservation=json.loads((r/'v3.1-negative-transport-preservation.json').read_text())
sources=list(old['source_hashes']);baseline=next(p for p in sources if 'baseline'in p);completion=next(p for p in sources if 'post_only'in p)
code='''import pathlib,json,time,subprocess,hashlib
base=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');release=pathlib.Path(RELEASE);old=pathlib.Path(OLD);prior=pathlib.Path(PRIOR)
assert not pathlib.Path('/proc/'+str(PRIORPID)).exists(),'Another development check is still running; serialize model use'
assert not pathlib.Path('/proc/'+str(OLDPID)).exists()
assert not(old/'summary.json').exists(),'Do not rerun completed semantic controls'
assert pathlib.Path(PRESERVED).exists()
hashes=HASHES
assert all(hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==sha for p,sha in hashes.items())
assert (old/'actor-equivalence.json').exists()
out=base/('completion-negative-'+str(time.time_ns()));log=out.with_suffix('.log')
with log.open('xb')as stream:
 p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'completion_history_negative.py'),'--baseline',BASELINE,'--completion',COMPLETION,'--root',str(out),'--token-file',str(base/'transport.token'),'--reuse-actor-equivalence',str(old/'actor-equivalence.json')],cwd=release,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':p.pid,'root':str(out),'release':str(release),'log':str(log),'source_hashes':hashes,'technical_retry_of':str(old),'preservation':PRESERVED,'scope':'serialized marked counterfactual control, successful native actor equivalence retained with hashes; not actual GUI trajectory'}))
'''.replace('RELEASE',repr(stage['release'])).replace('OLDPID',str(old['pid'])).replace('PRIORPID',str(prior['pid'])).replace('OLD',repr(old['root'])).replace('PRIOR',repr(prior['root'])).replace('PRESERVED',repr(preservation['root'])).replace('HASHES',repr(old['source_hashes'])).replace('BASELINE',repr(baseline)).replace('COMPLETION',repr(completion))
result=json.loads(remote(code,host='4090'));receipt.write_text(json.dumps(result,indent=2));print(json.dumps(result))
