"""Resume unfinished two-run validation only; original20 terminals never changed."""
import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;out=r/'v3.9.8-scroll-validation-resume.json';assert not out.exists()
old=json.loads((r/'v3.9.7-scroll-validation-launch.json').read_bytes());dev=json.loads((r/'v3.9.8-protocol-staging.json').read_bytes())
saved=json.loads((r/'v3.9.8-failure-preservation.json').read_bytes());review=json.loads((r/'v3.9.8-development-review.json').read_bytes())
assert review['allow_online']
code=r'''
import pathlib,json,time,hashlib,subprocess,fcntl,urllib.request,os,pwd
root=pathlib.Path(OLD['root']);release=pathlib.Path(DEV['release']);source=pathlib.Path(SAVED['source'])
gate=(root/'point-pixel-resume.lock').open('a');fcntl.flock(gate,fcntl.LOCK_EX|fcntl.LOCK_NB)
receipt=root/'v3.9.8-resume-manifest.json';assert not receipt.exists()
s=json.loads((root/'status.json').read_bytes());assert s['phase']=='technical_failure'and s['attempt']==str(source)
assert os.getuid()==1015 and not pathlib.Path('/proc',str(s['pid'])).exists()and not pathlib.Path('/proc',str(DEV['pid'])).exists()
batch=(root/'batch.lock').open('a');fcntl.flock(batch,fcntl.LOCK_EX|fcntl.LOCK_NB)
clients=[]
for proc in pathlib.Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  if proc.stat().st_uid!=os.getuid():continue
  cmd=(proc/'cmdline').read_bytes().split(b'\0')
  if any(x.endswith(b'/run_vwa_pilot.py')or x.endswith(b'/point_pixel_protocol_replay.py')for x in cmd):clients.append(int(proc.name))
 except OSError:pass
assert not clients,clients
raw=pathlib.Path(DEV['root'],'summary.json').read_bytes();summary=json.loads(raw)
assert summary['phase']=='completed'and summary['passed']and len(summary['results'])==8 and all(x['passed']for x in summary['results'])
assert hashlib.sha256(raw).hexdigest()==REVIEW['summary_sha256']and REVIEW['engineering_tests']==126
for n,h in DEV['bindings'].items():assert hashlib.sha256((release/n).read_bytes()).hexdigest()==h
assert(source/'technical-failure.json').exists()and not(source/'complete.json').exists()
assert hashlib.sha256((source/'events.jsonl').read_bytes()).hexdigest()==SAVED['sha256']['events.jsonl']
assert not list((root/'runs').glob('*/complete.json'))
originals=json.loads((root/'original-20-completed-pointers.json').read_bytes());assert len(originals)==20
for v in originals:
 p=pathlib.Path(OLD['source_root'])/'runs'/v['run']/'complete.json'
 assert hashlib.sha256(p.read_bytes()).hexdigest()==v['pointer_sha256']
 assert hashlib.sha256(pathlib.Path(v['attempt'],'complete.json').read_bytes()).hexdigest()==v['sha256']
token=(root.parent/'transport.token').read_text().strip()
health=json.load(urllib.request.urlopen(urllib.request.Request('http://192.0.2.11:18127',headers={'Authorization':'Bearer '+token}),timeout=15));assert health['phase']=='ready'and not health['actor_grammar']
container=json.loads(subprocess.check_output(['docker','inspect','qwen27_vwa_classifieds'],text=True))[0]
assert container['Id']=='de6f56798c3c5a278a96d7afe6844e8be2c5673301e44e1c887eecc56118f0dd'and container['State']['Running']and'whz-qwen27-vwa'in json.dumps(container['Config'].get('Labels'))
with urllib.request.urlopen('http://192.0.2.10:29980/index.php?page=login',timeout=15)as site:assert site.status==200
env=dict(os.environ,DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',CUDA_VISIBLE_DEVICES='')
log=root/('resume-v3.9.8-'+str(time.time_ns())+'.log');runs=OLD['only_runs']
command=['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'run_vwa_pilot.py'),'--root',str(root),'--plan',str(release/'plan80.json'),'--token-file',str(root.parent/'transport.token'),'--only-runs',*runs,'--priority-runs',runs[0]]
fcntl.flock(batch,fcntl.LOCK_UN);batch.close()
with log.open('xb')as f:p=subprocess.Popen(command,cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
record={**OLD,'pid':p.pid,'uid':os.getuid(),'release':str(release),'log':str(log),'time':time.time(),'command':command,'bindings':DEV['bindings'],'core_sha256':DEV['bindings']['defense/core.py'],'previous_failed_attempt':str(source),'failure_preservation':SAVED['preservation'],'review':REVIEW,'completed_before_resume':0,'remaining_configurations':2,'scope':'Only unfinished independent two-run scroll validation; failed joint attempt retained and linked. Original20 pointer/terminal SHAs unchanged. Only isolated point-reader transport uses pixels; all validators/native actor/conditions/budgets/scoring unchanged.'}
with receipt.open('x')as f:json.dump(record,f,indent=2)
print(json.dumps(record))
'''
d=json.loads(remote('OLD='+repr(old)+'\nDEV='+repr(dev)+'\nSAVED='+repr(saved)+'\nREVIEW='+repr(review)+'\n'+code,host='4090',timeout=60));out.write_text(json.dumps(d,indent=2));print(json.dumps({k:v for k,v in d.items()if k not in {'bindings','review'}}))
