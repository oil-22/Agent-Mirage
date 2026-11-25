"""Finite foreground-turn read-only watch of one formal outcome; no automation."""
import json,time,sys
from pathlib import Path
from remote import remote
sys.stdout.reconfigure(encoding='utf-8')
r=Path(__file__).resolve().parent
receipt=r/'v3.6.2-vwa-resume.json'
if not receipt.exists():receipt=r/'v3-vwa-launch.json'
launch=json.loads(receipt.read_text())
target='vwa--classifieds_112--clean--post_only'
code='''import pathlib,json,time,hashlib
root=pathlib.Path(ROOT);run=root/'runs'/TARGET;state=json.loads((root/'status.json').read_text());marker=run/'complete.json'
done=None
if marker.exists():
 pointer=json.loads(marker.read_text());p=pathlib.Path(pointer['attempt'])/'complete.json';assert hashlib.sha256(p.read_bytes()).hexdigest()==pointer['sha256'];done=json.loads(p.read_text())
attempts=sorted(run.glob('attempt-*'))
if not marker.exists()and (not attempts or(state['phase']=='waiting_model_preflight'and not state.get('attempt'))):
 print(json.dumps({'time':time.time(),'batch_phase':state['phase'],'attempt':None,'event_seq':-1,'event_kind':'waiting_attempt','event_age':None,'counts':{},'candidate':{},'done':None,'technical_failure':False}));raise SystemExit
attempt=pathlib.Path(json.loads(marker.read_text())['attempt'])if marker.exists()else attempts[-1]
events=[]
for line in(attempt/'events.jsonl').read_text().splitlines():
 try:events.append(json.loads(line))
 except json.JSONDecodeError:pass
candidate=next((e['data']for e in reversed(events)if e['kind']=='candidate'),{})
keep=['candidate','action_executed','verifier_request','verifier_raw','verifier_format_failure','state_invalidated','recapture_requested','target_alignment']
counts={k:sum(e['kind']==k for e in events)for k in keep}
print(json.dumps({'time':time.time(),'batch_phase':state['phase'],'attempt':str(attempt),'event_seq':events[-1]['seq']if events else-1,'event_kind':events[-1]['kind']if events else'waiting_events','event_age':round(time.time()-events[-1]['time'])if events else None,'counts':counts,'candidate':candidate,'done':done,'technical_failure':(attempt/'failure.json').exists()or(attempt/'technical-failure.json').exists()}))
'''.replace('ROOT',repr(launch['root'])).replace('TARGET',repr(target))
deadline=time.time()+90*60;previous=None
while time.time()<deadline:
    data=json.loads(remote(code,host='4090'))
    (r/'v3-foreground-watch-latest.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    key=(data['event_seq'],data['batch_phase'])
    if key!=previous:
        output={**data,'candidate':data['candidate'].get('text',''),'done':{k:data['done'].get(k)for k in ['outcome','official_reward','scoring_status','actor_calls','verifier_calls','environment_actions','blocked_reason']}if data['done']else None}
        print(json.dumps(output,ensure_ascii=False),flush=True);previous=key
    if data['done']or data['technical_failure']or data['batch_phase']not in {'running','completed','waiting_model_preflight'}:break
    time.sleep(20)
else:print(json.dumps({'watch_timeout':True,'remote_worker_unchanged':True}),flush=True)
