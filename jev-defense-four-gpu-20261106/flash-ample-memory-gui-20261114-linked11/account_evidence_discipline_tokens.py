"""CPU-only native chat-template accounting; no model or new request delivery."""
import json
import sys
import time
from pathlib import Path
from control import HERE, OUT, R3090, remote, save, sha


def main():
    prepared = Path(sys.argv[1]).resolve()
    assert prepared.parent == HERE
    for name, expected in json.loads((prepared / 'seal.json').read_bytes()).items():
        assert sha(prepared / name) == expected
    suffix = (prepared / 'proposed-system-suffix.txt').read_text(encoding='utf8')
    dest = HERE / ('evidence-discipline-token-accounting-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    code = ('ROOT=' + repr(OUT) + '\nPACKAGE=' + repr(R3090) + '\nSUFFIX=' + repr(suffix) + '\n' + r'''
import copy,hashlib,json,os,time
from pathlib import Path
from transformers import AutoProcessor
r=Path(ROOT);p=Path(PACKAGE);ref=json.loads((p/'primary-reference.json').read_bytes());model=Path(ref['primary_model'])
processor=AutoProcessor.from_pretrained(model,local_files_only=True,trust_remote_code=True)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def convert(messages):
 out=[]
 for message in messages:
  parts=message['content']if isinstance(message['content'],list)else[{'type':'text','text':message['content']}]
  blocks=[]
  for block in parts:
   if block['type']=='text':blocks.append(copy.deepcopy(block))
   elif block['type']=='image_url':blocks.append({'type':'image','image':'UNCHANGED_ORIGINAL_IMAGE_NOT_LOADED_FOR_TEXT_ACCOUNTING'})
   else:raise ValueError(block['type'])
  out.append({'role':message['role'],'content':blocks})
 return out
rows=[]
for number in [1,2,17,20,29,43,44,46,47,48]:
 d=r/'primary/requests'/('%05d'%(19+number));seal=json.loads((d/'seal.json').read_bytes())
 raw=(d/'wire-request.bin').read_bytes();assert digest(raw)==seal['wire-request.bin'];wire=json.loads(raw)
 assert wire['run_id']=='flash14-T017-clean-gate'and wire['decision_index']==number
 body=wire['body'];amended=copy.deepcopy(body);amended['messages'][0]['content']+='\n\n'+SUFFIX
 assert amended['messages'][1:]==body['messages'][1:]
 kwargs=dict(add_generation_prompt=True,tokenize=False,tools=body.get('tools'),**body.get('chat_template_kwargs',{}))
 baseline=processor.apply_chat_template(convert(body['messages']),**kwargs)
 changed=processor.apply_chat_template(convert(amended['messages']),**kwargs)
 old_ids=processor.tokenizer.encode(baseline,add_special_tokens=False)
 new_ids=processor.tokenizer.encode(changed,add_special_tokens=False)
 native=json.loads((d/'actual-generation.json').read_bytes())
 rows.append({'decision':number,'source_wire_sha256':digest(raw),'native_original_input_tokens':native['input_tokens'],'original_rendered_text_tokens_before_image_expansion':len(old_ids),'proposed_rendered_text_tokens_before_image_expansion':len(new_ids),'rendered_text_token_delta':len(new_ids)-len(old_ids),'estimated_full_input_if_image_expansion_identical':native['input_tokens']+len(new_ids)-len(old_ids),'actual_forward_for_amended_prompt':False,'original_image_count':sum(b.get('type')=='image_url'for m in body['messages']if isinstance(m['content'],list)for b in m['content'])})
metadata={name:digest((model/name).read_bytes())for name in ['tokenizer_config.json','chat_template.jinja','tokenizer.json','config.json']if(model/name).exists()}
print(json.dumps({'time':time.time(),'UID':os.getuid(),'model':str(model),'native_processor_class':type(processor).__name__,'tokenizer_class':type(processor.tokenizer).__name__,'metadata_sha256':metadata,'suffix_sha256':digest(SUFFIX.encode()),'accounting':rows,'new_model_GPU_GUI_calls':0,'weights_loaded':False,'images_resized_or_reencoded':False,'native_forward_capacity_proven':False,'full_amended_input_ID_equivalence_proven':False,'no_actual_request_delivered':True}))
''')
    raw, operation = remote('3090', code, 'native-CPU-template-token-accounting', timeout=55)
    result = json.loads(raw)
    save(dest / 'receipt.json', {
        'preparation': str(prepared), 'preparation_seal_sha256': sha(prepared / 'seal.json'),
        'operation': str(operation), 'result': result,
        'input_fidelity_is_static_not_semantic_validation': True})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'receipt': str(dest), 'new_model_GPU_GUI_calls': 0,
                      'token_deltas': [v['rendered_text_token_delta'] for v in result['accounting']],
                      'capacity_or_efficacy_proven': False}))


if __name__ == '__main__':
    main()
