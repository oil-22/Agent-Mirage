"""New bounded metadata-only read; source never imported or executed."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib,json,time,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent
J='autotrust/JEV-9B';JR='7ac669b8fb476ba926491e3d1c39f9330d68dbed'
Q='Qwen/Qwen3.5-9B';QR='c202236235762e1c871ad0ccb60c8ee5ba337b9a'
jobs=[('jev-fixed-api.json','/api/models/'+J+'/revision/'+JR+'?blobs=true',True),('qwen-fixed-api.json','/api/models/'+Q+'/revision/'+QR+'?blobs=true',True)]
for name in ['preprocessor_config.json','tokenizer_config.json','chat_template.jinja','generation_config.json','LICENSE','NOTICE']:
 jobs.append(('Qwen--'+name,'/'+Q+'/raw/'+QR+'/'+name,name.endswith('.json')))
for name in ['LICENSE','vl/calibration.json']:
 jobs.append(('JEV--'+name.replace('/','--'),'/'+J+'/raw/'+JR+'/'+name,name.endswith('.json')))
def fetch(job):
 name,suffix,is_json=job;attempts=[]
 for domain in ['https://hf-mirror.com','https://huggingface.co']:
  url=domain+suffix
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mirage-small-native-metadata/1.0'}),timeout=15)as r:
    raw=r.read(1_000_001);assert len(raw)<=1_000_000
    assert not raw.lstrip().lower().startswith(b'<!doctype html')
    if is_json:json.loads(raw)
   return name,raw,{'url':url,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'attempts':attempts}
  except Exception as e:attempts.append({'url':url,'error':type(e).__name__+': '+str(e)})
 return name,None,{'status':'unavailable','attempts':attempts}
O=H/('native-small-metadata-linked02-'+str(time.time_ns()));O.mkdir(exist_ok=False)
records=[]
with ThreadPoolExecutor(max_workers=8)as pool:
 for name,raw,r in pool.map(fetch,jobs):
  if raw is not None:(O/name).write_bytes(raw)
  records.append({'name':name,**r})
(O/'receipt.json').write_text(json.dumps({'UTC':datetime.now(timezone.utc).isoformat(),'parent_official_source_root':'official-small-source-1794046077389119500','records':records,'weight_downloads':0,'code_executed':False,'GPU_model_GUI_calls':0},indent=2),encoding='utf8')
(O/'seal.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in O.iterdir()if p.is_file()},indent=2),encoding='utf8')
print(json.dumps({'root':str(O),'success':sum('sha256'in x for x in records),'records':records}))
