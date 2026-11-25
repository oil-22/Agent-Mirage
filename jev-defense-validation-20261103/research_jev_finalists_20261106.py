"""Read-only final candidate source check. Never executes candidate code."""
import importlib.util, json, hashlib, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
B=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('survey',B/'research_jev_candidates_targeted_20261106.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
root=B/'model-research-finalists'/str(time.time_ns());root.mkdir(parents=True)
models=['perplexity-ai/pplx-decider-flash-v1.2','Rover00/WeMM-JEV']
rows=[]; meta={}
for model in models:
 row=m.get((model.replace('/','--')+'--meta.json','https://hf-mirror.com/api/models/'+model));raw=row.pop('raw',None)
 if raw:
  (root/row['file']).write_bytes(raw);meta[model]=json.loads(raw)
 rows.append(row)
jobs=[]
for model,d in meta.items():
 rev=d['sha'];ident=model.replace('/','--')
 for f in ['README.md','config.json','preprocessor_config.json','model.safetensors.index.json']:
  jobs.append((ident+'--'+f,'https://hf-mirror.com/'+model+'/raw/'+rev+'/'+f))
 jobs.append((ident+'--tree.json','https://hf-mirror.com/api/models/'+model+'/tree/'+rev))
with ThreadPoolExecutor(max_workers=6)as pool:
 for row in pool.map(m.get,jobs):
  raw=row.pop('raw',None)
  if raw:(root/row['file']).write_bytes(raw)
  rows.append(row)
(root/'receipt.json').write_text(json.dumps({'model_calls':0,'weight_downloads':0,'requests':rows},indent=2),encoding='utf8')
(root/'seal.json').write_text(json.dumps({f.name:hashlib.sha256(f.read_bytes()).hexdigest()for f in root.iterdir()if f.is_file()},indent=2),encoding='utf8')
print(json.dumps({'root':str(root),'revisions':{k:v['sha']for k,v in meta.items()},'failures':[r for r in rows if'error'in r]}))
