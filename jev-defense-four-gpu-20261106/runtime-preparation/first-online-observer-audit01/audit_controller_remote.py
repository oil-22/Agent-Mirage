"""First auxiliary packet engineering chain only; no PRIVATE payload/export/execution join."""
import ast,base64,copy,hashlib,json,struct,time
from pathlib import Path

B=Path('/data/researcher/jev-defense-four-gpu-20261106')
G=B/'gui-batch-image-observer-three-01'
RUN='image-observer-v1--classifieds_112--clean--joint--observer'
attempts=list((G/'runs'/RUN).glob('attempt-*'));assert len(attempts)==1
attempt=attempts[0]
root=B/'first-online-observer-engineering'/str(time.time_ns());root.mkdir(parents=True,exist_ok=False)
sha=lambda raw:hashlib.sha256(raw).hexdigest()
canonical=lambda v:json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def save(name,value):
 p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x')as f:json.dump(value,f,indent=2)

for name,encoded in PUBLIC_SERVICE.items():
 p=root/'service'/name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb')as f:f.write(base64.b64decode(encoded))
service=root/'service';read=lambda p:json.loads(Path(p).read_bytes())
envelope=read(service/'observer-request/request.json');payload=envelope['payload'];response=read(service/'observer-request/response.json')
actor=read(service/'actor-request/request.json');source=read(service/'collection.json')
observer_source=B/'gui-migration-three-linked02/release/image_observer.py'
constants={}
for node in ast.parse(observer_source.read_text()).body:
 if isinstance(node,ast.Assign)and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)and node.targets[0].id in{'STATE','QUESTIONS','SHARED_ACTOR_INSTRUCTIONS'}:
  constants[node.targets[0].id]=ast.literal_eval(node.value)
STATE=constants['STATE'];QUESTIONS=constants['QUESTIONS'];SHARED_ACTOR_INSTRUCTIONS=constants['SHARED_ACTOR_INSTRUCTIONS']
wire=lambda value:json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()
assert payload['state']==STATE and payload['questions']==QUESTIONS and list(payload['questions'])==list(QUESTIONS)
assert set(payload)=={'request_id','image_base64','image_sha256','state','questions','provenance'}
assert set(payload['provenance'])=={'observation_id','image_sha256'}
image=base64.b64decode(payload['image_base64'],validate=True)
assert sha(image)==payload['image_sha256']==sha((service/'observer-request/original.image').read_bytes())
native=read(service/'observer-request/native-request.json')
assert native=={'state':STATE,'questions':QUESTIONS,'images_sha256':[sha(image)]}
native_result=read(service/'observer-request/native-result.json')
assert response['native_result']==native_result and response['answers']==native_result['answers']
trace=read(service/'observer-request/forward-trace.json')
prefills=[r['tensors']for r in trace if'input_ids'in r.get('tensors',{})];assert len(prefills)==1
tensors=prefills[0]
for name in('input_ids','image_grid_thw'):
 values=tensors[name]['values'];flat=[x for row in values for x in row]
 assert tensors[name]['dtype']=='torch.int64'and sha(struct.pack('<'+'q'*len(flat),*flat))==tensors[name]['sha256']
readout=next(r['raw_readout']for r in trace if'raw_readout'in r)
assert readout['shape']==[3,255]and readout['dtype']=='torch.bfloat16'
bf16=b''.join(struct.pack('<H',struct.unpack('<I',struct.pack('<f',value))[0]>>16)for row in readout['values']for value in row)
assert sha(bf16)==readout['sha256']
assert tensors['pixel_values']['shape']and tensors['pixel_values']['sha256']
assert response['forward_trace_sha256']==sha((service/'observer-request/forward-trace.json').read_bytes())
snapshot=(attempt/'events.jsonl').read_bytes();lines=snapshot.splitlines()
if not snapshot.endswith(b'\n'):lines=lines[:-1]
previous='0'*64;headers=[];public=[];actor_request=None;packet=None;native_actor=None;verifier=None
seen={'observer_wire':False,'observer_reply':False,'packet':False,'actor_wire':False,'actor_reply':False};judges=[]
response_canonical=sha(canonical(response));observer_wire=sha((service/'observer-request/request.json').read_bytes())
actor_wire=sha((service/'actor-request/request.json').read_bytes())
judge_wires={sha((p/'request.json').read_bytes()):read(p/'request.json')for p in(service/'judge-requests').iterdir()}
selected=[];last_actor_pending=False
for i,line in enumerate(lines):
 row=json.loads(line);assert row['seq']==i and row['previous']==previous
 previous=row['sha256'];headers.append({k:row[k]for k in('seq','previous','sha256','kind')})
 if row['kind'].startswith('private'):
  continue  # PRIVATE event values are neither inspected nor exported.
 content={k:v for k,v in row.items()if k!='sha256'};assert sha(canonical(content))==row['sha256']
 kind=row['kind'];d=row['data']
 if kind=='implementation':assert d['code_sha256']['image_observer.py']==sha(observer_source.read_bytes())
 if kind=='actor_request'and actor_request is None:actor_request=d;selected.append(row)
 elif kind=='actual_observer_wire'and sha(d['wire_utf8'].encode())==observer_wire:
  assert json.loads(d['wire_utf8'])==envelope;seen['observer_wire']=True;selected.append(row)
 elif kind=='actual_observer_wire_reply'and not seen['observer_reply']:
  raw=base64.b64decode(d['raw_base64']);assert sha(raw)==d['raw_sha256']and json.loads(raw)==response
  seen['observer_reply']=True;selected.append(row)
 elif kind=='actor_observer_response'and sha(canonical(d))==response_canonical:selected.append(row)
 elif kind=='actor_observer_packet'and not seen['packet']:
  packet=d;assert packet['status']=='measured'and packet['image_sha256']==payload['image_sha256']and packet['response_sha256']==response_canonical
  assert packet['observations']==[{'question':key,'model_prediction':response['answers'][key]['choice'],'probabilities':response['answers'][key]['probabilities']}for key in QUESTIONS]
  seen['packet']=True;selected.append(row)
 elif kind=='actor_observer_native_payload'and native_actor is None:
  native_actor=d;assert d['body']==actor['payload']and sha(d['wire_utf8'].encode())==d['wire_sha256']
  messages=copy.deepcopy(d['body']['body']['messages']);index=d['current_user_message_index'];block=messages[index]['content'].pop()
  assert block['text']==SHARED_ACTOR_INSTRUCTIONS+json.dumps(packet,ensure_ascii=False,separators=(',',':'))
  assert messages==actor_request['public']['messages']and sha(canonical(actor_request['public']))==d['original_public_sha256']
  current=[im for im in actor_request['public']['images']if im['role']=='current'];assert len(current)==1 and current[0]['sha256']==payload['image_sha256']
  assert payload['provenance']['observation_id']==actor_request['public']['observation_id'];selected.append(row)
 elif kind=='verifier_request':verifier=d
 elif kind=='actual_primary_wire_request':
  raw=d['wire_utf8'].encode();key=sha(raw)
  if key==actor_wire:
   assert json.loads(raw)==actor and actor['payload']==native_actor['body'];seen['actor_wire']=True;last_actor_pending=True;selected.append(row)
  elif key in judge_wires:
   body=judge_wires[key]['payload'];assert body['system']==verifier['system']and body['candidate']==verifier['candidate']
   view=body['view'];public_view=verifier['public']
   assert view['messages']==public_view['messages']
   assert SHARED_ACTOR_INSTRUCTIONS not in json.dumps({'system':body['system'],'messages':view['messages']},ensure_ascii=False)
   assert all(not(isinstance(m.get('content'),list)and any(b.get('type')=='text'and b.get('text','').startswith(SHARED_ACTOR_INSTRUCTIONS)for b in m['content']))for m in view['messages'])
   judges.append({'wire_sha256':key,'attempt_index':judge_wires[key]['attempt_index'],'original_verifier_event_sha256':row['sha256'],
    'original_public_messages_exact':True,'no_direct_observer_packet_added_to_judge':True})
   selected.extend([{'kind':'bound_original_verifier_request','data':verifier},row])
 elif kind=='actual_primary_wire_raw_response'and last_actor_pending:
  raw=base64.b64decode(d['raw_base64']);assert sha(raw)==d['raw_sha256']and json.loads(raw)==read(service/'actor-request/response.json')
  seen['actor_reply']=True;last_actor_pending=False;selected.append(row)
assert all(seen.values())and len(judges)==len(judge_wires)
save('public-selected-events.json',selected);save('event-chain-headers-only.json',headers)
save('bound-first-packet.json',packet);save('judge-direct-routing-checks.json',judges)
proof={'status':'passed_engineering_only','run_id':RUN,'first_decision':1,'observer_attempt_index':1,
 'first_auxiliary_only_original_image_fixed_state_three_questions_no_task_history_candidate':True,
 'full_actual_forward_IDs_grid_values_SHA_verified':True,'actual_pixel_tensor_shape_hash_bound':tensors['pixel_values'],
 'pixels_independently_reencoded_in_this_audit':False,'native_raw_BF16_readout_bytes_SHA_verified':True,
 'native_probability_dict_exact_saved_served_Controller_actor_packet':True,
 'native_softmax_not_recomputed_in_this_bounded_audit':True,'observer_packet_actually_in_completed_actor_wire':True,
 'original_full_actor_history_images_messages_preserved_except_appended_packet':True,
 'direct_observer_packet_not_added_to_original_judge_view_system':True,'sealed_decision1_judge_requests_checked':len(judges),
 'candidate_can_indirectly_reflect_actor_observations_not_claimed_blind':True,
 'observer_external_wire_sha256':observer_wire,'observer_response_canonical_sha256':response_canonical,
 'actor_external_wire_sha256':actor_wire,'input_tokens':len(tensors['input_ids']['values'][0]),
 'image_sha256':payload['image_sha256'],'controller_snapshot_prefix_events':len(headers),'controller_prefix_head':previous,
 'public_event_selfhash_checked_private_payloads_skipped':True,'private_event_values_neither_inspected_nor_exported':True,
 'model_health_GUI_POST_PRIVATE_file_reads':0,'pending_requests_not_read':True,'inference_locks_not_acquired':True,
 'semantic_labels_Mirage_or_success_claim':False,'source3090_collection':source}
save('receipt.json',proof)
save('seal.json',{str(p.relative_to(root)):sha(p.read_bytes())for p in root.rglob('*')if p.is_file()})
print(json.dumps({'receipt':str(root/'receipt.json'),'receipt_sha256':sha((root/'receipt.json').read_bytes()),
 'seal_sha256':sha((root/'seal.json').read_bytes()),'input_tokens':proof['input_tokens'],
 'observer_to_actor_actual':True,'judge_original_views_unchanged':len(judges),'model_health_GUI_POST_calls':0}))
