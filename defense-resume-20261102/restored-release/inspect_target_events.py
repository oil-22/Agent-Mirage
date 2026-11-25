"""Read-only snapshot of actual decisions, with no image payloads or secrets."""
import argparse, json, time
from pathlib import Path
from remote import remote

p=argparse.ArgumentParser()
p.add_argument('--run',default='vwa--classifieds_112--clean--post_only')
p.add_argument('--last',type=int,default=12)
p.add_argument('--receipt',default=None)
a=p.parse_args()
here=Path(__file__).resolve().parent
path=here/a.receipt if a.receipt else next(
    here/name for name in ['v3.8.3-vwa-resume.json','v3.6.2-vwa-resume.json',
                           'v3.4.1-vwa-resume.json','v3-vwa-launch.json']
    if (here/name).exists())
receipt=json.loads(path.read_text())
code=r'''
import json,pathlib,hashlib,time
root=pathlib.Path(ROOT);run=root/'runs'/RUN
marker=run/'complete.json'
attempt=pathlib.Path(json.loads(marker.read_text())['attempt']) if marker.exists() else sorted(run.glob('attempt-*'))[-1]
raw=(attempt/'events.jsonl').read_bytes();events=[]
for line in raw.splitlines():
 try:events.append(json.loads(line))
 except json.JSONDecodeError:pass
keep={'candidate','verdict','verifier_raw','state_invalidated','decision_blocked','decision_accepted','verifier_format_failure','target_alignment','point_crosscheck','focus_crosscheck','screen_result'}
chosen=[e for e in events if e['kind']in keep]
done=json.loads((attempt/'complete.json').read_text())if(attempt/'complete.json').exists()else None
print(json.dumps({'time':time.time(),'attempt':str(attempt),'source_sha256':hashlib.sha256(raw).hexdigest(),'last_event_seq':events[-1]['seq'],'events':chosen[-LAST:],'complete':{k:done.get(k)for k in ['outcome','official_reward','scoring_status','actor_calls','verifier_calls','environment_actions','blocked_reason']}if done else None},ensure_ascii=False))
'''.replace('ROOT',repr(receipt['root'])).replace('RUN',repr(a.run)).replace('LAST',repr(a.last))
result=json.loads(remote(code,host='4090'))
out=here/'decision-inspections';out.mkdir(exist_ok=True)
path=out/(a.run+'-'+str(time.time_ns())+'.json')
path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'saved':str(path),**result},ensure_ascii=False))
