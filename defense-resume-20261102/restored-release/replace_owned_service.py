"""Bounded safe replacement after a completed development replay. No other processes."""
import argparse,json
from pathlib import Path
from remote import remote
ap=argparse.ArgumentParser();ap.add_argument('--previous',required=True);ap.add_argument('--receipt',required=True);ap.add_argument('--expandable-segments',action='store_true');a=ap.parse_args()
r=Path(__file__).resolve().parent;stage=json.loads((r/'v2-staging.json').read_text());old=json.loads((r/a.previous).read_text());replay=json.loads((r/'v2-replay-launch.json').read_text())
assert not(r/a.receipt).exists()
check=json.loads(remote('import pathlib\nprint((pathlib.Path('+repr(replay['root'])+')/"summary.json").read_text())',host='4090'));assert check['phase']=='completed'
code='''import pathlib,os,signal,time,json,hashlib,subprocess,fcntl
base=pathlib.Path('/home/researcher/mirage-defense-pilot-20261023');lock=(base/'service-replacement.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
old=pathlib.Path(OLD);proc=pathlib.Path('/proc')/str(PID)
def alive():
 if not proc.exists():return False
 if(proc/'stat').read_text().split()[2]=='Z':return False
 cmd=(proc/'cmdline').read_bytes().decode().replace(chr(0),' ');assert str(old)in cmd and 'inference_server.py'in cmd and proc.stat().st_uid==os.getuid(),cmd
 return True
assert alive();assert json.loads((old/'status.json').read_text())['phase']=='ready'
for p in(old/'requests').iterdir():assert(p/'response.json').exists()or(p/'failure.json').exists(),str(p)
out=base/('service-preservation-'+str(time.time_ns()));out.mkdir();rows={str(p.relative_to(old)):hashlib.sha256(p.read_bytes()).hexdigest()for p in old.rglob('*')if p.is_file()and p.suffix in {'.json','.jsonl','.log'}};(out/'manifest-before-stop.json').write_text(json.dumps(rows,indent=2))
os.kill(PID,signal.SIGUSR1)
for _ in range(30):
 if not alive():break
 time.sleep(0.5)
else:raise RuntimeError('Own service did not finish; no replacement launched')
assert json.loads((old/'status.json').read_text())['phase']=='stopped_at_request_boundary'
receipt=base/RECEIPT;assert not receipt.exists()
root=base/('inference-service-'+SERVICE_LABEL+'-'+str(time.time_ns()));root.mkdir();release=pathlib.Path(RELEASE)
env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='0,1,2,3',PYTHONPATH=str(base/'repair-deps-v2')+':'+str(release),OMP_NUM_THREADS='4',MKL_NUM_THREADS='4')
if EXPANDABLE:env['PYTORCH_CUDA_ALLOC_CONF']='expandable_segments:True'
with(root/'worker.log').open('xb')as log:
 child=subprocess.Popen(['/opt/whz/conda-envs/webmall-vlm/bin/python','-u',str(release/'inference_server.py'),'--root',str(root),'--token-file',str(base/'transport.token'),'--gate-shadow',str(base/'shadow-preflight-1792761125821027588/status.json')],cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
result={'pid':child.pid,'root':str(root),'release':str(release),'preserved':str(out),'time':time.time(),'old_stopped_at_request_boundary':True,'actor_changes':False,'allocator_expandable_segments':EXPANDABLE};receipt.write_text(json.dumps(result,indent=2));print(json.dumps(result))
'''.replace('OLD',repr(old['root'])).replace('PID',str(old['pid'])).replace('RELEASE',repr(stage['server_release'])).replace('RECEIPT',repr(a.receipt)).replace('SERVICE_LABEL',repr(a.receipt.split('-')[0])).replace('EXPANDABLE',repr(a.expandable_segments))
result=json.loads(remote(code));(r/a.receipt).write_text(json.dumps(result,indent=2));print(json.dumps(result))
