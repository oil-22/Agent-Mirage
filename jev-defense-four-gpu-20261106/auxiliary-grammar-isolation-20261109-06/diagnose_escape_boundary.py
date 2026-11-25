"""Preserve new CPU admission failure and locate its escaped-string boundary."""
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
GUI = HERE.parent / 'full-gui-bounded-evidence-20261109-03'
sys.path.insert(0, str(GUI))
from remote_control import remote, save, sha

failed_operation = GUI / 'operations/1794205935061228000-isolated-auxiliary-production-order-CPU-admission'
local = HERE / 'integration-escape-failure-preservation-01'
local.mkdir()
for name in ['source.py', 'stdout.txt', 'stderr.txt', 'receipt.json']:
    (local / name).write_bytes((failed_operation / name).read_bytes())
save(local / 'seal.json', {p.name: sha(p) for p in local.iterdir() if p.is_file()})

code = r'''
from pathlib import Path
import hashlib, json, os, sys, time
os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['HF_HUB_OFFLINE']='1'
b=Path('/home/researcher/jev-defense-four-gpu-20261106/auxiliary-grammar-isolation-20261109-06')
failed=sorted(b.glob('integration-*'))[-1];p=failed/'source'
h=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()
target=b/('escape-diagnostic-'+str(time.time_ns()));target.mkdir()
def put(name,v):
 with(target/name).open('x',encoding='utf8')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
put('original-CPU-source-preservation.json',{'original_root':str(failed),'original_source_seal_sha256':h(p/'source-seal.json'),
 'files':{str(q.relative_to(failed)):h(q)for q in failed.rglob('*')if q.is_file()},'original_modified':False,
 'new_model_HTTP_GUI_calls':0,'failure':'Escaped Unicode native-token condition was rejected during CPU integration admission.'})
original=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/full-gui-bounded-evidence-20261109-03')
sys.path[:0]=[str(p),str(original),str(original/'release'),str(original/'grammar-vendor')]
from defense.qwen_backend import LocalQwen
from model_runtime import module
support=module('escape_diag_primary_support',original/'preflight_support.py')
support.verify_original_dependencies(json.loads((original/'primary-reference.json').read_bytes()))
from transformers import AutoTokenizer
from auxiliary_grammar_import import load_auxiliary_grammar
from native_format_bridge import build_token_data,byte_schema
from bounded_schema import new_prefix_filter,SCHEMA
tokenizer=AutoTokenizer.from_pretrained('/home/researcher/models/Qwen3.5-9B',local_files_only=True,trust_remote_code=False)
data=build_token_data(tokenizer);data.eos_token_id=[248044,248046]
value={'schema_version':'image-evidence-v2-compact','coordinate_space':'normalized_1000',
 'frame':{'kind':'gui','summary':'独立界面 🧭; literal [brackets] and quote " stay data','limitations':[]},
 'text_spans':[{'id':'t2','text':'编号 204，等待确认; not a task answer','box_xyxy':[33,44,122,155],'readability':'clear'}],
 'elements':[{'id':'e3','kind':'input','description':'可见边框与文字，未推断操作系统焦点','box_xyxy':[55,66,177,188],'text_refs':[],'visibility':'clear'}],
 'uncertain_regions':[{'box_xyxy':[555,666,777,888],'reason':'小字局部不可读'}]}
text=json.dumps(value,ensure_ascii=True,separators=(',',':'));ids=tokenizer.encode(text,add_special_tokens=False)+[248046]
class Vector:
 def __init__(self,value):self.value=value
 def tolist(self):return self.value
f=new_prefix_filter(data);prefix=[1024,2048];token_failure=None
for i,t in enumerate(ids):
 allowed=f(0,Vector(prefix))
 if t not in allowed:
  token_failure={'index':i,'selected_id':t,'token_hex':data.native_raw_token_bytes.get(t,b'').hex(),
   'prefix_text':tokenizer.decode(ids[:i],skip_special_tokens=True),'allowed_count':len(allowed),
   'following_text':tokenizer.decode(ids[i:i+12],skip_special_tokens=True)};break
 prefix.append(t)
api,proof=load_auxiliary_grammar();parser=api.JsonSchemaParser(byte_schema(SCHEMA),
 config=api.CharacterLevelParserConfig(alphabet=''.join(chr(i)for i in range(32,256))))
char_failure=None
for i,c in enumerate(text.encode().decode('latin1')):
 if c not in parser.get_allowed_characters():
  char_failure={'byte_index':i,'next_character':c,'prefix_tail':text[max(0,i-50):i]};break
 parser=parser.add_character(c)
import torch
assert not torch.cuda.is_initialized()
result={'token_failure':token_failure,'character_failure':char_failure,'CPU_only':True,'new_model_HTTP_GUI_calls':0,
 'actual_private_imports':proof,'full_value_text':text,'main_graph_not_replaced':True,'CUDA_initialized':False}
put('receipt.json',result);put('seal.json',{str(q.relative_to(target)):h(q)for q in target.rglob('*')if q.is_file()})
print(json.dumps({'remote':str(target),'result':result}))
'''
out, op = remote('3090', code, 'new-private-grammar-escape-boundary-diagnostic-CPU', timeout=110)
save(local / 'linked-diagnostic.json', {'operation': str(op), 'value': json.loads(out)})
v=json.loads(out)['result']
print(json.dumps({'local':str(local),'token_failure':v['token_failure'],'character_failure':v['character_failure'],
                  'new_model_HTTP_GUI_calls':0},ensure_ascii=False))
