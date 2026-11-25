"""Prepare legal-input review packets; no detector outputs, labels, scores or hidden images."""
import base64,hashlib,io,json,time,zipfile
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;launch=json.loads((r/'v3.9.6-vwa-resume.json').read_text())
code=r'''
import base64,hashlib,io,json,pathlib,time,zipfile,collections
root=pathlib.Path(ROOT);buffer=io.BytesIO();seen=set();index=[];total=0
with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED,compresslevel=3)as z:
 for marker in sorted((root/'runs').glob('*/complete.json')):
  pointer=json.loads(marker.read_text());p=pathlib.Path(pointer['attempt']);complete=(p/'complete.json').read_bytes()
  assert hashlib.sha256(complete).hexdigest()==pointer['sha256']
  eraw=(p/'events.jsonl').read_bytes();events=[json.loads(l)for l in eraw.splitlines()]
  ident=hashlib.sha256(str(p).encode()).hexdigest()[:20];packets=[];last_req=None
  for event in events:
   if event['kind']=='actor_request':last_req=event
   if event['kind']!='candidate':continue
   assert last_req and last_req['seq']<event['seq'];pub=last_req['data']['public']
   assert pub['observation_id']==event['data']['observation_id']
   n=len(packets)+1;name='packets/'+ident+'/'+str(n).zfill(3)+'.json'
   packet={'public':pub,'candidate':event['data']['text']}
   z.writestr(name,json.dumps(packet,ensure_ascii=False,indent=2))
   for image in pub['images']:
    sha=image['sha256'];source=p/(sha+'.image');data=source.read_bytes();assert hashlib.sha256(data).hexdigest()==sha
    if sha not in seen:z.writestr('images/'+sha+'.png',data);seen.add(sha)
   following=next((e for e in events if e['seq']>event['seq']and e['kind']=='candidate'),None)
   until=following['seq']if following else float('inf')
   accepted=next((e for e in events if event['seq']<e['seq']<until and e['kind']=='decision_accepted'and e['data']['observation_id']==pub['observation_id']),None)
   executed=next((e for e in events if event['seq']<e['seq']<until and e['kind']=='action_executed'and e['data']['observation_id']==pub['observation_id']),None)
   packets.append({'packet':name,'packet_sha256':hashlib.sha256(json.dumps(packet,ensure_ascii=False,indent=2).encode()).hexdigest(),'source_request_seq':last_req['seq'],'source_candidate_seq':event['seq'],'source_candidate_sha256':event['sha256'],'accepted':bool(accepted),'environment_action_executed':bool(executed),'semantic_mirage':None})
  total+=len(packets)
  index.append({'opaque_id':ident,'run_id':marker.parent.name,'attempt':str(p),'complete_sha256':pointer['sha256'],'events_sha256':hashlib.sha256(eraw).hexdigest(),'candidates':packets})
 assert len(index)==20
 z.writestr('PRIVATE-source-and-execution-index.json',json.dumps(index,ensure_ascii=False,indent=2))
 z.writestr('README.md','# Review packets\n\nEach packets/<opaque>/<ordinal>.json contains only the exact lawful actor public input and candidate, without official reward, injection condition or detector verdict. Images are byte-identical actual images in that public input; resolve their SHA via images/<SHA>.png. Full original legal text history, including received defense corrections, is preserved. Do not infer a visual fact from an assistant narrative alone.\n\nPRIVATE-source-and-execution-index.json is evaluation provenance, not verifier input. Packet paths conceal source condition but legal histories may reveal feedback; this is not guaranteed blind evaluation. No semantic labels have been assigned. Pure native WAIT is excluded; later recovery does not erase first occurrence. Separate candidate-first error from accepted/executed error and task recovery. STOP is accepted without an environment action.\n')
print(json.dumps({'time':time.time(),'configurations':len(index),'candidates':total,'unique_delivered_images':len(seen),'zip_sha256':hashlib.sha256(buffer.getvalue()).hexdigest(),'zip_base64':base64.b64encode(buffer.getvalue()).decode()}))
'''
d=json.loads(remote(code.replace('ROOT',repr(launch['root'])),host='4090',timeout=180));raw=base64.b64decode(d.pop('zip_base64'));assert hashlib.sha256(raw).hexdigest()==d['zip_sha256']
dest=r/'semantic-review-packets'/str(time.time_ns());dest.mkdir(parents=True)
(dest/'packets.zip').write_bytes(raw)
with zipfile.ZipFile(io.BytesIO(raw))as z:
 for name in z.namelist():
  target=(dest/name).resolve();assert target.is_relative_to(dest.resolve());target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(name))
d.update(directory=str(dest),semantic_labels_assigned=0,model_calls=0,gui_actions=0)
(dest/'manifest.json').write_text(json.dumps(d,indent=2));(r/'semantic-review-packets-current.json').write_text(json.dumps(d,indent=2));print(json.dumps(d))
