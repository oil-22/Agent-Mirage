import hashlib,json,time,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent
O=H/('official-readme-linked03-'+str(time.time_ns()));O.mkdir(exist_ok=False)
url='https://hf-mirror.com/Qwen/Qwen3.5-9B/raw/c202236235762e1c871ad0ccb60c8ee5ba337b9a/README.md'
try:
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mirage-native-source-review/1.0'}),timeout=20)as r:raw=r.read(200_001)
 assert len(raw)<200_001 and not raw.lstrip().startswith(b'<!')
 assert hashlib.sha256(raw).hexdigest()=='c5f5a8c2dddab69cfbf05279235aa5fddb137939a06539c4c7637aa900fef6d0'
 (O/'Qwen3.5-9B-README.md').write_bytes(raw)
 receipt={'url':url,'revision':'c202236235762e1c871ad0ccb60c8ee5ba337b9a','sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'matches_existing_full_identity':True,'model_GPU_GUI_calls':0}
except Exception as e:receipt={'url':url,'error':type(e).__name__+': '+str(e),'model_GPU_GUI_calls':0}
(O/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
(O/'seal.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in O.iterdir()if p.is_file()},indent=2),encoding='utf8')
print(json.dumps({'root':str(O),**receipt}))
