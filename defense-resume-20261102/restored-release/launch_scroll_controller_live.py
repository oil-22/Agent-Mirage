"""Preserve single-check diagnostic, then run complete original decision flow."""
import json,base64,hashlib
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;out=r/'v3.9.7-controller-live-launch.json';assert not out.exists()
launch=json.loads((r/'v3.9.7-sourcefix-launch.json').read_bytes())
raw=(r/'scroll_decision_recovery.py').read_bytes();ident=hashlib.sha256(raw).hexdigest()[:16]
code='LAUNCH='+repr(launch)+'\nRAW='+repr(base64.b64encode(raw).decode())+'\nIDENT='+repr(ident)+'\n'+r'''
import pathlib,json,hashlib,shutil,time,subprocess,os,base64
base=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');old=LAUNCH['live'];source=pathlib.Path(old['root'])
assert not pathlib.Path('/proc',str(old['pid'])).exists();assert json.loads((pathlib.Path(LAUNCH['root'])/'summary.json').read_bytes())['passed']
assert(source/'failure.json').exists()and not(source/'after-repair.png').exists()
preserve=base/'preservation'/('scroll-live-singlecheck-'+str(time.time_ns()));preserve.mkdir(parents=True)
shutil.copytree(source,preserve/'attempt');shutil.copytree(old['release'],preserve/'release',ignore=shutil.ignore_patterns('__pycache__','*.pyc'));shutil.copy2(old['log'],preserve/'worker.log')
(preserve/'launch.json').write_text(json.dumps(old,indent=2));manifest={str(p.relative_to(preserve)):hashlib.sha256(p.read_bytes()).hexdigest()for p in preserve.rglob('*')if p.is_file()}
(preserve/'manifest.json').write_text(json.dumps({'reason':'Model JSON correctly up, main checker retained insufficient historical claim; no recovery action executed. Single inspect did not run full native decision recovery.','sha256':manifest},indent=2))
release=pathlib.Path(old['release']).parent/IDENT;assert not release.exists();shutil.copytree(old['release'],release,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
(release/'scroll_decision_recovery.py').write_bytes(base64.b64decode(RAW))
assert(release/'defense/core.py').read_bytes()==(pathlib.Path(old['release'])/'defense/core.py').read_bytes()
env=dict(os.environ,DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',CUDA_VISIBLE_DEVICES='')
root=base/('scroll-live-controller-'+str(time.time_ns()));log=root.with_suffix('.log')
command=['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'scroll_decision_recovery.py'),'--source',old['source'],'--root',str(root),'--token-file',str(base/'transport.token')]
with log.open('xb')as stream:p=subprocess.Popen(command,cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
live={**old,'time':time.time(),'pid':p.pid,'root':str(root),'release':str(release),'log':str(log),'command':command,'previous_failed_diagnostic':old['root'],'failure_preservation':str(preserve),'scope':'Original entire Controller.decide at source step9 after8actual prefix actions; prior call counts carried; original per-decision budgets and all probes.'}
record={**LAUNCH,'release':str(release),'live':live};(base/'scroll-controller-live-current.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
'''
record=json.loads(remote(code,host='4090',timeout=60));out.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(record['live']))
