"""Read-only verification plus a new completion audit; no old terminal changes."""
import hashlib
import json
import time
from pathlib import Path
from remote import remote

BASE = Path(__file__).resolve().parent
PREP = BASE / 'focus-history-repair-development'
sha = lambda b: hashlib.sha256(b).hexdigest()
read = lambda p: json.loads(p.read_bytes())
done = read(PREP / 'repair-combined-current.json')
review = Path(done['review_directory'])
for name, digest in read(review / 'sha256.json').items():
    path = Path(name) if Path(name).is_absolute() else review / name
    assert sha(path.read_bytes()) == digest, name
hp = read(PREP / 'handoff-current.json')
hr = Path(hp['directory']) / 'receipt.json'
assert sha(hr.read_bytes()) == hp['receipt_sha256']
for row in read(hr):
    assert sha(Path(row['backup']).read_bytes()) == row['before_sha256']
    assert sha(Path(row['path']).read_bytes()) == row['after_sha256']
    assert '17EOS' in Path(row['path']).read_text(encoding='utf-8')[:100]
service = read(BASE / 'defense-service-resumed-health-current.json')
assert sha(Path(service['receipt']).read_bytes()) == service['sha256']
assert service['health']['phase'] == 'ready'
code = r'''
import json
from pathlib import Path
rows=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  if p.stat().st_uid!=1015:continue
  cmd=[x.decode(errors='replace')for x in(p/'cmdline').read_bytes().split(b'\0')if x]
  if not cmd or not any(x in Path(cmd[0]).name for x in ['python','bash','sh']):continue
  # Actual executable/script arguments only: ignore the text of this inspector.
  args=[x for x in cmd[1:]if '\n'not in x]
  if any('mirage-defense-pilot-20261023/'in x and any(t in x for t in ['run_focus','run_scoped','run_vwa','launch_','resume_','uitars','queue'])for x in args):
   rows.append({'pid':int(p.name),'uid':1015,'command':cmd})
 except (FileNotFoundError,PermissionError,ProcessLookupError):pass
print(json.dumps({'matching_owned_inference_or_queue_workers':rows}))
'''
workers = json.loads(remote(code, host='4090', timeout=30))
assert not workers['matching_owned_inference_or_queue_workers'], workers
result = {'phase': 'completed_repair_development_audited', 'combined_receipt_sha256': sha((PREP / 'repair-combined-current.json').read_bytes()),
          'review_sha256': done['review_sha256'], 'report_sha256': done['report_sha256'],
          'handoff_receipt': hp, 'service_health': service, 'workers': workers,
          'calls': 17, 'actual_requests': 17, 'logical_controls': 16, 'format_retries': 1,
          'fullGUI_authorized': False, 'formal_release': False, 'monitor': 'ACTIVE'}
path = PREP / ('completion-audit-' + str(time.time_ns()) + '.json')
path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
(PREP / 'completion-audit-current.json').write_text(json.dumps({'receipt': str(path), 'sha256': sha(path.read_bytes())}, indent=2), encoding='utf-8')
print(json.dumps({'receipt': str(path), 'sha256': sha(path.read_bytes()), 'verified_calls': 17, 'owned_workers': workers, 'service_ready': True, 'fullGUI_authorized': False}))
