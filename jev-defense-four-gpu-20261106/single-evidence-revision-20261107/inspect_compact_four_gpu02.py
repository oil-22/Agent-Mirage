"""Read only actual new attempt processes, journals, requests and terminal seals."""
import hashlib
import importlib.util
import json
from pathlib import Path
import time

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'gpu-compact-progress-evidence-02'/str(time.time_ns());OUT.mkdir(parents=True,exist_ok=False)
spec=importlib.util.spec_from_file_location('readonly_remote',ROOT.parents[1]/'defense-resume-20261102/restored-release/remote.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
code='''import hashlib,json,os,pathlib,subprocess,time
root=pathlib.Path('/home/researcher/jev-defense-four-gpu-20261106/single-evidence-revision-20261107/gpu-compact-four-first-attempts-02')
package=pathlib.Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/single-jev-9b-compact-preflight-02')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def identity(pid):
 p=pathlib.Path('/proc')/str(pid)
 if not p.exists():return None
 tail=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(b'\\0',b' ').decode().strip(),'start_ticks':tail[19],'state':tail[0]}
out={'read_only':True,'snapshot_unix':time.time(),'root_exists':root.exists(),'new_model_health_or_GUI_calls':0}
if root.exists():
 out['files']=[str(p.relative_to(root))for p in root.rglob('*')if p.is_file()and p.suffix!='.tensor']
 for name in ['process.json','worker-launch.json','exit.json','launcher-failure.json','postexit-resource-failure.json','worker/claim.json','worker/current-weight-identity.json','worker/terminal.json','worker/failure.json']:
  p=root/name
  if p.is_file():out[name]=json.loads(p.read_bytes())
 for name in ['process.json','worker-launch.json']:
  if name in out:
   expected=out[name].get('identity',out[name]);out['actual_'+name]=identity(expected['pid'])
 out['results']=[json.loads(p.read_bytes())for p in sorted((root/'worker').glob('r*/result.json'))]
 out['worker_log_tail']=(root/'worker.log').read_text(errors='replace')[-2500:]if(root/'worker.log').is_file()else None
 out['worker_loaded']=(root/'worker/loaded.json').is_file()
 if out['worker_loaded']:
  loaded=json.loads((root/'worker/loaded.json').read_bytes())
  out['loaded_summary']={k:loaded.get(k)for k in ['model_class','load_seconds','base_model','jev_relationship','actual_attention_backends']}
  out['loaded_summary']['actual_cuda_tensors']=len(loaded['actual_cuda_tensors'])
 if(root/'terminal-manifest.json').is_file():
  seal=json.loads((root/'terminal-manifest.json').read_bytes())
  out['terminal_manifest_sha256']=sha(root/'terminal-manifest.json')
  out['terminal_all_files_verified']=all(sha(root/name)==h for name,h in seal.items())
  out['terminal_file_count']=len(seal)
 for name in ['journal.jsonl','worker/journal.jsonl']:
  p=root/name
  if p.is_file():
   raw=p.read_bytes();lines=raw.splitlines();previous='0'*64;count=0;last=None
   for line in lines:
    event=json.loads(line);supplied=event.pop('sha256')
    seq=event.get('seq',event.get('index'));prev=event.get('previous',event.get('previous_sha256'))
    assert seq==count and prev==previous
    canonical=json.dumps(event,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
    assert hashlib.sha256(canonical).hexdigest()==supplied
    previous=supplied;count+=1;last=event
   out[name]={'events':count,'head':previous,'raw_sha256':hashlib.sha256(raw).hexdigest(),'last':last}
out['gpu_rows']=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits']).decode().splitlines()
out['compute_rows']=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_memory','--format=csv,noheader,nounits']).decode().splitlines()
out['prelaunch_failures']=[str(p)for p in(package/'prelaunch-failures').glob('*/failure.json')]
print(json.dumps(out,ensure_ascii=False))
'''
(OUT/'remote-readonly.py').write_text(code,encoding='utf-8')
reply=module.remote(code,host='3090',timeout=90);value=json.loads(reply)
(OUT/'snapshot.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(OUT/'seal.json').write_text(json.dumps({p.name:sha(p)for p in OUT.iterdir()if p.is_file()},indent=2)+'\n',encoding='utf-8')
summary={k:value.get(k)for k in ['root_exists','worker_loaded','loaded_summary','actual_worker-launch.json','exit.json','worker/terminal.json','worker/failure.json','results','compute_rows','prelaunch_failures','terminal_all_files_verified','terminal_file_count']}
summary.update(local_snapshot=str(OUT/'snapshot.json'),snapshot_sha256=sha(OUT/'snapshot.json'))
print(json.dumps(summary,ensure_ascii=False))
