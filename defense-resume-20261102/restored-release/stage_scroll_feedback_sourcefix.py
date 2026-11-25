"""Preserve misselected development evidence and test exact scroll-failure input."""
import base64,hashlib,json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;out=r/'v3.9.7-sourcefix-launch.json';assert not out.exists()
dev=json.loads((r/'v3.9.7-staging-retry.json').read_bytes());live=json.loads((r/'v3.9.7-live-launch.json').read_bytes())
files={n:base64.b64encode((r/n).read_bytes()).decode()for n in ['scroll_source.py','scroll_feedback_replay.py','scroll_live_recovery.py']}
identity=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()[:16]
code=r'''
import pathlib,json,hashlib,shutil,subprocess,os,time,base64
base=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023')
preserve=base/'preservation'/('scroll-source-selection-'+str(time.time_ns()));preserve.mkdir(parents=True)
for name,old in [('development',DEV),('live',LIVE)]:
 assert not pathlib.Path('/proc',str(old['pid'])).exists()
 shutil.copytree(old['root'],preserve/name)
 shutil.copy2(old['log'],preserve/(name+'.log'))
 (preserve/(name+'-launch.json')).write_text(json.dumps(old,indent=2))
shutil.copytree(LIVE['release'],preserve/'release',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
manifest={str(p.relative_to(preserve)):hashlib.sha256(p.read_bytes()).hexdigest()for p in preserve.rglob('*')if p.is_file()}
(preserve/'manifest.json').write_text(json.dumps({'reason':'Development selected first focus correction, not scroll mismatch; GUI prerequisite rejected, zero GUI actions','sha256':manifest},indent=2))
release=pathlib.Path(LIVE['release']).parent/IDENTITY;assert not release.exists()
shutil.copytree(LIVE['release'],release,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for n,b in FILES.items():(release/n).write_bytes(base64.b64decode(b))
assert(release/'defense/core.py').read_bytes()==(pathlib.Path(DEV['release'])/'defense/core.py').read_bytes()
env=dict(os.environ,DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',CUDA_VISIBLE_DEVICES='')
# Verify source node without a model call before staging.
check="""import sys,json\nfrom pathlib import Path\nfrom scroll_source import with_native_action_feedback\nsys.path[:0]=['/data/researcher/vwa100-2026-10-09','/data/researcher/vwa100-2026-10-09/upstream/visualwebarena-main']\nfrom run_reddit_internvl_smoke import parse,action\ndef proposal(t):\n p=parse(t);action(p);return {'name':p['type'],'parsed':True,'executor_fallback_wait':False,'payload':p,'coordinate_space':'normalized_1000'}\nroot=Path('/data/researcher/mirage-defense-pilot-20261023/vwa-v39-1792930297029784133')\nfor arm in ['joint','post_only']:\n p=json.loads((root/'runs'/('vwa--classifieds_112--stale_replace--'+arm)/'complete.json').read_bytes());events=[json.loads(x)for x in(Path(p['attempt'])/'events.jsonl').read_text().splitlines()]\n req,c,seq=with_native_action_feedback(events,proposal);assert req['data']['public']['observation_id'].startswith('009-');assert c[-1]['rejected_native_proposal']['payload']=={'type':'scroll','direction':'down'};print(json.dumps({'arm':arm,'source_request_seq':req['seq'],'source_rejected_seq':seq,'source_observation':req['data']['public']['observation_id']}))\n"""
cp=subprocess.run(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-c',check],cwd=release,env=env,capture_output=True,text=True);assert cp.returncode==0,cp.stderr+cp.stdout
(preserve/'new-source-check.txt').write_text(cp.stdout)
root=base/('scroll-feedback-exactnode-'+str(time.time_ns()));log=root.with_suffix('.log')
command=list(DEV['command']);command[2]=str(release/'scroll_feedback_replay.py');command[command.index('--root')+1]=str(root)
with log.open('xb')as stream:p=subprocess.Popen(command,cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
record={**DEV,'time':time.time(),'pid':p.pid,'root':str(root),'release':str(release),'log':str(log),'command':command,'source_selection_preservation':str(preserve),'source_node_check':cp.stdout,'scope':'Exact step9 scroll conflict; no future reference observations, source-bound new feedback; no GUI'}
lr=base/('scroll-live-exactnode-'+str(time.time_ns()));ll=lr.with_suffix('.log');lc=list(LIVE['command']);lc[2]=str(release/'scroll_live_recovery.py');lc[lc.index('--root')+1]=str(lr);lc[lc.index('--development')+1]=str(root)
with ll.open('xb')as stream:lp=subprocess.Popen(lc,cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
record['live']={**LIVE,'time':time.time(),'pid':lp.pid,'root':str(lr),'release':str(release),'log':str(ll),'command':lc,'development_root':str(root)}
(base/'scroll-feedback-exactnode-current.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
'''
record=json.loads(remote('DEV='+repr(dev)+'\nLIVE='+repr(live)+'\nFILES='+repr(files)+'\nIDENTITY='+repr(identity)+'\n'+code,host='4090',timeout=60))
out.write_text(json.dumps(record,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in record.items()if k not in ['unchanged_sha256','live']}));print(json.dumps(record['live']))
