import json
from pathlib import Path
root=Path(__file__).parent/'judge-legal-projection-linked03/review/judges'
seen=set()
for path in sorted(root.glob('*.json')):
 d=json.loads(path.read_bytes());phase=d['phase']
 if phase in ('point','alignment','focus','person_read','absence_relation','history_report') and phase not in seen:
  seen.add(phase);print('STAGE '+phase+'\n'+d['actual_native_payload']['system'])
