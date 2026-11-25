"""Resume the finite upgrade after the previous service exited normally."""
from pathlib import Path
import json
from remote import remote
r=Path(__file__).resolve().parent;stage=json.loads((r/'v2-staging.json').read_text());old=json.loads((r/'v2-service-launch.json').read_text())
assert not(r/'v3-service-launch.json').exists()
code='''import pathlib,os,json,time,hashlib,subprocess,fcntl
base=pathlib.Path('/home/researcher/mirage-defense-pilot-20261023');lock=(base/'upgrade-v2.3.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
old=pathlib.Path(OLD);assert not pathlib.Path('/proc/PID').exists();assert json.loads((old/'status.json').read_text())['phase']=='stopped_at_request_boundary'
receipt=base/'v3-service-launch.json';assert not receipt.exists()
preserved=base/('v2.2-final-preservation-'+str(time.time_ns()));preserved.mkdir();rows={str(p.relative_to(old)):hashlib.sha256(p.read_bytes()).hexdigest()for p in old.rglob('*')if p.is_file()and p.suffix in {'.json','.jsonl','.log'}};(preserved/'manifest.json').write_text(json.dumps(rows,indent=2))
root=base/('inference-service-v3-'+str(time.time_ns()));root.mkdir();release=pathlib.Path(RELEASE)
env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='0,1,2,3',PYTHONPATH=str(base/'repair-deps-v2')+':'+str(release),OMP_NUM_THREADS='4',MKL_NUM_THREADS='4')
with(root/'worker.log').open('xb')as log:
 child=subprocess.Popen(['/opt/whz/conda-envs/webmall-vlm/bin/python','-u',str(release/'inference_server.py'),'--root',str(root),'--token-file',str(base/'transport.token'),'--gate-shadow',str(base/'shadow-preflight-1792761125821027588/status.json')],cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
result={'pid':child.pid,'root':str(root),'release':str(release),'preserved':str(preserved),'time':time.time(),'old_stopped_at_request_boundary':True,'actor_changes':False};receipt.write_text(json.dumps(result,indent=2));print(json.dumps(result))
'''.replace('OLD',repr(old['root'])).replace('PID',str(old['pid'])).replace('RELEASE',repr(stage['server_release']))
result=json.loads(remote(code));(r/'v3-service-launch.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
