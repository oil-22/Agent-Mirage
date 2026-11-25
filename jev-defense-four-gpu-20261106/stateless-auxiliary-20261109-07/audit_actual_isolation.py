"""Bind actual sealed auxiliary inputs to independently reconstructed one-shot inputs."""
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
GUI=HERE.parent/'full-gui-bounded-evidence-20261109-03'
sys.path.insert(0,str(GUI))
from remote_control import remote,save,sha

code=r'''
from pathlib import Path
import base64,hashlib,io,json,os,struct,sys,time
os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['HF_HUB_OFFLINE']='1'
p=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/full-gui-bounded-evidence-20261109-03')
w=Path('/home/researcher/jev-defense-four-gpu-20261106/full-gui-bounded-evidence-20261109-03/worker')
sys.path[:0]=[str(p),str(p/'release')]
import image_evidence as contract
from transformers import AutoProcessor
import torch
from PIL import Image
processor=AutoProcessor.from_pretrained('/home/researcher/models/Qwen3.5-9B',local_files_only=True,trust_remote_code=False)
h=lambda b:hashlib.sha256(b).hexdigest();rows=[]
for d in sorted((w/'requests').iterdir()):
 if not(d/'seal.json').exists()or not(d/'response.json').exists():continue
 response=json.loads((d/'response.json').read_bytes())
 if response['operation']!='evidence':continue
 seal_raw=(d/'seal.json').read_bytes();seal=json.loads(seal_raw)
 for name,expected in seal.items():assert h((d/name).read_bytes())==expected,(d.name,name)
 payload=json.loads((d/'payload.json').read_bytes());raw=contract.validate_image_only_request(payload)
 assert raw==(d/'original.png').read_bytes()
 messages=[{'role':'user','content':[{'type':'image','image':Image.open(io.BytesIO(raw)).convert('RGB')},
  {'type':'text','text':contract.FIXED_PROMPT}]}]
 expected=processor.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,
  enable_thinking=False,tools=None,return_dict=True,return_tensors='pt')
 prepared=json.loads((d/'prepared.json').read_bytes());forward=json.loads((d/'first-forward.json').read_bytes())
 assert set(prepared)==set(expected)==set(forward)
 for name,tensor in expected.items():
  b=tensor.contiguous().view(torch.uint8).numpy().tobytes()
  assert h(b)==prepared[name]['sha256']==forward[name]['sha256'],(d.name,name)
  assert list(tensor.shape)==prepared[name]['shape']==forward[name]['shape']
 actual=json.loads((d/'actual-generation.json').read_bytes())
 config=json.loads((d/'effective-generation.json').read_bytes())
 rows.append({'request':d.name,'original_seal_sha256':h(seal_raw),'all_original_files_verified':len(seal),
  'image_sha256':payload['image_sha256'],'fixed_prompt_sha256':payload['prompt_sha256'],
  'one_image_one_user_fixed_prompt_native_CPU_reconstruction_matches_actual_first_forward':True,
  'actual_input_tokens':actual['input_tokens'],'actual_output_tokens':actual['output_tokens'],
  'natural_EOS':actual['natural_EOS'],'cache_implementation':config.get('cache_implementation'),
  'contract_available':(d/'evidence-packet.json').exists(),
  'contract_failure':json.loads((d/'contract-failure.json').read_bytes())if(d/'contract-failure.json').exists()else None})
assert rows and not torch.cuda.is_initialized()
root=Path('/home/researcher/jev-defense-four-gpu-20261106/stateless-auxiliary-20261109-07')/('actual-input-audit-'+str(time.time_ns()));root.mkdir(parents=True)
value={'time':time.time(),'rows':rows,'CPU_only':True,'new_model_HTTP_GUI_calls':0,
 'actual_auxiliary_task_history_candidate_leak_observed':False,
 'actual_first_forward_tensors_bound_to_fresh_one_message_CPU_inputs':True,
 'actual_per_call_runtime_past_KV_not_recorded_in_old_audit':True,
 'do_not_claim_GPU_past_cache_empty_verified_until_new_boundary_runs':True,
 'live_condition_changed':False,'same_image_reply_reuse_present_in_old_Controller':True,
 'models_loaded':False,'CUDA_initialized':False}
with(root/'receipt.json').open('x',encoding='utf8')as f:json.dump(value,f,ensure_ascii=False,sort_keys=True,indent=2);f.write('\n')
with(root/'seal.json').open('x',encoding='utf8')as f:json.dump({'receipt.json':h((root/'receipt.json').read_bytes())},f,indent=2);f.write('\n')
print(json.dumps({'remote':str(root),'receipt_sha256':h((root/'receipt.json').read_bytes()),'result':value}))
'''
out,operation=remote('3090',code,'actual-auxiliary-one-image-one-prompt-forward-input-isolation-audit',timeout=140)
v=json.loads(out);local=HERE/('actual-input-audit-'+str(time.time_ns()));local.mkdir()
save(local/'receipt.json',v)
save(local/'collection.json',{'operation':str(operation),'receipt_sha256':sha(local/'receipt.json'),'remote':v['remote']})
print(json.dumps({'local':str(local),'requests_verified':len(v['result']['rows']),
 'available':sum(x['contract_available']for x in v['result']['rows']),
 'input_tensor_isolation_verified':True,'GPU_past_empty_proof_pending':True,'new_model_GUI_calls':0}))
