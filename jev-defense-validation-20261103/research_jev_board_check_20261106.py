"""A bounded public board/metadata check; no weights, no inference."""
import importlib.util, json, hashlib, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
B=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('survey',B/'research_jev_candidates_targeted_20261106.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
root=B/'model-research-board'/str(time.time_ns());root.mkdir(parents=True)
jobs=[
 ('board-root.html','https://multimodalart-jev-decision-index.hf.space/'),
 ('board-config.json','https://multimodalart-jev-decision-index.hf.space/config'),
 ('board-api.json','https://hf-mirror.com/api/spaces/multimodalart/jev-decision-index/tree/main'),
 ('rsi-tree.json','https://hf-mirror.com/api/models/shgao/rsi-jev-v7.0-vl-4b/tree/58baf6fc961f42108756b27ff92fddf4aea3b1d8'),
 ('27b-tree.json','https://hf-mirror.com/api/models/autotrust/JEV-27B-VL/tree/9e53b8a809d2ab98e3e6a55b2b2dbf94b4c1e84a')]
rows=[]
with ThreadPoolExecutor(max_workers=5) as pool:
 for row in pool.map(m.get,jobs):
  raw=row.pop('raw',None)
  if raw is not None:
   (root/row['file']).write_bytes(raw)
   if row['file'].endswith('.json'):
    try:json.loads(raw);row['valid_json']=True
    except Exception:row['valid_json']=False
  rows.append(row)
(root/'receipt.json').write_text(json.dumps({'model_calls':0,'weight_downloads':0,'requests':rows},indent=2),encoding='utf8')
(root/'seal.json').write_text(json.dumps({f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in root.iterdir() if f.is_file()},indent=2),encoding='utf8')
print(json.dumps({'root':str(root),'requests':rows},ensure_ascii=True))
