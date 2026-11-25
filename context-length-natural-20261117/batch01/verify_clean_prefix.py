"""Check actual post-probe main-line inputs against saved normal images/outputs."""
from pathlib import Path
import json,subprocess
from datetime import datetime,timezone,timedelta

P=Path(__file__).resolve().parent
ROOT='/data/researcher/context-length-natural-20261117/batch01'
def remote(host,code):
    r=subprocess.run(['D:/Git/usr/bin/ssh.exe','-o','BatchMode=yes','-o','ConnectTimeout=10',host,'python3 -'],input='ROOT='+repr(ROOT)+'\n'+code,text=True,capture_output=True,timeout=35)
    if r.returncode:raise RuntimeError(r.stderr[-2000:])
    return json.loads(r.stdout)

g=remote('4090',r'''
from pathlib import Path
import json,hashlib
p=Path(ROOT)/'gui-output';out={}
for folder in p.glob('T*/clean'):
    tid=int(folder.parent.name[1:]);cps=[]
    for cp in folder.glob('checkpoint-*'):
        if not(cp/'post-probe-state.json').exists():continue
        r=json.loads((cp/'checkpoint.json').read_text())
        assert json.loads((cp/'post-probe-state.json').read_text())==r['fingerprint']
        cps.append(r['step'])
    if not cps:continue
    out[str(tid)]={'completed_probe_steps':cps,
        'normal_images':{str(int(f.name[:3])):hashlib.sha256(f.read_bytes()).hexdigest() for f in folder.glob('*-observed.png')},
        'normal_outputs':{str(int(f.name[:3])):hashlib.sha256(json.loads(f.read_text())['text'].encode()).hexdigest() for f in folder.glob('*-response.json')}}
print(json.dumps(out))
''')
m=remote('3090',r'''
from pathlib import Path
import json,hashlib
p=Path(ROOT)/'model-output/requests';out=[]
for folder in sorted(p.iterdir()):
    if not(folder/'input-info.json').exists():continue
    r=json.loads((folder/'request.json').read_text());meta=r.get('meta',{})
    if meta.get('stage')!='clean_control':continue
    info=json.loads((folder/'input-info.json').read_text())
    out.append({'task':meta['task'],'step':meta['step'],'input_tokens':info['input_tokens'],'request':folder.name,
        'image_hashes':[x['sha256'] for x in info['images']],
        'assistant_hashes':[hashlib.sha256(x['content'].encode()).hexdigest() for x in r['body']['messages'] if x['role']=='assistant']})
print(json.dumps(out))
''')
checks=[]
for r in m:
    c=g.get(str(r['task']))
    if not c or r['step']<=min(c['completed_probe_steps']):continue
    if not all(str(i) in c['normal_outputs'] for i in range(1,r['step'])):continue
    if not all(str(i) in c['normal_images'] for i in range(1,r['step']+1)):continue
    assert r['image_hashes']==[c['normal_images'][str(i)] for i in range(1,r['step']+1)],r
    assert r['assistant_hashes']==[c['normal_outputs'][str(i)] for i in range(1,r['step'])],r
    checks.append({'task':r['task'],'step':r['step'],'input_tokens':r['input_tokens'],'request':r['request'],
        'all_retained_images_match_normal_trajectory':True,'all_retained_assistant_outputs_match_normal_trajectory':True})
assert checks,'No post-probe normal requests available yet.'
result={'checked_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'checks':checks,
    'scope':'Actual main-line requests after isolated probes; not a semantic Mirage label.'}
(P/'clean-prefix-verification.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result))
