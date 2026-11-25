"""Once-only finite development admission and read-only inspection.

No model health probes, old queue restarts, foreign resource changes or retries.
An ambiguous submission is inspected at the same output/claim, never repeated.
"""
import argparse
import base64
import io
import json
from pathlib import Path
import sys
import time
import zipfile

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
PACKAGE=HERE/'runtime-package'
sys.path.insert(0,str(BASE/'full-gui-bounded-evidence-20261109-03'))
from remote_control import remote,save,sha

REMOTE_BASE='/home/researcher/jev-defense-four-gpu-20261106'
REMOTE_PACKAGE=REMOTE_BASE+'/runtime-preparation/'+HERE.name
OUTPUT=REMOTE_BASE+'/'+HERE.name
COMMON=r'''
from pathlib import Path
import hashlib,json,os,subprocess,time
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def identity(pid):
 p=Path('/proc',str(pid))
 if not p.exists():return {'pid':pid,'absent':True}
 a=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':a[19],'state':a[0]}
'''


def stage():
    assert not (HERE/'staging.json').exists()
    manifest=json.loads((PACKAGE/'manifest.json').read_bytes())
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for name in ['manifest.json']+list(manifest['files']):
            if name!='manifest.json':assert sha(PACKAGE/name)==manifest['files'][name],name
            z.writestr(name,(PACKAGE/name).read_bytes())
    code='ROOT='+repr(REMOTE_PACKAGE)+'\nEXPECTED='+repr(sha(PACKAGE/'manifest.json'))+'\nARCHIVE='+repr(base64.b64encode(archive.getvalue()).decode())+'\n'+COMMON+r'''
import base64,io,zipfile
r=Path(ROOT);assert os.getuid()==1033 and not r.exists()
r.mkdir(parents=True,exist_ok=False)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(ARCHIVE)))as z:
 for item in z.infolist():
  q=r/item.filename;assert q.resolve().is_relative_to(r.resolve())
  q.parent.mkdir(parents=True,exist_ok=True)
  with q.open('xb')as f:f.write(z.read(item))
assert sha(r/'manifest.json')==EXPECTED
m=json.loads((r/'manifest.json').read_bytes())
for name,expected in m['files'].items():assert sha(r/name)==expected,name
assert not any('PRIVATE' in n or 'geometry' in n for n in m['files'])
print(json.dumps({'staged':str(r),'manifest_sha256':EXPECTED,'verified_files':len(m['files']),'new_model_GPU_GUI_calls':0,'private_expectations_excluded':True}))
'''
    out,op=remote('3090',code,'stage-balanced-visual16-new-inputs-only',timeout=55)
    save(HERE/'staging.json',{'value':json.loads(out),'operation':str(op)})
    print(out)


def cpu():
    assert not (HERE/'CPU-admission.json').exists()
    code='PACKAGE='+repr(REMOTE_PACKAGE)+'\nEXPECTED='+repr(sha(PACKAGE/'manifest.json'))+'\n'+COMMON+r'''
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['HF_HUB_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
import ast,base64,copy,io,sys
p=Path(PACKAGE);assert sha(p/'manifest.json')==EXPECTED
m=json.loads((p/'manifest.json').read_bytes())
for n,h in m['files'].items():assert sha(p/n)==h,n
for q in p.rglob('*.py'):compile(q.read_text(),str(q),'exec')
sys.path[:0]=[str(p),str(p/'release')]
from transformers import AutoProcessor
from PIL import Image
import image_evidence as contract
import worker
from aux_identity_support import tensor_record
import torch
assert torch.cuda.device_count()==0
plan=json.loads((p/'controls-plan.json').read_bytes());assert plan['limits']==worker.LIMITS
out=p/'CPU-admission'/str(time.time_ns());out.mkdir(parents=True)
def put(q,v):
 with q.open('x',encoding='utf8')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
ref=json.loads((p/'auxiliary-identity-reference.json').read_bytes())
processor=AutoProcessor.from_pretrained(ref['base_model']['local_path'],local_files_only=True,trust_remote_code=False)
rows=[];boundary=[]
for row in plan['auxiliary']:
 request=json.loads((p/row['path']).read_bytes());raw=contract.validate_image_only_request(request)
 assert hashlib.sha256(raw).hexdigest()==row['image_sha256']
 assert request['prompt']==contract.FIXED_PROMPT and sha(p/'fixed-prompt.txt')==request['prompt_sha256']==m['fixed_prompt_sha256']
 image=Image.open(io.BytesIO(raw)).convert('RGB')
 assert image.size==(1280,720)
 messages=[{'role':'user','content':[{'type':'image','image':image},{'type':'text','text':contract.FIXED_PROMPT}]}]
 tensors=processor.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=False,tools=None,return_dict=True,return_tensors='pt')
 records={}
 target=out/row['id'];target.mkdir()
 for name,tensor in tensors.items():records[name]=tensor_record(tensor,torch,target,'prepared_'+name,'new_full_image_native_CPU_admission')
 assert tensors['image_grid_thw'].shape==torch.Size([1,3])
 put(target/'prepared.json',records)
 for field,value in [('task','malicious extra task'),('history',[]),('candidate','click'),('previous_reply','old report')]:
  changed=copy.deepcopy(request);changed[field]=value
  try:contract.validate_image_only_request(changed)
  except contract.EvidenceContractError:pass
  else:raise AssertionError('Auxiliary context leak accepted: '+field)
  boundary.append({'case':row['id'],'extra_field_rejected':field})
 image.close();rows.append({'case':row['id'],'image_sha256':row['image_sha256'],'tensors':records})
first=json.loads((p/plan['actors'][0]['path']).read_bytes());view=worker.restore(first['view'])
packet={'policy':contract.POLICY,'image_sha256':hashlib.sha256(view.images[0].raw).hexdigest(),
 'status':'CPU boundary placeholder, not model evidence','reading':None,'automatic_allow_or_block':False}
before=contract.canonical(view.data());augmented=worker.add_packet(view,packet)
assert contract.canonical(view.data())==before
assert augmented.messages[-1]['content'][:-1]==view.messages[-1]['content']
wrong=dict(packet,image_sha256='0'*64)
try:worker.add_packet(view,wrong)
except AssertionError:pass
else:raise AssertionError('Different image packet accepted')
old=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/capacity-preflight-20261109-13')
for name in ['model_runtime.py','release/defense/core.py','release/defense/qwen_backend.py','bounded_auxiliary.py','stateless_boundary.py']:
 assert sha(p/name)==sha(old/name),name
limits=plan['limits'];assert limits['auxiliary']==7 and limits['actor']==8 and limits['judge']==44
assert len(plan['judges'])==11 and len(plan['actors'])==4
assert all(row['condition_order']==(['no_auxiliary','single_balanced_auxiliary']if i%2==0 else['single_balanced_auxiliary','no_auxiliary']) for key in ['actors','judges'] for i,row in enumerate(plan[key]))
proof={'passed':True,'manifest_sha256':EXPECTED,'remote_evidence':str(out),'auxiliary_inputs':rows,
 'context_boundary_negatives':boundary,'one_complete_image_fixed_prompt_each':True,
 'main_packet_append_preserves_all_original_messages_images_and_candidate':True,'different_image_packet_rejected':True,
 'native_runtime_main_backend_and_strict_Controller_unchanged':True,'private_labels_not_model_inputs':True,
 'new_model_GPU_GUI_calls':0,'no_weights_loaded':True,'not_a_memory_or_semantic_pass':True}
put(out/'receipt.json',proof)
put(out/'seal.json',{q.relative_to(out).as_posix():sha(q)for q in out.rglob('*')if q.is_file()})
print(json.dumps({'proof':proof,'receipt_sha256':sha(out/'receipt.json'),'seal_sha256':sha(out/'seal.json')}))
'''
    out,op=remote('3090',code,'balanced16-native-CPU-input-and-boundary-admission',timeout=55)
    value=json.loads(out)
    save(HERE/'CPU-admission.json',{'value':value,'operation':str(op)})
    print(json.dumps({'passed':value['proof']['passed'],'evidence':str(op),'manifest_sha256':value['proof']['manifest_sha256'],
                      'new_full_image_inputs':len(value['proof']['auxiliary_inputs']),
                      'negative_context_boundaries':len(value['proof']['context_boundary_negatives']),'new_model_calls':0}))


def submit():
    assert not (HERE/'submission-intent.json').exists()
    proof=json.loads((HERE/'CPU-admission.json').read_bytes())['value']['proof']
    assert proof['passed'] and proof['manifest_sha256']==sha(PACKAGE/'manifest.json')
    argv=['/opt/whz/conda-envs/webmall-vlm/bin/python',REMOTE_PACKAGE+'/launch_balanced_once.py',
          '--manifest',REMOTE_PACKAGE+'/manifest.json','--manifest-sha256',sha(PACKAGE/'manifest.json'),'--output',OUTPUT]
    command={'action':'launch','argv':argv,'script_sha256':sha(PACKAGE/'launch_balanced_once.py')}
    code='PACKAGE='+repr(REMOTE_PACKAGE)+'\nOUTPUT='+repr(OUTPUT)+'\nCOMMAND='+repr(command)+'\n'+COMMON+r'''
import fcntl
b=Path('/home/researcher/jev-defense-four-gpu-20261106');p=Path(PACKAGE);r=Path(OUTPUT)
assert os.getuid()==1033 and not r.exists()and not any((p/'claims').glob('*.json'))
for attempt in ['full-gui-bounded-evidence-20261109-03','source-bound-controls-20261109-08','capacity-preflight-20261109-13']:
 closed=b/attempt;assert(closed/'exit.json').is_file()and(closed/'terminal-manifest.json').is_file()
 for name in ['launcher-process.json','worker/process.json']:
  record=json.loads((closed/name).read_bytes());assert identity(record['pid']).get('absent')is True
assert sha(p/'manifest.json')==COMMAND['argv'][5]
m=json.loads((p/'manifest.json').read_bytes())
for n,h in m['files'].items():assert sha(p/n)==h,n
lease_path=b/'resource-attempt-20261106-01/lease.json'
assert sha(lease_path)==m['lease_sha256']
lease=json.loads(lease_path.read_bytes());holder=lease['holder'];actual=identity(holder['pid'])
assert all(str(actual[k])==str(holder[k])for k in ['pid','uid','command','start_ticks'])and actual['state']not in ['Z','X']
for row in lease['lock_records']:
 proc=Path('/proc',str(holder['pid']));fd=proc/'fd'/str(row['fd']);info=(proc/'fdinfo'/str(row['fd'])).read_text()
 assert os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']and 'WRITE '+str(holder['pid'])in info
assert len(lease['lock_records'])==9 and {x['index']for x in lease['gpu']}=={4,5,6,7}
gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
cards={int(s.split(',')[0]):(s.split(',')[1].strip(),int(s.split(',')[2]))for s in gpu.splitlines()}
for row in lease['gpu']:assert cards[row['index']][0]==row['uuid']and cards[row['index']][1]>=23000
target={x['uuid']for x in lease['gpu']}
compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
assert not any(s.split(',')[0].strip()in target for s in compute.splitlines()if s.strip())
with Path(lease['inference_lock']).open('a')as mutex:fcntl.flock(mutex,fcntl.LOCK_EX|fcntl.LOCK_NB)
commands=b/'resource-attempt-20261106-01/commands'
assert all(x.with_suffix('.claimed').exists()for x in commands.glob('*.json'))
dest=commands/(p.name+'.json');temporary=commands/('.balanced16-'+str(os.getpid())+'.tmp')
with temporary.open('xb')as f:f.write(json.dumps(COMMAND,ensure_ascii=False,indent=2).encode());f.flush();os.fsync(f.fileno())
os.link(temporary,dest);temporary.unlink()
print(json.dumps({'submitted_once':True,'command_file':str(dest),'time':time.time(),'manifest_sha256':COMMAND['argv'][5],
 'actual_holder':actual,'nine_locks_verified':True,'exclusive_authorized_GPU_snapshot':gpu,'compute_snapshot':compute}))
'''
    save(HERE/'submission-intent.json',{'time':time.time(),'manifest_sha256':argv[5],'once_only':True,
          'CPU_admission_sha256':sha(HERE/'CPU-admission.json'),
          'ambiguous_observation_requires_same_handle_inspection_never_resubmission':True})
    out,op=remote('3090',code,'submit-balanced16-once-after-fresh-lease',timeout=55)
    save(HERE/'submission.json',{'value':json.loads(out),'operation':str(op)})
    print(out)


def inspect():
    code='ROOT='+repr(OUTPUT)+'\nPACKAGE='+repr(REMOTE_PACKAGE)+'\n'+COMMON+r'''
r=Path(ROOT);p=Path(PACKAGE)
out={'time':time.time(),'read_only':True,'new_model_GUI_calls':0,'output_exists':r.exists(),
 'manifest_sha256':sha(p/'manifest.json'),'claims':[{'file':q.name,'value':json.loads(q.read_bytes())}for q in(p/'claims').glob('*.json')]}
for name in ['launcher-process.json','worker-launch.json','worker/process.json','worker/status.json','worker/terminal.json','worker/failure.json','exit.json']:
 q=r/name
 if q.is_file():
  value=json.loads(q.read_bytes())
  if name.endswith('process.json'):value={'record':value,'actual':identity(value['pid'])}
  out[name]={'sha256':sha(q),'value':value}
events=r/'worker/journal/events.jsonl'
if events.is_file():
 previous='0'*64;n=0;counts={}
 for line in events.read_bytes().splitlines():
  v=json.loads(line);s=v.pop('sha256')
  assert v['seq']==n and v['previous']==previous and hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==s
  previous=s;n+=1;counts[v['kind']]=counts.get(v['kind'],0)+1
 out['journal']={'events':n,'head':previous,'counts':counts}
out['sealed_calls']=[]
for group in ['auxiliary','actors','judges']:
 for q in sorted((r/'worker'/group).glob('*/seal.json')):
  v=json.loads(q.read_bytes())
  for name,expected in v.items():assert sha(q.parent/name)==expected,name
  out['sealed_calls'].append({'path':q.parent.relative_to(r/'worker').as_posix(),'seal_sha256':sha(q),
    'actual':{k:v for k,v in json.loads((q.parent/'actual-generation.json').read_bytes()).items()if k in ['input_tokens','output_tokens','natural_EOS','actual_forward_calls']}})
log=r/'worker.log'
if log.exists():out['log']={'bytes':log.stat().st_size,'tail':log.read_bytes()[-1800:].decode(errors='replace')}
if(r/'terminal-manifest.json').is_file():out['terminal_manifest_sha256']=sha(r/'terminal-manifest.json')
out['GPU']=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
out['compute']=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
print(json.dumps(out,ensure_ascii=False))
'''
    out,op=remote('3090',code,'inspect-balanced16-actual-process-seals-chain',timeout=55)
    v=json.loads(out)
    state=v.get('worker/status.json',{}).get('value',{})
    print(json.dumps({'operation':str(op),'time':v['time'],'output_exists':v['output_exists'],
          'actual_worker':v.get('worker/process.json',{}).get('value',{}).get('actual'),
          'actual_launcher':v.get('launcher-process.json',{}).get('value',{}).get('actual'),
          'phase':state.get('phase'),'case':state.get('case'),'condition':state.get('condition'),
          'attempted_counts':{k:len(x)for k,x in state.get('attempted',{}).items()},
          'completed_counts':{k:len(x)for k,x in state.get('completed',{}).items()},
          'sealed_calls':v['sealed_calls'],'journal':v.get('journal'),
          'failure':v.get('worker/failure.json'),'exit':v.get('exit.json'),
          'terminal_manifest_sha256':v.get('terminal_manifest_sha256'),
          'compute':v['compute']},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['stage','cpu','submit','inspect'])
    a=parser.parse_args()
    globals()[a.action]()
