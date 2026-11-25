"""New finite28-cap main preflight; stateless readings are sealed stage inputs.

Reuse read-only/atomic orchestration functions with all paths rebound to22.
No completed output, worker, control, queue or publication is executed again.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
TEMPLATE=BASE/'unicode-guard-real-preflight-20261109-18/orchestrate.py'
spec=importlib.util.spec_from_file_location('finite_main22_orchestration_library',TEMPLATE)
library=importlib.util.module_from_spec(spec);spec.loader.exec_module(library)
original_remote=library.remote
def remote(host,code,label,**kwargs):
    return original_remote(host,code,label.replace('unicode18','main22').replace('balanced-visual16','complete-history-main22'),**kwargs)
library.HERE=HERE;library.BASE=BASE;library.PACKAGE=HERE/'runtime-package'
library.REMOTE_PACKAGE='/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/'+HERE.name
library.OUTPUT='/home/researcher/jev-defense-four-gpu-20261106/'+HERE.name
library.remote=remote
save,sha=library.save,library.sha


def cpu():
    assert not(HERE/'CPU-admission.json').exists()
    code='PACKAGE='+repr(library.REMOTE_PACKAGE)+'\nEXPECTED='+repr(sha(library.PACKAGE/'manifest.json'))+'\n'+library.COMMON+r'''
os.environ.update(CUDA_VISIBLE_DEVICES='',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2')
import base64,copy,sys
from contextlib import nullcontext
p=Path(PACKAGE);assert sha(p/'manifest.json')==EXPECTED
m=json.loads((p/'manifest.json').read_bytes())
for name,h in m['files'].items():assert sha(p/name)==h,name
for q in p.rglob('*.py'):compile(q.read_text(),str(q),'exec')
sys.path[:0]=[str(p),str(p/'release')]
import torch
from transformers import AutoProcessor,GenerationConfig
from defense.qwen_backend import LocalQwen
from defense.prompts import VERIFY
from defense.core import canonical,digest
from aux_identity_support import tensor_record
import worker,image_evidence as contract
assert torch.cuda.device_count()==0
plan=json.loads((p/'controls-plan.json').read_bytes())
assert plan['limits']==worker.LIMITS==m['limits']
assert plan['auxiliary']==[] and len(plan['actors'])==2 and len(plan['judges'])==6
assert m['limits']['auxiliary']==0 and m['limits']['actor']==4 and m['limits']['judge']==24
out=p/'CPU-admission'/str(time.time_ns());out.mkdir(parents=True)
def put(q,v):
 with q.open('x',encoding='utf8')as stream:json.dump(v,stream,ensure_ascii=False,indent=2);stream.write('\n')
packets={};bindings=[]
for row in plan['stage_readings']:
 local=p/row['directory'];original=Path(row['source_root'])
 assert sha(original/'seal.json')==row['source_seal_sha256']
 for name in ['request.json','packet.json','raw-output.txt','original.png','actual-generation.json','seal.json']:
  assert sha(local/name)==sha(original/name),name
 request=json.loads((local/'request.json').read_bytes());raw=contract.validate_image_only_request(request)
 assert digest(raw)==row['image_sha256'] and json.loads((local/'actual-generation.json').read_bytes())['natural_EOS']
 packet=contract.actor_packet(request,(local/'raw-output.txt').read_text(),True)
 assert packet==json.loads((local/'packet.json').read_bytes())
 packets[row['id']]=packet;bindings.append({'case':row['id'],'image_sha256':row['image_sha256'],'frozen_source_seal_sha256':row['source_seal_sha256'],'fresh_auxiliary_call':False})
ref=json.loads((p/'primary-reference.json').read_bytes())
processor=AutoProcessor.from_pretrained(ref['primary_model'],local_files_only=True,trust_remote_code=True)
generation=GenerationConfig.from_pretrained(ref['primary_model'],local_files_only=True)
class Capture(Exception):pass
class CPUModel:
 device=torch.device('cpu')
 generation_config=generation
 def generate(self,**inputs):
  state['tensors']={name:tensor_record(tensor,torch,state['root'],name,'native_CPU_full_original_main_input')for name,tensor in inputs.items()if isinstance(tensor,torch.Tensor)}
  state['generation']=inputs['generation_config'].to_dict()
  raise Capture()
template=json.loads((p/'actor-template.json').read_bytes());rows=[];judge_rows=[]
for row in plan['actors']:
 frozen=json.loads((p/row['path']).read_bytes());view=worker.restore(frozen['view'])
 for condition in row['condition_order']:
  actual=worker.add_packet(view,packets[row['scene']])if condition=='single_balanced_auxiliary'else view
  body={k:copy.deepcopy(v)for k,v in template.items()if k!='messages'};body['messages']=copy.deepcopy(actual.messages)
  target=out/(row['id']+'-'+condition);target.mkdir()
  state={'root':target};engine=LocalQwen.__new__(LocalQwen);engine.processor=processor;engine.model=CPUModel();engine.torch=torch
  try:engine.generate(body['messages'],2048,target/'unused-native.json',original_body=body)
  except Capture:pass
  else:raise AssertionError('Unexpected generation')
  assert state['generation']['max_new_tokens']==2048
  assert state['tensors']['image_grid_thw']['shape']==[3,3]
  put(target/'CPU-prepared.json',{'tensors':state['tensors'],'body_sha256':digest(canonical(body))})
  rows.append({'case':row['id'],'condition':condition,'tensors':state['tensors'],'body_sha256':digest(canonical(body))})
for row in plan['judges']:
 frozen=json.loads((p/row['path']).read_bytes());view=worker.restore(frozen['view'])
 for condition in row['condition_order']:
  actual=worker.add_packet(view,packets[row['scene']])if condition=='single_balanced_auxiliary'else view
  captured={}
  def capture(messages,max_tokens,path,**kwargs):
   assert max_tokens==4096;captured['messages_sha256']=digest(canonical(messages));return 'CPU_ONLY_NOT_A_REPLY'
  engine=LocalQwen.__new__(LocalQwen);engine.generate=capture
  engine.judge(VERIFY,actual,frozen['candidate'])
  judge_rows.append({'case':row['id'],'condition':condition,'full_original_history_images_resolve_native_judge_transport':True,
                     'unaugmented_VERIFY_wire_message_sha256':captured['messages_sha256']})
old=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/unicode-guard-real-preflight-20261109-18')
for name in ['model_runtime.py','release/defense/core.py','release/defense/qwen_backend.py','release/image_evidence.py']:
 assert sha(p/name)==sha(old/name),name
closed=Path('/home/researcher/jev-defense-four-gpu-20261106/unicode-guard-real-preflight-20261109-18')
for name in ['launcher-process.json','worker/process.json']:
 record=json.loads((closed/name).read_bytes());assert identity(record['pid']).get('absent')is True
proof={'passed':True,'manifest_sha256':EXPECTED,'remote_evidence':str(out),'actor_inputs':rows,'judge_wire_inputs':judge_rows,
       'frozen_auxiliary_stage_bindings':bindings,'fresh_auxiliary_calls':0,'original_full_history_and_images_preserved':True,
       'strict_validator_native_processor_model_generation_unchanged':True,'private_labels_not_model_inputs':True,
       'new_model_GPU_GUI_calls':0,'weights_loaded':False,'not_a_memory_semantic_or_efficacy_pass':True}
put(out/'receipt.json',proof);put(out/'seal.json',{q.relative_to(out).as_posix():sha(q)for q in out.rglob('*')if q.is_file()})
print(json.dumps({'proof':proof,'receipt_sha256':sha(out/'receipt.json'),'seal_sha256':sha(out/'seal.json')}))
'''
    output,operation=remote('3090',code,'main22-native-CPU-full-history-and-frozen-readings',timeout=55)
    value=json.loads(output);save(HERE/'CPU-admission.json',{'value':value,'operation':str(operation)})
    print(json.dumps({'passed':value['proof']['passed'],'main_actor_inputs':len(value['proof']['actor_inputs']),
          'main_judge_wire_inputs':len(value['proof']['judge_wire_inputs']),'fresh_auxiliary_calls':0,'model_calls':0,'operation':str(operation)}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['stage','cpu','submit','inspect'])
    action=parser.parse_args().action
    if action=='cpu':cpu()
    else:getattr(library,action)()
