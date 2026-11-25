"""Once-only, source-bound live diagnostic, with failed control retained honestly."""
import base64,hashlib,json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;out=r/'v3.9.9-controller-live-launch.json';assert not out.exists()
dev=json.loads((r/'v3.9.9-staging.json').read_bytes());saved=json.loads((r/'v3.9.9-failure-preservation.json').read_bytes())
raw=(r/'point_decision_recovery.py').read_bytes();ident=hashlib.sha256(raw+json.dumps(dev['bindings'],sort_keys=True).encode()).hexdigest()[:16]
code=r'''
import pathlib,json,hashlib,shutil,base64,time,subprocess,fcntl,os,urllib.request
base=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');batch=pathlib.Path(SAVED['source']).parents[2]
gate=(batch/'point-recovery-live.lock').open('a');fcntl.flock(gate,fcntl.LOCK_EX|fcntl.LOCK_NB)
marker=batch/'v3.9.9-controller-live-launch.json';assert not marker.exists()
assert os.getuid()==1015 and not pathlib.Path('/proc',str(DEV['pid'])).exists()
state=json.loads((batch/'status.json').read_bytes());assert state['phase']=='technical_failure'and state['attempt']==SAVED['source']and not pathlib.Path('/proc',str(state['pid'])).exists()
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  if p.stat().st_uid!=os.getuid():continue
  cmd=(p/'cmdline').read_bytes().split(b'\0')
  assert not any(x.endswith(b'/run_vwa_pilot.py')or x.endswith(b'/point_decision_recovery.py')or x.endswith(b'/scroll_decision_recovery.py')for x in cmd),(p.name,cmd)
 except OSError:pass
prior=pathlib.Path(DEV['release']);devroot=pathlib.Path(DEV['root']);summary=json.loads((devroot/'summary.json').read_bytes())
assert summary['phase']=='completed'and len(summary['results'])==7 and not summary['passed']
results={v['case']:v for v in summary['results']};assert all(v['passed']for n,v in results.items()if n!='background')
assert not results['background']['passed']and results['background']['verifier_calls']==2 and 'Point not inside current point evidence'in results['background']['error']
assert hashlib.sha256((pathlib.Path(SAVED['source'])/'events.jsonl').read_bytes()).hexdigest()==SAVED['sha256']['events.jsonl']
for n,h in DEV['bindings'].items():assert hashlib.sha256((prior/n).read_bytes()).hexdigest()==h
preserve=base/'preservation'/('point-recovery-development-'+str(time.time_ns()));preserve.mkdir(parents=True);shutil.copytree(devroot,preserve/'controls');shutil.copytree(prior,preserve/'release',ignore=shutil.ignore_patterns('__pycache__','*.pyc'));shutil.copy2(DEV['log'],preserve/'worker.log')
manifest={str(p.relative_to(preserve)):hashlib.sha256(p.read_bytes()).hexdigest()for p in preserve.rglob('*')if p.is_file()};(preserve/'manifest.json').write_text(json.dumps({'sha256':manifest,'reason':'Original seven-control development was6/7, background localization failed twice strict containment. Retain failure, do not relabel it passing or claim accurate background localization. Live diagnostic tests bounded fail-closed recovery, not reader accuracy.'},indent=2))
release=prior.parent/IDENT;assert not release.exists();shutil.copytree(prior,release,ignore=shutil.ignore_patterns('__pycache__','*.pyc'));(release/'point_decision_recovery.py').write_bytes(base64.b64decode(RAW))
assert(release/'defense/core.py').read_bytes()==(prior/'defense/core.py').read_bytes()
container=json.loads(subprocess.check_output(['docker','inspect','qwen27_vwa_classifieds'],text=True))[0];assert container['Id']=='de6f56798c3c5a278a96d7afe6844e8be2c5673301e44e1c887eecc56118f0dd'and container['State']['Running']and'whz-qwen27-vwa'in json.dumps(container['Config'].get('Labels'))
token=(base/'transport.token').read_text().strip();health=json.load(urllib.request.urlopen(urllib.request.Request('http://192.0.2.11:18127',headers={'Authorization':'Bearer '+token}),timeout=15));assert health['phase']=='ready'and not health['actor_grammar']
env=dict(os.environ,DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',CUDA_VISIBLE_DEVICES='')
root=base/('point-live-controller-'+str(time.time_ns()));log=root.with_suffix('.log');command=['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'point_decision_recovery.py'),'--source',SAVED['source'],'--root',str(root),'--token-file',str(base/'transport.token')]
with log.open('xb')as f:p=subprocess.Popen(command,cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
names=list(DEV['bindings'])+['point_decision_recovery.py','defense/prompts.py'];bindings={n:hashlib.sha256((release/n).read_bytes()).hexdigest()for n in names}
record={'pid':p.pid,'uid':os.getuid(),'root':str(root),'release':str(release),'log':str(log),'command':command,'time':time.time(),'source':SAVED['source'],'bindings':bindings,'control_root':str(devroot),'control_summary_sha256':hashlib.sha256((devroot/'summary.json').read_bytes()).hexdigest(),'control_results':'6/7; original background localization failure preserved; diagnostic only, not full-run approval','development_preservation':str(preserve),'scope':'Source step21 full bounded Controller.decide after20 actually replayed actions. Source prefix calls count, same-live recaptures, no forced target. Full validation not yet authorized by this review.'}
with marker.open('x')as f:json.dump(record,f,indent=2)
print(json.dumps(record))
'''
x=json.loads(remote('DEV='+repr(dev)+'\nSAVED='+repr(saved)+'\nRAW='+repr(base64.b64encode(raw).decode())+'\nIDENT='+repr(ident)+'\n'+code,host='4090',timeout=60));out.write_text(json.dumps(x,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in x.items()if k!='bindings'}))
