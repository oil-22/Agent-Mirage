"""Read-only verification of independent two-run repair validation."""
import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;receipt=next(r/n for n in ['v3.9.9-scroll-validation-resume.json','v3.9.8-scroll-validation-resume.json','v3.9.7-scroll-validation-launch.json']if(r/n).exists());launch=json.loads(receipt.read_bytes())
code='LAUNCH='+repr(launch)+'\n'+r'''
import pathlib,json,time,hashlib,pwd,collections,subprocess
root=pathlib.Path(LAUNCH['root']);proc=pathlib.Path('/proc',str(LAUNCH['pid']))
if proc.exists():
 assert pwd.getpwuid(proc.stat().st_uid).pw_name=='whz'
 cmd=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode();assert LAUNCH['root']in cmd and LAUNCH['release']in cmd and 'run_vwa_pilot.py'in cmd
state=json.loads((root/'status.json').read_bytes());rows=[]
for run in sorted((root/'runs').iterdir()):
 marker=run/'complete.json';pointer=json.loads(marker.read_bytes())if marker.exists()else None
 attempts=[]
 for p in sorted(run.glob('attempt-*')):
  events=[]
  for line in(p/'events.jsonl').read_text().splitlines():
   try:events.append(json.loads(line))
   except json.JSONDecodeError:pass
  counts=collections.Counter(e['kind']for e in events)
  actions=[e for e in events if e['kind']=='action_executed']
  attempts.append({'attempt':str(p),'counts':dict(counts),'last_event_age_seconds':time.time()-events[-1]['time']if events else None,'last_event_kind':events[-1]['kind']if events else None,'recent_candidates':[{'seq':e['seq'],'observation':e['data']['observation_id'],'text':e['data']['text']}for e in events if e['kind']=='candidate'][-2:],'up_executions':[{'seq':e['seq'],'observation':e['data']['observation_id'],'payload':e['data']['proposal']['payload']}for e in actions if e['data']['proposal'].get('payload',{}).get('direction')=='up'],'technical_failure':[(f.name,json.loads(f.read_bytes()))for f in [p/'failure.json',p/'technical-failure.json']if f.exists()]})
 complete=None
 if pointer:
  raw=(pathlib.Path(pointer['attempt'])/'complete.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==pointer['sha256'];complete=json.loads(raw)
 rows.append({'run':run.name,'pointer':pointer,'complete':complete,'attempts':attempts})
originals=json.loads((root/'original-20-completed-pointers.json').read_bytes())
for row in originals:
 p=pathlib.Path(LAUNCH['source_root'])/'runs'/row['run']/'complete.json';assert hashlib.sha256(p.read_bytes()).hexdigest()==row['pointer_sha256'];assert hashlib.sha256((pathlib.Path(row['attempt'])/'complete.json').read_bytes()).hexdigest()==row['sha256']
audit=json.loads(subprocess.check_output(['/data/researcher/vwa100-2026-10-09/venv/bin/python',LAUNCH['release']+'/audit_vwa_v2.py',str(root)],text=True))
record={'time':time.time(),'state':state,'process':{'owner':pwd.getpwuid(proc.stat().st_uid).pw_name,'cmd':(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode()}if proc.exists()else None,'rows':rows,'audit':audit,'original20_pointer_and_terminal_sha_verified':True,'log_tail':pathlib.Path(LAUNCH['log']).read_text()[-1800:]}
print(json.dumps(record))
'''
record=json.loads(remote(code,host='4090',timeout=60))
for name in ['scroll-validation-progress.json',receipt.name.split('-scroll-validation-')[0]+'-scroll-validation-progress.json']:
 (r/name).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
def compact_attempt(x):
 d={k:v for k,v in x.items()if k!='technical_failure'}
 d['technical_failure']=[{'file':name,**{k:value.get(k)for k in ['outcome','blocked_reason','technical_status','traceback']}}for name,value in x['technical_failure']]
 return d
print(json.dumps({**{k:v for k,v in record.items()if k not in ['rows','process','audit']},'alive':bool(record['process']),'all_event_chains_valid':all(x['hash_chain_ok']for x in record['audit']['rows']),'rows':[{'run':x['run'],'complete':{k:x['complete'].get(k)for k in ['outcome','official_reward','blocked_reason','actor_calls','verifier_calls']}if x['complete']else None,'attempts':[compact_attempt(v)for v in x['attempts']]}for x in record['rows']]},ensure_ascii=True))
