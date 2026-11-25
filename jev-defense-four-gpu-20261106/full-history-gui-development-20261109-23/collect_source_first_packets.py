"""Read actual GUI candidates and full lawful inputs before outcome/score joins.

No model requests, browser interaction, queue changes, or private scorer reads.
Collections are immutable and incremental by the original candidate event hash.
"""
import argparse
import ast
import base64
import copy
import hashlib
import json
from pathlib import Path
import time

from remote_control import HERE, ROOT3090, ROOT4090, remote, save, sha


GUI_SOURCE = r'''
import ast,base64,hashlib,json,re,time
from pathlib import Path
def h(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
r=Path(ROOT);packets=[];private=[];snapshots=[];all_candidates=0
native=Path('/data/researcher/jev-defense-validation-20261103/runtime-stage-01/native/run_reddit_internvl_smoke.py')
source=native.read_bytes();tree=ast.parse(source.decode())
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='parse')
assert h(ast.dump(node,include_attributes=False).encode())==PARSER_AST_SHA
ns={'json':json,'re':re};exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-native-parser-extraction','exec'),ns)
for a in sorted((r/'batch/runs').glob('*/attempt-*')):
 p=a/'events.jsonl'
 if not p.is_file():continue
 raw=p.read_bytes();complete=raw[:raw.rfind(b'\n')+1];events=[];previous='0'*64
 for line in complete.splitlines():
  v=json.loads(line);sig=v.pop('sha256')
  assert v['seq']==len(events)and v['previous']==previous and h(canonical(v))==sig
  v['sha256']=sig;events.append(v);previous=sig
 snap={'event_count':len(events),'chain_head':previous,'complete_prefix_bytes':len(complete),'complete_prefix_sha256':h(complete)}
 snapshots.append(dict(snap,attempt=str(a)))
 observation={};wire=None;actor_context=None;response=None;raw_response=None
 for e in events:
  kind=e['kind']
  if kind=='observation':observation[e['data']['public']['observation_id']]=e
  if kind=='actor_request':actor_context=e
  if kind=='actual_actor_wire_request':wire=e;response=None;raw_response=None
  if kind=='actual_actor_wire_raw_response':raw_response=e
  if kind=='actual_actor_wire_response':response=e
  if kind!='candidate':continue
  all_candidates+=1
  if e['sha256']in EXCLUDE or len(packets)>=MAX_NEW:continue
  assert wire is not None and response is not None and raw_response is not None and actor_context is not None
  body=wire['data']['body'];payload=body['payload'];actor=payload['body'];public=actor_context['data']['public']
  assert payload['operation']=='actor'and public['observation_id']==e['data']['observation_id']
  assert h(canonical(body))==wire['data']['wire_sha256']
  value=response['data']['body'];response_raw=base64.b64decode(raw_response['data']['raw_base64'],validate=True)
  assert raw_response['data']['http_status']==200 and h(response_raw)==raw_response['data']['raw_sha256']
  assert json.loads(response_raw)==value and value['text']==e['data']['text']
  assert value['request_id']==body['request_id']and value['external_wire_sha256']==wire['data']['wire_sha256']
  assert value['payload_sha256']==h(canonical(payload))
  images=[]
  for mi,message in enumerate(actor['messages']):
   if not isinstance(message.get('content'),list):continue
   for bi,block in enumerate(message['content']):
    if block.get('type')!='image_url':continue
    url=block['image_url']['url'];assert url.startswith('data:image/png;base64,')
    image=base64.b64decode(url.split(',',1)[1],validate=True);image_sha=h(image)
    assert (a/(image_sha+'.image')).read_bytes()==image
    images.append({'message_index':mi,'block_index':bi,'sha256':image_sha,'raw_base64':base64.b64encode(image).decode()})
  current=[]
  for im in public['images']:
   image=(a/(im['sha256']+'.image')).read_bytes();assert h(image)==im['sha256']
   assert im['sha256']in {row['sha256']for row in images}
   current.append(im)
  try:parsed={'payload':ns['parse'](e['data']['text']),'error':None}
  except (ValueError,TypeError,SyntaxError)as exc:parsed={'payload':None,'error':{'type':type(exc).__name__,'message':str(exc)}}
  packet={'schema':'actual-complete-history-source-first-candidate-v1','id':e['sha256'][:20],
   'candidate':e['data']['text'],'candidate_event_sha256':e['sha256'],'candidate_text_sha256':h(e['data']['text'].encode()),
   'actual_actor_request':actor,'actor_request_body_sha256':h(canonical(actor)),
   'actor_wire_event_sha256':wire['sha256'],'actual_actor_wire_sha256':wire['data']['wire_sha256'],
   'actor_reply_event_sha256':response['sha256'],'actor_raw_reply_event_sha256':raw_response['sha256'],
   'observation_id':public['observation_id'],'recent_action':public['recent_action'],'execution_feedback':public['execution_feedback'],
   'actor_context_event_sha256':actor_context['sha256'],'current_and_reference_image_inventory':current,
   'actual_delivered_images':images,'snapshot':snap,'native_parser_result':parsed,
   'native_parse_scope':'Original parse function only; this is not executor validation or action execution',
   'native_parser_file_sha256':h(source),'native_parser_AST_sha256':PARSER_AST_SHA,
   'checker_labels_current_acceptance_execution_scoring_private_delivery_excluded':True,
   'lawful_prior_feedback_and_auxiliary_text_in_actual_main_history_retained':True,
   'blinding_limit':'Historical corrections/auxiliary text may reveal prior decisions or arm; not fully blind'}
  packets.append(packet)
  private.append({'id':packet['id'],'attempt':str(a),'candidate_seq':e['seq'],'request_id':body['request_id'],
    'service_receipt':value['receipt'],'actual_actor_wire_sha256':wire['data']['wire_sha256'],
    'candidate_text_sha256':packet['candidate_text_sha256'],'actor_request_body_sha256':packet['actor_request_body_sha256']})
print(json.dumps({'public_packets':packets,'PRIVATE_source_index':private,'PRIVATE_snapshots':snapshots,
 'all_candidates_at_snapshot':all_candidates,'new_model_GUI_scorer_calls':0},ensure_ascii=False))
'''


SERVICE_SOURCE = r'''
import hashlib,json
from pathlib import Path
def h(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def sha(path):return h(Path(path).read_bytes())
r=Path(ROOT).resolve();results=[]
for row in ROWS:
 p=Path(row['service_receipt']).resolve();assert p.parent==r/'worker/requests'
 seal=json.loads((p/'seal.json').read_bytes())
 for name,expected in seal.items():assert Path(name).name==name and sha(p/name)==expected,(str(p),name)
 wire=(p/'external-wire.json').read_bytes();body=json.loads(wire);reply=json.loads((p/'response.json').read_bytes())
 assert h(wire)==row['actual_actor_wire_sha256']and body['request_id']==row['request_id']==reply['request_id']
 assert h(canonical(body['payload']['body']))==row['actor_request_body_sha256']
 assert h(reply['text'].encode())==row['candidate_text_sha256']
 prepared=json.loads((p/'prepared.json').read_bytes());forward=json.loads((p/'first-forward.json').read_bytes())
 assert set(prepared)==set(forward)
 for key in prepared:
  assert all(prepared[key][field]==forward[key][field]for field in ['shape','dtype','bytes','sha256'])
  for item in [prepared[key],forward[key]]:assert seal[item['file']]==item['sha256']
 actual=json.loads((p/'actual-generation.json').read_bytes());generation=json.loads((p/'effective-generation.json').read_bytes())
 eos=generation['eos_token_id'];eos=[eos]if isinstance(eos,int)else eos
 assert generation['max_new_tokens']==2048 and actual['natural_EOS']and actual['output_ids'][-1]in eos
 assert actual['input_tokens']==prepared['input_ids']['shape'][1]
 assert len(actual['output_ids'])==actual['output_tokens']==actual['actual_forward_calls']
 native=json.loads((p/'native-call.json').read_bytes())
 assert native['text']==reply['text']and native['generated_ids']==actual['output_ids']
 assert native['request_messages_sha256']==h(canonical(body['payload']['body']['messages']))
 results.append({'id':row['id'],'request_id':row['request_id'],'seal_sha256':sha(p/'seal.json'),
   'original_request_reply_and_full_tensor_files_verified':len(seal),'actual_full_request_messages_bound':True,
   'prepared_first_forward_binary_SHA_equal':True,'natural_EOS':True,'input_tokens':actual['input_tokens'],
   'output_tokens':actual['output_tokens'],'max_new_tokens':generation['max_new_tokens']})
print(json.dumps({'read_only':True,'actor_cross_host_bindings':results,'new_model_GUI_scorer_calls':0}))
'''


def main(max_new):
    parent = HERE / 'source-first-packets'
    excluded = set()
    if parent.exists():
        for receipt in parent.glob('*/collection.json'):
            record = json.loads(receipt.read_bytes())
            excluded.update(row['candidate_event_sha256'] for row in record['packets'])
    original_parser = HERE.parent / 'complete-history-main-preflight-20261109-22/runtime-package/native-parser-source.py'
    tree = ast.parse(original_parser.read_text(encoding='utf8'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'parse')
    parser_hash = hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()
    root = parent / str(time.time_ns())
    root.mkdir(parents=True, exist_ok=False)
    try:
        prefix = 'ROOT=' + repr(ROOT4090) + '\nEXCLUDE=' + repr(excluded) + '\nMAX_NEW=' + repr(max_new) + '\nPARSER_AST_SHA=' + repr(parser_hash) + '\n'
        output, operation = remote('4090', prefix + GUI_SOURCE, 'source-first-full-main-history-no-current-outcomes', timeout=55)
        data = json.loads(output)
        save(root / 'PRIVATE-source-index.json', data['PRIVATE_source_index'])
        save(root / 'PRIVATE-snapshot-index.json', data['PRIVATE_snapshots'])
        rows = []
        for packet in data['public_packets']:
            target = root / packet['id']
            target.mkdir()
            save(target / 'packet.json', packet)
            rendered = copy.deepcopy(packet)
            for i, image in enumerate(packet['actual_delivered_images']):
                name = 'image-%02d.png' % i
                (target / name).write_bytes(base64.b64decode(image['raw_base64'], validate=True))
                assert sha(target / name) == image['sha256']
                block = rendered['actual_actor_request']['messages'][image['message_index']]['content'][image['block_index']]
                block['image_url'] = {'original_local_file': name, 'sha256': image['sha256']}
                rendered['actual_delivered_images'][i] = {k: v for k, v in image.items() if k != 'raw_base64'}
                rendered['actual_delivered_images'][i]['original_local_file'] = name
            rendered['rendering_notice'] = 'Only image data URLs replaced with local references for reading; exact original body remains packet.json'
            save(target / 'review-text.json', rendered)
            save(target / 'seal.json', {p.name: sha(p) for p in target.iterdir() if p.is_file()})
            rows.append({'id': packet['id'], 'candidate_event_sha256': packet['candidate_event_sha256'],
                         'packet_sha256': sha(target / 'packet.json'), 'images': len(packet['actual_delivered_images'])})
        service_prefix = 'ROOT=' + repr(ROOT3090) + '\nROWS=' + repr(data['PRIVATE_source_index']) + '\n'
        output2, operation2 = remote('3090', service_prefix + SERVICE_SOURCE, 'source-first-actor-cross-host-native-tensors-no-judge-labels', timeout=55)
        service = json.loads(output2)
        assert len(service['actor_cross_host_bindings']) == len(rows)
        save(root / 'actor-service-bindings.json', service)
        save(root / 'collection.json', {'schema': 'complete-main-history-source-first-collection-v1', 'time': time.time(),
             'public_packets': len(rows), 'packets': rows, 'all_candidates_at_snapshot': data['all_candidates_at_snapshot'],
             'earlier_exported_candidates': len(excluded), 'GUI_operation': str(operation), 'service_operation': str(operation2),
             'exact_full_history_image_bytes_and_service_forward_verified': True,
             'current_outcome_execution_detector_scorer_injection_labels_in_packets': False,
             'legal_prior_feedback_in_actual_history_retained': True, 'fully_blind_or_independent_human_review': False,
             'new_model_GUI_scorer_paid_calls': 0})
        save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file()})
        print(json.dumps({'collection': str(root), 'receipt_sha256': sha(root / 'collection.json'),
              'new_packets': len(rows), 'all_candidates_at_snapshot': data['all_candidates_at_snapshot'],
              'candidates': [{'id': p['id'], 'text': p['candidate'], 'images': len(p['actual_delivered_images'])} for p in data['public_packets']]}, ensure_ascii=False))
    except BaseException as exc:
        save(root / 'collection-failure.json', {'type': type(exc).__name__, 'message': str(exc),
             'previous_exports_and_operations_preserved': True, 'new_model_GUI_scorer_calls': 0})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-new', type=int, default=20)
    args = parser.parse_args()
    assert 1 <= args.max_new <= 70
    main(args.max_new)
