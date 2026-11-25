"""One bounded independent four-step diagnostic; never a completed formal round."""
import json
from pathlib import Path
from remote import remote
here=Path(__file__).resolve().parent;out=here/'v3.8.3-baseline-diagnostic-launch.json';assert not out.exists()
formal=json.loads((here/'v3.8.3-vwa-resume.json').read_text())
code=r'''import pathlib,json,subprocess,os,time,hashlib
base=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');formal=pathlib.Path(FORMAL);release=pathlib.Path(RELEASE)
state=json.loads((formal/'status.json').read_text());assert state['phase']=='running'and state['run']=='vwa--classifieds_112--blank_replace--joint'
assert not(formal/'runs/vwa--classifieds_112--blank_replace--baseline').exists()
root=base/('baseline-blank-diagnostic-v383-'+str(time.time_ns()));root.mkdir();log=root/'worker.log'
env=os.environ.copy();env.update(DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',CUDA_VISIBLE_DEVICES='')
with log.open('xb')as stream:p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'run_vwa_pilot.py'),'--root',str(root),'--plan',str(release/'plan80.json'),'--token-file',str(base/'transport.token'),'--diagnostic-run','vwa--classifieds_112--blank_replace--baseline','--diagnostic-step-cap','4'],cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':p.pid,'root':str(root),'log':str(log),'release':str(release),'time':time.time(),'diagnostic_only':True,'step_cap':4,'official_scoring':False,'formal_results_modified':False,'scope':'Independent original-actor four-step exposure diagnostic only. Does not contribute to formal round completion or task success; formal50-step run continues unchanged.'}))
'''.replace('FORMAL',repr(formal['root'])).replace('RELEASE',repr(formal['release']))
data=json.loads(remote(code,host='4090'));out.write_text(json.dumps(data,indent=2));print(json.dumps(data))
