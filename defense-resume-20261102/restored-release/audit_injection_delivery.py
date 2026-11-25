"""Read-only delivery/reply accounting, separate from semantic Mirage labels."""
import argparse,json
from pathlib import Path
from remote import remote
p=argparse.ArgumentParser();p.add_argument('--receipt',default='v3.4.1-vwa-resume.json');a=p.parse_args()
here=Path(__file__).resolve().parent;launch=json.loads((here/a.receipt).read_text())
code=r'''
import pathlib,json,hashlib,time
root=pathlib.Path(ROOT);rows=[]
for run in sorted((root/'runs').iterdir()):
 attempts=sorted(run.glob('attempt-*'));marker=run/'complete.json';pointer=None
 if marker.exists():
  pointer=json.loads(marker.read_text());bound=pathlib.Path(pointer['attempt'])
  assert hashlib.sha256((bound/'complete.json').read_bytes()).hexdigest()==pointer['sha256']
  if bound not in attempts:attempts.append(bound)
 for attempt in attempts:
  events=[]
  for line in(attempt/'events.jsonl').read_bytes().splitlines():
   try:events.append(json.loads(line))
   except json.JSONDecodeError:pass
  injections=[]
  for event in events:
   if event['kind']!='private_delivery_ledger'or not event['data']['fired']:continue
   step=event['data']['step'];prefix=f'{step:03}-'
   initial=next((e['data']['public']['observation_id']for e in events if e['seq']>event['seq']and e['kind']=='observation'and e['data'].get('audience','actor')=='actor'and e['data']['public']['observation_id'].startswith(prefix)),None)
   requests=[e for e in events if e['kind']=='actor_request'and e['data']['public']['observation_id']==initial]
   replies=[e for e in events if e['kind']=='candidate'and e['data']['observation_id']==initial]
   wait=0
   for reply in replies:
    try:
     text=reply['data']['text'];action=json.loads(text.split('<action>')[1].split('</action>')[0]);wait+=action.get('type')in {'wait','noop'}
    except(ValueError,IndexError,TypeError):pass
   injections.append({'step':step,'initial_observation':initial,'injection_prepared':True,'actor_requests_on_injected_observation':len(requests),'actual_actor_replies_on_injected_observation':len(replies),'native_wait_replies':wait,'semantic_mirage':None})
  done=json.loads((attempt/'complete.json').read_text())if(attempt/'complete.json').exists()else None
  rows.append({'run':run.name,'attempt':str(attempt),'selected_completed_attempt':bool(pointer and str(attempt)==pointer['attempt']),'outcome':done.get('outcome')if done else None,'injections':injections,'paused':(attempt/'paused.json').exists(),'technical_failure':(attempt/'technical-failure.json').exists()or(attempt/'failure.json').exists(),'semantic_mirage':None})
print(json.dumps({'time':time.time(),'root':str(root),'rows':rows,'scope':'delivery and actual-reply accounting only; no detector or infrastructure state is used as a Mirage truth label'},ensure_ascii=False))
'''.replace('ROOT',repr(launch['root']))
data=json.loads(remote(code,host='4090'));out=here/'latest-injection-delivery-audit.json'
out.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(data,ensure_ascii=False))
