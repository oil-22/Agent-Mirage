"""Preserve the actual sorted-list overblocking, then request owned safe pause."""
import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent
receipt=r/'v3.4.1-sorted-obligation-pause.json'
assert not receipt.exists()
old=json.loads((r/'v3.4.1-vwa-resume.json').read_text())
code=r'''
import pathlib,json,time,hashlib,os,signal
root=pathlib.Path(ROOT);state=json.loads((root/'status.json').read_text());pid=PID
assert state['pid']==pid
cmd=pathlib.Path('/proc/'+str(pid)+'/cmdline').read_bytes().replace(b'\0',b' ').decode()
assert 'run_vwa_pilot.py' in cmd and str(root) in cmd
attempt=pathlib.Path(state['attempt']);assert root in attempt.parents
dest=root/'preservation'/('sorted-obligation-prepause-'+str(time.time_ns()));dest.mkdir(parents=True)
paths=[root/'status.json',pathlib.Path(LOG),attempt/'events.jsonl']
paths+=list((attempt/'screenshots').glob('*.png'))
paths+=list(attempt.glob('*.json'))
hashes={}
for i,p in enumerate(paths):
 raw=p.read_bytes();hashes[str(p)]=hashlib.sha256(raw).hexdigest();(dest/(str(i)+'-'+p.name)).write_bytes(raw)
(dest/'hashes.json').write_text(json.dumps(hashes,indent=2))
os.kill(pid,signal.SIGUSR1)
print(json.dumps({'time':time.time(),'pid':pid,'attempt':str(attempt),'preservation':str(dest),'signal':'SIGUSR1','reason':'Actual completion verifier incorrectly required all50 despite observable ascending-price order; preserve and safely pause before algorithm correction','hashes':hashes}))
'''.replace('ROOT',repr(old['root'])).replace('PID',repr(old['pid'])).replace('LOG',repr(old['log']))
result=json.loads(remote(code,host='4090'));receipt.write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items()if k!='hashes'}))
