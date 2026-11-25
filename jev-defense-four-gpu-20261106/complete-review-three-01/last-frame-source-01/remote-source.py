
import base64,hashlib,json,struct
from pathlib import Path
p=Path('/data/researcher/jev-defense-four-gpu-20261106/gui-batch-image-observer-three-01/runs/image-observer-v1--classifieds_112--clean--joint--observer/attempt-1793987248242098761')
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha((p/'technical-failure.json').read_bytes())=='66d18d91d05e635d58363a54b9a26aa78bcfde06bcd6edeb66f4c86b1e52f01a'
public=native=candidate=None
for line in(p/'events.jsonl').read_bytes().splitlines():
 r=json.loads(line)
 if r['kind']=='actor_request':public=r
 if r['kind']=='actor_observer_native_payload':native=r
 if r['kind']=='candidate':candidate=(r,public,native)
r,public,native=candidate
for row in(r,public,native):assert sha(json.dumps({k:v for k,v in row.items()if k!='sha256'},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())==row['sha256']
v=native['data'];m=v['body']['body']['messages'][v['current_user_message_index']]
blocks=[b for b in m['content']if b['type']=='image_url'];assert len(blocks)==1
url=blocks[0]['image_url']['url'];assert url.startswith('data:image/png;base64,')
raw=base64.b64decode(url.split(',',1)[1],validate=True)
declared=[im for im in public['data']['public']['images']if im['role']=='current'];assert len(declared)==1 and declared[0]['sha256']==sha(raw)
print(json.dumps({'candidate':r['data'],'candidate_event_sha256':r['sha256'],'native_event_sha256':native['sha256'],'public_event_sha256':public['sha256'],'image_sha256':sha(raw),'size':list(struct.unpack('>II',raw[16:24])),'image_base64':base64.b64encode(raw).decode(),'no_new_model_GUI_health_scorer_calls':True}))
