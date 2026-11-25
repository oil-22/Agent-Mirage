"""Once-only isolated20-control BF16/SDPA replay on verified free owned4090GPU3."""
import argparse,base64,hashlib,json
from pathlib import Path
from remote import remote
ap=argparse.ArgumentParser();ap.add_argument('--retry-loader',action='store_true');args=ap.parse_args()
base=Path(__file__).resolve().parent;prep=base/'uitars-verifier-preparation';receipt=prep/('real-loader-retry-launch.json'if args.retry_loader else'real-preflight-launch.json');assert not receipt.exists(),'Inspect existing real preflight; never duplicate'
cpu_launch=json.loads((prep/'cpu-extension-retry-launch.json').read_bytes());cpu=json.loads((prep/'cpu-extension-retry-result.json').read_bytes());assert cpu['completed']and cpu['result']['cases']==20 and cpu['result']['all_inputs_with_original_output_budget_fit_declared_context']
frozen=json.loads((prep/'frozen-controls-current.json').read_bytes());folder=Path(frozen['folder']);review=json.loads((folder/'PRIVATE-independent-review.json').read_bytes());assert review['ready_for_isolated_real_model_preflight_only']
identity=json.loads(Path(json.loads((prep/'identity-current.json').read_bytes())['path']).read_bytes());upstream=json.loads((prep/'pinned-upstream-api-20261027.json').read_bytes());siblings={v['rfilename']:v for v in upstream['siblings']}
weights=[]
for w in identity['weights']:
 assert w['manifest_match']and siblings[w['file']]['lfs']['sha256']==w['actual_sha256'];weights.append({'file':w['file'],'bytes':w['actual_bytes'],'sha256':w['actual_sha256']})
runner=(base/'uitars_real_preflight.py').read_bytes();proof=json.loads((prep/('loader-repair-static-proof.json'if args.retry_loader else'real-replay-static-protocol-proof.json')).read_bytes());assert proof['runner_sha256']==hashlib.sha256(runner).hexdigest()
preservation=json.loads((prep/'real-loader-failure-preservation.json').read_bytes())if args.retry_loader else None
backend=(base/'defense/uitars_backend.py').read_bytes()
if args.retry_loader:assert proof['backend_sha256']==hashlib.sha256(backend).hexdigest()and proof['generation_and_model_load_call_unchanged']
code=r'''
import pathlib,json,os,fcntl,subprocess,time,hashlib,base64,shutil
base=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');assert os.getuid()==1015
startup=(base/'uitars-real-preflight-start.lock').open('a');fcntl.flock(startup,fcntl.LOCK_EX|fcntl.LOCK_NB)
active=base/('uitars-real-loader-retry-active.json'if RETRY else'uitars-real-preflight-active.json');assert not active.exists(),'Recover existing receipt instead of relaunch'
if RETRY:
 old=pathlib.Path(PRESERVATION['original_root']);sealed=pathlib.Path(PRESERVATION['sealed_manifest']);assert hashlib.sha256(sealed.read_bytes()).hexdigest()==PRESERVATION['sealed_manifest_sha256']
 assert json.loads((old/'technical-failure.json').read_bytes())['model_calls']==0
 assert not pathlib.Path('/proc',str(json.loads((old/'launch.json').read_bytes())['pid'])).exists()
 for n,h in json.loads(sealed.read_bytes()).items():
  assert hashlib.sha256((old/n).read_bytes()).hexdigest()==h
  assert hashlib.sha256((pathlib.Path(PRESERVATION['preserved_root'])/n).read_bytes()).hexdigest()==h
source=pathlib.Path(CPU['root']);raw=(source/'cpu-result.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==CPU_RESULT_SHA
c=json.loads(raw);assert c['cases']==20 and c['all_inputs_with_original_output_budget_fit_declared_context']
assert hashlib.sha256((source/'public-requests.json').read_bytes()).hexdigest()==PUBLIC_SHA
assert not pathlib.Path('/proc',str(CPU['pid'])).exists()
lockpath=pathlib.Path('/data/researcher/crossmodel-injection-attention-20261025/glm-gpu3.lock');lock=lockpath.open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
gpu_processes=subprocess.check_output(['nvidia-smi','--id=3','--query-compute-apps=pid','--format=csv,noheader,nounits']).decode().strip();assert not gpu_processes,gpu_processes
free=int(subprocess.check_output(['nvidia-smi','--id=3','--query-gpu=memory.free','--format=csv,noheader,nounits']).decode());assert free>23500
assert shutil.disk_usage(base).free>5*1024**3
root=base/(('uitars-real-loader-retry-'if RETRY else'uitars-real-preflight-')+str(time.time_ns()));root.mkdir()
for p in source.glob('*.png'):shutil.copyfile(p,root/p.name)
for n in ['public-requests.json','cpu-result.json','pinned-metadata-audit.json']:shutil.copyfile(source/n,root/n)
shutil.copytree(source/'release',root/'release');shutil.copytree(source/'deps',root/'deps')
worker=root/'release/uitars_real_preflight.py';worker.write_bytes(base64.b64decode(RUNNER));assert hashlib.sha256(worker.read_bytes()).hexdigest()==RUNNER_SHA
for n,h in CPU['code_and_input_sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
if RETRY:
 (root/'release/defense/uitars_backend.py').write_bytes(base64.b64decode(BACKEND))
 assert hashlib.sha256((root/'release/defense/uitars_backend.py').read_bytes()).hexdigest()==BACKEND_SHA
 (root/'retry-origin.json').write_text(json.dumps(PRESERVATION,indent=2))
assert hashlib.sha256((root/'release/defense/core.py').read_bytes()).hexdigest()==CORE_SHA
record={'time':time.time(),'root':str(root),'cpu_root':str(source),'cpu_result_sha256':CPU_RESULT_SHA,'pinned_revision':REVISION,'pinned_weights':WEIGHTS,'uid':os.getuid(),'physical_gpu':3,'gpu_free_mib_before':free,'lock':str(lockpath),'runner_sha256':RUNNER_SHA,'core_sha256':CORE_SHA,'model':'ByteDance-Seed/UI-TARS-1.5-7B','dtype':'BF16','attention_backend':'sdpa','cases':20,'max_calls':40,'max_format_retries_per_case':1,'max_output_tokens_per_call':4096,'public_requests_sha256':PUBLIC_SHA,'scope':'Isolated nonblind development replay, no actor calls, GUI actions, official scoring,27B fallback, formal outcome overwrite or semantic labels.'}
if RETRY:record.update(retry_origin=PRESERVATION,backend_sha256=BACKEND_SHA,repair_scope='Actual CUDA tensor device verification when hf_device_map metadata absent; flush exception before final seal. Generation/model load contract unchanged.')
command=['/data/researcher/venvs/qwen35-9b-full-20261019/bin/python','-u',str(worker),'--root',str(root)]
env=dict(os.environ,CUDA_VISIBLE_DEVICES='3',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',TOKENIZERS_PARALLELISM='false',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONPATH=str(root/'deps')+':'+str(root/'release'),MIRAGE_GPU_LOCK_FD=str(lock.fileno()))
(root/'launch.json').write_text(json.dumps(record,indent=2));log=root/'worker.log'
with log.open('xb')as f:p=subprocess.Popen(command,cwd=root/'release',env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(lock.fileno(),))
record.update(pid=p.pid,command=command,log=str(log));(root/'launch.json').write_text(json.dumps(record,indent=2))
with active.open('x')as f:json.dump(record,f,indent=2)
lock.close();print(json.dumps(record))
'''
bindings={'CPU':cpu_launch,'CPU_RESULT_SHA':cpu['result_sha256'],'PUBLIC_SHA':hashlib.sha256((folder/'public-requests.json').read_bytes()).hexdigest(),'RUNNER':base64.b64encode(runner).decode(),'RUNNER_SHA':hashlib.sha256(runner).hexdigest(),'CORE_SHA':proof['core_sha256'],'WEIGHTS':weights,'REVISION':upstream['sha']}
bindings.update(RETRY=args.retry_loader,PRESERVATION=preservation,BACKEND=base64.b64encode(backend).decode(),BACKEND_SHA=hashlib.sha256(backend).hexdigest())
record=json.loads(remote('\n'.join(k+'='+repr(v)for k,v in bindings.items())+'\n'+code,host='4090',timeout=50))
receipt.write_text(json.dumps(record,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in record.items()if k!='pinned_weights'}))
