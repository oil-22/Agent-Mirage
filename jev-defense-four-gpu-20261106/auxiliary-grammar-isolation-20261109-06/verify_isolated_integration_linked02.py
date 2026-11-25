"""New integration admission with actual production import order; CPU only."""
import base64
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

SOURCE = HERE / 'isolated-runtime-source-linked02'
buf = io.BytesIO()
with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
    for path in SOURCE.rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts:
            z.write(path, path.relative_to(SOURCE).as_posix())

CODE = 'ARCHIVE=' + repr(base64.b64encode(buf.getvalue()).decode()) + '\n' + r'''
from pathlib import Path
import base64, hashlib, io, json, os, sys, time, zipfile
os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['HF_HUB_OFFLINE']='1'
base=Path('/home/researcher/jev-defense-four-gpu-20261106/auxiliary-grammar-isolation-20261109-06')
root=base/('integration-linked02-'+str(time.time_ns()));root.mkdir(exist_ok=False)
p=root/'source';p.mkdir()
with zipfile.ZipFile(io.BytesIO(base64.b64decode(ARCHIVE)))as z:
 for name in z.namelist():assert(p/name).resolve().is_relative_to(p.resolve())
 z.extractall(p)
h=lambda b:hashlib.sha256(b).hexdigest()
def put(path,value):
 with path.open('x',encoding='utf8')as f:json.dump(value,f,ensure_ascii=False,sort_keys=True,indent=2);f.write('\n')
for name,expected in json.loads((p/'source-seal.json').read_bytes()).items():assert h((p/name).read_bytes())==expected
original=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/full-gui-bounded-evidence-20261109-03')
sys.path[:0]=[str(p),str(original),str(original/'release'),str(original/'grammar-vendor')]
from defense.qwen_backend import LocalQwen
from model_runtime import module
support=module('isolation_primary_support',original/'preflight_support.py')
support.verify_original_dependencies(json.loads((original/'primary-reference.json').read_bytes()))
import lmformatenforcer as main_api
canonical_before={k:v for k,v in sys.modules.items()if k=='lmformatenforcer'or k.startswith('lmformatenforcer.')}
from transformers import AutoTokenizer
from auxiliary_grammar_import import load_auxiliary_grammar
from bounded_schema import new_prefix_filter,schema_sha256
from native_format_bridge import build_token_data
tokenizer=AutoTokenizer.from_pretrained('/home/researcher/models/Qwen3.5-9B',local_files_only=True,trust_remote_code=False)
api,proof=load_auxiliary_grammar()
data=build_token_data(tokenizer);data.eos_token_id=[248044,248046]
assert type(data).__module__.startswith(proof['alias'])
class Vector:
 def __init__(self,value):self.value=value
 def tolist(self):return self.value
def replay(ids,prompt):
 f=new_prefix_filter(data);prefix=list(prompt)
 assert type(f.enforcer).__module__.startswith(proof['alias'])
 for index,token in enumerate(ids):
  allowed=f(0,Vector(prefix))
  if token not in allowed:return {'accepted':False,'first_disallowed_index':index,'selected_id':token}
  prefix.append(token)
 return {'accepted':True,'checked_tokens':len(ids)}
record=Path('/home/researcher/jev-defense-four-gpu-20261106/full-gui-bounded-evidence-20261109-03/worker/requests/0051')
actual=json.loads((record/'actual-generation.json').read_bytes());sequence=json.loads((record/'sequence_ids.json').read_bytes())[0]
recorded=replay(actual['output_ids'],sequence[:actual['input_tokens']]);assert not recorded['accepted']
base_value={'schema_version':'image-evidence-v2-compact','coordinate_space':'normalized_1000',
 'frame':{'kind':'gui','summary':'独立界面 🧭; literal [brackets] and quote " stay data','limitations':[]},
 'text_spans':[{'id':'t2','text':'编号 204，等待确认; not a task answer','box_xyxy':[33,44,122,155],'readability':'clear'}],
 'elements':[{'id':'e3','kind':'input','description':'可见边框与文字，未推断操作系统焦点','box_xyxy':[55,66,177,188],'text_refs':[],'visibility':'clear'}],
 'uncertain_regions':[{'box_xyxy':[555,666,777,888],'reason':'小字局部不可读'}]}
cases=[]
for name,refs,ascii_escape,expected in [('JSON-escaped-Unicode-empty',[],True,True),('nonempty-existing-ID-after-escape-fix',['t2'],True,False)]:
 value=json.loads(json.dumps(base_value));value['elements'][0]['text_refs']=refs
 text=json.dumps(value,ensure_ascii=ascii_escape,separators=(',',':'))
 ids=tokenizer.encode(text,add_special_tokens=False)+[248046]
 result=replay(ids,[1024,2048]);assert result['accepted']==expected,(name,result)
 cases.append({'case':name,'expected':expected,'actual':result,'text_sha256':h(text.encode())})
assert {k:v for k,v in sys.modules.items()if k=='lmformatenforcer'or k.startswith('lmformatenforcer.')}==canonical_before
assert main_api.JsonSchemaParser is canonical_before['lmformatenforcer'].JsonSchemaParser
import torch
assert not torch.cuda.is_initialized()
result={'passed':True,'time':time.time(),'recorded_failure_0051_now_mask_rejected_without_generation':recorded,
 'new_production_order_native_token_cases':cases,'actual_auxiliary_import_proof':proof,
 'main_canonical_module_graph_unchanged':True,'schema_sha256':schema_sha256(),
 'new_model_HTTP_GUI_calls':0,'CUDA_initialized':False,'weights_loaded':False,
 'runtime_package':str(p),'source_seal_sha256':h((p/'source-seal.json').read_bytes()),
 'semantic_accuracy_or_efficacy_pass':False,
 'remaining_known_issue':'Exact final character-length checks can still reject strings allowed by the UTF8 byte grammar. No clipping or correction introduced.'}
put(root/'receipt.json',result);put(root/'seal.json',{str(q.relative_to(root)):h(q.read_bytes())for q in root.rglob('*')if q.is_file()})
print(json.dumps({'remote':str(root),'result':result}))
'''

out, operation = remote('3090', CODE, 'isolated-auxiliary-production-order-CPU-admission-linked02', timeout=150)
value = json.loads(out)
local = HERE / ('integration-linked02-admission-' + str(time.time_ns()))
local.mkdir()
save(local / 'receipt.json', value)
save(local / 'collection.json', {'operation': str(operation), 'remote': value['remote'],
    'receipt_sha256': sha(local / 'receipt.json'), 'new_model_HTTP_GUI_calls': 0})
print(json.dumps({'local': str(local), 'passed': value['result']['passed'],
    'recorded_failure_rejected': value['result']['recorded_failure_0051_now_mask_rejected_without_generation'],
    'new_native_cases': len(value['result']['new_production_order_native_token_cases']),
    'main_unchanged': value['result']['main_canonical_module_graph_unchanged'], 'model_GUI_calls': 0}))
