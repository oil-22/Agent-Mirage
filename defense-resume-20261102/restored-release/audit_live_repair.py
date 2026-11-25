"""Manual read-only audit of bounded live check and formal batch; no automation."""
import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent
for receipt,out in [('v2-live-diagnostic-launch.json','latest-v2-diagnostic-audit.json'),('v2-post-diagnostic-launch.json','latest-v2-post-diagnostic-audit.json'),('v2-vwa-launch.json','latest-v2-live-audit.json')]:
 p=r/receipt
 if not p.exists():continue
 launch=json.loads(p.read_text())
 code='''import subprocess
print(subprocess.check_output(['/data/researcher/vwa100-2026-10-09/venv/bin/python',SCRIPT,ROOT],text=True))
'''.replace('SCRIPT',repr(launch['release']+'/audit_vwa_v2.py')).replace('ROOT',repr(launch['root']))
 data=json.loads(remote(code,host='4090'));(r/out).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 print(receipt,json.dumps({k:v for k,v in data.items()if k!='rows'}))
 for row in data['rows'][-2:]:print(json.dumps(row))
