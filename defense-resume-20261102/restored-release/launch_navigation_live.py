"""Finite gated local recovery check; no recurring monitor or duplicate model."""
import base64,json,re
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;out=r/'v3.9.3-live-launch.json';assert not out.exists()
dev=json.loads((r/'v3.9.3-staging.json').read_text());old=json.loads((r/'v3.9-vwa-launch.json').read_text())
raw=base64.b64encode((r/'navigation_live_recovery.py').read_bytes()).decode()
code=r'''
import pathlib,time,json,base64,os,subprocess,hashlib
root=pathlib.Path(OLD['root']);state=json.loads((root/'status.json').read_text());assert state['phase']=='technical_failure'and not pathlib.Path('/proc',str(state['pid'])).exists()
work=root.parent/('navigation-live-'+str(time.time_ns()));work.mkdir();script=work/'navigation_live_recovery.py';script.write_bytes(base64.b64decode(RAW))
env=os.environ.copy();env.update(DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',CUDA_VISIBLE_DEVICES='')
log=work/'live.log'
with log.open('xb')as stream:
 p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(script),'--source',DEV['source'],'--root',str(work/'run'),'--probe',DEV['root'],'--release',DEV['release'],'--token-file',str(root.parent/'transport.token')],cwd=DEV['release'],env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':p.pid,'root':str(work/'run'),'release':DEV['release'],'log':str(log),'driver_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),'time':time.time(),'scope':'One source-initialized live back diagnostic after nine real prefix actions; not formal completion. Finite prerequisite, no recurring monitoring.'}))
'''
v={'OLD':old,'DEV':dev,'RAW':raw};code=re.sub(r'\b(?:OLD|DEV|RAW)\b',lambda m:repr(v[m.group()]),code)
compile(code,'live-launch','exec');d=json.loads(remote(code,host='4090'));out.write_text(json.dumps(d,indent=2),encoding='utf8');print(json.dumps(d))
