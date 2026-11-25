"""Immutable v2 release; reuse existing idle native27B service. No new model process."""
import base64,hashlib,json,time
from pathlib import Path
from remote import remote

R=Path(__file__).resolve().parent
names=['defense/__init__.py','defense/core.py','defense/prompts.py','defense/http_backend.py','defense/qwen_backend.py','defense/schema.py','inference_server.py','run_vwa_pilot.py','replay_v2.py','focus_delta_replay.py','target_alignment_replay.py','completion_history_replay.py','completion_history_negative.py','audit_vwa_v2.py','plan80.json','native-vwa-request.json']
names+=['completion_state_repair.py']
names+=['bounded_comparison_replay.py']
names+=['completion_probe_replay.py']
names+=['comparison_scope_replay.py']
names+=['history_report_delta.py']
names+=['history_guard_delta.py']
names+=['readiness_regression.py']
names+=['readiness_live_recovery.py']
files={n:base64.b64encode((R/n).read_bytes()).decode()for n in names}
release=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()[:16]
code='''import base64,json,pathlib,py_compile
r=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');p=r/'releases'/RELEASE;p.mkdir(parents=True,exist_ok=True)
for name,data in json.loads(PAYLOAD).items():
 out=p/name;out.parent.mkdir(parents=True,exist_ok=True);raw=base64.b64decode(data)
 if out.exists():assert out.read_bytes()==raw
 else:out.write_bytes(raw)
 if name.endswith('.py'):py_compile.compile(str(out),doraise=True)
print(json.dumps({'release':str(p),'root':str(r),'sha256':RELEASE}))
'''.replace('RELEASE',repr(release)).replace('PAYLOAD',repr(json.dumps(files)))
result=json.loads(remote(code,host='4090'))
server=json.loads(remote(code.replace('/data/researcher/mirage-defense-pilot-20261023','/home/researcher/mirage-defense-pilot-20261023'),host='3090'))
result['server_release']=server['release'];(R/'v2-staging.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

if __name__=='__main__':
 import sys
 if '--stage-only'in sys.argv:sys.exit(0)
 previous=R/'v2-replay-launch.json'
 if previous.exists():
  history=R/'replay-launch-archive';history.mkdir(exist_ok=True)
  old=json.loads(previous.read_text());out=history/(Path(old['root']).name+'.json')
  if out.exists():assert out.read_bytes()==previous.read_bytes()
  else:out.write_bytes(previous.read_bytes())
 code='''import pathlib,subprocess,json,time
r=pathlib.Path(ROOT);release=pathlib.Path(RELEASE);out=r/('replay-v2-'+str(time.time_ns()))
log=out.with_suffix('.log').open('xb')
p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'replay_v2.py'),'--source',str(r/'vwa-pilot-1792763019425022294'),'--root',str(out),'--token-file',str(r/'transport.token')],cwd=release,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':p.pid,'root':str(out),'release':str(release),'log':str(out.with_suffix('.log'))}))
'''.replace('ROOT',repr(result['root'])).replace('RELEASE',repr(result['release']))
 receipt=json.loads(remote(code,host='4090'));(R/'v2-replay-launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
