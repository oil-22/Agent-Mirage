from remote_control import remote
code=r'''
from pathlib import Path,PurePosixPath
import gzip,json
names=[];configs={};prefixes={}
with gzip.open('/data/researcher/attention-audit-20261031/members.jsonl.gz','rt')as f:
 for line in f:
  row=json.loads(line);name=row[0];n=PurePosixPath(name)
  if 'selected100-classifieds-reddit'not in name:continue
  if 'evaluator_configs_v1/classifieds_'in name and name.endswith('.json'):
   configs[n.name]=configs.get(n.name,0)+1
  elif n.suffix in {'.json','.jsonl','.csv'} and len(n.parts)<10 and not any(k in name for k in ['/runs/','/trace/','/requests/','/results/','/history/']):
   names.append(row)
print(json.dumps({'possible_catalog_members':names[:45],'distinct_classifieds_config_names':sorted(configs),
 'read_only_names_only':True,'models_GUI_scorer_calls':0},ensure_ascii=False))
'''
out,path=remote('4090',code,'public-task-member-names-only',timeout=60);print(out)
