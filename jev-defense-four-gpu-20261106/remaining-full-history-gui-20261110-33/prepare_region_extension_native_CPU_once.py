"""CPU-only exact native inputs for an UNSENT prompt, never generation or GUI."""
from pathlib import Path
import base64
import hashlib
import json
import time

import orchestrate


SOURCE = r'''
import base64,io,traceback
assert os.getuid()==1033 and os.environ.get('CUDA_VISIBLE_DEVICES')==''
assert not Path(TARGET).exists()
root=Path(TARGET);assert root.parent.is_dir()and root.parent.stat().st_uid==1033
root.mkdir()
save=lambda name,value:(root/name).write_bytes(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()+b'\n')
save('process.json',identity(os.getpid()))
save('intent.json',{'time':time.time(),'fixed_sources':CASES,'CPU_only':True,'no_model_GUI_scorer_calls':True,'source':BINDING})
failure=None;records=[]
try:
 package=Path(PACKAGE)
 assert sha(package/'manifest.json')==EXPECTED_MANIFEST
 original_fixed=(package/'fixed-prompt.txt').read_text()
 assert hashlib.sha256(original_fixed.encode()).hexdigest()==PROMPTS['v6']['sha256']
 for name,prompt in PROMPTS.items():
  assert hashlib.sha256(prompt['text'].encode()).hexdigest()==prompt['sha256']
  (root/('UNSENT-'+name+'.txt')).write_bytes(prompt['text'].encode())
 metadata={}
 reference=json.loads((package/'auxiliary-identity-reference.json').read_bytes())
 model_path=Path(reference['base_model']['local_path'])
 assert reference['base_model']=={'local_path':'/home/researcher/models/Qwen3.5-9B','repo':'Qwen/Qwen3.5-9B','revision':'c202236235762e1c871ad0ccb60c8ee5ba337b9a'}
 for row in reference['metadata_files']:
  path=model_path/row['filename'];assert path.stat().st_size==row['bytes']and sha(path)==row['sha256']
  metadata[row['filename']]=row['sha256']
 assert len(metadata)==9
 import torch,transformers
 from transformers import AutoProcessor
 from PIL import Image
 assert torch.__version__==VERSIONS['torch']and transformers.__version__==VERSIONS['transformers']
 assert not torch.cuda.is_initialized()
 torch.set_num_threads(1)
 processor=AutoProcessor.from_pretrained(model_path,local_files_only=True,trust_remote_code=False)
 configuration=json.loads((model_path/'config.json').read_bytes())
 context_cap=configuration['text_config']['max_position_embeddings']
 assert isinstance(context_cap,int)and context_cap>0
 for case in CASES:
  source=Path(OUTPUT)/'worker/requests'/case['request']
  assert sha(source/'seal.json')==case['request_seal_sha256']
  sealed=json.loads((source/'seal.json').read_bytes())
  for name in ['original.png','payload.json','prepared.json','effective-generation.json']:
   assert sha(source/name)==sealed[name],name
  image_raw=(source/'original.png').read_bytes()
  assert hashlib.sha256(image_raw).hexdigest()==case['image_sha256']
  request=json.loads((source/'payload.json').read_bytes())
  assert request['prompt']==original_fixed and request['original_size']==[1280,720]
  assert set(request)=={'policy','model','revision','image_base64','image_sha256','original_size','prompt','prompt_sha256'}
  assert base64.b64decode(request['image_base64'],validate=True)==image_raw
  original=json.loads((source/'prepared.json').read_bytes())
  effective=json.loads((source/'effective-generation.json').read_bytes())
  assert effective['max_new_tokens']==2048 and effective['do_sample']is False
  row={'request':case['request'],'image_sha256':case['image_sha256'],'request_seal_sha256':case['request_seal_sha256'],'variants':{}}
  baseline=None
  for variant,prompt in PROMPTS.items():
   image=Image.open(io.BytesIO(image_raw)).convert('RGB');assert image.size==(1280,720)
   messages=[{'role':'user','content':[{'type':'image','image':image},{'type':'text','text':prompt['text']}]}]
   torch.manual_seed(0)
   inputs=processor.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=False,
    tools=None,return_dict=True,return_tensors='pt')
   inventory={}
   for name,tensor in inputs.items():
    assert isinstance(tensor,torch.Tensor)and tensor.device.type=='cpu'
    stable=tensor.detach().contiguous();raw=stable.view(torch.uint8).numpy().tobytes(order='C')
    filename=case['request']+'-'+variant+'-'+name+'.tensor';(root/filename).write_bytes(raw)
    inventory[name]={'shape':list(stable.shape),'dtype':str(stable.dtype),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'file':filename}
    if name in ['input_ids','image_grid_thw']:
     save(case['request']+'-'+variant+'-'+name+'.json',stable.tolist())
   assert set(inventory)==set(original)
   if variant=='v6':
    for name,actual in inventory.items():
     assert all(actual[k]==original[name][k]for k in ['shape','dtype','bytes','sha256']),(case['request'],name)
    baseline=inventory
   else:
    for name in ['pixel_values','image_grid_thw']:
     assert all(inventory[name][k]==baseline[name][k]for k in ['shape','dtype','bytes','sha256']),(variant,name)
   length=inputs['input_ids'].shape[-1]
   assert length+effective['max_new_tokens']<=context_cap
   row['variants'][variant]={'input_tokens':length,'prompt_utf8_sha256':prompt['sha256'],'all_tensors':inventory,
    'native_pixel_values_and_grid_equal_original_v6':True,'context_tokens_with_original_output_cap':length+2048,
    'text_config_context_cap':context_cap,'native_preparation_only_no_forward':True}
   image.close();messages.clear();inputs=None
  row['v8_minus_v6_tokens']=row['variants']['v8']['input_tokens']-row['variants']['v6']['input_tokens']
  row['v9_minus_v6_tokens']=row['variants']['v9']['input_tokens']-row['variants']['v6']['input_tokens']
  row['v9_minus_v8_tokens']=row['variants']['v9']['input_tokens']-row['variants']['v8']['input_tokens']
  records.append(row);save('completed-'+case['request']+'.json',row)
 assert not torch.cuda.is_initialized()
 save('receipt.json',{'passed':True,'time':time.time(),'records':records,'model_metadata_sha256':metadata,
  'torch':torch.__version__,'transformers':transformers.__version__,'actual_CPU_only':True,
  'CUDA_initialized':False,'weights_loaded':False,'model_forward_calls':0,'generation_calls':0,
  'GUI_capture_action_scorer_paid_calls':0,'original2048_aux_output_and_generation_unchanged':True,
  'original_image_bytes_and_native_pixel_grid_tensors_unchanged':True,
  'known_source_development_not_independent_new_semantic_controls':True,
  'new_prompt_semantics_GPU_fit_or_defense_efficacy_proven':False,'running32_or_validator_changed':False})
except BaseException as error:
 failure=type(error).__name__+': '+str(error)
 (root/'failure.txt').write_text(traceback.format_exc())
 save('failure.json',{'error':failure,'completed':len(records),'no_automatic_retry':True,'model_GUI_calls':0})
finally:
 save('terminal.json',{'time':time.time(),'error':failure,'completed_sources':len(records),'expected_sources':len(CASES),
  'status':'completed_CPU_inputs'if failure is None else'failed_CPU_preparation','no_generation_GUI_retry':True})
 save('seal.json',{p.name:sha(p)for p in root.iterdir()if p.is_file()and p.name!='seal.json'})
 print(json.dumps({'root':str(root),'error':failure,'seal_sha256':sha(root/'seal.json'),
  'receipt':json.loads((root/'receipt.json').read_bytes())if(root/'receipt.json').exists()else None,
  'terminal':json.loads((root/'terminal.json').read_bytes())},ensure_ascii=False))
'''


def main():
    here = orchestrate.HERE
    pointer = here / 'region-extension-native-CPU-submitted.json'
    assert not pointer.exists(), 'Inspect this exact submitted CPU attempt; never duplicate it'
    diagnosis = json.loads((here / 'query-object-source-diagnosis-created.json').read_bytes())
    staged = Path(diagnosis['root'])
    for name, expected in json.loads((staged / 'seal.json').read_bytes()).items():
        assert orchestrate.sha(staged / name) == expected
    prompts = {}
    for key, path in [('v6', here / 'runtime-package/fixed-prompt.txt'),
                      ('v8', staged / 'parent-UNSENT-v8.txt'),
                      ('v9', staged / 'UNSENT-region-source-extension-v9.txt')]:
        value = path.read_text(encoding='utf-8')
        prompts[key] = dict(text=value, sha256=hashlib.sha256(value.encode()).hexdigest())
    cases = []
    for ident in ['0117', '0122', '0128']:
        authority = json.loads((here / ('auxiliary-source-' + ident + '-collected.json')).read_bytes())
        source = Path(authority['root'])
        assert orchestrate.sha(source / 'seal.json') == authority['seal_sha256']
        receipt = json.loads((source / 'receipt.json').read_bytes())['source']
        cases.append(dict(request=ident, image_sha256=receipt['request']['image_sha256'],
            request_seal_sha256=receipt['request_seal_sha256']))
    evidence = here / 'actual-evidence-1794272333951960400'
    loaded = json.loads((evidence / '3090.json').read_bytes())['worker/loaded.json']['value']
    versions = {key: loaded[key] for key in ['torch', 'transformers']}
    target = orchestrate.OUTPUT.rsplit('/', 1)[0] + '/region-extension-native-CPU-' + str(time.time_ns())
    intent = dict(time=time.time(), remote_target=target, source_diagnosis=diagnosis,
        known_source_cases=cases, source_sha256=orchestrate.sha(Path(__file__)),
        no_generation_GUI_or_running_conditions_change=True)
    orchestrate.save(pointer, intent)
    code = ('TARGET=' + repr(target) + '\nPACKAGE=' + repr(orchestrate.REMOTE_PACKAGE)
        + '\nOUTPUT=' + repr(orchestrate.OUTPUT) + '\nCASES=' + repr(cases)
        + '\nVERSIONS=' + repr(versions) + '\nBINDING=' + repr(intent)
        + '\nEXPECTED_MANIFEST=' + repr(orchestrate.sha(orchestrate.PACKAGE / 'manifest.json'))
        + '\nPROMPTS=' + repr(prompts) + '\n' + orchestrate.COMMON + '\n' + SOURCE)
    private = "import os\nos.environ['CUDA_VISIBLE_DEVICES']=''\nos.environ['OMP_NUM_THREADS']='1'\nos.environ['OPENBLAS_NUM_THREADS']='1'\nos.environ['TOKENIZERS_PARALLELISM']='false'\n"
    output, operation = orchestrate.remote('3090', code, 'new-UNSENT-region-extension-exact-native-CPU-inputs-only',
        timeout=55, private_prefix=private, interpreter='/opt/whz/conda-envs/webmall-vlm/bin/python')
    result = json.loads(output)
    out = here / ('region-extension-native-CPU-result-' + str(time.time_ns()))
    out.mkdir()
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    orchestrate.save(out / 'remote-result.json', result)
    orchestrate.save(out / 'receipt.json', dict(remote_operation=str(operation), submission=intent,
        result=result, local_is_remote_receipt_copy=True, all_native_tensor_binaries_retained_remotely=True,
        no_current_experiment_inputs_or_outputs_changed=True))
    orchestrate.save(out / 'seal.json', {p.name: orchestrate.sha(p) for p in out.iterdir() if p.is_file()})
    authority = dict(root=str(out), receipt_sha256=orchestrate.sha(out / 'receipt.json'),
        seal_sha256=orchestrate.sha(out / 'seal.json'))
    orchestrate.save(here / 'region-extension-native-CPU-result-created.json', authority)
    print(json.dumps(dict(authority, error=result['error'],
        native_token_counts=[{k:v for k,v in row.items()if k in ['request','v8_minus_v6_tokens','v9_minus_v6_tokens','v9_minus_v8_tokens']} |
            {'variants':{key:val['input_tokens']for key,val in row['variants'].items()}}
            for row in (result['receipt'] or {}).get('records', [])])))


if __name__ == '__main__':
    main()
