import argparse,json
from pathlib import Path
from remote import remote
PREP=Path(__file__).resolve().parent/'focus-history-repair-development/readiness-supplement'
p=argparse.ArgumentParser();p.add_argument('--only',nargs='*');args=p.parse_args();row=json.loads((PREP/'launch-current.json').read_bytes())
code='ROOT='+repr(row['root'])+'\nONLY='+repr(args.only)+r'''
import json
from pathlib import Path
r=Path(ROOT);out=[]
for case in json.loads((r/'plan.json').read_bytes())['cases']:
 if ONLY is not None and case['id']not in ONLY:continue
 f=r/(case['id']+'-result.json')
 events=r/'journal'/case['id']/'events.jsonl';checks=[]
 if events.exists():
  for line in events.read_text().splitlines():
   x=json.loads(line)
   if x['kind']in ['current_only_execution_history_scope','historical_event_source_scope','verifier_format_failure']:checks.append({'kind':x['kind'],'data':x['data']})
 if f.exists():
  x=json.loads(f.read_bytes());out.append({'case':case['id'],'result':{k:v for k,v in x.items()if k not in {'calls','direction_check'}},'checks':checks})
 elif checks:out.append({'case':case['id'],'pending':True,'checks':checks})
print(json.dumps(out,ensure_ascii=False))
'''
print(remote(code,host='4090',timeout=60))
