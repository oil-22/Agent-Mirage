"""Launch a bounded prefix-replay/live recovery diagnostic, gated on reviewed controls."""
import json
from pathlib import Path
from remote import remote
here=Path(__file__).resolve().parent;out=here/'v3.9-live-recovery-launch.json';assert not out.exists()
dev=json.loads((here/'v3.9-readiness-launch.json').read_text());stage=json.loads((here/'v2-staging.json').read_text())
old=json.loads((here/'v3.8.3-vwa-resume.json').read_text())
code=r'''
import pathlib,json,hashlib,subprocess,time,os
base=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');release=pathlib.Path(RELEASE);source=pathlib.Path(SOURCE)
state=json.loads((source/'status.json').read_text());assert state['phase']=='paused_at_decision_boundary'
for n,sha in BINDINGS.items():assert hashlib.sha256((release/n).read_bytes()).hexdigest()==sha,n
root=base/('readiness-live-v39-'+str(time.time_ns()));log=root.with_suffix('.log');gate=pathlib.Path(DEVROOT)/'reviewed-acceptance.json'
env=os.environ.copy();env.update(DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',CUDA_VISIBLE_DEVICES='')
with log.open('xb')as stream:
 p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'readiness_live_recovery.py'),'--source',str(source),'--root',str(root),'--gate',str(gate),'--token-file',str(base/'transport.token')],cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':p.pid,'root':str(root),'release':str(release),'log':str(log),'gate':str(gate),'source':str(source),'time':time.time(),'scope':'Two-step live diagnostic after explicit archived action prefix replay; waits for reviewed controls. Not formal runs or natural whole-task recovery.'}))
'''.replace('RELEASE',repr(stage['release'])).replace('SOURCE',repr(old['root'])).replace('DEVROOT',repr(dev['root'])).replace('BINDINGS',repr(dev['bindings']))
data=json.loads(remote(code,host='4090'));out.write_text(json.dumps(data,indent=2),encoding='utf-8');print(json.dumps(data))
