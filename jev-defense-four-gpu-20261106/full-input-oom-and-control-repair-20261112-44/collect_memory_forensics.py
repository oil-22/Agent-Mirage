"""Read-only source-bound diagnosis of R40's sealed prefill OOM."""
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
PRIOR=HERE.parent/'remaining28-source-reference-gui-20261110-40'
sys.path.insert(0,str(PRIOR))
import orchestrate as original


SOURCE=r'''
from pathlib import Path
import ast,collections,hashlib,json,os,subprocess,time
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return {'sha256':sha(p),'bytes':p.stat().st_size,'value':json.loads(p.read_bytes())}
r=Path(ROOT);out={'time':time.time(),'uid':os.getuid(),'read_only':True,'new_model_GUI_calls':0,'root':str(r),'files':{}}
for name in ['worker/loaded.json','worker/new-placement.json','worker/terminal.json','worker/failure.json','exit.json']:
 p=r/name
 if p.is_file():out['files'][name]=read(p)
for p in sorted((r/'worker').glob('prefill-residency-*.json'))[-3:]:out['files'][str(p.relative_to(r))]=read(p)
for request in ['0131','0133','0134']:
 folder=r/'worker/requests'/request;seal=json.loads((folder/'seal.json').read_bytes())
 for name in ['prepared.json','first-forward.json','effective-generation.json','actual-generation.json','failed-memory.json','failure-memory.json','forward-count.json','failure.json']:
  p=folder/name
  if p.is_file():
   assert sha(p)==seal[name]
   out['files'][str(p.relative_to(r))]=read(p)
out['generation_records']=[]
for folder in sorted((r/'worker/requests').glob('*')):
 if not folder.is_dir():continue
 seal=json.loads((folder/'seal.json').read_bytes());wire=json.loads((folder/'external-wire.json').read_bytes())
 assert sha(folder/'external-wire.json')==seal['external-wire.json']
 payload=wire['payload'];op='evidence'if'image_base64'in payload else payload['operation']
 row={'request':folder.name,'operation':op,'run_id':wire['trajectory_id'],'seal_sha256':sha(folder/'seal.json'),'failed':(folder/'failure.json').exists()}
 p=folder/'actual-generation.json'
 if p.is_file():
  assert sha(p)==seal[p.name]
  record=json.loads(p.read_bytes());row['actual_generation_sha256']=sha(p)
  row.update({k:record[k]for k in ['input_tokens','output_tokens','natural_EOS','actual_forward_calls']})
  effective=json.loads((folder/'effective-generation.json').read_bytes());assert sha(folder/'effective-generation.json')==seal['effective-generation.json']
  eos=effective['eos_token_id'];eos=[eos]if isinstance(eos,int)else eos
  assert row['natural_EOS']and record['output_ids'][-1]in eos and len(record['output_ids'])==row['output_tokens']
  row['max_new_tokens']=effective['max_new_tokens']
 out['generation_records'].append(row)
native=Path('/opt/whz/conda-envs/webmall-vlm/lib/python3.11/site-packages/transformers/models/qwen3_5/modeling_qwen3_5.py')
source=native.read_bytes();loaded=out['files']['worker/loaded.json']['value']
assert hashlib.sha256(source).hexdigest()==loaded['native_model_source_sha256']
out['native_source']={'path':str(native),'sha256':sha(native),'text':source.decode()}
out['system_RAM']={line.split(':')[0]:line.split(':')[1].strip()for line in Path('/proc/meminfo').read_text().splitlines()if line.startswith(('MemTotal:','MemAvailable:','SwapTotal:','SwapFree:'))}
out['GPU']=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True,timeout=12)
out['compute']=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True,timeout=12)
print(json.dumps(out,ensure_ascii=True))
'''


def main():
 original.admitted()
 target=HERE/('memory-forensics-'+str(time.time_ns()));target.mkdir()
 try:
  raw,operation=original.remote('3090','ROOT='+repr(original.OUTPUT)+'\n'+SOURCE,'R44-native-full-input-OOM-forensics-no-replay',timeout=50)
  value=json.loads(raw);original.save(target/'forensics.json',value)
  original.save(target/'operation.json',{'path':str(operation)})
  (target/'native-modeling-qwen3_5.py').write_text(value['native_source']['text'],encoding='utf8')
  original.save(target/'scope.json',{'source_sha256':original.sha(Path(__file__)),'failed_GUI_and_request_not_retried':True,'new_model_GUI_calls':0})
  original.save(target/'seal.json',{p.name:original.sha(p)for p in target.iterdir()if p.is_file()})
 except BaseException as exc:
  original.save(target/'inspection-failure.json',{'type':type(exc).__name__,'message':str(exc)});raise
 first=value['files']['worker/requests/0134/first-forward.json']['value']
 sessions={name:{k:row['value'].get(k)for k in ['session','input_tokens','success','visited_groups','same_native_execution_device_map','partial_prefill_seconds','memory_after_restore']}for name,row in value['files'].items()if 'prefill-residency-'in name}
 print(json.dumps({'evidence':str(target),'failed_input':first,'recent_sessions':sessions,'RAM':value['system_RAM'],
  'replies':sum(not p['failed']for p in value['generation_records']),'EOS':sum(p.get('natural_EOS',False)for p in value['generation_records']),
  'input_tokens':sum(p.get('input_tokens',0)for p in value['generation_records']),
  'output_tokens':sum(p.get('output_tokens',0)for p in value['generation_records'])},ensure_ascii=True))


if __name__=='__main__':main()
