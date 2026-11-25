"""Only the newly changed empty-reference mask on the frozen native tokenizer."""
import json
from remote_control import HERE,remote,save,sha

root='/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/full-gui-bounded-evidence-20261109-03'
code='PACKAGE='+repr(root)+'\n'+r'''
from pathlib import Path
import copy,hashlib,json,sys,time
p=Path(PACKAGE);sys.path[:0]=[str(p),str(p/'release'),str(p/'grammar-vendor')]
from transformers import AutoTokenizer
from bounded_schema import new_prefix_filter,schema_sha256
from native_format_bridge import build_token_data
from model_runtime import save
target=p/'new-empty-reference-native-CPU';target.mkdir(exist_ok=False)
tokenizer=AutoTokenizer.from_pretrained('/home/researcher/models/Qwen3.5-9B',local_files_only=True,trust_remote_code=False)
data=build_token_data(tokenizer);data.eos_token_id=[248044,248046]
base={'schema_version':'image-evidence-v2-compact','coordinate_space':'normalized_1000',
 'frame':{'kind':'gui','summary':'Independent literals and regions','limitations':[]},
 'text_spans':[{'id':'t1','text':'Visible literal','box_xyxy':[5,5,10,10],'readability':'clear'}],
 'elements':[{'id':'e1','kind':'button','description':'Visible control','box_xyxy':[50,50,100,100],'text_refs':[],'visibility':'clear'}],
 'uncertain_regions':[]}
rows=[]
for name,refs,expected in [('empty',[],True),('existing',['t1'],False),('missing',['t6'],False)]:
 value=copy.deepcopy(base);value['elements'][0]['text_refs']=refs
 text=json.dumps(value,separators=(',',':'),ensure_ascii=False);ids=tokenizer.encode(text,add_special_tokens=False)
 from bounded_schema import SCHEMA
 from lmformatenforcer import TokenEnforcer,JsonSchemaParser,CharacterLevelParserConfig
 from native_format_bridge import byte_schema
 e=TokenEnforcer(data,JsonSchemaParser(byte_schema(SCHEMA),config=CharacterLevelParserConfig(alphabet=''.join(chr(i)for i in range(32,256)))))
 prefix=[1234];rejected=None
 for index,token in enumerate(ids+[248046]):
  allowed=e.get_allowed_tokens(prefix).allowed_tokens
  if token not in allowed:rejected=index;break
  prefix.append(token)
 accepted=rejected is None;assert accepted==expected,name
 rows.append({'name':name,'accepted':accepted,'expected':expected,'rejected_at':rejected,'text_sha256':hashlib.sha256(text.encode()).hexdigest()})
import torch
assert not torch.cuda.is_initialized()
result={'passed':True,'new_targeted_native_cases':rows,'schema_sha256':schema_sha256(),
 'fixed_private_vendor_sha256':hashlib.sha256((p/'grammar-vendor/lmformatenforcer/jsonschemaparser.py').read_bytes()).hexdigest(),
 'weights_model_generation_GUI_calls':0,'CUDA_initialized':False,'prior_completed9_tokenizer_tests_not_reexecuted':True}
save(target/'receipt.json',result);print(json.dumps(result))
'''
out,path=remote('3090',code,'new-empty-reference-native-CPU',timeout=60)
save(HERE/'emptyrefs-native-CPU-result.json',{'operation':str(path),'result':json.loads(out)})
print(out)
