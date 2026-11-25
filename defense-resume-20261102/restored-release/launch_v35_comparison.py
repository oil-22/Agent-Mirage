"""Launch one immutable, serial development control set after the formal safe pause."""
import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;receipt=r/'v3.5-comparison-launch.json'
assert not receipt.exists(),'Inspect existing result; never rerun unchanged controls'
old=json.loads((r/'v3.4.1-vwa-resume.json').read_text())
stage=json.loads((r/'v2-staging.json').read_text())
code=r'''
import pathlib,json,hashlib,os,time,subprocess,urllib.request,fcntl
root=pathlib.Path(ROOT);release=pathlib.Path(RELEASE);old=pathlib.Path(OLD)
state=json.loads((root/'status.json').read_text())
assert state['phase']in {'paused_at_run_boundary','paused_at_decision_boundary','technical_failure','failed'},state
assert not pathlib.Path('/proc/'+str(state['pid'])).exists(),'Formal worker still running; do not overlap model requests'
with(root/'batch.lock').open('a')as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
core=(release/'defense/core.py').read_text().replace("DEFENSE_VERSION='evidence-v3.5-bounded-comparison-20261025'","DEFENSE_VERSION='evidence-v3.4.1-reference-context-guard-20261025'")
assert core==(old/'defense/core.py').read_text(),'Unexpected controller change'
unchanged=['defense/schema.py','defense/http_backend.py','defense/qwen_backend.py','run_vwa_pilot.py','native-vwa-request.json','plan80.json']
for n in unchanged:assert(release/n).read_bytes()==(old/n).read_bytes(),n
source=pathlib.Path(SOURCE);assert root in source.parents
preserve=root/'preservation'/('sorted-obligation-final-'+str(time.time_ns()));preserve.mkdir(parents=True)
paths=[root/'status.json',source,pathlib.Path(LOG)]+list(source.parent.glob('*.json'))+list(source.parent.glob('*.png'))+list(source.parent.glob('*.zip'))
hashes={}
for i,p in enumerate(paths):
 raw=p.read_bytes();hashes[str(p)]=hashlib.sha256(raw).hexdigest();(preserve/(str(i)+'-'+p.name)).write_bytes(raw)
(preserve/'hashes.json').write_text(json.dumps(hashes,indent=2))
req=urllib.request.Request('http://192.0.2.11:18127',headers={'Authorization':'Bearer '+(root.parent/'transport.token').read_text().strip()})
health=json.loads(urllib.request.urlopen(req,timeout=10).read());assert health['phase']=='ready'and not health['actor_grammar']
for entry in pathlib.Path('/proc').iterdir():
 if not entry.name.isdigit():continue
 try:
  if entry.stat().st_uid!=os.getuid():continue
  cmd=(entry/'cmdline').read_bytes().replace(b'\0',b' ').decode()
 except(OSError,UnicodeDecodeError):continue
 assert not('python' in cmd and any(n in cmd for n in ['bounded_comparison_replay.py','completion_state_repair.py','completion_history_negative.py'])),'Another own development request process exists'
out=root.parent/('bounded-comparison-'+str(time.time_ns()));log=out.with_suffix('.log')
with log.open('xb')as stream:
 p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'bounded_comparison_replay.py'),'--source',str(source),'--root',str(out),'--token-file',str(root.parent/'transport.token')],cwd=release,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
result={'pid':p.pid,'root':str(out),'release':str(release),'log':str(log),'time':time.time(),'preservation':str(preserve),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'unchanged_files':{n:hashlib.sha256((release/n).read_bytes()).hexdigest()for n in unchanged},'scope':'serial frozen-input development controls; not online trajectories or efficacy'}
print(json.dumps(result))
'''.replace('ROOT',repr(old['root'])).replace('RELEASE',repr(stage['release'])).replace('OLD',repr(old['release'])).replace('LOG',repr(old['log'])).replace('SOURCE',repr(old['root']+'/runs/vwa--classifieds_112--clean--post_only/attempt-1792904475291409319/events.jsonl'))
result=json.loads(remote(code,host='4090'));receipt.write_text(json.dumps(result,indent=2))
print(json.dumps(result))
