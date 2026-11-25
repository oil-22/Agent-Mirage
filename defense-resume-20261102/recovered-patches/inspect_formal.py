"""One-shot read-only inspection of the active formal repair batch.

Shows actual event counts instead of the worker's last-run step display.
Never sends evidence to inference or reads authentication material.
"""
import argparse
import json
from pathlib import Path
from remote import remote

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--compact', action='store_true')
parser.add_argument('--brief', action='store_true')
args = parser.parse_args()
receipt = HERE / 'v3.6.2-vwa-resume.json'
if not receipt.exists(): receipt = HERE / 'v3.4.1-vwa-resume.json'
if not receipt.exists(): receipt = HERE / 'v3-vwa-launch.json'
if not receipt.exists(): receipt = HERE / 'v2.9-vwa-resume.json'
if not receipt.exists(): receipt = HERE / 'v2-vwa-launch.json'
launch = json.loads(receipt.read_text())
code = r'''
import hashlib,json,pathlib,subprocess,time
root=pathlib.Path(ROOT)
state=json.loads((root/'status.json').read_text())
attempt=pathlib.Path(state['attempt'])
events=[]
for line in (attempt/'events.jsonl').read_text().splitlines():
    try: events.append(json.loads(line))
    except json.JSONDecodeError: pass
counts={kind:sum(e['kind']==kind for e in events) for kind in
    ['candidate','action_executed','verifier_request','verifier_raw',
     'verifier_format_failure','state_invalidated','recapture_requested','target_alignment']}
keep={'candidate','decision_blocked','verifier_format_failure',
      'state_invalidated','point_crosscheck','focus_crosscheck','target_alignment'}
recent=[e for e in events if e['kind'] in keep][-4:]
completed=[]
for marker in sorted((root/'runs').glob('*/complete.json')):
    pointer=json.loads(marker.read_text());p=pathlib.Path(pointer['attempt'])/'complete.json'
    raw=p.read_bytes();d=json.loads(raw)
    completed.append({k:d.get(k)for k in
       ['run','outcome','official_reward','scoring_status','actor_calls',
        'verifier_calls','environment_actions','blocked_reason']})
    completed[-1]['marker_hash_ok']=hashlib.sha256(raw).hexdigest()==pointer['sha256']
proc=subprocess.run(['ps','-p',str(state['pid']),'-o','pid,etime,stat,args'],
    text=True,capture_output=True)
print(json.dumps({'observed_at':time.time(),'status':state,
 'last_event_age_seconds':round(time.time()-events[-1]['time'],1)if events else None,
 'counts':counts,'recent':recent,'completed':completed,
 'process':proc.stdout.strip()},ensure_ascii=False))
'''.replace('ROOT', repr(launch['root']))
data = json.loads(remote(code, host='4090'))
(HERE / 'latest-formal-inspection.json').write_text(
    json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
if args.brief:
    print(json.dumps({'status':data['status']['phase'],
        'run':data['status']['run'], 'completed':data['status']['completed'],
        'counts':data['counts'], 'event_age_seconds':data['last_event_age_seconds']},ensure_ascii=False))
elif args.compact:
    state = data['status']
    print(json.dumps({
        'phase':state['phase'], 'completed':state['completed'],
        'run':state['run'], 'counts':data['counts'],
        'last_event_age_seconds':data['last_event_age_seconds'],
        'recent':[{'kind':e['kind'],'data':e['data']} for e in data['recent']
                  if e['kind'] in {'candidate','decision_blocked',
                                   'state_invalidated','verifier_format_failure'}],
        'finished':[{'run_id':d['run']['run_id'],
                     'outcome':d['outcome'], 'reward':d['official_reward'],
                     'marker_hash_ok':d['marker_hash_ok']} for d in data['completed']],
    }, ensure_ascii=False))
else:
    print(json.dumps(data, ensure_ascii=False, indent=2))
