"""Replace only our idle eight-GPU service, preserving all requests and failures."""
import json
from pathlib import Path
from remote import remote
here=Path(__file__).resolve().parent;output=here/'v9-service-launch.json';assert not output.exists()
old=json.loads((here/'v8-service-launch.json').read_text());stage=json.loads((here/'v2-staging.json').read_text())
failure=json.loads((here/'v3.8-history-failure-preservation.json').read_text(encoding='utf-8'))
code=r'''
import pathlib,os,signal,time,json,hashlib,subprocess,fcntl,ast
base=pathlib.Path('/home/researcher/mirage-defense-pilot-20261023');old=pathlib.Path(OLD);release=pathlib.Path(RELEASE)
lock=(base/'service-replacement.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
proc=pathlib.Path('/proc')/str(PID)
alive=proc.exists()and(proc/'stat').read_text().split()[2]!='Z'
if alive:
 assert proc.stat().st_uid==os.getuid()
 cmd=(proc/'cmdline').read_bytes().decode().replace(chr(0),' ');assert str(old)in cmd and 'inference_server.py'in cmd
assert json.loads((old/'status.json').read_text())['phase']in {'ready','stopped_at_request_boundary'}
for p in(old/'requests').iterdir():assert(p/'response.json').exists()or(p/'failure.json').exists(),str(p)
for name in ['inference_server.py','defense/http_backend.py','native-vwa-request.json','plan80.json']:
 assert(release/name).read_bytes()==(pathlib.Path(OLDRELEASE)/name).read_bytes(),name
def generate(path):return next(ast.dump(n,include_attributes=False)for n in ast.walk(ast.parse(path.read_text()))if isinstance(n,ast.FunctionDef)and n.name=='generate')
assert generate(release/'defense/qwen_backend.py')==generate(pathlib.Path(OLDRELEASE)/'defense/qwen_backend.py')
out=base/('service-preservation-v9-'+str(time.time_ns()));out.mkdir()
hashes={str(p.relative_to(old)):hashlib.sha256(p.read_bytes()).hexdigest()for p in old.rglob('*')if p.is_file()}
(out/'hashes.json').write_text(json.dumps(hashes,indent=2))
if alive:os.kill(PID,signal.SIGUSR1)
for _ in range(30):
 if not proc.exists()or(proc/'stat').read_text().split()[2]=='Z':break
 time.sleep(0.5)
else:raise RuntimeError('Owned service did not stop at boundary')
assert json.loads((old/'status.json').read_text())['phase']=='stopped_at_request_boundary'
gpus=[0,1,2,3,4,6,7]
for gpu in gpus:
 used=int(subprocess.check_output(['nvidia-smi',f'--id={gpu}','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True))
 assert used<1024,(gpu,used)
root=base/('inference-service-v9-'+str(time.time_ns()));root.mkdir()
env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES=','.join(map(str,gpus)),PYTHONPATH=str(base/'repair-deps-v2')+':'+str(release),OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True')
with(root/'worker.log').open('xb')as log:
 p=subprocess.Popen(['/opt/whz/conda-envs/webmall-vlm/bin/python','-u',str(release/'inference_server.py'),'--root',str(root),'--token-file',str(base/'transport.token'),'--gate-shadow',str(base/'shadow-preflight-1792761125821027588/status.json'),'--placement','balanced'],cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
result={'pid':p.pid,'root':str(root),'release':str(release),'previous':OLD,'preservation':str(out),'time':time.time(),'gpus':gpus,'placement':'balanced','actor_generate_ast_unchanged':True,'scope':'History-only grammar/source restriction; default visual verifier schema unchanged; GPU5 excluded for another user'}
(base/'v9-service-launch.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
'''.replace('OLDRELEASE',repr(old['release'])).replace('OLD',repr(old['root'])).replace('RELEASE',repr(stage['server_release'])).replace('PID',str(old['pid']))
data=json.loads(remote(code,host='3090'));output.write_text(json.dumps(data,indent=2));print(json.dumps(data))
