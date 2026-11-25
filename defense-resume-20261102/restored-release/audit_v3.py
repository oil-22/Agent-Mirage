"""Read-only explicit v3 audit, includes hash-bound reused baseline provenance."""
import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent
receipt=r/'v3.6.2-vwa-resume.json'
if not receipt.exists():receipt=r/'v3.4.1-vwa-resume.json'
if not receipt.exists():receipt=r/'v3-vwa-launch.json'
launch=json.loads(receipt.read_text())
code='''import subprocess,json,pathlib
data=json.loads(subprocess.check_output(['/data/researcher/vwa100-2026-10-09/venv/bin/python',SCRIPT,ROOT],text=True))
for row in data['rows']:
 p=pathlib.Path(row['attempt'])/'events.jsonl'
 if p.exists():
  with p.open()as stream:
   first=json.loads(next(stream))
  if first['kind']=='implementation':
   row['defense_version']=first['data'].get('version')
   row['code_directory']=first['data'].get('code_directory')
print(json.dumps(data))
'''.replace('SCRIPT',repr(launch['release']+'/audit_vwa_v2.py')).replace('ROOT',repr(launch['root']))
data=json.loads(remote(code,host='4090'));(r/'latest-v3-formal-audit.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
print(json.dumps({'phase':data['status']['phase'],'completed':data['completed'],'by_arm':data['by_arm'],
    'rows':[{k:x[k]for k in ['run_id','outcome','hash_chain_ok','counters','reused_from_prior_batch','attempt_failure']}for x in data['rows']]},ensure_ascii=False))
