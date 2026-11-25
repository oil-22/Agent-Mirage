"""One finite dependency job: finish old request, preserve receipts, replace own service."""
import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;stage=json.loads((r/'v2-staging.json').read_text());old=json.loads((r/'v2-service-launch.json').read_text())
assert not(r/'v3-upgrade-launch.json').exists(),'Inspect existing finite upgrade job'
script='''import pathlib,os,json,time,hashlib,subprocess,fcntl
base=pathlib.Path('/home/researcher/mirage-defense-pilot-20261023');lock=(base/'upgrade-v2.3.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
old=pathlib.Path(OLD);proc=pathlib.Path('/proc')/str(PID);deadline=time.time()+1800
while proc.exists()and time.time()<deadline:
 cmd=(proc/'cmdline').read_bytes().decode().replace(chr(0),' ');assert str(old)in cmd and proc.stat().st_uid==os.getuid(),cmd
 time.sleep(2)
assert not proc.exists(),'Old request did not finish; replacement remains gated'
assert json.loads((old/'status.json').read_text())['phase']=='stopped_at_request_boundary'
preserved=base/('v2.2-final-preservation-'+str(time.time_ns()));preserved.mkdir();rows={str(p.relative_to(old)):hashlib.sha256(p.read_bytes()).hexdigest()for p in old.rglob('*')if p.is_file()and p.suffix in {'.json','.jsonl','.log'}};(preserved/'manifest.json').write_text(json.dumps(rows,indent=2))
receipt=base/'v3-service-launch.json';assert not receipt.exists()
root=base/('inference-service-v3-'+str(time.time_ns()));root.mkdir();release=pathlib.Path(RELEASE)
env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='0,1,2,3',PYTHONPATH=str(base/'repair-deps-v2')+':'+str(release),OMP_NUM_THREADS='4',MKL_NUM_THREADS='4')
with(root/'worker.log').open('xb')as log:
 child=subprocess.Popen(['/opt/whz/conda-envs/webmall-vlm/bin/python','-u',str(release/'inference_server.py'),'--root',str(root),'--token-file',str(base/'transport.token'),'--gate-shadow',str(base/'shadow-preflight-1792761125821027588/status.json')],cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
result={'pid':child.pid,'root':str(root),'release':str(release),'preserved':str(preserved),'time':time.time(),'verifier':'bounded grammar; reasons<=480 characters; partial token receipts','actor_changes':False};receipt.write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
'''.replace('OLD',repr(old['root'])).replace('PID',str(old['pid'])).replace('RELEASE',repr(stage['server_release']))
code='''import pathlib,subprocess,json,time
r=pathlib.Path('/home/researcher/mirage-defense-pilot-20261023');out=r/('finite-upgrade-'+str(time.time_ns()));out.mkdir();(out/'upgrade.py').write_text(SCRIPT)
with(out/'worker.log').open('xb')as log:
 child=subprocess.Popen(['python3','-u',str(out/'upgrade.py')],cwd=out,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':child.pid,'root':str(out),'scope':'one finite prerequisite upgrade, not periodic monitoring'}))
'''.replace('SCRIPT',repr(script))
result=json.loads(remote(code));(r/'v3-upgrade-launch.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
