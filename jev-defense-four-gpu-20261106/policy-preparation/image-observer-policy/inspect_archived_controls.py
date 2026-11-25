"""Read-only bounded archive index inspection; not an experiment launcher."""
import gzip,json
from pathlib import Path
base=Path('/data/researcher/defense-resume-20261102/archive-evidence')
print(json.dumps({'evidence_files':[str(p)for p in base.rglob('*')if p.is_file()][:30]}))
need=['frozen-controls-current.json','noresults-source-current.json','frozen-controls-reviewed-']
rows=[]
with gzip.open('/data/researcher/attention-audit-20261031/members.jsonl.gz','rt')as f:
    for line in f:
        if any(k in line for k in need):
            rows.append(json.loads(line))
            if len(rows)==75:break
print(json.dumps({'members':rows}))
