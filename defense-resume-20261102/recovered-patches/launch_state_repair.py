"""One immutable, provenance-bound v3.1 development launch (not a GUI run)."""
import json,argparse
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--receipt',default='v3.1-state-repair-launch.json');a=ap.parse_args()
receipt=r/a.receipt;assert not receipt.exists(),'Inspect existing attempt, do not duplicate'
stage=json.loads((r/'v2-staging.json').read_text());prior=json.loads((r/'v3.0-completion-replay-launch.json').read_text())
developers=[json.loads(p.read_text())for pattern in ['*-state-repair-launch.json','*-completion-negative-launch.json']for p in r.glob(pattern)]
code='''import pathlib,json,subprocess,time,urllib.request,hashlib
base=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');release=pathlib.Path(RELEASE)
for launch in DEVELOPERS:
 proc=pathlib.Path('/proc')/str(launch['pid'])
 if proc.exists()and(proc/'stat').read_text().split()[2]!='Z':
  cmd=(proc/'cmdline').read_bytes().decode().replace(chr(0),' ')
  assert launch['root']not in cmd,'Another own development check is active; model use must be serialized'
req=urllib.request.Request('http://192.0.2.11:18127',headers={'Authorization':'Bearer '+(base/'transport.token').read_text().strip()})
health=json.loads(urllib.request.urlopen(req,timeout=10).read());assert health['phase']=='ready',health
formal=base/'vwa-v2-1792889217112260713';state=json.loads((formal/'status.json').read_text())
assert state['phase']=='paused_at_decision_boundary'and not pathlib.Path('/proc/'+str(state['pid'])).exists(),state
prior=pathlib.Path(PRIOR);summary=json.loads((prior/'summary.json').read_text());assert summary['phase']=='completed'and not summary['passed']
preserve=base/('state-repair-preservation-'+str(time.time_ns()));preserve.mkdir()
paths=[prior/'summary.json',prior/'manifest.json',prior/'completion/events.jsonl',pathlib.Path(SOURCE),formal/'status.json']
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}
(preserve/'hashes.json').write_text(json.dumps(hashes,indent=2))
for i,p in enumerate(paths):(preserve/(str(i)+'-'+p.name)).write_bytes(p.read_bytes())
out=base/('state-repair-'+str(time.time_ns()));log=out.with_suffix('.log')
with log.open('xb')as stream:
 p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'completion_state_repair.py'),'--source',SOURCE,'--prior',str(prior/'summary.json'),'--root',str(out),'--token-file',str(base/'transport.token')],cwd=release,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':p.pid,'root':str(out),'release':str(release),'log':str(log),'preservation':str(preserve),'source':SOURCE,'prior':str(prior),'scope':'offline source-bound state repair, no GUI or new screenshots'}))
'''.replace('RELEASE',repr(stage['release'])).replace('PRIOR',repr(prior['root'])).replace('SOURCE',repr(prior['source'])).replace('DEVELOPERS',repr(developers))
result=json.loads(remote(code,host='4090'));receipt.write_text(json.dumps(result,indent=2));print(json.dumps(result))
