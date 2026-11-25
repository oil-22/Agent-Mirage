"""Native CPU input preparation for the proposed preread, no model loading.

Only new proposed inputs are processed. Old raw visual tensors are referenced
at their completed audit time, not redundantly rehashed or regenerated.
"""
import base64
import hashlib
import json
import zlib
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from control import remote


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def main():
    assert not (HERE / 'native-CPU-current.json').exists(), 'Do not repeat completed native input preparation'
    pointer = json.loads((HERE / 'proposed-inputs-current.json').read_bytes())
    proposed = Path(pointer['root'])
    assert sha(proposed / 'seal.json') == pointer['seal_sha256']
    for name, expected in json.loads((proposed / 'seal.json').read_bytes()).items():
        assert sha(proposed / name) == expected, name
    manifest = json.loads((proposed / 'manifest.json').read_bytes())
    frozen = Path(manifest['frozen_sources'])
    sources = {r['case_id']: r for r in json.loads((frozen / 'PRIVATE-source-index.json').read_bytes())}
    contract_source = (proposed / 'reading_contract.py').read_text(encoding='utf8')
    native = HERE.parent / 'approved-offline-receipt-repair-01/package/native'
    reference = json.loads((native / 'primary-reference.json').read_bytes())
    dest = HERE / ('native-CPU-linked02-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    remote_root = '/home/researcher/jev-defense-four-gpu-20261106/history-image-preread-CPU-' + dest.name.split('-')[-1]
    backend = native / 'release/defense/qwen_backend.py'
    code = r'''
import base64,copy,hashlib,io,json,os,time,zlib
from pathlib import Path
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OMP_NUM_THREADS']='4'
os.environ['TOKENIZERS_PARALLELISM']='false'
os.nice(10)
available=int(next(line.split()[1]for line in Path('/proc/meminfo').read_text().splitlines()if line.startswith('MemAvailable:')))*1024
assert available>=8*1024**3,'Insufficient CPU-preparation RAM; do not alter input'
import torch
from PIL import Image
from transformers import AutoProcessor
torch.set_num_threads(4)
assert not torch.cuda.is_initialized()
def digest(data):return hashlib.sha256(data).hexdigest()
def sha(path):return digest(path.read_bytes())
def save(path,value):
 with path.open('x',encoding='utf8')as stream:json.dump(value,stream,ensure_ascii=False,indent=2)
assert digest(CONTRACT_SOURCE.encode())==CONTRACT_SHA
namespace={};exec(compile(CONTRACT_SOURCE,'frozen-reading-contract.py','exec'),namespace)
source=Path(SOURCE['folder']);seal=json.loads((source/'seal.json').read_bytes())
assert sha(source/'seal.json')==SOURCE['seal_sha256']
for name in ['body.json','wire-request.bin','prepared.json','first-forward.json']:
 assert sha(source/name)==seal[name],name
assert sha(source/'body.json')==SOURCE['source_body_file_sha256']
original=json.loads((source/'body.json').read_bytes())
wire=json.loads((source/'wire-request.bin').read_bytes())
assert wire['body']==original and wire['request_id']==SOURCE['request_id']
proposed,binding=namespace['project_source'](original)
frozen_body=zlib.decompress(base64.b64decode(FROZEN_BODY_Z64,validate=True))
frozen_binding=base64.b64decode(FROZEN_BINDING_B64,validate=True)
assert digest(frozen_body)==EXPECTED_BODY_SHA and json.loads(frozen_body)==proposed
assert digest(frozen_binding)==EXPECTED_BINDING_SHA and json.loads(frozen_binding)==binding
backend=Path(BACKEND_PATH);assert sha(backend)==BACKEND_SHA
target=Path(DEST)/SOURCE['case_id'];target.mkdir(parents=True,exist_ok=False)
processor=AutoProcessor.from_pretrained(MODEL,local_files_only=True,trust_remote_code=True)
converted=[]
for message in proposed['messages']:
 parts=message['content']if isinstance(message['content'],list)else[{'type':'text','text':message['content']}]
 blocks=[]
 for block in parts:
  if block['type']=='text':blocks.append(copy.deepcopy(block))
  elif block['type']=='image_url':
   url=block['image_url']['url'];assert url.startswith('data:image/png;base64,')
   blocks.append({'type':'image','image':Image.open(io.BytesIO(base64.b64decode(url.split(',',1)[1],validate=True))).convert('RGB')})
  else:raise ValueError(block['type'])
 converted.append({'role':message['role'],'content':blocks})
inputs=processor.apply_chat_template(converted,add_generation_prompt=True,tokenize=True,return_dict=True,return_tensors='pt',tools=proposed.get('tools'),**proposed.get('chat_template_kwargs',{}))
old=json.loads((source/'prepared.json').read_bytes())
first=json.loads((source/'first-forward.json').read_bytes())
assert set(inputs)==set(old)==set(first)
records={};text_keys={'input_ids','attention_mask','token_type_ids','mm_token_type_ids','position_ids'}
for key,value in inputs.items():
 assert isinstance(value,torch.Tensor)and value.device.type=='cpu'
 data=value.detach().contiguous().view(torch.uint8).numpy().tobytes()
 row={'shape':list(value.shape),'dtype':str(value.dtype),'bytes':len(data),'sha256':digest(data)}
 if key in text_keys:
  name=key+'.tensor'
  with(target/name).open('xb')as stream:stream.write(data)
  row['new_CPU_raw_file']=name
 else:
  assert all(row[field]==old[key][field]==first[key][field]for field in ['shape','dtype','bytes','sha256']),key
  row['unchanged_original_actual_raw_reference']=str(source/old[key]['file'])
  row['prior_full_raw_audit_referenced_not_repeated']=True
 records[key]=row
with(target/'preread-full-body.json').open('xb')as stream:stream.write(frozen_body)
with(target/'source-binding.json').open('xb')as stream:stream.write(frozen_binding)
assert not torch.cuda.is_initialized()
result={'time':time.time(),'case_id':SOURCE['case_id'],'original_request_id':SOURCE['request_id'],
 'original_body_file_sha256':sha(source/'body.json'),'source_request_seal_sha256':sha(source/'seal.json'),
 'proposed_preread_body_file_sha256':sha(target/'preread-full-body.json'),
 'proposed_preread_body_canonical_sha256':digest(namespace['canonical'](proposed)),
 'source_binding_file_sha256':sha(target/'source-binding.json'),'contract_sha256':CONTRACT_SHA,
 'native_backend_sha256':BACKEND_SHA,'native_processor_class':type(processor).__name__,
 'all_original_PNG_occurrences_in_original_order':len(binding['image_occurrences']),
 'all_prepared_visual_bytes_and_grid_equal_original_actual_forward':True,
 'original_actual_input_tokens':old['input_ids']['shape'][-1],
 'proposed_preread_input_tokens':int(inputs['input_ids'].shape[-1]),'prepared':records,
 'weights_loaded':False,'CUDA_initialized':False,'new_model_GUI_Flash_scorer_calls':0,
 'generation_or_GPU_capacity_or_semantics_proven':False,
 'actor_actual_dynamic_feedback_body_and_forward_not_yet_available':True,
 'old_raw_input_audits_referenced_at_original_read_times':True}
save(target/'result.json',result)
save(target/'seal.json',{path.name:sha(path)for path in target.iterdir()if path.is_file()})
print(json.dumps({'result':result,'remote_case':str(target),'remote_seal_sha256':sha(target/'seal.json')}))
'''
    summaries = []
    for row in manifest['cases']:
        common = ('SOURCE=' + repr(sources[row['case_id']]) + '\n'
                  + 'CONTRACT_SOURCE=' + repr(contract_source) + '\n'
                  + 'CONTRACT_SHA=' + repr(sha(proposed / 'reading_contract.py')) + '\n'
                  + 'FROZEN_BODY_Z64=' + repr(base64.b64encode(zlib.compress((proposed / row['case_id'] / 'preread-full-body.json').read_bytes())).decode()) + '\n'
                  + 'FROZEN_BINDING_B64=' + repr(base64.b64encode((proposed / row['case_id'] / 'source-binding.json').read_bytes()).decode()) + '\n'
                  + 'EXPECTED_BODY_SHA=' + repr(row['proposed_preread_body_file_sha256']) + '\n'
                  + 'EXPECTED_BINDING_SHA=' + repr(row['binding_sha256']) + '\n'
                  + 'BACKEND_PATH=' + repr('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/evidence-discipline-offline-20261115-receipt-repair01/native/release/defense/qwen_backend.py') + '\n'
                  + 'BACKEND_SHA=' + repr(sha(backend)) + '\n'
                  + 'MODEL=' + repr(reference['primary_model']) + '\n'
                  + 'DEST=' + repr(remote_root) + '\n')
        raw, operation = remote('3090', common + code, 'new-preread-native-CPU-linked02-' + row['case_id'], timeout=55)
        value = json.loads(raw)
        save(dest / (row['case_id'] + '.json'), {'operation': str(operation), **value})
        summaries.append(value['result'])
        print(json.dumps({'native_CPU_prepared': len(summaries), 'expected': len(manifest['cases']),
                          'case_id': row['case_id'], 'preread_input_tokens': value['result']['proposed_preread_input_tokens'],
                          'new_model_GUI_calls': 0}), flush=True)
    save(dest / 'summary.json', {'time': time.time(), 'proposed_inputs': str(proposed),
         'proposed_inputs_seal_sha256': sha(proposed / 'seal.json'), 'remote_root': remote_root,
         'cases': len(summaries), 'prepared_preread_input_token_counts':
             {row['case_id']: row['proposed_preread_input_tokens'] for row in summaries},
         'all_new_visual_tensors_equal_prior_actual_source_forward': True,
         'all_actual_actor_dynamic_bodies_unavailable_until_real_reading': True,
         'new_model_GUI_Flash_scorer_calls': 0, 'weights_loaded': False, 'CUDA_initialized': False,
         'real_generation_semantics_GPU_capacity_or_lock_qualification': False,
         'new_condition_authorized': False})
    save(dest / 'seal.json', {path.name: sha(path) for path in dest.iterdir() if path.is_file()})
    save(HERE / 'native-CPU-current.json', {'root': str(dest), 'seal_sha256': sha(dest / 'seal.json')})
    print(json.dumps({'native_CPU': str(dest), 'prepared': len(summaries), 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
