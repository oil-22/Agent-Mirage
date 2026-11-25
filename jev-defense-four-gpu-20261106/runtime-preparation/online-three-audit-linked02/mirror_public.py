"""Copy sealed public audit to local and4090; no token/health/model calls."""
import base64
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote

stamp='1793986896126859644'
source=r'''
import base64,hashlib,json
from pathlib import Path
root=Path('/home/researcher/jev-defense-four-gpu-20261106/online-three-independent-audits/1793986896126859644')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(root/'receipt.json')=='fd1701a0872a982e3bf8491068ace77840bcdba45e1bc9a0c7b2179f6ea900b0'
seal=json.loads((root/'seal.json').read_bytes())
assert not any('private.token'in name for name in seal)
for name,expected in seal.items():assert sha(root/name)==expected
print(json.dumps({'files':{name:base64.b64encode((root/name).read_bytes()).decode()for name in list(seal)+['seal.json']}}))
'''
value=json.loads(remote(source,timeout=180,host='3090'))
target=Path(__file__).parents[3]/'online-three-independent-audits'/stamp
target.mkdir(parents=True,exist_ok=False)
seal=json.loads(base64.b64decode(value['files']['seal.json']))
for name,encoded in value['files'].items():
    raw=base64.b64decode(encoded)
    if name!='seal.json':assert hashlib.sha256(raw).hexdigest()==seal[name]
    path=target/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb')as f:f.write(raw)
mirror=r'''
import base64,hashlib,json
from pathlib import Path
BASE=Path('/data/researcher/jev-defense-four-gpu-20261106')
root=BASE/'online-three-independent-audits/1793986896126859644'
root.mkdir(parents=True,exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
seal=json.loads(base64.b64decode(FILES['seal.json']))
for name,encoded in FILES.items():
    raw=base64.b64decode(encoded)
    if name!='seal.json':assert hashlib.sha256(raw).hexdigest()==seal[name]
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb')as f:f.write(raw)
for name,digest in seal.items():assert sha(root/name)==digest
assert sha(root/'receipt.json')=='fd1701a0872a982e3bf8491068ace77840bcdba45e1bc9a0c7b2179f6ea900b0'
audit=json.loads((root/'receipt.json').read_bytes())
derived=BASE/'online-three-resource-conditions/1793986896126859644'
derived.mkdir(parents=True,exist_ok=False)
evidence=[{'path':str(root/name),'sha256':digest}for name,digest in seal.items()]
proof={'status':'passed','decoder_layer_counts':[14,22,22,6],'allocator':'expandable_segments:True',
 'decoder_layers14_22_22_6':True,'allocator_expandable_segments':True,
 'new_capacity_not_old15720':True,'all_three_same_resource':True,
 'source_evidence':evidence,'source_bound_actual_audit':{'path':str(root/'receipt.json'),'sha256':sha(root/'receipt.json')},
 'original_3090_audit_receipt':'/home/researcher/jev-defense-four-gpu-20261106/online-three-independent-audits/1793986896126859644/receipt.json',
 'original_audit_SHA_preserved':True,'complete_4090_mirror_all_SHA_verified':True,
 'actual_uid_full_command_verified':audit['actual_uid_full_command_verified'],
 'all_inherited_locks_held':audit['all_inherited_locks_held'],
 'no_foreign_compute_on_leased_GPUs':audit['no_foreign_compute_on_leased_GPUs'],
 'actual_allowed_pids':audit['actual_allowed_pids'],'physical_gpu_uuids':audit['physical_gpu_uuids'],
 'both_native_CUDA_load_audits_bound':True,'both_authenticated_health_ready':True,
 'capacity_input_tokens':21470,'capacity_original_images':12,'original_output_budget':4096,
 'all_three_unstarted_at_audit':True,'scope':'immutable audited conditions; current fresh ownership still separately required',
 'new_model_GUI_health_POST_calls_by_mirror':0,'private_tokens_copied':False}
path=derived/'resource-conditions.json'
with path.open('x')as f:json.dump(proof,f,indent=2)
with(derived/'seal.json').open('x')as f:json.dump({'resource-conditions.json':sha(path)},f,indent=2)
print(json.dumps({'public_mirror':str(root),'public_mirror_seal_sha256':sha(root/'seal.json'),
 'public_files_SHA_verified':len(seal)+1,'resource_conditions':str(path),'resource_conditions_sha256':sha(path),
 'resource_seal_sha256':sha(derived/'seal.json'),'source_evidence_files':len(evidence),
 'model_GUI_health_POST_calls':0,'private_tokens_copied':False}))
'''
result=json.loads(remote('FILES='+repr(value['files'])+'\n'+mirror,timeout=180,host='4090'))
with(target/'local-4090-transfer.json').open('x')as f:json.dump(result,f,indent=2)
print(json.dumps({'local':str(target),**result}))
