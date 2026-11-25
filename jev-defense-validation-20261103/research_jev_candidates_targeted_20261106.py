"""Metadata/source-only narrowed research; no models are loaded."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib, json, time, urllib.request
from pathlib import Path

B = Path(__file__).resolve().parent
PARENT = B / 'model-research-mirror' / '1793970517432356400'
ITEMS = {}
for f in PARENT.glob('catalog-*.json'):
    for row in json.loads(f.read_text(encoding='utf-8')):
        ITEMS[row['id']] = row
NAMES = ['autotrust/JEV-27B-VL', 'autotrust/JEV-9B', 'TokenRhythm/NeoHorse-Jev-4B',
         'chaoliangUNSW/Jev-Style-2B-Decision-v4.2', 'chaoliangUNSW/Jev-Style-Cascade-9B',
         'shgao/rsi-jev-v7.0-vl-4b', 'mradermacher/Qwen3.5-4B-Jev-Judge-GGUF']

def get(job):
    name, url = job
    out = {'file': name, 'url': url}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'Mirage-Jev-source-review/1.0'}), timeout=15) as r:
            raw = r.read(2000000)
            out.update(status=r.status, raw=raw, sha256=hashlib.sha256(raw).hexdigest())
    except Exception as e:
        out['error'] = type(e).__name__ + ': ' + str(e)
    return out

def main():
    root = B / 'model-research-targeted' / str(time.time_ns())
    root.mkdir(parents=True)
    jobs = []
    for model in NAMES:
        ident = model.replace('/', '--')
        jobs.append((ident+'--meta.json', 'https://hf-mirror.com/api/models/'+model))
        rev = ITEMS.get(model,{}).get('sha','main')
        for fn in ['README.md','config.json','vl/serve.sh','serve.sh']:
            jobs.append((ident+'--'+fn.replace('/','--'), 'https://hf-mirror.com/'+model+'/raw/'+rev+'/'+fn))
    # Community board source, for independent verification of model-card leaderboard claims.
    jobs += [('board-meta.json','https://hf-mirror.com/api/spaces/multimodalart/jev-decision-index'),
             ('board-app.py','https://hf-mirror.com/spaces/multimodalart/jev-decision-index/raw/main/app.py')]
    receipt=[]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for row in pool.map(get,jobs):
            raw=row.pop('raw',None)
            if raw is not None:(root/row['file']).write_bytes(raw)
            receipt.append(row)
    (root/'receipt.json').write_text(json.dumps({'UTC':datetime.now(timezone.utc).isoformat(),'parent':str(PARENT),'model_calls':0,'weight_downloads':0,'requests':receipt},ensure_ascii=False,indent=2),encoding='utf-8')
    (root/'seal.json').write_text(json.dumps({f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in root.iterdir() if f.is_file()},indent=2),encoding='utf-8')
    print(json.dumps({'root':str(root),'ok':sum('sha256' in x for x in receipt),'failed':[x for x in receipt if 'error'in x]},ensure_ascii=True))
if __name__=='__main__':main()
