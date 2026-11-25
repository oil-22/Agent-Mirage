"""Read-only archive inventory on the project's existing hosts. No GUI or model."""
import collections
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
SOURCE = r'''
from pathlib import Path
import os,collections,json
root=Path('/data/researcher')
roots=[p for p in root.iterdir() if p.is_dir()]
printable=[p.name for p in roots if p.name.lower() not in ('.ssh','.config','.cache','.local')]
pick=[p for p in roots if any(z in p.name.lower() for z in ('archive','webmall','android','uitars','jev-defense','trajectory','context-length','webarena','osworld','gui-','agent-mirage'))]
missing=[]
out={}
for p in sorted(pick):
 groups=collections.defaultdict(collections.Counter); names=collections.defaultdict(collections.Counter); ex={};shapes=collections.defaultdict(set)
 for d,ds,fs in os.walk(p):
  ds[:]=[s for s in ds if s not in {'.git','models','node_modules','__pycache__','site-packages','miniconda3','huggingface','auth','model-output','snapshots','venv','.venv','.cache','wandb','eval_configs'} and not s.startswith('PRIVATE')]
  rel=Path(d).relative_to(p); group='/'.join(rel.parts[:1]) or '.'
  for f in fs:
   if f.startswith('.') or f.startswith('PRIVATE'):continue
   ext=f.lower().rsplit('.',1)[-1]
   if ext in ('png','jpg','jpeg','zip','tgz','tar','gz','json','jsonl','parquet','webp','mp4'):
    groups[group][ext]+=1
    if ext in ('json','jsonl','zip'):names[group][f]+=1
    if ext in ('jsonl','png','zip') and len(shapes[(group,ext)])<3:
     shapes[(group,ext)].add(str(rel/f))
 out[p.name]={'groups':{k:{'ext':dict(v),'names':names[k].most_common(10),'examples':{e:sorted(shapes[(k,e)]) for e in ('png','jsonl','zip')}} for k,v in groups.items()}}
print(json.dumps({'roots':sorted(printable),'sources':out}))
'''

if __name__ == '__main__':
    from concurrent.futures import ThreadPoolExecutor
    def run(host):
        r=subprocess.run(['D:/Git/usr/bin/ssh.exe','-o','BatchMode=yes','-o','ConnectTimeout=8',host,'python3 -B -'],
                         input=SOURCE.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=150)
        if r.returncode:
            print(host,r.stderr.decode(errors='replace')[-600:]);return
        data=json.loads(r.stdout)
        f=HERE/('archive-inventory-'+host+'.json')
        f.write_text(json.dumps(data,ensure_ascii=False,indent=1),encoding='utf-8')
        print(host,'directories:',data['roots'])
        for k,v in data['sources'].items():
            c=collections.Counter()
            for g in v['groups'].values():c.update(g['ext'])
            print(host,k,dict(c))
    with ThreadPoolExecutor(2) as pool:list(pool.map(run,['4090','3090']))
