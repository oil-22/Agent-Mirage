"""Read only archive member names, never evaluator answers or model traces."""
from remote_control import remote
code=r'''
from pathlib import Path
import gzip,json,time
p=Path('/data/researcher/attention-audit-20261031/members.jsonl.gz')
out={'read_only':True,'model_GUI_calls':0,'index_exists':p.exists(),'candidate_public_catalog_members':[],'config_member_count':0}
if p.exists():
 with gzip.open(p,'rt')as f:
  for line in f:
   row=json.loads(line);n=row[0]
   if '/selected100-classifieds-reddit-v2/'not in n:continue
   if n.endswith('/manifest.json'):out['candidate_public_catalog_members'].append(row)
   if '/evaluator_configs_v1/classifieds_'in n and n.endswith('.json'):out['config_member_count']+=1
print(json.dumps(out,ensure_ascii=False))
'''
out,path=remote('4090',code,'archived-public-catalog-member-discovery',timeout=60);print(out)
