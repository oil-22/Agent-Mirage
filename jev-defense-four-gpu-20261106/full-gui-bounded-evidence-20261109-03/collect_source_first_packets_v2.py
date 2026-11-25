"""Public lawful candidate packets, excluding checker outcomes/private joins."""
import base64
import json
import time
from remote_control import HERE,ROOT4090,remote,save,sha

code='ROOT='+repr(ROOT4090)+'\n'+r'''
from pathlib import Path
import base64,hashlib,json,time
r=Path(ROOT);packets=[];private=[];h=lambda b:hashlib.sha256(b).hexdigest()
for a in sorted((r/'batch/runs').glob('*/attempt-*')):
 p=a/'events.jsonl'
 if not p.exists():continue
 raw=p.read_bytes();lines=raw.splitlines()
 if not raw.endswith(b'\n'):lines=lines[:-1]
 events=[];previous='0'*64
 for line in lines:
  v=json.loads(line);sig=v.pop('sha256');assert v['seq']==len(events)and v['previous']==previous
  assert h(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())==sig
  v['sha256']=sig;events.append(v);previous=sig
 observation={};wire=None;actor_context=None
 for e in events:
  if e['kind']=='observation':observation[e['data']['public']['observation_id']]=e
  if e['kind']=='actor_request':actor_context=e
  if e['kind']=='actual_actor_wire_request':wire=e
  if e['kind']!='candidate':continue
  assert wire is not None
  identity=h((a.parent.name+':'+str(e['seq'])).encode())[:20]
  obs=observation[e['data']['observation_id']]
  assert actor_context is not None and actor_context['data']['public']['observation_id']==e['data']['observation_id']
  actor_public=actor_context['data']['public']
  body=wire['data']['body'];payload=body['payload'];assert payload['operation']=='actor'
  actor=payload['body'];images=[]
  for m in actor['messages']:
   if not isinstance(m.get('content'),list):continue
   for b in m['content']:
    if b.get('type')!='image_url':continue
    url=b['image_url']['url'];assert url.startswith('data:image/png;base64,')
    raw_image=base64.b64decode(url.split(',',1)[1]);images.append({'sha256':h(raw_image),'raw_base64':base64.b64encode(raw_image).decode()})
  packet={'id':identity,'candidate':e['data']['text'],'candidate_event_sha256':e['sha256'],
    'candidate_text_sha256':h(e['data']['text'].encode()),'actual_actor_request':actor,
    'actor_wire_event_sha256':wire['sha256'],'actual_actor_wire_sha256':wire['data']['wire_sha256'],
    'observation_id':actor_public['observation_id'],'recent_action':actor_public['recent_action'],
    'execution_feedback':actor_public['execution_feedback'],'actor_context_event_sha256':actor_context['sha256'],
    'context_metadata_source':'actual actor_request, never preceding scene-only checker projection','actual_delivered_images':images,
    'checker_labels_private_delivery_execution_scorer_excluded':True,
    'snapshot_event_chain_head':previous,'snapshot_events':len(events)}
  packets.append(packet);private.append({'id':identity,'attempt':str(a),'candidate_seq':e['seq']})
print(json.dumps({'public_packets':packets,'PRIVATE_source_index_not_label_input':private,'model_GUI_scorer_calls':0}))
'''
out,operation=remote('4090',code,'source-first-candidate-public-export-v2-actual-actor-context',timeout=60)
data=json.loads(out);root=HERE/'source-first-packets'/str(time.time_ns());root.mkdir(parents=True)
for packet in data['public_packets']:
    target=root/packet['id'];target.mkdir()
    save(target/'packet.json',packet)
    for i,row in enumerate(packet['actual_delivered_images']):
        p=target/('image-%02d.png'%i);p.write_bytes(base64.b64decode(row['raw_base64']));assert sha(p)==row['sha256']
    save(target/'seal.json',{p.name:sha(p)for p in target.iterdir()if p.is_file()})
save(root/'PRIVATE-source-index.json',data['PRIVATE_source_index_not_label_input'])
save(root/'collection.json',{'operation':str(operation),'public_packets':len(data['public_packets']),
    'no_private_execution_or_injection_labels_in_packets':True,'models_GUI_calls':0})
print(json.dumps({'root':str(root),'packets':len(data['public_packets']),
    'candidates':[{'id':p['id'],'candidate':p['candidate'],'images':len(p['actual_delivered_images'])}for p in data['public_packets']]},ensure_ascii=False))
