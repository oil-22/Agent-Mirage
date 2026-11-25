"""Replay sealed auxiliary IDs on CPU after the actual primary dependency restore.

No weights, CUDA, HTTP, GUI actions, or additional model generations. The
running GUI package and canonical main grammar are never changed.
"""
import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import zipfile

HERE = Path(__file__).resolve().parent
GUI = HERE.parent / 'full-gui-bounded-evidence-20261109-03'
sys.path.insert(0, str(GUI))
from remote_control import remote, save, sha

CODE = r'''
from pathlib import Path
import base64, hashlib, importlib.util, io, json, os, struct, sys, time, zipfile
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['HF_HUB_OFFLINE']='1'
p=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/full-gui-bounded-evidence-20261109-03')
w=Path('/home/researcher/jev-defense-four-gpu-20261106/full-gui-bounded-evidence-20261109-03/worker')
target=Path('/home/researcher/jev-defense-four-gpu-20261106/auxiliary-grammar-isolation-20261109-06')/str(time.time_ns())
target.mkdir(parents=True,exist_ok=False)
h=lambda raw:hashlib.sha256(raw).hexdigest()
def put(path,value):
 with path.open('x',encoding='utf8')as f:json.dump(value,f,ensure_ascii=False,sort_keys=True,indent=2);f.write('\n')
def file_identity(path):
 path=Path(path);return {'file':str(path.resolve()),'sha256':h(path.read_bytes())}
# The source at this stage is frozen. Copy, never modify it.
put(target/'invocation.json',{'pid':os.getpid(),'uid':os.getuid(),'time':time.time(),
 'production_package':str(p),'CPU_only':True,'new_model_HTTP_GUI_calls':0})
sealed=[]
for d in sorted((w/'requests').iterdir()):
 if not(d/'seal.json').exists()or not(d/'response.json').exists():continue
 response=json.loads((d/'response.json').read_bytes())
 if response['operation']!='evidence':continue
 seal_raw=(d/'seal.json').read_bytes();seal=json.loads(seal_raw)
 exported=target/'preserved'/d.name;exported.mkdir(parents=True)
 for name,expected in seal.items():
  raw=(d/name).read_bytes();assert h(raw)==expected,(d.name,name)
  # Tensor bytes remain immutable at their original remote SHA-bound paths.
  if not name.endswith('.tensor'):(exported/name).write_bytes(raw)
 (exported/'seal.json').write_bytes(seal_raw)
 sealed.append({'request':d.name,'root':str(d),'seal_sha256':h(seal_raw),
  'all_files_SHA_verified':len(seal),'raw_tensor_bytes_retained_original_remote':True})
put(target/'preservation.json',sealed)
assert any(v['request']=='0051'for v in sealed)
sys.path[:0]=[str(p),str(p/'release'),str(p/'grammar-vendor')]
# Matches load_runtime's import and dependency-restore order, stopping before weights.
from defense.qwen_backend import LocalQwen
from model_runtime import module
support=module('diagnostic_primary_support',p/'preflight_support.py')
reference=json.loads((p/'primary-reference.json').read_bytes())
dep=support.verify_original_dependencies(reference)
import lmformatenforcer as canonical_api
import lmformatenforcer.jsonschemaparser as canonical_parser
from transformers import AutoTokenizer
from bounded_schema import SCHEMA,schema_sha256,new_prefix_filter
from native_format_bridge import build_token_data,byte_schema
original_modules={k: v for k,v in sys.modules.items()if k=='lmformatenforcer'or k.startswith('lmformatenforcer.')}
original_identity={k:file_identity(v.__file__)for k,v in original_modules.items()if getattr(v,'__file__',None)}
assert Path(canonical_api.__file__).resolve().parent!=p/'grammar-vendor/lmformatenforcer'
tokenizer=AutoTokenizer.from_pretrained('/home/researcher/models/Qwen3.5-9B',local_files_only=True,trust_remote_code=False)
data=build_token_data(tokenizer);data.eos_token_id=[248044,248046]
d=w/'requests/0051';actual=json.loads((d/'actual-generation.json').read_bytes())
sequence=json.loads((d/'sequence_ids.json').read_bytes())[0]
ids=actual['output_ids'];prompt=sequence[:actual['input_tokens']]
assert sequence==prompt+ids
assert h(struct.pack('<'+'q'*len(sequence),*sequence))==json.loads((d/'seal.json').read_bytes())['sequence_ids.tensor']
class Vector:
 def __init__(self,value):self.value=value
 def tolist(self):return self.value
def replay(callback):
 prefix=prompt[:];rows=[];first_disallowed=None
 for i,token in enumerate(ids):
  allowed=callback(0,Vector(prefix));ok=token in allowed
  rows.append({'index':i,'selected_id':token,'allowed_count':len(allowed),'selected_allowed':ok})
  if not ok:
   first_disallowed={'index':i,'selected_id':token,'raw_token_hex':data.native_raw_token_bytes.get(token,b'').hex(),
    'prefix_tail':tokenizer.decode(ids[max(0,i-12):i],skip_special_tokens=True)};break
  prefix.append(token)
 return {'steps_checked':len(rows),'all_recorded_selected_tokens_allowed':first_disallowed is None,
  'first_disallowed':first_disallowed,'steps':rows}
production=replay(new_prefix_filter(data))
put(target/'production-native-ID-replay.json',production)
assert production['all_recorded_selected_tokens_allowed']
# Proposed fix: load the complete relative-import module graph under a unique
# namespace. Never evict or replace any canonical main module.
name='_mirage_auxiliary_lmfe_cpu_diagnostic'
private_path=p/'grammar-vendor/lmformatenforcer'
spec=importlib.util.spec_from_file_location(name,private_path/'__init__.py',submodule_search_locations=[str(private_path)])
private_api=importlib.util.module_from_spec(spec);sys.modules[name]=private_api;spec.loader.exec_module(private_api)
private_data=private_api.TokenEnforcerTokenizerData(data.regular_tokens,data.decoder,data.eos_token_id,False,len(tokenizer))
private_enforcer=private_api.TokenEnforcer(private_data,private_api.JsonSchemaParser(byte_schema(SCHEMA),
 config=private_api.CharacterLevelParserConfig(alphabet=''.join(chr(i)for i in range(32,256)))))
isolated=replay(lambda batch,vector:private_enforcer.get_allowed_tokens(vector.tolist()).allowed_tokens)
put(target/'isolated-native-ID-replay.json',isolated)
assert not isolated['all_recorded_selected_tokens_allowed']
assert all(sys.modules.get(k)is v for k,v in original_modules.items())
assert {k:file_identity(v.__file__)for k,v in original_modules.items()if getattr(v,'__file__',None)}==original_identity
assert private_api.JsonSchemaParser is not canonical_api.JsonSchemaParser
private_identity={k:file_identity(v.__file__)for k,v in sys.modules.items()if (k==name or k.startswith(name+'.'))and getattr(v,'__file__',None)}
import torch
assert not torch.cuda.is_initialized()
result={'time':time.time(),'source_request':'0051','preserved_sealed_auxiliary_requests':sealed,
 'schema_sha256':schema_sha256(),'original_dependency_proof':dep,
 'production_imports':original_identity,'private_alias_imports':private_identity,
 'actual_production_uses_unpatched_primary_grammar':True,
 'recorded_production_tokens_all_allowed':production['all_recorded_selected_tokens_allowed'],
 'private_alias_first_disallowed':isolated['first_disallowed'],
 'canonical_main_modules_objects_and_files_unchanged':True,'CUDA_initialized':False,
 'new_model_HTTP_GUI_calls':0,'live_process_or_frozen_package_modified':False,
 'conclusion':'Production dependency restore supersedes and caches the main grammar before auxiliary setup; recorded nonempty text_refs are allowed by that graph, rejected by private alias.',
 'not_a_new_model_or_semantic_pass':True}
put(target/'receipt.json',result)
put(target/'seal.json',{str(q.relative_to(target)):h(q.read_bytes())for q in target.rglob('*')if q.is_file()})
archive=io.BytesIO()
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED)as z:
 for q in target.rglob('*'):
  if q.is_file():z.write(q,str(q.relative_to(target)))
print(json.dumps({'remote':str(target),'result':result,'archive_base64':base64.b64encode(archive.getvalue()).decode()}))
'''

if __name__ == '__main__':
    out, operation = remote('3090', CODE, 'production-import-and-sealed-native-ID-replay-CPU', timeout=160)
    value = json.loads(out)
    local = HERE / 'diagnostic-collection' / str(time.time_ns())
    local.mkdir(parents=True)
    archive = base64.b64decode(value.pop('archive_base64'))
    (local / 'original.zip').write_bytes(archive)
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        for name in z.namelist():
            dest = (local / 'original' / name).resolve()
            assert dest.is_relative_to((local / 'original').resolve())
        z.extractall(local / 'original')
    save(local / 'collection.json', {'operation': str(operation), 'remote': value['remote'],
        'archive_sha256': sha(local / 'original.zip'), 'new_model_HTTP_GUI_calls': 0})
    result = value['result']
    print(json.dumps({'local': str(local), 'remote': value['remote'],
        'preserved_auxiliary_requests': [x['request'] for x in result['preserved_sealed_auxiliary_requests']],
        'production_graph_confirmed': result['actual_production_uses_unpatched_primary_grammar'],
        'isolated_first_disallowed': result['private_alias_first_disallowed'],
        'main_unchanged': result['canonical_main_modules_objects_and_files_unchanged'],
        'new_model_HTTP_GUI_calls': 0}, ensure_ascii=False))
