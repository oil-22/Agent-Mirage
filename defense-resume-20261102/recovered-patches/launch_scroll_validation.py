"""New two-run validation batch only after reviewed model and live controls."""
import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;out=r/'v3.9.7-scroll-validation-launch.json';assert not out.exists(),'Inspect existing batch, do not duplicate'
receipt=next(r/n for n in ['v3.9.7-controller-live-launch.json','v3.9.7-sourcefix-launch.json']if(r/n).exists())
launch=json.loads(receipt.read_bytes())
review=json.loads((r/'v3.9.7-development-review.json').read_bytes());assert review['allow_full_validation']
code='LAUNCH='+repr(launch)+'\nREVIEW='+repr(review)+'\n'+r'''
import pathlib,hashlib,json,time,pwd,subprocess,os,fcntl,urllib.request
base=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');release=pathlib.Path(LAUNCH['release'])
dev=pathlib.Path(LAUNCH['root']);live=pathlib.Path(LAUNCH['live']['root'])
assert json.loads((dev/'summary.json').read_bytes())['passed']
assert hashlib.sha256((dev/'summary.json').read_bytes()).hexdigest()==REVIEW['development_summary_sha256']
assert hashlib.sha256((live/'summary.json').read_bytes()).hexdigest()==REVIEW['live_summary_sha256']
assert not pathlib.Path('/proc',str(LAUNCH['live']['pid'])).exists()
assert not pathlib.Path('/proc',str(LAUNCH['pid'])).exists()
lock=(base/'scroll-validation-startup.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
active=base/'scroll-validation-active.json';assert not active.exists(),'Existing launch receipt; inspect, never duplicate'
clients=[]
for proc in pathlib.Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  if pwd.getpwuid(proc.stat().st_uid).pw_name!='whz':continue
  cmd=(proc/'cmdline').read_bytes().split(b'\0')
  if any(x.endswith(b'/run_vwa_pilot.py')or x.endswith(b'/scroll_live_recovery.py')or x.endswith(b'/scroll_decision_recovery.py')for x in cmd):clients.append({'pid':int(proc.name),'command':b' '.join(cmd).decode()})
 except (OSError,KeyError):pass
assert not clients,clients
token=(base/'transport.token').read_text().strip()
service=json.load(urllib.request.urlopen(urllib.request.Request('http://192.0.2.11:18127',headers={'Authorization':'Bearer '+token}),timeout=15));assert service['phase']=='ready'
site=subprocess.run(['docker','inspect','qwen27_vwa_classifieds'],capture_output=True,text=True,check=True)
container=json.loads(site.stdout)[0];assert container['Id']=='de6f56798c3c5a278a96d7afe6844e8be2c5673301e44e1c887eecc56118f0dd'and container['State']['Running']
assert 'whz-qwen27-vwa'in json.dumps(container['Config'].get('Labels'))
with urllib.request.urlopen('http://192.0.2.10:29980/index.php?page=login',timeout=15)as response:assert response.status==200
oldroot=base/'vwa-v39-1792930297029784133';completed=[]
for marker in sorted((oldroot/'runs').glob('*/complete.json')):
 pointer=json.loads(marker.read_bytes());raw=(pathlib.Path(pointer['attempt'])/'complete.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==pointer['sha256']
 completed.append({'run':marker.parent.name,'pointer_sha256':hashlib.sha256(marker.read_bytes()).hexdigest(),**pointer})
assert len(completed)==20
root=base/('vwa-scroll-validation-'+str(time.time_ns()));root.mkdir();log=root/'worker.log'
(root/'original-20-completed-pointers.json').write_text(json.dumps(completed,indent=2))
runs=['vwa--classifieds_112--stale_replace--joint','vwa--classifieds_112--stale_replace--post_only']
(root/'validation-provenance.json').write_text(json.dumps({'user_request':'Repair two stale-frame prose-up/action-down terminal failures. Independent new-version full trajectories; originals retained.','source_root':str(oldroot),'source_runs':[x for x in completed if x['run']in runs],'development_review':REVIEW,'expected_runs':runs,'unchanged_conditions':['native actor system and parameters','seed20261011','task112','1280x720 original screenshots','full history','injection position/method','50steps','70actor/140verifier','2regeneration/2recapture per decision','BF16/SDPA','official scoring'],'only_changes':['source-bound rejected action feedback','symmetric native direction protocol clarification'],'not_a_paired_latest_version_efficacy_study':True},indent=2))
env=dict(os.environ,DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',CUDA_VISIBLE_DEVICES='')
command=['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'run_vwa_pilot.py'),'--root',str(root),'--plan',str(release/'plan80.json'),'--token-file',str(base/'transport.token'),'--only-runs',*runs,'--priority-runs',runs[0]]
with log.open('xb')as stream:p=subprocess.Popen(command,cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
record={'time':time.time(),'pid':p.pid,'root':str(root),'release':str(release),'log':str(log),'command':command,'review':REVIEW,'expected':2,'only_runs':runs,'source_root':str(oldroot),'original20_untouched':True,'core_sha256':hashlib.sha256((release/'defense/core.py').read_bytes()).hexdigest()}
active.write_text(json.dumps(record,indent=2));print(json.dumps(record))
'''
record=json.loads(remote(code,host='4090',timeout=60));out.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in record.items()if k!='review'}))
