"""Freeze native CPU inputs for a proposed, not authorized, prompt condition.

No weights, CUDA initialization, model generation, GUI, scorer or service
mutation. Original sealed native inputs are the equality references. Pixel
bytes proven equal refer to their already preserved original raw tensors.
"""
import json
import time
from pathlib import Path
from control import HERE, OUT, R3090, remote, save, sha


def main():
    pointer = json.loads((HERE / 'evidence-discipline-preparation-current.json').read_bytes())
    prepared = Path(pointer['preparation'])
    assert sha(prepared / 'seal.json') == pointer['preparation_seal_sha256']
    for name, expected in json.loads((prepared / 'seal.json').read_bytes()).items():
        assert sha(prepared / name) == expected
    suffix = (prepared / 'proposed-system-suffix.txt').read_text(encoding='utf8')
    token = str(time.time_ns())
    dest = HERE / ('evidence-discipline-native-CPU-' + token)
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    remote_root = OUT + '/candidate-native-CPU-' + token
    original_source = HERE / 'package/release/defense/qwen_backend.py'
    cases = [1, 2, 17, 20, 29, 43, 44, 46, 47, 48]
    common = ('ROOT=' + repr(OUT) + '\nPACKAGE=' + repr(R3090) + '\nDEST=' + repr(remote_root)
              + '\nSUFFIX=' + repr(suffix) + '\nBACKEND_SHA=' + repr(sha(original_source)) + '\n')
    code = r'''
import base64,copy,hashlib,io,json,os,time
from pathlib import Path
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OMP_NUM_THREADS']='4'
os.nice(10)
available=int(next(s.split()[1]for s in Path('/proc/meminfo').read_text().splitlines()if s.startswith('MemAvailable:')))*1024
assert available>=8*1024**3,'Wait for CPU preparation RAM; do not alter model/input'
import torch
from PIL import Image
from transformers import AutoProcessor
torch.set_num_threads(4)
assert not torch.cuda.is_initialized()
r=Path(ROOT);p=Path(PACKAGE);target=Path(DEST)/('%02d'%NUMBER)
target.mkdir(parents=True,exist_ok=False)
def digest(data):return hashlib.sha256(data).hexdigest()
def save(path,value):
 with path.open('x',encoding='utf8')as f:json.dump(value,f,ensure_ascii=False,indent=2)
def sha(path):
 h=hashlib.sha256()
 with path.open('rb')as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
 return h.hexdigest()
assert sha(p/'release/defense/qwen_backend.py')==BACKEND_SHA
reference=json.loads((p/'primary-reference.json').read_bytes())
processor=AutoProcessor.from_pretrained(reference['primary_model'],local_files_only=True,trust_remote_code=True)
source=r/'primary/requests'/('%05d'%(19+NUMBER));seal=json.loads((source/'seal.json').read_bytes())
for name in ['wire-request.bin','body.json','prepared.json','first-forward.json']:
 assert sha(source/name)==seal[name]
wire=json.loads((source/'wire-request.bin').read_bytes())
assert wire['run_id']=='flash14-T017-clean-gate'and wire['decision_index']==NUMBER
original=json.loads((source/'body.json').read_bytes());assert wire['body']==original
expected=json.loads((source/'prepared.json').read_bytes())
first=json.loads((source/'first-forward.json').read_bytes())
amended=copy.deepcopy(original);amended['messages'][0]['content']+='\n\n'+SUFFIX
assert amended['messages'][1:]==original['messages'][1:]
assert {k:v for k,v in amended.items()if k!='messages'}=={k:v for k,v in original.items()if k!='messages'}
save(target/'proposed-full-body.json',amended)
def convert(messages):
 out=[]
 for message in messages:
  parts=message['content']if isinstance(message['content'],list)else[{'type':'text','text':message['content']}]
  blocks=[]
  for block in parts:
   if block['type']=='text':blocks.append(copy.deepcopy(block))
   elif block['type']=='image_url':
    url=block['image_url']['url'];assert url.startswith('data:image/png;base64,')
    blocks.append({'type':'image','image':Image.open(io.BytesIO(base64.b64decode(url.split(',',1)[1]))).convert('RGB')})
   else:raise ValueError(block['type'])
  out.append({'role':message['role'],'content':blocks})
 return out
def apply(body):
 return processor.apply_chat_template(convert(body['messages']),add_generation_prompt=True,tokenize=True,return_dict=True,return_tensors='pt',tools=body.get('tools'),**body.get('chat_template_kwargs',{}))
def record(value):
 assert isinstance(value,torch.Tensor)and value.device.type=='cpu'
 raw=value.detach().contiguous().view(torch.uint8).numpy().tobytes()
 return {'shape':list(value.shape),'dtype':str(value.dtype),'bytes':len(raw),'sha256':digest(raw)}
old=apply(original);old_records={k:record(v)for k,v in old.items()}
assert set(old_records)==set(expected)==set(first)
for key,metadata in old_records.items():
 assert all(metadata[f]==expected[key][f]==first[key][f]for f in ['shape','dtype','bytes','sha256']),key
old_ids=old['input_ids'][0].tolist()
del old
new=apply(amended);new_records={k:record(v)for k,v in new.items()}
assert set(new_records)==set(old_records)
assert new['input_ids'].shape[-1]-old_records['input_ids']['shape'][-1]==292
text_keys={'input_ids','attention_mask','token_type_ids','mm_token_type_ids','position_ids'}
for key,metadata in new_records.items():
 if key in text_keys:
  raw=new[key].detach().contiguous().view(torch.uint8).numpy().tobytes()
  name='proposed_'+key+'.tensor'
  with(target/name).open('xb')as f:f.write(raw)
  metadata['new_raw_file']=name
 else:
  assert metadata==old_records[key],key
  metadata['unchanged_byte_equal_original_raw_reference']=str(source/expected[key]['file'])
  metadata['previous_actual_raw_verification_referenced_not_rehashed_now']=True
new_ids=new['input_ids'][0].tolist()
prefix=0
while prefix<min(len(old_ids),len(new_ids))and old_ids[prefix]==new_ids[prefix]:prefix+=1
suffix=0
while suffix<min(len(old_ids)-prefix,len(new_ids)-prefix)and old_ids[-1-suffix]==new_ids[-1-suffix]:suffix+=1
assert not torch.cuda.is_initialized()
result={'source_run':wire['run_id'],'source_decision':NUMBER,'source_wire_sha256':sha(source/'wire-request.bin'),'source_body_sha256':sha(source/'body.json'),'source_request_seal_sha256':sha(source/'seal.json'),'backend_sha256':BACKEND_SHA,'processor_class':type(processor).__name__,'suffix_sha256':digest(SUFFIX.encode()),'original_native_CPU_equals_actual_prepared_and_first_forward':True,'old_prepared':old_records,'proposed_prepared':new_records,'full_input_token_delta':len(new_ids)-len(old_ids),'original_input_tokens':len(old_ids),'proposed_input_tokens':len(new_ids),'exact_ID_edit_window':{'common_prefix_tokens':prefix,'common_suffix_tokens':suffix,'old_middle_tokens':len(old_ids)-prefix-suffix,'proposed_middle_tokens':len(new_ids)-prefix-suffix},'full_original_PNGs_and_non_system_history_preserved':True,'proposed_full_body_sha256':sha(target/'proposed-full-body.json'),'weights_loaded':False,'CUDA_initialized':False,'new_model_GUI_scorer_calls':0,'generation_or_capacity_proven':False,'native_CPU_preparation_only':True,'time':time.time()}
save(target/'result.json',result)
save(target/'seal.json',{f.name:sha(f)for f in target.iterdir()if f.is_file()})
print(json.dumps({'result':result,'remote_case':str(target),'remote_seal_sha256':sha(target/'seal.json')}))
'''
    rows = []
    for number in cases:
        raw, operation = remote('3090', common + 'NUMBER=' + repr(number) + '\n' + code,
                                'candidate-native-CPU-only-' + str(number), timeout=55)
        result = json.loads(raw)
        save(dest / ('case-%02d.json' % number), {'operation': str(operation), **result})
        rows.append(result)
        print(json.dumps({'native_CPU_checked': len(rows), 'expected': len(cases),
                          'case': number, 'new_model_GUI_calls': 0}), flush=True)
    summary = {'source_preparation': str(prepared), 'source_preparation_seal_sha256': sha(prepared / 'seal.json'),
               'remote_root': remote_root, 'cases': cases, 'checks_passed': len(rows),
               'all_exact_full_input_token_deltas': sorted({v['result']['full_input_token_delta'] for v in rows}),
               'max_proposed_native_input_tokens': max(v['result']['proposed_input_tokens'] for v in rows),
               'all_baseline_CPU_ID_pixel_grid_bytes_equal_actual_source': True,
               'all_proposed_pixels_and_grid_unchanged': True,
               'semantic_or_generation_or_GPU_capacity_tests': False,
               'new_model_GUI_scorer_calls': 0, 'weights_loaded': False,
               'current_queue_or_sources_changed': False,
               'formal_release': False, 'new_condition_authorized': False,
               'previous_raw_input_audits_remain_at_their_recorded_read_times': True,
               'time': time.time()}
    save(dest / 'summary.json', summary)
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'preparation': str(dest), **summary}))


if __name__ == '__main__':
    main()
