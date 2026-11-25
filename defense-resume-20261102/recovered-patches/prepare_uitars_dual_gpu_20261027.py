"""Prepare a separately authorized two-device capacity condition, without inference."""
import ast
import hashlib
import json
import time
from pathlib import Path
from remote import remote

BASE=Path(__file__).resolve().parent
PREP=BASE/'uitars-verifier-preparation'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
receipt=PREP/'dual-gpu-staging.json'
assert not receipt.exists(),'Inspect existing staging instead of duplicating it'
preserve=json.loads((PREP/'real-memory-diagnostic-preservation.json').read_bytes())
parent=json.loads((PREP/'real-memory-diagnostic-launch.json').read_bytes())
source=(BASE/'uitars_memory_diagnostic.py').read_text(encoding='utf-8')
worker=source

def replace(old,new):
    global worker
    assert worker.count(old)==1,old
    worker=worker.replace(old,new)

replace("assert os.getuid()==1015 and os.environ['CUDA_VISIBLE_DEVICES']=='3'", "assert os.getuid()==1015 and os.environ['CUDA_VISIBLE_DEVICES']=='3,1'\n assert launch['condition']=='independent_dual_gpu_bf16_full_input' and launch['max_calls']==2")
replace("max_memory_gib=23,placement={'':0}","max_memory_gib=23,placement='balanced'")
replace("torch=backend.torch;assert torch.cuda.device_count()==1", "torch=backend.torch;assert torch.cuda.device_count()==2\n assert backend.runtime['actual_tensor_devices']==['cuda:0','cuda:1']\n assert all(str(v) not in {'cpu','disk'} for v in backend.runtime['device_map'].values())")
replace("allocated_bytes=torch.cuda.memory_allocated(),reserved_bytes=torch.cuda.memory_reserved()", "device_memory=device_memory(),physical_gpu_pair=[3,1]")
replace("torch.cuda.reset_peak_memory_stats();started=time.time()", "[torch.cuda.reset_peak_memory_stats(i) for i in range(2)];started=time.time()")
replace("for retry in range(1):", "for retry in range(2):")
replace("assert calls<1 and launch['parent_consumed_calls']+calls<40", "assert calls<launch['max_calls']==2")
replace("'peak_allocated_bytes':torch.cuda.max_memory_allocated(),'peak_reserved_bytes':torch.cuda.max_memory_reserved(),'resident_allocated_bytes':torch.cuda.memory_allocated(),", "'device_memory':device_memory(),'reserved_gpu_seconds_for_case':2*(time.time()-started),")
replace("'parent_consumed_calls':8,'combined_model_calls':8+calls,", "'condition':'independent_dual_gpu_bf16_full_input','single_gpu_original_results_unchanged':True,'two_gpu_reserved_seconds_lower_bound':2*(time.time()-launch['lease_started_at']),")
replace("'parent_contract_invalid_cases':2,", "'physical_gpu_pair':[3,1],'cost_scope':'two reserved GPUs, not single-GPU pricing; per-device peaks are not simultaneous combined peak; no currency or energy claim',")
replace("failure.update(peak_allocated_bytes=backend.torch.cuda.max_memory_allocated(),peak_reserved_bytes=backend.torch.cuda.max_memory_reserved())", "failure.update(device_memory=device_memory(),physical_gpu_pair=[3,1],two_gpu_reserved_seconds_lower_bound=2*(time.time()-launch['lease_started_at']))")
memory_helper="""
def device_memory():
 return [{'logical_gpu':i,'physical_gpu':[3,1][i],
          'peak_allocated_bytes':torch.cuda.max_memory_allocated(i),
          'peak_reserved_bytes':torch.cuda.max_memory_reserved(i),
          'resident_allocated_bytes':torch.cuda.memory_allocated(i),
          'resident_reserved_bytes':torch.cuda.memory_reserved(i)}for i in range(2)]

"""
replace("try:\n assert os.getuid()",memory_helper+"try:\n assert os.getuid()")
# Generation, serialization, validators and format-retry prompts remain exact.
old_tree=ast.parse(source);new_tree=ast.parse(worker)
functions=lambda tree:{n.name:ast.dump(n,include_attributes=False)for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
assert all(functions(old_tree)[k]==functions(new_tree)[k]for k in ['status','validate','format_feedback'])
worker_path=BASE/'uitars_dual_gpu_preflight.py';assert not worker_path.exists();worker_path.write_text(worker,encoding='utf-8')
authorization={'time':time.time(),'user_reply':'另设双 GPU 预检，保留完整输入和 BF16，并按双卡计算部署成本',
 'authorized':True,'condition':'independent_dual_gpu_bf16_full_input','scope':'New separately linked capacity preflight only; not replacing original single-GPU results, not a formal GUI group',
 'only_case_ids':['long-history-candidate'],'max_calls':2,'max_format_retries_per_case':1,'max_output_tokens_per_call':4096,
 'physical_gpu_pair_proposed':[3,1],'placement':'balanced','precision':'BF16','backend':'sdpa',
 'full_input_tokens':39598,'original_images':22,'expected_input_ids_sha256':'f81c10ce6fb4574b20edc217e9481e045674add0ebdf2b4f098cbe6813cd5ea5',
 'model_revision':'683d002dd99d8f95104d31e70391a39348857f4e',
 'changes':['two exclusively leased GPUs with balanced model placement instead of one; explicit user authorization'],
 'unchanged':['all original public characters/history/images/native processor','fixed weights/BF16/SDPA','native judge system/candidate/grammar','4096 output cap','strict validators','original one format-retry protocol'],
 'limits':['No27B fallback','No GUI/actor/official scoring/paid API','No truncation/resizing/quantization','No automatic extra GPU or retry of a terminal in this new condition',
           'Original20 single-GPU controls and both preserved OOMs remain immutable; short failed controls are not rerun',
           'A reply/format pass does not establish semantic correctness, general feasibility or lower end-to-end cost'],
 'resource_policy':'Require both GPU3 and GPU1 completely free of all compute processes and >23500MiB free, both task lock files held and inherited; never stop/preempt other users or the3090 defense service. Check immediately before launch. If unavailable, record waiting without launch.'}
(PREP/'dual-gpu-user-authorization-20261027.json').write_text(json.dumps(authorization,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
proof={'worker_sha256':sha(worker_path.read_bytes()),'original_worker_sha256':sha(source.encode()),
 'unchanged_helpers':['status','validate','format_feedback'],'worker_ast_parses':True,
 'backend_source_policy':'Copy exact sealed parent release; LocalQwen.generate/judge and UI adapter byte-identical. Placement argument only changed at worker construction.',
 'original_preservation':preserve,'authorization':authorization,'model_calls':0}
(PREP/'dual-gpu-static-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
code='PRESERVE='+repr(preserve)+'\nPARENT='+repr(parent)+'\nPROOF='+repr(proof)+'\n'+r'''
import pathlib,json,hashlib,shutil,time,os,base64
assert os.getuid()==1015
original=pathlib.Path(PRESERVE['original_root']);snapshot=pathlib.Path(PRESERVE['preserved_root'])
seal=pathlib.Path(PRESERVE['sealed_manifest']);assert hashlib.sha256(seal.read_bytes()).hexdigest()==PRESERVE['sealed_manifest_sha256']
for n,h in json.loads(seal.read_bytes()).items():
 assert hashlib.sha256((original/n).read_bytes()).hexdigest()==h
 assert hashlib.sha256((snapshot/n).read_bytes()).hexdigest()==h
assert hashlib.sha256((original/'release/defense/uitars_backend.py').read_bytes()).hexdigest()==PARENT['backend_sha256']
case=next(c for c in json.loads((original/'public-requests.json').read_bytes())if c['id']=='long-history-candidate')
cpu=next(c for c in json.loads((original/'cpu-result.json').read_bytes())['rows']if c['id']=='long-history-candidate')
assert cpu['input_ids_sha256']==PROOF['authorization']['expected_input_ids_sha256']
assert len(case['request']['public']['images'])==22
root=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023')/('uitars-dual-gpu-staged-'+str(time.time_ns()));root.mkdir()
for n in ['public-requests.json','cpu-result.json','pinned-metadata-audit.json']:shutil.copyfile(original/n,root/n)
for p in original.glob('*.png'):shutil.copyfile(p,root/p.name)
shutil.copytree(original/'release',root/'release');shutil.copytree(original/'deps',root/'deps')
(root/'release/uitars_dual_gpu_preflight.py').write_bytes(base64.b64decode(WORKER))
assert hashlib.sha256((root/'release/uitars_dual_gpu_preflight.py').read_bytes()).hexdigest()==PROOF['worker_sha256']
for n in ['qwen_backend.py','uitars_backend.py','core.py','prompts.py','schema.py']:
 assert (root/'release/defense'/n).read_bytes()==(original/'release/defense'/n).read_bytes()
record={k:PARENT[k]for k in ['pinned_weights','pinned_revision','model','dtype','attention_backend','public_requests_sha256','max_output_tokens_per_call']}
record.update(root=str(root),condition='independent_dual_gpu_bf16_full_input',cases=1,only_case_ids=['long-history-candidate'],max_calls=2,max_format_retries_per_case=1,
 source_root=str(original),source_preservation=PRESERVE,worker_sha256=PROOF['worker_sha256'],authorization=PROOF['authorization'],physical_gpu_pair=[3,1],staged_at=time.time(),inference_started=False)
(root/'staging-plan.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
seal={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()for p in root.rglob('*')if p.is_file()and'__pycache__'not in p.parts}
(root/'staged-sha256.json').write_text(json.dumps(seal,indent=2))
record['staged_manifest_sha256']=hashlib.sha256((root/'staged-sha256.json').read_bytes()).hexdigest()
print(json.dumps(record))
'''
import base64
record=json.loads(remote('WORKER='+repr(base64.b64encode(worker_path.read_bytes()).decode())+'\n'+code,host='4090',timeout=60))
receipt.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'staged_root':record['root'],'staged_manifest_sha256':record['staged_manifest_sha256'],'worker_sha256':record['worker_sha256'],'model_calls':0,'ready_for_resource_guard':True}))
