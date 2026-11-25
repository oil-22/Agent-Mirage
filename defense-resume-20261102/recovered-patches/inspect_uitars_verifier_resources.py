"""Read-only metadata/resources for a separate UI-TARS verifier candidate."""
import hashlib,json,time
from pathlib import Path
from remote import remote
CODE=r'''
import pathlib,json,os,pwd,hashlib,subprocess
roots=[pathlib.Path('/data/llms/UI-TARS-1.5-7B'),pathlib.Path('/opt/whz/llms/UI-TARS-1.5-7B')]
models=[]
for root in roots:
 if not root.exists():continue
 files={}
 for n in ['config.json','generation_config.json','preprocessor_config.json','tokenizer_config.json','model.safetensors.index.json']:
  p=root/n
  if p.exists():
   v=json.loads(p.read_bytes());files[n]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'data':v if n not in ['tokenizer_config.json','model.safetensors.index.json']else {k:v.get(k)for k in (['tokenizer_class','model_max_length','chat_template']if n=='tokenizer_config.json'else['metadata'])}}
 cards={n:(root/n).read_text(errors='replace')[:16000]for n in ['README.md','LICENSE','LICENSE.txt']if(root/n).exists()}
 models.append({'path':str(root),'resolved_path':str(root.resolve()),'files':files,'cards':cards,'weight_files':[{'name':p.name,'bytes':p.stat().st_size}for p in sorted(root.glob('*.safetensors'))]})
processes=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  if p.stat().st_uid!=os.getuid():continue
  parts=(p/'cmdline').read_bytes().split(b'\0');cmd=' '.join(x.decode(errors='replace')for x in parts)
  if not any(x in cmd for x in ['inference_server.py','run_vwa_pilot.py','uitars','UI-TARS','qwen9-scale','qwen9-remaining']):continue
  if b'python3'in parts and b'-'in parts:continue
  processes.append({'pid':int(p.name),'uid':p.stat().st_uid,'cmd':cmd})
 except OSError:pass
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=20);return{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr[:500]}
print(json.dumps({'uid':os.getuid(),'owner':pwd.getpwuid(os.getuid()).pw_name,'models':models,'owned_relevant_processes':processes,'gpu':run(['nvidia-smi','--query-gpu=index,name,memory.total,memory.used,utilization.gpu','--format=csv,noheader']),'gpu_processes':run(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader']),'scope':'Read only; no model or queue launched/stopped, metadata hashes only, no weights validation or verifier readiness claim.'}))
'''
if __name__=='__main__':
 import sys
 host=sys.argv[1];assert host in ['3090','4090'];d=json.loads(remote(CODE,host=host,timeout=50))
 r=Path(__file__).resolve().parent/'uitars-verifier-preparation';r.mkdir(exist_ok=True)
 out=r/(host+'-metadata-'+str(time.time_ns())+'.json');out.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps({'snapshot':str(out),'models':[{'path':v['path'],'architecture':v['files'].get('config.json'),'weights':v['weight_files']}for v in d['models']],'owned_processes':d['owned_relevant_processes'],'gpu':d['gpu']},ensure_ascii=True))
