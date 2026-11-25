from pathlib import Path
import json,subprocess

ROOT='/data/researcher/context-length-pilot-20261117/quant-nf4-02'
script=r'''
from pathlib import Path
import json,time,os
p=Path(ROOT)
out={'time':time.time()}
for f in ['gui-output/status.json','model-output/status.json']:
    if (p/f).exists():out[f]=json.loads((p/f).read_text())
out['terminals']=[]
for f in sorted((p/'gui-output').glob('T*/branches/*/*/terminal.json')):
    d=json.loads(f.read_text());out['terminals'].append({'path':str(f.relative_to(p/'gui-output')),**d})
out['clean_terminals']=[]
for f in sorted((p/'gui-output').glob('T*/clean/terminal.json')):
    out['clean_terminals'].append({'path':str(f.relative_to(p/'gui-output')),**json.loads(f.read_text())})
for pid in [3181517,3706201]:
    f=Path('/proc')/str(pid)/'stat'
    if f.exists():out[str(pid)]=f.read_text().split()[2]
out['exit_files']={str(f.relative_to(p)):f.read_text()[-4000:] for f in p.glob('*exit*') if f.is_file()}
for sub in ['gui-output','model-output']:
    for name in ['exit.json','failure.json','startup-failure.json','idle-timeout.json']:
        f=p/sub/name
        if f.exists():out[str(f.relative_to(p))]=json.loads(f.read_text())
print(json.dumps(out))
'''
results={}
for host in ['4090','3090']:
    r=subprocess.run(['D:/Git/usr/bin/ssh.exe','-o','BatchMode=yes','-o','ConnectTimeout=10',host,'python3 -'],input='ROOT='+repr(ROOT)+'\n'+script,text=True,capture_output=True,timeout=40)
    if r.returncode:raise RuntimeError(r.stderr)
    d=json.loads(r.stdout);results[host]=d
    (Path(__file__).parent/(host+'-live-status.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
    print(host,json.dumps({k:v for k,v in d.items() if k not in ['terminals','clean_terminals']}))
    print('terminals',len(d['terminals']))
    if d['terminals']:
        from collections import Counter
        print('outcomes',dict(Counter(t.get('outcome') for t in d['terminals'])))
        print('rewards',dict(Counter(str(t.get('reward')) for t in d['terminals'])))
