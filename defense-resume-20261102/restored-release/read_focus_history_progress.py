"""Read completed repair case replies without generating or retrying anything."""
import argparse,json
from pathlib import Path
from remote import remote
PREP=Path(__file__).resolve().parent/'focus-history-repair-development'
row=json.loads((PREP/'launch-current.json').read_bytes())
p=argparse.ArgumentParser();p.add_argument('--only',nargs='*');args=p.parse_args()
code='ROOT='+repr(row['root'])+'\nONLY='+repr(args.only)+r'''
import json
from pathlib import Path
r=Path(ROOT);out=[]
for p in sorted(r.glob('*-result.json')):
 x=json.loads(p.read_bytes())
 if ONLY is None or x['id']in ONLY:out.append({k:v for k,v in x.items()if k not in {'calls','direction_check'}})
print(json.dumps(out,ensure_ascii=False))
'''
print(remote(code,host='4090',timeout=60))
