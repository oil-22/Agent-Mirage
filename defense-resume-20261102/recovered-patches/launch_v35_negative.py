"""Recheck actual wrong-current-page rejection after the verifier-prompt change."""
import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;receipt=r/'v3.5-negative-launch.json'
assert not receipt.exists()
old=json.loads((r/'v3.2-completion-negative-launch.json').read_text())
prior=json.loads((r/'v3.5-comparison-launch.json').read_text())
sources=list(old['source_hashes']);baseline=next(p for p in sources if 'baseline'in p);completion=next(p for p in sources if 'post_only'in p)
code=r'''
import pathlib,json,time,subprocess,hashlib
prior=pathlib.Path(PRIOR);release=pathlib.Path(RELEASE);old=pathlib.Path(OLD)
assert not pathlib.Path('/proc/'+str(PRIORPID)).exists(),'Serialize inference; controls still running'
assert(prior/'summary.json').exists(),'Inspect/preserve any failed controls before proceeding'
assert all(hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==sha for p,sha in HASHES.items())
assert(old/'actor-equivalence.json').exists()
base=prior.parent;out=base/('completion-negative-v35-'+str(time.time_ns()));log=out.with_suffix('.log')
with log.open('xb')as stream:
 p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'completion_history_negative.py'),'--baseline',BASELINE,'--completion',COMPLETION,'--root',str(out),'--token-file',str(base/'transport.token'),'--reuse-actor-equivalence',str(old/'actor-equivalence.json')],cwd=release,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':p.pid,'root':str(out),'release':str(release),'log':str(log),'time':time.time(),'source_hashes':HASHES,'scope':'changed-verifier-prompt negative regression, composed wrong-current candidate and legal baseline history; not an actual trajectory or Mirage rate'}))
'''.replace('PRIORPID',repr(prior['pid'])).replace('PRIOR',repr(prior['root'])).replace('RELEASE',repr(prior['release'])).replace('OLD',repr(old['root'])).replace('HASHES',repr(old['source_hashes'])).replace('BASELINE',repr(baseline)).replace('COMPLETION',repr(completion))
result=json.loads(remote(code,host='4090'));receipt.write_text(json.dumps(result,indent=2));print(json.dumps(result))
