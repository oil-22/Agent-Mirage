"""Bounded metadata/source reads only. Never request weights or run model code."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib,json,time,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent
jobs=[
('autotrust--JEV-9B--vl--serve_decide.py','autotrust/JEV-9B','7ac669b8fb476ba926491e3d1c39f9330d68dbed','vl/serve_decide.py'),
('autotrust--JEV-9B--vl--adapter_config.json','autotrust/JEV-9B','7ac669b8fb476ba926491e3d1c39f9330d68dbed','vl/adapter_vllm/adapter_config.json'),
('autotrust--JEV-9B--vl--decision_head.json','autotrust/JEV-9B','7ac669b8fb476ba926491e3d1c39f9330d68dbed','vl/adapter_vllm/decision_head.json'),
('Qwen--Qwen3.5-9B--config.json','Qwen/Qwen3.5-9B','c202236235762e1c871ad0ccb60c8ee5ba337b9a','config.json'),
('Qwen--Qwen3.5-9B--model.safetensors.index.json','Qwen/Qwen3.5-9B','c202236235762e1c871ad0ccb60c8ee5ba337b9a','model.safetensors.index.json'),
]
def fetch(job):
 name,repo,revision,file=job;assert not file.endswith('.safetensors')
 urls=['https://huggingface.co/'+repo+'/raw/'+revision+'/'+file,'https://hf-mirror.com/'+repo+'/raw/'+revision+'/'+file]
 attempts=[]
 for url in urls:
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mirage-source-only-capability-review/1.0'}),timeout=12)as r:
    data=r.read(2_000_001);assert len(data)<=2_000_000
    assert not data.lstrip().lower().startswith(b'<!doctype html')
    return name,data,{'repository':repo,'revision':revision,'file':file,'url':url,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'attempts':attempts}
  except Exception as e:attempts.append({'url':url,'error':type(e).__name__+': '+str(e)})
 return name,None,{'repository':repo,'revision':revision,'file':file,'attempts':attempts,'status':'unavailable'}
O=H/('official-small-source-'+str(time.time_ns()));O.mkdir(exist_ok=False)
records=[]
with ThreadPoolExecutor(max_workers=5)as pool:
 for name,raw,record in pool.map(fetch,jobs):
  if raw is not None:(O/name).write_bytes(raw)
  records.append(record)
(O/'receipt.json').write_text(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'records':records,'weight_downloads':0,'model_GPU_GUI_calls':0,'downloaded_code_executed':False},indent=2),encoding='utf8')
(O/'seal.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in O.iterdir()if p.is_file()},indent=2),encoding='utf8')
print(json.dumps({'root':str(O),'successful_sources':sum('sha256'in r for r in records),'records':records}))
