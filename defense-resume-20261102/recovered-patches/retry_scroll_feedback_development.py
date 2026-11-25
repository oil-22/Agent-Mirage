"""Preserve startup-only environment failure; retry unchanged development code."""
import json
from pathlib import Path
from remote import remote

r=Path(__file__).resolve().parent;out=r/'v3.9.7-staging-retry.json';assert not out.exists()
old=json.loads((r/'v3.9.7-staging.json').read_bytes())
code=r'''
import pathlib,json,hashlib,shutil,subprocess,os,time
base=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');source=pathlib.Path(OLD['root'])
assert not pathlib.Path('/proc',str(OLD['pid'])).exists()and not(source/'summary.json').exists()
lograw=pathlib.Path(OLD['log']).read_bytes();assert b"KeyError: 'DATASET'"in lograw
assert not list(source.glob('*-result.json')),'No model-result retry without separate source review'
preserve=base/'preservation'/('scroll-feedback-startup-'+str(time.time_ns()));preserve.mkdir(parents=True)
shutil.copytree(source,preserve/'attempt');(preserve/'worker.log').write_bytes(lograw)
(preserve/'launch.json').write_text(json.dumps(OLD,indent=2))
manifest={'startup_error':'missing DATASET in development subprocess environment','new_model_calls_before_failure':0,'code_sha256':hashlib.sha256((pathlib.Path(OLD['release'])/'scroll_feedback_replay.py').read_bytes()).hexdigest(),'log_sha256':hashlib.sha256(lograw).hexdigest(),'source':OLD['root'],'source_retained':True}
(preserve/'manifest.json').write_text(json.dumps(manifest,indent=2))
root=base/('scroll-feedback-probe-envretry-'+str(time.time_ns()));log=root.with_suffix('.log')
env=dict(os.environ,DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',CUDA_VISIBLE_DEVICES='')
command=list(OLD['command']);command[command.index('--root')+1]=str(root)
with log.open('xb')as stream:p=subprocess.Popen(command,cwd=OLD['release'],env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
record={**OLD,'time':time.time(),'pid':p.pid,'root':str(root),'log':str(log),'command':command,'previous_attempt':OLD['root'],'startup_preservation':str(preserve),'only_retry_change':'original VWA environment variables supplied; model/probe/core code unchanged'}
(base/'scroll-feedback-development-current.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
'''
record=json.loads(remote('OLD='+repr(old)+'\n'+code,host='4090',timeout=45))
out.write_text(json.dumps(record,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in record.items()if k!='unchanged_sha256'}))
