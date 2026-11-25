"""Once-only new feedback arm, two calls remaining in the original development ceiling."""
import base64,hashlib,json,time
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent;PREP=BASE/'source-evidence-preview-development';active=PREP/'routing-launch.json'
assert not active.exists()
parent=json.loads((PREP/'launch.json').read_bytes());controls=json.loads((PREP/'controls-launch.json').read_bytes())
a=json.loads((Path(parent['local_root'])/'collected/summary.json').read_bytes());b=json.loads((Path(controls['local_root'])/'collected/summary.json').read_bytes())
assert a['phase']==b['phase']=='completed'and a['new_model_calls']+b['new_model_calls']==29
stamp=str(time.time_ns());root='/data/researcher/mirage-defense-pilot-20261023/source-evidence-routing-diagnostic-'+stamp;local=PREP/('routing-'+stamp);local.mkdir()
plan={'parent_root':parent['root'],'controls_root':controls['root'],'prior_calls':29,'max_new_calls':2,'combined_ceiling':31,'cases':['c03','c04'],'scope':'New evidence-routing feedback condition, reuses exact sealed readouts; no replay of any completed condition and no GUI/formal trial. Selected after v1 failures, no independent efficacy claim.'}
source=(BASE/'source_evidence_routing_diagnostic.py').read_bytes();(local/'source_evidence_routing_diagnostic.py').write_bytes(source);(local/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
code='ROOT='+repr(root)+'\nPLAN='+repr(plan)+'\nSOURCE='+repr(base64.b64encode(source).decode())+'\n'+r'''
import pathlib,json,os,fcntl,base64,subprocess,time,hashlib
assert os.getuid()==1015
root=pathlib.Path(ROOT);base=root.parent;lock=(base/'source-evidence-preview-development.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
active=base/'source-evidence-routing-diagnostic-active.json';assert not active.exists()
assert json.loads((pathlib.Path(PLAN['controls_root'])/'status.json').read_bytes())['phase']=='completed'
root.mkdir();(root/'plan.json').write_text(json.dumps(PLAN,indent=2));(root/'source_evidence_routing_diagnostic.py').write_bytes(base64.b64decode(SOURCE))
command=['/data/researcher/venvs/qwen35-9b-full-20261019/bin/python','-u',str(root/'source_evidence_routing_diagnostic.py'),'--root',ROOT]
with(root/'worker.log').open('xb')as f:p=subprocess.Popen(command,cwd=root,env=dict(os.environ,OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2'),stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(lock.fileno(),))
proc=pathlib.Path('/proc')/str(p.pid);assert proc.stat().st_uid==1015
r={'root':ROOT,'pid':p.pid,'uid':1015,'full_command':(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(),'command':command,'plan_sha256':hashlib.sha256((root/'plan.json').read_bytes()).hexdigest(),'worker_sha256':hashlib.sha256((root/'source_evidence_routing_diagnostic.py').read_bytes()).hexdigest(),'started_at':time.time()}
(root/'launch.json').write_text(json.dumps(r,indent=2))
with active.open('x')as f:json.dump(r,f,indent=2)
print(json.dumps(r))
'''
r=json.loads(remote(code,host='4090',timeout=60));r['local_root']=str(local);active.write_text(json.dumps(r,indent=2),encoding='utf-8');(local/'launch.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
