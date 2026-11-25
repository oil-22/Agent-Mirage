"""Read-only full candidate identity, pinned public manifest and CPU runtime audit."""
import hashlib,json,time
from pathlib import Path
from remote import remote

CODE=r'''
import pathlib,json,hashlib,subprocess,urllib.request,time,os
root=pathlib.Path('/data/llms/UI-TARS-1.5-7B')
evidence=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023/uitars-identity-'+str(time.time_ns()));evidence.mkdir()
def save(name,value):(evidence/name).write_text(json.dumps(value,indent=2))
manifest=json.loads((root/'webmall_download_manifest.json').read_bytes())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
weights=[]
for v in manifest['weights']:
 p=root/v['file'];actual=sha(p)
 weights.append(dict(v,actual_sha256=actual,actual_bytes=p.stat().st_size,manifest_match=actual==v['sha256'] and p.stat().st_size==v['bytes']))
 save('weights-progress.json',weights)
metadata={p.name:sha(p) for p in sorted(root.iterdir()) if p.is_file() and p.suffix in ['.json','.txt']}
official={}
try:
 url='https://huggingface.co/api/models/'+manifest['repo']+'/revision/'+manifest['revision']+'?blobs=true'
 with urllib.request.urlopen(url,timeout=30) as r:official=json.loads(r.read())
 siblings={v['rfilename']:v for v in official.get('siblings',[])}
 for v in weights:
  upstream=siblings.get(v['file'],{}).get('lfs',{}).get('sha256')
  v['pinned_upstream_sha256']=upstream;v['pinned_upstream_match']=upstream==v['actual_sha256'] if upstream else None
except Exception as e:official={'error':repr(e)}
save('identity-before-runtime.json',{'weights':weights,'metadata_sha256':metadata,'official':official,'manifest':manifest})
runtime_code="""import json,torch,transformers,importlib.metadata
from transformers import AutoProcessor,Qwen2_5_VLForConditionalGeneration
p=AutoProcessor.from_pretrained('/data/llms/UI-TARS-1.5-7B',local_files_only=True)
print(json.dumps({'torch':torch.__version__,'transformers':transformers.__version__,'lmformatenforcer':importlib.metadata.version('lm-format-enforcer'),'processor_class':type(p).__name__,'image_processor':p.image_processor.to_dict(),'tokenizer_class':type(p.tokenizer).__name__,'tokenizer_model_max_length':p.tokenizer.model_max_length,'chat_template':p.chat_template,'model_class_imported':Qwen2_5_VLForConditionalGeneration.__name__,'model_loaded':False}))"""
env=dict(os.environ,OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',CUDA_VISIBLE_DEVICES='')
try:
 p=subprocess.run(['/data/researcher/venvs/qwen35-9b-full-20261019/bin/python','-c',runtime_code],capture_output=True,text=True,timeout=120,env=env)
 runtime={'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
except subprocess.TimeoutExpired as e:
 runtime={'returncode':None,'error':'CPU runtime probe timeout120seconds','stdout':str(e.stdout),'stderr':str(e.stderr)}
result={'time':time.time(),'remote_evidence':str(evidence),'manifest':manifest,'weights':weights,'metadata_sha256':metadata,'official_api':{'id':official.get('id'),'sha':official.get('sha'),'error':official.get('error')},'runtime':runtime,'scope':'Full local weight reread and pinned public hash comparison; CPU processor load only. No model inference, GPU allocation, external paid call, or readiness claim.'}
save('result.json',result)
print(json.dumps(result))
'''
if __name__=='__main__':
 base=Path(__file__).resolve().parent/'uitars-verifier-preparation'
 out=base/('identity-full-'+str(time.time_ns())+'.json')
 raw=remote(CODE,host='4090',timeout=720).encode();data=json.loads(raw)
 out.write_bytes(raw)
 marker={'path':str(out),'sha256':hashlib.sha256(raw).hexdigest(),'all_weights_local_match':all(v['manifest_match']for v in data['weights']),'all_weights_pinned_match':all(v.get('pinned_upstream_match')is True for v in data['weights']),'runtime_returncode':data['runtime']['returncode']}
 (base/'identity-current.json').write_text(json.dumps(marker,indent=2),encoding='utf8')
 print(json.dumps(marker));print(json.dumps(data['official_api']));print(json.dumps(data['runtime']))
