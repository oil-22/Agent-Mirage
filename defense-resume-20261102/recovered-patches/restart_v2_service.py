"""Gracefully replace only the verified experiment service after preserving its evidence."""
import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;stage=json.loads((r/'v2-staging.json').read_text())
assert not(r/'v2-service-launch.json').exists(),'Inspect existing v2 service; do not duplicate'
code='''import pathlib,os,signal,time,json,hashlib,subprocess
base=pathlib.Path('/home/researcher/mirage-defense-pilot-20261023');old=base/'inference-service-1792762946666648486';pid=1293867
proc=pathlib.Path('/proc')/str(pid);cmd=(proc/'cmdline').read_bytes().decode().replace(chr(0),' ')
assert str(old)in cmd and 'inference_server.py'in cmd and proc.stat().st_uid==os.getuid(),cmd
state=json.loads((old/'status.json').read_text());assert state['phase']=='ready'
preserve=base/('service-v1-preservation-'+str(time.time_ns()));preserve.mkdir()
rows={str(p.relative_to(old)):hashlib.sha256(p.read_bytes()).hexdigest()for p in old.rglob('*')if p.is_file()and p.suffix in {'.json','.jsonl','.log'}}
(preserve/'manifest.json').write_text(json.dumps({'process':cmd,'files':rows,'time':time.time()},indent=2))
os.kill(pid,signal.SIGUSR1)
for _ in range(30):
 if not proc.exists():break
 time.sleep(0.5)
else:raise RuntimeError('Old service did not exit at request boundary; no replacement launched')
root=base/('inference-service-v2-'+str(time.time_ns()));root.mkdir();release=pathlib.Path(RELEASE)
env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='0,1,2,3',PYTHONPATH=str(base/'repair-deps-v2')+':'+str(release),OMP_NUM_THREADS='4',MKL_NUM_THREADS='4')
log=(root/'worker.log').open('xb');child=subprocess.Popen(['/opt/whz/conda-envs/webmall-vlm/bin/python','-u',str(release/'inference_server.py'),'--root',str(root),'--token-file',str(base/'transport.token'),'--gate-shadow',str(base/'shadow-preflight-1792761125821027588/status.json')],cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
result={'pid':child.pid,'root':str(root),'release':str(release),'preserved':str(preserve),'old_stopped_at_request_boundary':True,'time':time.time()};(base/'v2-service-launch.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
'''.replace('RELEASE',repr(stage['server_release']))
result=json.loads(remote(code,timeout=90));(r/'v2-service-launch.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
