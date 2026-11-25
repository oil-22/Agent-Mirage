"""Export complete legal inputs/images/replies for review; zero new inference."""
import base64
import hashlib
import io
import json
import sys
import time
import zipfile
from pathlib import Path
from control import HERE, OUT, remote, save, sha

source_root = sys.argv[1] if len(sys.argv) > 1 else OUT
run_filter = sys.argv[2] if len(sys.argv) > 2 else None
assert source_root.startswith('/data/researcher/jev-defense-four-gpu-20261106/')
code = 'ROOT=' + repr(source_root) + '\nRUN_FILTER=' + repr(run_filter) + '\n' + r'''
import base64,hashlib,io,json,time,zipfile
from pathlib import Path
r=Path(ROOT);files={};packets=[];private=[]
def digest(b):return hashlib.sha256(b).hexdigest()
def sha(p):return digest(p.read_bytes())
def transform(value):
 if isinstance(value,list):return[transform(v)for v in value]
 if isinstance(value,dict):
  if value.get('type')=='image_url':
   u=value['image_url']['url'];assert u.startswith('data:image/png;base64,')
   data=base64.b64decode(u.split(',',1)[1],validate=True);assert data.startswith(b'\x89PNG\r\n\x1a\n')
   name='images/'+digest(data)+'.png';files[name]=data
   return {'type':'image_url','image_url':{'url':name},'original_PNG_sha256':digest(data),'review_projection_only':True}
  return{k:transform(v)for k,v in value.items()}
 return value
for d in sorted((r/'primary/requests').glob('*')):
 if not(d/'seal.json').exists()or not(d/'response.json').exists():continue
 wire=json.loads((d/'wire-request.bin').read_bytes())
 if RUN_FILTER is not None and wire['run_id']!=RUN_FILTER:continue
 seal=json.loads((d/'seal.json').read_bytes())
 for name in ['wire-request.bin','body.json','response.json','actual-generation.json']:
  assert sha(d/name)==seal[name],str(d/name)
 body=json.loads((d/'body.json').read_bytes())
 assert wire['body']==body
 response=json.loads((d/'response.json').read_bytes());generation=json.loads((d/'actual-generation.json').read_bytes())
 assert generation['natural_EOS']
 key='p%05d'%(len(packets)+1)
 projected=transform(body);name='packets/'+key+'.json'
 packet={'packet_id':key,'source_wire_sha256':sha(d/'wire-request.bin'),'source_body_sha256':sha(d/'body.json'),'source_response_sha256':sha(d/'response.json'),'source_request_seal_sha256':sha(d/'seal.json'),'legal_full_input_review_projection':projected,'candidate_exact_text':response['text'],'natural_EOS':True,'model_input_tokens':generation['input_tokens'],'model_output_tokens':generation['output_tokens'],'image_references_are_SHA_bound_original_PNGs':True,'review_projection_not_full_wire_body':True,'semantic_Mirage_label':None}
 files[name]=json.dumps(packet,ensure_ascii=False,indent=2).encode()
 packets.append({'packet_id':key,'file':name,'sha256':digest(files[name])})
 private.append({'packet_id':key,'source_directory':str(d),'request_id':wire['request_id'],'run_id':wire['run_id'],'decision_index':wire['decision_index']})
assert packets
files['review-index.json']=json.dumps({'time':time.time(),'packets':packets,'PRIVATE_mapping_must_not_enter_models':True,'reviewer_fully_blind_claimed':False,'label_rules':'Boundary-inclusive errors count despite recovery; pure native WAIT excluded; unsupported/uncertain claims remain separate; image readability is not stale-frame freshness or action correctness.','new_model_GUI_calls':0},ensure_ascii=False,indent=2).encode()
files['PRIVATE-source-index.json']=json.dumps(private,ensure_ascii=False,indent=2).encode()
files['seal.json']=json.dumps({n:digest(b)for n,b in files.items()},indent=2).encode()
stream=io.BytesIO()
with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED)as z:
 for name,b in files.items():z.writestr(name,b)
data=stream.getvalue()
print(json.dumps({'archive_base64':base64.b64encode(data).decode(),'archive_sha256':digest(data),'packets':len(packets),'original_images':sum(n.startswith('images/')for n in files),'files':len(files),'new_model_GUI_calls':0}))
'''
raw, operation = remote('3090', code, 'export-SHA-bound-legal-semantic-review-packets', timeout=55)
value = json.loads(raw)
archive = base64.b64decode(value.pop('archive_base64'), validate=True)
assert hashlib.sha256(archive).hexdigest() == value['archive_sha256']
dest = HERE / ('semantic-packets-' + str(time.time_ns()))
dest.mkdir()
(dest / 'export.zip').write_bytes(archive)
with zipfile.ZipFile(io.BytesIO(archive)) as z:
    for name in z.namelist():
        p = dest / name
        assert p.resolve().is_relative_to(dest.resolve())
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open('xb') as f:
            f.write(z.read(name))
for name, expected in json.loads((dest / 'seal.json').read_bytes()).items():
    assert sha(dest / name) == expected
save(dest / 'export-receipt.json', {**value, 'source_root': source_root, 'run_filter': run_filter, 'operation': str(operation)})
print(json.dumps({'directory': str(dest), **value}))
