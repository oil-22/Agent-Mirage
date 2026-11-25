"""Copy native Python source for adapter development; never modify the server."""
import base64,hashlib,json
from pathlib import Path
from remote import remote
HERE=Path(__file__).resolve().parent
names=['run_qwen_osworld.py','run_qwen_osworld_action_v4.py','run_qwen_osworld_action_v5.py',
       'run_qwen_osworld_grounding_v3.py','diagnose_action_completion.py',
       'resume_grounding_v3_cached_input.py','verified_evaluator_transport.py']
code=r'''
import pathlib,json,base64,hashlib
base=pathlib.Path('/data/researcher/osworld-qwen27-2026-10-13')
out={}
for name in NAMES:
 raw=(base/name).read_bytes()
 out[name]={'source':str(base/name),'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
print(json.dumps(out))
'''.replace('NAMES',repr(names))
data=json.loads(remote(code,host='4090'));dest=HERE/'native-adapter-sources'/'osworld';dest.mkdir(parents=True,exist_ok=True)
for name,row in data.items():
 raw=base64.b64decode(row.pop('base64'));assert hashlib.sha256(raw).hexdigest()==row['sha256']
 p=dest/name
 if p.exists():assert p.read_bytes()==raw
 else:p.write_bytes(raw)
(dest/'provenance.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print(json.dumps({'copied':len(data),'directory':str(dest),'server_changes':False}))
