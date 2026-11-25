"""Snapshot completed independent outcomes and actual last-decision inputs, read only."""
import base64,json,time
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;x=json.loads((r/'v3.9.9-scroll-validation-resume.json').read_bytes())
code=r'''
import pathlib,json,hashlib,base64,collections,time
root=pathlib.Path(X['root']);rows=[];images={}
for p in sorted((root/'runs').glob('*/complete.json')):
 pointer=json.loads(p.read_bytes());a=pathlib.Path(pointer['attempt']);raw=(a/'complete.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==pointer['sha256']
 events=[json.loads(l)for l in(a/'events.jsonl').read_text().splitlines()]
 last_observations=[]
 for e in events:
  if e['kind']=='observation'and e['data'].get('audience','actor')=='actor':last_observations.append(e['data']['public']['observation_id'])
 tail_ids=list(dict.fromkeys(last_observations))[-4:];selected=[]
 up_sequences=[e['seq']for e in events if e['kind']=='action_executed'and e['data'].get('proposal',{}).get('payload',{}).get('direction')=='up']
 for e in events:
  d=e['data'];pub=d.get('public',{});oid=pub.get('observation_id',d.get('observation_id'))
  if oid in tail_ids or e['seq']>=events[-1]['seq']-16 or any(abs(e['seq']-s)<=16 for s in up_sequences):
   selected.append(e)
   for im in pub.get('images',[]):
    f=a/(im['sha256']+'.image')
    if f.exists():images[im['sha256']]=base64.b64encode(f.read_bytes()).decode()
 final=a/'final-actually-captured.png'
 if final.exists():images[hashlib.sha256(final.read_bytes()).hexdigest()]=base64.b64encode(final.read_bytes()).decode()
 rows.append({'run':p.parent.name,'attempt':str(a),'pointer_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'terminal_sha256':pointer['sha256'],'complete':json.loads(raw),'events_sha256':hashlib.sha256((a/'events.jsonl').read_bytes()).hexdigest(),'counts':dict(collections.Counter(e['kind']for e in events)),'late_events':selected,'final_image_sha256':hashlib.sha256(final.read_bytes()).hexdigest()if final.exists()else None,'all_point_recovery_events':[e for e in events if e['kind']=='point_evidence_unavailable'],'all_native_actions':[e for e in events if e['kind']=='action_executed'],'all_candidates':[e for e in events if e['kind']=='candidate']})
print(json.dumps({'time':time.time(),'state':json.loads((root/'status.json').read_bytes()),'rows':rows,'images':images}))
'''
d=json.loads(remote('X='+repr(x)+'\n'+code,host='4090',timeout=50));dest=r/'scroll-validation-outcomes'/str(time.time_ns());dest.mkdir(parents=True)
for sha,raw in d.pop('images').items():(dest/(sha+'.png')).write_bytes(base64.b64decode(raw))
(dest/'evidence.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
(r/'scroll-validation-outcomes-current.json').write_text(json.dumps({'folder':str(dest),'snapshot_time':d['time']},indent=2),encoding='utf8')
for row in d['rows']:
 print(json.dumps({'run':row['run'],'terminal':{k:row['complete'].get(k)for k in ['outcome','blocked_reason','official_reward','technical_status','environment_actions','actor_calls','verifier_calls']},'recovery_events':row['all_point_recovery_events'],'late':[e for e in row['late_events']if e['kind']in ['screen_result','verifier_raw','candidate','decision_blocked']],'final_image':str(dest/(row['final_image_sha256']+'.png'))},ensure_ascii=True))
print(json.dumps({'local_folder':str(dest),'state':d['state']}))
