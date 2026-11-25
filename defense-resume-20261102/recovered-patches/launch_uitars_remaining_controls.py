"""Once-only remaining19 development controls; parent failed control is never repeated."""
import base64,hashlib,json
from pathlib import Path
from remote import remote

base=Path(__file__).resolve().parent;prep=base/'uitars-verifier-preparation'
receipt=prep/'real-remaining-controls-launch.json';assert not receipt.exists(),'Inspect existing receipt; never duplicate'
parent=json.loads((prep/'real-loader-retry-launch.json').read_bytes())
preservation=json.loads((prep/'real-contract-failure-preservation.json').read_bytes())
assert preservation['original_root']==parent['root']and preservation['consumed_model_calls']==2
assert preservation['case']=='page5-readiness'and preservation['case_budget_exhausted']
cpu=json.loads((prep/'cpu-extension-retry-launch.json').read_bytes())
proof=json.loads((prep/'remaining-controls-static-proof.json').read_bytes())
runner=(base/'uitars_remaining_controls.py').read_bytes()
assert hashlib.sha256(runner).hexdigest()==proof['runner_sha256']
code=r'''
import pathlib,json,hashlib,os,fcntl,subprocess,shutil,base64,time
base=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');assert os.getuid()==1015
startup=(base/'uitars-real-preflight-start.lock').open('a');fcntl.flock(startup,fcntl.LOCK_EX|fcntl.LOCK_NB)
active=base/'uitars-real-remaining-controls-active.json';assert not active.exists(),'Recover existing receipt'
old=pathlib.Path(PARENT['root']);assert not pathlib.Path('/proc',str(PARENT['pid'])).exists()
seal=pathlib.Path(PRESERVE['sealed_manifest']);assert hashlib.sha256(seal.read_bytes()).hexdigest()==PRESERVE['sealed_manifest_sha256']
for n,h in json.loads(seal.read_bytes()).items():
 assert hashlib.sha256((old/n).read_bytes()).hexdigest()==h
 assert hashlib.sha256((pathlib.Path(PRESERVE['preserved_root'])/n).read_bytes()).hexdigest()==h
assert json.loads((old/'technical-failure.json').read_bytes())['model_calls']==2
assert not (old/'results.json').exists()
cases=json.loads((old/'public-requests.json').read_bytes());ids=[c['id']for c in cases if c['id']!='page5-readiness']
assert len(cases)==20 and len(ids)==19 and len(set(ids))==19
assert {p.name for p in old.iterdir()if p.is_dir()and(p/'source-request.json').exists()}=={'page5-readiness'}
assert hashlib.sha256((old/'release/defense/uitars_backend.py').read_bytes()).hexdigest()==PROOF['backend_sha256']
assert hashlib.sha256((old/'release/defense/core.py').read_bytes()).hexdigest()==PROOF['core_sha256']
lockpath=pathlib.Path('/data/researcher/crossmodel-injection-attention-20261025/glm-gpu3.lock');lock=lockpath.open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
apps=subprocess.check_output(['nvidia-smi','--id=3','--query-compute-apps=pid','--format=csv,noheader,nounits']).decode().strip();assert not apps,apps
free=int(subprocess.check_output(['nvidia-smi','--id=3','--query-gpu=memory.free','--format=csv,noheader,nounits']).decode());assert free>23500
assert shutil.disk_usage(base).free>5*1024**3
root=base/('uitars-real-remaining-controls-'+str(time.time_ns()));root.mkdir()
for p in old.glob('*.png'):shutil.copyfile(p,root/p.name)
for n in ['public-requests.json','cpu-result.json','pinned-metadata-audit.json']:shutil.copyfile(old/n,root/n)
shutil.copytree(old/'release',root/'release');shutil.copytree(old/'deps',root/'deps')
worker=root/'release/uitars_remaining_controls.py';worker.write_bytes(base64.b64decode(RUNNER));assert hashlib.sha256(worker.read_bytes()).hexdigest()==PROOF['runner_sha256']
record={k:v for k,v in PARENT.items()if k not in {'pid','command','log','root','time','retry_origin','repair_scope'}}
record.update(time=time.time(),root=str(root),cases=19,only_case_ids=ids,parent_consumed_calls=2,max_calls=38,original_total_model_call_limit=40,runner_sha256=PROOF['runner_sha256'],retry_origin=PRESERVE,loader_failure_origin=PARENT['retry_origin'],gpu_free_mib_before=free,scope='Remaining19 untouched development inputs. Original failed page5-readiness skipped forever; exhausted citation/schema failures are preserved failed cases, not accepted. No additional retries, GUI, official score or paidAPI.')
(root/'parent-origin.json').write_text(json.dumps(PRESERVE,indent=2))
command=['/data/researcher/venvs/qwen35-9b-full-20261019/bin/python','-u',str(worker),'--root',str(root)]
env=dict(os.environ,CUDA_VISIBLE_DEVICES='3',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',TOKENIZERS_PARALLELISM='false',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONPATH=str(root/'deps')+':'+str(root/'release'),MIRAGE_GPU_LOCK_FD=str(lock.fileno()))
(root/'launch.json').write_text(json.dumps(record,indent=2));log=root/'worker.log'
with log.open('xb')as f:p=subprocess.Popen(command,cwd=root/'release',env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(lock.fileno(),))
record.update(pid=p.pid,command=command,log=str(log));(root/'launch.json').write_text(json.dumps(record,indent=2))
with active.open('x')as f:json.dump(record,f,indent=2)
lock.close();print(json.dumps(record))
'''
bindings={'PARENT':parent,'PRESERVE':preservation,'PROOF':proof,'RUNNER':base64.b64encode(runner).decode()}
record=json.loads(remote('\n'.join(k+'='+repr(v)for k,v in bindings.items())+'\n'+code,host='4090',timeout=50))
receipt.write_text(json.dumps(record,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in record.items()if k not in {'pinned_weights','retry_origin','loader_failure_origin'}}))
