"""Export frozen legal inputs for source review while the existing run completes.

Reads no new or baseline replies, labels, actions, or official scores. No model
or browser modules are imported. This is an input projection, never a wire body.
"""
import base64
import hashlib
import io
import json
import time
import zipfile
from pathlib import Path
from control import HERE, remote, save, sha
from audit_offline_receipt_repair_postexit import PACKAGE, PREP


READER = r'''
import base64,hashlib,io,json,zipfile
from pathlib import Path
p=Path(PACKAGE)
def digest(data):return hashlib.sha256(data).hexdigest()
def sha(path):return digest(path.read_bytes())
assert sha(p/'offline-manifest.json')==EXPECTED
m=json.loads((p/'offline-manifest.json').read_bytes())
plan=json.loads((p/'development-plan.json').read_bytes())
assert sha(p/'development-plan.json')==m['files']['development-plan.json']
files={};bodies={};rows=[]
def project(value):
 if isinstance(value,list):return [project(v)for v in value]
 if isinstance(value,dict):
  if value.get('type')=='image_url':
   raw=base64.b64decode(value['image_url']['url'].split(',',1)[1],validate=True)
   assert raw.startswith(b'\x89PNG\r\n\x1a\n')
   h=digest(raw);name='images/'+h+'.png';files[name]=raw
   return {'type':'image_url','image_url':{'url':name},'original_PNG_sha256':h}
  return {k:project(v)for k,v in value.items()}
 return value
for row in plan['inputs']:
 n=row['case'];f=Path(row['proposed_full_body']);raw=f.read_bytes()
 assert digest(raw)==row['proposed_full_body_sha256']
 wrapper=p/'CPU-receipts'/('case-%02d.json'%n)
 assert sha(wrapper)==row['native_CPU_input_receipt_sha256']
 w=json.loads(wrapper.read_bytes());assert w['remote_case']==str(f.parent)
 assert sha(f.parent/'seal.json')==w['remote_seal_sha256']==m['CPU_case_seals'][str(n)]
 assert json.loads((f.parent/'seal.json').read_bytes())[f.name]==digest(raw)
 body=json.loads(raw);bodies[n]=body
 projection={'case':n,'source_body_sha256':digest(raw),'legal_input_projection':project(body),
  'projection_not_wire_body':True,'new_or_baseline_reply_or_label_joined':False}
 name='inputs/case-%02d.json'%n;data=json.dumps(projection,ensure_ascii=False,indent=2).encode()
 files[name]=data;rows.append({'case':n,'file':name,'sha256':digest(data),'source_body_sha256':digest(raw)})
longest=max(bodies,key=lambda n:len(bodies[n]['messages']));full=bodies[longest]['messages']
prefix_checks={str(n):b['messages']==full[:len(b['messages'])]for n,b in bodies.items()}
files['index.json']=json.dumps({'inputs':rows,'largest_case':longest,'exact_legal_history_prefix_checks':prefix_checks,
 'original_PNG_count':sum(n.startswith('images/')for n in files),'no_new_or_baseline_output_labels_or_scores_read':True,
 'new_model_GUI_calls':0,'preparation_only_not_actual_runtime_audit':True},ensure_ascii=False,indent=2).encode()
files['seal.json']=json.dumps({n:digest(v)for n,v in files.items()},indent=2).encode()
stream=io.BytesIO()
with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED)as z:
 for n,b in files.items():z.writestr(n,b)
raw=stream.getvalue()
print(json.dumps({'archive':base64.b64encode(raw).decode(),'archive_sha256':digest(raw)}))
'''


def main():
    pointer = HERE / 'frozen-offline10-legal-input-review-current.json'
    assert not pointer.exists(), 'Reuse the existing immutable input export'
    code = 'PACKAGE=' + repr(PACKAGE) + '\nEXPECTED=' + repr(sha(PREP / 'package/offline-manifest.json')) + '\n' + READER
    raw, operation = remote('3090', code, 'approved-offline10-frozen-legal-inputs-only')
    value = json.loads(raw)
    data = base64.b64decode(value['archive'], validate=True)
    assert hashlib.sha256(data).hexdigest() == value['archive_sha256']
    dest = HERE / ('frozen-offline10-legal-input-review-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    (dest / 'export.zip').write_bytes(data)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name in archive.namelist():
            target = dest / name
            assert target.resolve().is_relative_to(dest.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as output:
                output.write(archive.read(name))
    inner = json.loads((dest / 'seal.json').read_bytes())
    assert all(sha(dest / n) == h for n, h in inner.items())
    save(dest / 'export-receipt.json', {'operation': str(operation), 'archive_sha256': value['archive_sha256'],
         'projection_seal_sha256': sha(dest / 'seal.json'), 'no_runtime_audit_or_effectiveness_claim': True})
    save(pointer, {'inputs': str(dest), 'projection_seal_sha256': sha(dest / 'seal.json'),
                  'receipt_sha256': sha(dest / 'export-receipt.json')})
    index = json.loads((dest / 'index.json').read_bytes())
    print(json.dumps({'inputs': str(dest), **{k:v for k,v in index.items() if k != 'inputs'}}))


if __name__ == '__main__':
    main()
