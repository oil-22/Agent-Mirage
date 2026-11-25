"""Read-only two-hour inspection; retain hash-bound raw terminal evidence."""
import hashlib,json,time
from pathlib import Path
from remote import remote

base=Path(__file__).resolve().parent
receipt_path=next(base/n for n in ['v3.9.6-vwa-resume.json','v3.9.5-site-recovery-resume.json']if(base/n).exists())
receipt=json.loads(receipt_path.read_text())
code='''
import pathlib,json,hashlib,time,subprocess,urllib.request
root=pathlib.Path(ROOT)
rows=[]
for marker in sorted((root/'runs').glob('*/complete.json')):
 p=json.loads(marker.read_text());a=pathlib.Path(p['attempt']);raw=(a/'complete.json').read_bytes()
 assert hashlib.sha256(raw).hexdigest()==p['sha256']
 events=[json.loads(x)for x in(a/'events.jsonl').read_text().splitlines()]
 rows.append({'run':marker.parent.name,'attempt':str(a),'sha256':p['sha256'],'complete':json.loads(raw),'tail':events[-8:]})
site={}
try:
 with urllib.request.urlopen('http://192.0.2.10:29980/index.php?page=login',timeout=15)as r:site={'status':r.status,'sha256':hashlib.sha256(r.read()).hexdigest()}
except Exception as e:site={'error':str(e)}
print(json.dumps({'time':time.time(),'rows':rows,'site':site}))
'''.replace('ROOT',repr(receipt['root']))
evidence=json.loads(remote(code,host='4090'))
service=json.loads(remote('''
import pathlib,json,pwd,subprocess
p=pathlib.Path('/proc/2140814')
print(json.dumps({'alive':p.exists(),'owner':pwd.getpwuid(p.stat().st_uid).pw_name if p.exists()else None,'cmd':(p/'cmdline').read_bytes().replace(b'\\0',b' ').decode()if p.exists()else None,'gpu':subprocess.run(['nvidia-smi','--query-gpu=index,memory.used,utilization.gpu','--format=csv,noheader'],capture_output=True,text=True).stdout}))
''',host='3090'))
evidence['service']=service
out=base/'heartbeat-evidence'/str(time.time_ns());out.mkdir(parents=True)
raw=json.dumps(evidence,ensure_ascii=False,indent=2).encode();(out/'terminal-evidence.json').write_bytes(raw)
(out/'manifest.json').write_text(json.dumps({'sha256':hashlib.sha256(raw).hexdigest(),'source_root':receipt['root'],'read_only':True},indent=2))
print(json.dumps({'saved':str(out),'site':evidence['site'],'service':service,'completed':[{'run':r['run'],'sha256':r['sha256'],**{k:r['complete'].get(k)for k in ['outcome','official_reward','blocked_reason','scoring_status']}}for r in evidence['rows']]}))
