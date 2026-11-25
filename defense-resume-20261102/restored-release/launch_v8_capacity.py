"""Use newly authorized idle GPUs, preserving the failed request and native math."""
import json
from pathlib import Path
from remote import remote

here = Path(__file__).resolve().parent
out = here / 'v8-service-launch.json'
assert not out.exists(), 'Inspect existing service rather than launching twice'
old = json.loads((here / 'v7-service-launch.json').read_text())
stage = json.loads((here / 'v2-staging.json').read_text())
preserved = json.loads((here / 'v3.6.2-online-oom-preservation.json').read_text())
formal = json.loads((here / 'v3.6.2-vwa-resume.json').read_text())
check = json.loads(remote('''import pathlib,json
p=pathlib.Path('/proc')/str(PID)
print(json.dumps({'exited':not p.exists()or(p/'stat').read_text().split()[2]=='Z','phase':json.loads((pathlib.Path(ROOT)/'status.json').read_text())['phase']}))
'''.replace('PID', str(formal['pid'])).replace('ROOT', repr(formal['root'])), host='4090'))
assert check == {'exited': True, 'phase': 'technical_failure'}
code = '''import pathlib,json,os,ast,hashlib,signal,time,subprocess,fcntl
base=pathlib.Path('/home/researcher/mirage-defense-pilot-20261023')
lock=(base/'service-replacement.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
old=pathlib.Path(OLD);release=pathlib.Path(RELEASE);oldrelease=pathlib.Path(OLDRELEASE)
assert pathlib.Path(PRESERVED).exists()
receipt=base/'v8-service-launch.json';assert not receipt.exists()
def methods(path,names):
 tree=ast.parse(path.read_text());return {n.name:ast.dump(n,include_attributes=False)for n in ast.walk(tree)if isinstance(n,ast.FunctionDef)and n.name in names}
assert methods(oldrelease/'defense/qwen_backend.py',{'generate','judge'})==methods(release/'defense/qwen_backend.py',{'generate','judge'})
assert methods(oldrelease/'inference_server.py',{'do_POST','do_GET','authorized','send'})==methods(release/'inference_server.py',{'do_POST','do_GET','authorized','send'})
assert (oldrelease/'defense/schema.py').read_bytes()==(release/'defense/schema.py').read_bytes()
assert json.loads((old/'status.json').read_text())['phase']=='ready'
for request in(old/'requests').iterdir():assert(request/'response.json').exists()or(request/'failure.json').exists()
proc=pathlib.Path('/proc')/str(PID)
assert proc.stat().st_uid==os.getuid()
cmd=(proc/'cmdline').read_bytes().decode().replace(chr(0),' ')
assert str(old)in cmd and 'inference_server.py'in cmd
for gpu in range(4,8):
 used=int(subprocess.check_output(['nvidia-smi',f'--id={gpu}','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).strip())
 assert used<16,('Newly authorized GPU no longer idle',gpu,used)
archive=base/('service-preservation-v8-'+str(time.time_ns()));archive.mkdir()
hashes={str(p.relative_to(old)):hashlib.sha256(p.read_bytes()).hexdigest()for p in old.rglob('*')if p.is_file()}
(archive/'before-stop-hashes.json').write_text(json.dumps(hashes,indent=2))
os.kill(PID,signal.SIGUSR1)
for _ in range(40):
 if not proc.exists()or(proc/'stat').read_text().split()[2]=='Z':break
 time.sleep(0.5)
else:raise RuntimeError('Own service did not stop at boundary')
assert json.loads((old/'status.json').read_text())['phase']=='stopped_at_request_boundary'
root=base/('inference-service-v8-'+str(time.time_ns()));root.mkdir()
env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='0,1,2,3,4,5,6,7',PYTHONPATH=str(base/'repair-deps-v2')+':'+str(release),OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True')
with(root/'worker.log').open('xb')as log:
 child=subprocess.Popen(['/opt/whz/conda-envs/webmall-vlm/bin/python','-u',str(release/'inference_server.py'),'--root',str(root),'--token-file',str(base/'transport.token'),'--gate-shadow',str(base/'shadow-preflight-1792761125821027588/status.json'),'--placement','balanced'],cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
result={'pid':child.pid,'root':str(root),'release':str(release),'previous':str(old),'preserved':str(archive),'time':time.time(),'physical_gpus':list(range(8)),'placement':'balanced','old_stopped_at_request_boundary':True,'native_generate_and_judge_ast_identical':True,'request_handling_ast_identical':True,'schema_identical':True,'actor_changes':False,'allocator_expandable_segments':True,'authorization':'User explicitly permitted idle3090cards;4–7were checked idle immediately before launch;0–3owned by this task only'}
receipt.write_text(json.dumps(result,indent=2));print(json.dumps(result))
'''.replace('OLDRELEASE', repr(old['release'])).replace('OLD', repr(old['root'])).replace('RELEASE', repr(stage['server_release'])).replace('PRESERVED', repr(preserved['service']['root'])).replace('PID', str(old['pid']))
data = json.loads(remote(code, host='3090'))
out.write_text(json.dumps(data, indent=2), encoding='utf-8')
print(json.dumps(data))
