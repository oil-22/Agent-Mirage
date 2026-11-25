"""Bind source-reviewed raw actor text to native tokens; no inference or GUI."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE / 'full-history-gui-development-20261109-23'))
from remote_control import remote, save, sha


CODE = r'''
from pathlib import Path
import hashlib,json,time
from transformers import AutoTokenizer
def h(raw):return hashlib.sha256(raw).hexdigest()
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
tokenizers={};rows=[]
for item in ITEMS:
 p=Path(item['service_receipt']).resolve()
 assert p.parent.name=='requests'and p.parent.parent.name=='worker'
 assert p.parent.parent.parent.name in ALLOWED_ROOTS
 seal=json.loads((p/'seal.json').read_bytes())
 for name in ['external-wire.json','payload.json','native-call.json','actual-generation.json','effective-generation.json','response.json']:
  assert h((p/name).read_bytes())==seal[name],(str(p),name)
 wire=json.loads((p/'external-wire.json').read_bytes());body=wire['payload']['body']
 assert wire['payload']['operation']=='actor'
 assert h(canonical(body))==item['actor_request_body_sha256']
 assert h((p/'external-wire.json').read_bytes())==item['actual_actor_wire_sha256']
 native=json.loads((p/'native-call.json').read_bytes())
 actual=json.loads((p/'actual-generation.json').read_bytes())
 reply=json.loads((p/'response.json').read_bytes());cfg=json.loads((p/'effective-generation.json').read_bytes())
 assert native['generated_ids']==actual['output_ids']
 assert native['verifier_grammar']is None
 assert native['generation_config']==cfg and cfg['max_new_tokens']==2048
 assert cfg['do_sample']is False and body['chat_template_kwargs']['enable_thinking']is False
 for field in ['force_words_ids','forced_decoder_ids','forced_bos_token_id','constraints','bad_words_ids','suppress_tokens','begin_suppress_tokens']:
  assert cfg.get(field)in [None,[]],field
 assert actual['natural_EOS']and not native['hit_output_cap']
 assert native['text']==reply['text']==item['candidate']
 assert h(reply['text'].encode())==item['candidate_text_sha256']
 assert native['request_messages_sha256']==h(canonical(body['messages']))
 assert 'Explain your current visual evidence and uncertainty briefly, then output <action>{JSON}</action>.'in body['messages'][0]['content']
 model=body['model']
 assert model=='/opt/whz/llms/Qwen3.8-27B'
 if model not in tokenizers:tokenizers[model]=AutoTokenizer.from_pretrained(model,local_files_only=True,trust_remote_code=True)
 tokenizer=tokenizers[model]
 decoded=tokenizer.decode(actual['output_ids'],skip_special_tokens=True)
 assert decoded.strip()==native['text']
 rows.append({'id':item['id'],'native_receipt':str(p),'native_seal_sha256':h((p/'seal.json').read_bytes()),
  'candidate_event_sha256':item['candidate_event_sha256'],'candidate_text_sha256':item['candidate_text_sha256'],
  'actual_output_tokens':actual['output_tokens'],'raw_ID_decode_equals_native_and_unmodified_candidate':True,
  'actor_grammar_or_forced_words':False,'input_requests_brief_visual_evidence_and_uncertainty':True,
  'native_non_thinking_condition_preserved':True,'candidate':item['candidate'],
  'decoded_with_special_tokens_sha256':h(tokenizer.decode(actual['output_ids'],skip_special_tokens=False).encode()),
  'decoded_without_special_tokens_sha256':h(decoded.encode())})
print(json.dumps({'time':time.time(),'passed':True,'rows':rows,'new_model_GUI_scorer_paid_calls':0,
 'tokenizer_only_CPU_reconstruction_no_weights_or_forward':True,
 'only_native_special_token_removal_and_outer_whitespace_strip_no_explanatory_text_extraction':True,
 'not_an_action_only_constraint_or_new_prompt':True,'no_trajectory_zero_Mirage_or_efficacy_claim':True},ensure_ascii=False))
'''


def main():
    pointer = HERE / 'actor-output-fidelity-audit-created.json'
    assert not pointer.exists()
    roots = ['full-history-gui-development-20261109-23',
             'memory-scheduled-full-history-gui-20261109-29', HERE.name]
    items, authorities, seen = [], [], set()
    for name in roots:
        for receipt in sorted((BASE / name / 'source-first-packets').glob('*/collection.json')):
            collection = receipt.parent
            data = json.loads(receipt.read_bytes())
            private = {row['id']: row for row in json.loads((collection / 'PRIVATE-source-index.json').read_bytes())}
            seal = json.loads((collection / 'seal.json').read_bytes())
            for filename in ['collection.json', 'PRIVATE-source-index.json']:
                assert sha(collection / filename) == seal[filename]
            for record in data['packets']:
                packet_path = collection / record['id'] / 'packet.json'
                assert sha(packet_path) == record['packet_sha256'] == seal[record['id'] + '/packet.json']
                packet = json.loads(packet_path.read_bytes())
                assert packet['candidate_event_sha256'] not in seen
                seen.add(packet['candidate_event_sha256'])
                items.append(dict(private[record['id']], candidate=packet['candidate'],
                                  candidate_event_sha256=packet['candidate_event_sha256']))
            authorities.append({'path': str(receipt), 'sha256': sha(receipt)})
    assert len(items) == 19
    package = HERE / 'runtime-package'
    manifest = json.loads((package / 'manifest.json').read_bytes())
    sources = {}
    for name in ['gpu_server.py', 'model_runtime.py', 'release/defense/qwen_backend.py']:
        assert sha(package / name) == manifest['files'][name]
        ast.parse((package / name).read_text(encoding='utf8'))
        sources[name] = sha(package / name)
    prefix = 'ITEMS=' + repr(items) + '\nALLOWED_ROOTS=' + repr(roots) + '\n'
    output, operation = remote('3090', prefix + CODE, 'native-actor-IDs-text-fidelity19-no-inference', timeout=55)
    result = json.loads(output)
    result.update(schema='nineteen-source-bound-native-actor-text-measurement-fidelity-v1',
                  source_collections=authorities, reviewed_frozen_runtime_sources_SHA256=sources,
                  remote_operation=str(operation),
                  limitation='Single continuing task prefix, all19currently action-only; no completed matched trajectory or Mirage reduction. Historical instructions/examples and non-thinking configuration can affect natural response style. No prompt or output was changed to add or suppress narration.')
    out = HERE / ('actor-output-fidelity-audit-' + str(time.time_ns()))
    out.mkdir()
    save(out / 'audit.json', result)
    save(out / 'seal.json', {'audit.json': sha(out / 'audit.json')})
    save(pointer, {'audit': str(out / 'audit.json'), 'audit_sha256': sha(out / 'audit.json'),
                   'seal_sha256': sha(out / 'seal.json')})
    print(json.dumps({'audit': str(out / 'audit.json'), 'passed': result['passed'],
                      'source_bound_actor_replies': len(result['rows']), 'new_model_or_GUI_calls': 0}))


if __name__ == '__main__':
    main()
