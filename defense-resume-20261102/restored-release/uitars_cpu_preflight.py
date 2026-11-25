"""CPU-only original-public-request serialization, native processor and grammar checks."""
import argparse,base64,copy,hashlib,io,json,time
from pathlib import Path
from PIL import Image
import torch,transformers
from transformers import AutoConfig,AutoProcessor
from lmformatenforcer import JsonSchemaParser
from lmformatenforcer.integrations.transformers import build_transformers_prefix_allowed_tokens_fn,build_token_enforcer_tokenizer_data
from defense.core import PublicView,VisibleImage
from defense.qwen_backend import LocalQwen

ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);args=ap.parse_args();root=args.root
assert not torch.cuda.is_available(),'This preflight must not allocate GPU resources'
model='/data/llms/UI-TARS-1.5-7B';processor=AutoProcessor.from_pretrained(model,local_files_only=True)
cfg=AutoConfig.from_pretrained(model,local_files_only=True)
td=build_token_enforcer_tokenizer_data(processor.tokenizer)
rows=[]
for case in json.loads((root/'public-requests.json').read_bytes()):
 started=time.time();request=case['request'];p=request['public'];images=[]
 for im in p['images']:
  raw=(root/(im['sha256']+'.png')).read_bytes();assert hashlib.sha256(raw).hexdigest()==im['sha256'];images.append(VisibleImage(raw,im['role']))
 view=PublicView(p['observation_id'],p['messages'],tuple(images),p['recent_action'],p['execution_feedback'],p['observed_at'])
 assert view.data()==p
 captured={};backend=LocalQwen.__new__(LocalQwen)
 def capture(messages,max_tokens,receipt,**kwargs):
  captured.update(messages=messages,max_tokens=max_tokens,**kwargs);return ''
 backend.generate=capture;backend.judge(request['system'],view,request.get('candidate'),receipt=None)
 converted=[];sizes=[]
 for message in captured['messages']:
  content=message['content'];parts=content if isinstance(content,list)else[{'type':'text','text':content}];blocks=[]
  for b in parts:
   if b['type']=='text':blocks.append(copy.deepcopy(b))
   else:
    url=b['image_url'];url=url['url']if isinstance(url,dict)else url
    im=Image.open(io.BytesIO(base64.b64decode(url.split(',',1)[1]))).convert('RGB');sizes.append(list(im.size));blocks.append({'type':'image','image':im})
  converted.append({'role':message['role'],'content':blocks})
 inputs=processor.apply_chat_template(converted,add_generation_prompt=True,tokenize=True,return_dict=True,return_tensors='pt',tools=None,enable_thinking=False)
 fn=build_transformers_prefix_allowed_tokens_fn(td,JsonSchemaParser(captured['json_schema']))
 allowed=fn(0,inputs['input_ids'][0]);assert allowed
 tokens=inputs['input_ids'].shape[-1];maxpos=getattr(cfg,'max_position_embeddings',getattr(getattr(cfg,'text_config',None),'max_position_embeddings',None))
 rows.append({'id':case['id'],'source_event_sha256':case.get('source_event_sha256'),'source_binding':case.get('source_binding'),'input_tokens':tokens,'original_image_sizes':sizes,
 'image_grid_thw':inputs.get('image_grid_thw',torch.empty(0)).tolist(),'pixel_values_shape':list(inputs['pixel_values'].shape)if'pixel_values'in inputs else None,
 'input_ids_sha256':hashlib.sha256(inputs['input_ids'].numpy().tobytes()).hexdigest(),'schema_sha256':hashlib.sha256(json.dumps(captured['json_schema'],sort_keys=True).encode()).hexdigest(),
 'max_new_tokens':captured['max_tokens'],'max_position_embeddings':maxpos,'fits_declared_context_with_output_budget':tokens+captured['max_tokens']<=maxpos if maxpos else None,
 'grammar_first_step_has_allowed_tokens':True,'seconds':time.time()-started})
 (root/'cpu-progress.json').write_text(json.dumps(rows,indent=2))
result={'time':time.time(),'cases':len(rows),'rows':rows,'model_loaded':False,'gpu_used':False,'model_inference_calls':0,
 'native_processor':processor.image_processor.to_dict(),'torch':torch.__version__,'transformers':transformers.__version__,
 'all_inputs_with_original_output_budget_fit_declared_context':all(r['fits_declared_context_with_output_budget']is True for r in rows),
 'no_external_resizing_or_truncation':True,'full_model_grammar_compatibility_proven':False,'formal_ready':False}
with(root/'cpu-result.json').open('x')as f:json.dump(result,f,indent=2)
print(json.dumps(result))
