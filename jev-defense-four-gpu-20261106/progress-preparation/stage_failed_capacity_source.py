"""Prepare independent new sources/spec and CPU evidence only; never submit or load."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import time

BASE=Path('/home/researcher/jev-defense-four-gpu-20261106')
stamp=str(time.time_ns());root=BASE/'failed-capacity-source-preparation'/stamp
runtime=BASE/'runtime-preparation'/('failed-layout-capacity-'+stamp)
root.mkdir(parents=True);runtime.mkdir()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_bytes())
def save(path,value):
    with path.open('x')as handle:json.dump(value,handle,indent=2)
for name,encoded in SOURCE_FILES.items():
    with(runtime/name).open('xb')as handle:handle.write(base64.b64decode(encoded))
proposal=BASE/'capacity-replay-proposals/1793983188398346555'
cpu=BASE/'failed-input-CPU-layout-audits/1793982908234148012'
preservation=BASE/'failed-gui-service-preservation/1793982653388639508'
assert sha(proposal/'receipt.json')=='a0e6638ea5a9c78d703d18770fe7066ecc1b983c739324465bb3812acccfb935'
assert sha(cpu/'receipt.json')=='acb9b2fb465bb2763a696c83599d5b50f1aa61f5de78393b244084d5db02a6e9'
original=read(preservation/'service-group/runtime-config.json')
command=['/opt/whz/conda-envs/webmall-vlm/bin/python',str(runtime/'test_capacity_sources.py'),
 '--parent-root',str(preservation/'sources/native-source'),
 '--frozen-wire',str(proposal/'frozen-judge-payload-wire.json'),'-v']
result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=dict(os.environ,
 CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1'))
(root/'CPU-tests.stdout').write_bytes(result.stdout);(root/'CPU-tests.stderr').write_bytes(result.stderr)
assert result.returncode==0,result.stderr.decode()
layout=read(original['layout']);layout.update(decoder_layers_per_logical_device=[14,22,22,6],
 primary_placement='explicit_asymmetric_14_22_22_6')
save(root/'layout.json',layout)
placement=read(cpu/'native-state-placement-comparison.json')
native=copy.deepcopy(read(original['primary_native_layout_receipt']))
native.update(scope='new14/22/22/6 native meta-bound CPU parameter lower bound; not GPU capacity',
 layout_sha256=sha(root/'layout.json'),contract_source_sha256=sha(runtime/'four_gpu_contract.py'),
 planned_parameter_bytes_by_logical_device={key:value['bytes']for key,value in placement['candidate'].items()},
 planned_parameter_GiB_by_logical_device={key:value['bytes']/1024**3 for key,value in placement['candidate'].items()},
 parent_native_layout_receipt=original['primary_native_layout_receipt'],
 parent_native_layout_receipt_sha256=sha(Path(original['primary_native_layout_receipt'])),
 failed_input_CPU_layout_proof=str(cpu/'receipt.json'),failed_input_CPU_layout_proof_sha256=sha(cpu/'receipt.json'),
 within_proposed_parameter_budgets=all(placement['candidate'][str(i)]['bytes']<layout['primary_max_memory_gib'][i]*1024**3 for i in range(4)))
assert native['within_proposed_parameter_budgets']
save(root/'native-layout-receipt.json',native)
for name in('primary-admission.json','helper-admission.json','frozen-judge-payload-wire.json'):
    with(root/name).open('xb')as handle:handle.write((proposal/name).read_bytes())
token=root/'private.token'
with token.open('x')as handle:handle.write(secrets.token_hex(32))
token.chmod(0o600)
keep=['primary_release','primary_model','primary_expected_runtime','primary_backend_sha256',
 'primary_dependency_receipt','primary_dependency_receipt_sha256','flash_model','flash_identity_receipt',
 'flash_identity_receipt_sha256','flash_stable_identity_receipt','flash_stable_identity_receipt_sha256',
 'flash_observer_contract','flash_observer_contract_sha256']
spec={key:original[key]for key in keep}
group=BASE/('failed-input-capacity-group-'+stamp)
spec.update(stage='single_failed_judge_capacity_replay_14_22_22_6',root_reviewed_approval=False,
 primary_calls=1,helper_calls=0,actor_GUI_scorer_calls=0,max_output_tokens=4096,automatic_retry=False,
 primary_allocator='expandable_segments:True',layer_counts=[14,22,22,6],
 layout=str(root/'layout.json'),primary_native_layout_receipt=str(root/'native-layout-receipt.json'),
 primary_native_layout_receipt_sha256=sha(root/'native-layout-receipt.json'),
 proposal_receipt=str(proposal/'receipt.json'),proposal_receipt_sha256=sha(proposal/'receipt.json'),
 CPU_proof=str(cpu/'receipt.json'),CPU_proof_sha256=sha(cpu/'receipt.json'),
 frozen_wire=str(root/'frozen-judge-payload-wire.json'),new_group=str(group),
 token_file=str(token),once_only_claim=str(root/'launch.once-only.json'),
 submission_claim=str(root/'submission.once-only.json'),client_receipt_root=str(root/'one-client-submission'),
 roles={role:{'python':original['roles'][role]['python'],'port':original['roles'][role]['port'],
 'admission':str(root/('primary-admission.json'if role=='primary'else'helper-admission.json'))}
 for role in('primary','pplx_flash')},
 admission_sha256={'primary':sha(root/'primary-admission.json'),'pplx_flash':sha(root/'helper-admission.json')},
 worker_source_sha256=sha(runtime/'preflight_service.py'),contract_source_sha256=sha(runtime/'four_gpu_contract.py'),
 source_sha256={name:sha(runtime/name)for name in SOURCE_FILES},
 old_group=str(BASE/'online-service-group-1793978182501156243'),
 old_terminal_mode='postexit_copy_original_metadata_missing',old_terminal_manifest=None,
 old_terminal_manifest_sha256=None,old_postexit_audit=None,
 GUI_release_after_capacity=False,resume_old_GUI_budget=False)
save(root/'launch-specification.draft.json',spec)
import sys
sys.path.insert(0,str(runtime))
from capacity_gate import validate_static
validate_static(spec,runtime)
changes={'worker':'only atomic evidence save+uuid import and runtime placement label18/20/20/6→14/22/22/6; all other AST unchanged',
 'contract':'only primary_device_map18/38/58→14/36/58; all other AST unchanged',
 'backend':'original release and exact backend SHA reused, no generate/judge/schema changes',
 'allocator':'primary new process only expandable_segments:True; helper env removes allocator override',
 'stop_control':'source-bound samePID/UID/startticks empty-cmd zombie exclusion; waits real Popen exitcode; never guesses0',
 'admission':'new finite primary1judge/helper0resident; original73 online requests and failed terminal not reused',
 'transport':'new capacity4-field payload exact native keyorder wire; old5-field envelope preserved as provenance',
 'evidence_publication':'worker registration/ready/request seals and client seal use complete fsynced hidden temp then atomic no-clobber hardlink; client inventory excludes itself',
 'old_terminal_gate':'requires new actual postexit source-manifest and audit binding old missing metadata/unknownexitcodes; not synthesized'}
save(root/'source-changes.json',changes)
save(root/'receipt.json',{'status':'source_CPU_prepared_not_launched','root':str(root),'runtime_source_root':str(runtime),
 'new_group':str(group),'draft_spec':str(root/'launch-specification.draft.json'),
 'draft_spec_sha256':sha(root/'launch-specification.draft.json'),
 'source_sha256':spec['source_sha256'],'CPU_tests_exit_code':result.returncode,
 'CPU_tests_stdout_sha256':sha(root/'CPU-tests.stdout'),'CPU_tests_stderr_sha256':sha(root/'CPU-tests.stderr'),
 'root_reviewed_approval':False,'old_postexit_evidence_not_yet_bound':True,
 'actual_gpu_model_GUI_calls':0,'holder_command_submitted':False,'old_live_or_terminal_changed':False,
 'primary_planned_calls':1,'helper_actor_GUI_scorer_planned_calls':0,
 'private_token_created_remote_only_mode0600':True,'private_token_not_in_public_seal':True})
save(root/'seal.json',{str(p.relative_to(root)):sha(p)for p in root.rglob('*')if p.is_file()and p!=token})
save(runtime/'source-seal.json',{name:sha(runtime/name)for name in SOURCE_FILES})
print(json.dumps({'receipt':str(root/'receipt.json'),'receipt_sha256':sha(root/'receipt.json'),
 'seal_sha256':sha(root/'seal.json'),'runtime_source_root':str(runtime),
 'draft_spec':str(root/'launch-specification.draft.json'),'draft_spec_sha256':sha(root/'launch-specification.draft.json'),
 'CPU_tests_exit_code':result.returncode,'CPU_stderr':result.stderr.decode(),
 'root_reviewed_approval':False,'actual_gpu_model_GUI_calls':0}))
