"""Once-only actor controls, no repeated completed actor condition or extra total-call ceiling."""
import base64,hashlib,json,time
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent;PREP=BASE/'source-evidence-preview-development';active=PREP/'controls-launch.json'
assert not active.exists(),'Never duplicate this control extension'
parent=json.loads((PREP/'launch.json').read_bytes());folder=Path(parent['local_root'])/'collected'
summary=json.loads((folder/'summary.json').read_bytes());assert summary['phase']=='completed' and summary['new_model_calls']+6<=31
sha=lambda b:hashlib.sha256(b).hexdigest()
stamp=str(time.time_ns());root='/data/researcher/mirage-defense-pilot-20261023/source-evidence-preview-controls-'+stamp
plan={'parent_root':parent['root'],'parent_summary_sha256':sha((folder/'summary.json').read_bytes()),'cases':['c06','c07','c08'],'max_new_model_calls':6,'combined_max_model_calls':31,'purpose':'Previously unattempted actor controls: pure WAIT on blank/nearblank and real pagination; exact sealed readouts reused. No semantic expected labels sent.'}
source=(BASE/'source_evidence_preview_controls.py').read_bytes()
local=PREP/('controls-'+stamp);local.mkdir();(local/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');(local/'source_evidence_preview_controls.py').write_bytes(source)
code='ROOT='+repr(root)+'\nPLAN='+repr(plan)+'\nSOURCE='+repr(base64.b64encode(source).decode())+'\n'+r'''
import pathlib,json,base64,os,fcntl,subprocess,time,hashlib
assert os.getuid()==1015
root=pathlib.Path(ROOT);parent=pathlib.Path(PLAN['parent_root']);assert json.loads((parent/'status.json').read_bytes())['phase']=='completed'
base=parent.parent;lock=(base/'source-evidence-preview-development.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
active=base/'source-evidence-preview-controls-active.json';assert not active.exists()
root.mkdir();(root/'plan.json').write_text(json.dumps(PLAN,indent=2));(root/'source_evidence_preview_controls.py').write_bytes(base64.b64decode(SOURCE))
command=['/data/researcher/venvs/qwen35-9b-full-20261019/bin/python','-u',str(root/'source_evidence_preview_controls.py'),'--root',ROOT]
with(root/'worker.log').open('xb')as f:p=subprocess.Popen(command,cwd=root,env=dict(os.environ,OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2'),stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(lock.fileno(),))
proc=pathlib.Path('/proc')/str(p.pid);assert proc.stat().st_uid==1015
rec={'root':ROOT,'pid':p.pid,'uid':1015,'full_command':(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(),'command':command,'plan_sha256':hashlib.sha256((root/'plan.json').read_bytes()).hexdigest(),'worker_sha256':hashlib.sha256((root/'source_evidence_preview_controls.py').read_bytes()).hexdigest(),'started_at':time.time()}
(root/'launch.json').write_text(json.dumps(rec,indent=2))
with active.open('x')as f:json.dump(rec,f,indent=2)
print(json.dumps(rec))
'''
r=json.loads(remote(code,host='4090',timeout=60));r['local_root']=str(local);active.write_text(json.dumps(r,indent=2),encoding='utf-8');(local/'launch.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
