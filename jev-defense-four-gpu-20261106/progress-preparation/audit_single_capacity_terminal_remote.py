"""Independent terminal preservation/audit. No HTTP, model import or GPU allocation."""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

BASE=Path('/home/researcher/jev-defense-four-gpu-20261106')
PREP=BASE/'failed-capacity-source-preparation/1793984469336572715'
GROUP=BASE/'failed-input-capacity-group-1793984469336572715'
CPU=BASE/'failed-input-CPU-layout-audits/1793982908234148012'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_bytes())
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x')as handle:json.dump(value,handle,indent=2)

terminal=GROUP/'terminal-manifest.json'
client=PREP/'one-client-submission'
if not terminal.exists()or not(client/'seal.json').exists():
    print(json.dumps({'status':'waiting_for_actual_terminal','terminal_present':terminal.exists(),
        'client_seal_present':(client/'seal.json').exists(),'new_model_HTTP_GUI_calls':0}))
    raise SystemExit(0)

root=BASE/'single-capacity-independent-audits'/str(time.time_ns());root.mkdir(parents=True)
copied=[]
def copyfile(source,target):
    before=(source.stat().st_size,source.stat().st_mtime_ns,source.stat().st_ino);digest=sha(source)
    target.parent.mkdir(parents=True,exist_ok=True)
    with source.open('rb')as src,target.open('xb')as dst:shutil.copyfileobj(src,dst)
    assert before==(source.stat().st_size,source.stat().st_mtime_ns,source.stat().st_ino)
    assert sha(source)==digest and sha(target)==digest
    copied.append({'source':str(source),'copy':str(target.relative_to(root)),'sha256':digest})
def tree(source,target):
    for path in sorted(source.rglob('*')):
        if path.is_file()and'__pycache__'not in path.parts and path.suffix!='.pyc':copyfile(path,target/path.relative_to(source))
try:
    # Preserve full actual new results before interpreting success/failure.
    tree(GROUP,root/'original-service-group');tree(client,root/'original-client')
    specpath=PREP/'launch-specification.reviewed.json'
    assert sha(specpath)=='1b8c78a9127f81af006f78221dfece70b898a158b1c0cca30b6bae881fc11a6f'
    spec=read(specpath);source=Path(spec['roles']['primary']['python'])
    worker=Path(read(GROUP/'runtime-config.json')['commands']['primary'][2]).parent
    tree(worker,root/'actual-runtime-source')
    for name in('launch-specification.reviewed.json','launch-specification.draft.json','layout.json',
        'native-layout-receipt.json','primary-admission.json','helper-admission.json','source-changes.json',
        'holder-command.proposed.json','reviewed-finalization.json','launch.once-only.json',
        'submission.once-only.json','receipt.json','seal.json'):
        if(PREP/name).exists():copyfile(PREP/name,root/'preparation-public'/name)
    for name,encoded in AUDITOR_SOURCES.items():
        path=root/'auditor-source'/name;path.parent.mkdir(exist_ok=True)
        with path.open('xb')as handle:handle.write(base64.b64decode(encoded))
    sys.path.insert(0,str(worker))
    from capacity_gate import verify_manifest,validate_static,validate_old_terminal,identity,same
    verify_manifest(GROUP,terminal,sha(terminal));validate_static(spec,worker)
    verify_manifest(client,client/'seal.json',sha(client/'seal.json'))
    assert'seal.json'not in read(client/'seal.json')
    assert sha(CPU/'receipt.json')=='acb9b2fb465bb2763a696c83599d5b50f1aa61f5de78393b244084d5db02a6e9'
    for name,expected in read(CPU/'seal.json').items():assert sha(CPU/name)==expected
    requests=list((GROUP/'primary/requests').iterdir());assert len(requests)==1
    assert list((GROUP/'pplx_flash/requests').iterdir())==[]
    request=requests[0]
    for name,expected in read(request/'seal.json').items():assert sha(request/name)==expected
    if(request/'failure.json').exists():
        failure=read(request/'failure.json')
        save(root/'failed-terminal-classification.json',{'status':'new_capacity_model_failure_preserved',
            'original_error':failure['error'],'model_request_count':1,'helper_calls':0,
            'no_retry':True,'capacity_passed':False,'semantic_Mirage_inferred':False})
        raise RuntimeError('Actual new capacity model failure: '+failure['error'].splitlines()[-1])
    assert not(GROUP/'launcher-failure.json').exists(),'Actual new lifecycle failed; preserved, no normalization'
    assert read(GROUP/'capacity-attempt-terminal.json')['status']=='completed'
    exited=read(GROUP/'exit.json');assert{row['role']for row in exited['workers']}=={'primary','pplx_flash'}
    assert all(row['exit_code']==0 for row in exited['workers'])
    assert all(not same(identity(row['identity']['pid']),row['identity'])for row in exited['workers'])
    assert read(GROUP/'primary/stopped.json')['calls']==1 and read(GROUP/'pplx_flash/stopped.json')['calls']==0
    assert not list(GROUP.glob('controlled-idle-stop-*.json')),'Forced stop is distinct, not normal marker-only proof'
    assert sha(request/'request.json')=='b66a7a24a4037ced2b4ec5aa602853c6cde4d44c0b06aac3c619152a8bbf198e'
    body=read(request/'request.json');cpu=read(CPU/'CPU-native-tensor-records.json')
    generation=read(request/'generation.json');response=read(request/'response.json')
    forwards=read(request/'forward-trace.json');prefills=[row for row in forwards if'pixel_values'in row.get('tensors',{})]
    assert len(prefills)==1
    for key in('input_ids','pixel_values','image_grid_thw'):assert prefills[0]['tensors'][key]==cpu[key],key
    assert generation['input_ids']==cpu['input_ids']['values'][0]and len(generation['input_ids'])==21470
    expected_config=read(CPU/'original-native-generation-config.reconstructed.json')
    assert generation['generation_config']==expected_config
    constructed=read(CPU/'original-judge-call-schema-and-messages.reconstructed.json')
    assert generation['verifier_grammar']['schema']==constructed['json_schema']
    assert generation['verifier_grammar']['engine']=='lm-format-enforcer'
    assert generation['verifier_grammar']['version']=='0.11.3'
    canonical=lambda value:json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    assert generation['request_messages_sha256']==hashlib.sha256(canonical(constructed['messages'])).hexdigest()
    assert generation['verifier_grammar']['schema_sha256']==hashlib.sha256(canonical(constructed['json_schema'])).hexdigest()
    ids=generation['generated_ids'];eos=expected_config['eos_token_id'];eos=eos if isinstance(eos,list)else[eos]
    assert 0<len(ids)<4096 and ids[-1]in eos and generation['hit_output_cap']is False
    assert response['verdict']==generation['text']
    assert response['input_tokens']==21470 and response['output_tokens']==len(ids)
    assert response['forward_trace_sha256']==sha(request/'forward-trace.json')
    schema_parseable=True
    try:json.loads(generation['text'])
    except json.JSONDecodeError:schema_parseable=False
    primary=read(GROUP/'primary/loaded.json');flash=read(GROUP/'pplx_flash/loaded.json')
    expected_map=read(CPU/'candidate-device-map.json')
    assert primary['device_map']=={key:str(value)for key,value in expected_map.items()}
    assert primary['placement']=='explicit_asymmetric_14_22_22_6'
    assert primary['dtype']=='torch.bfloat16'and primary['backend']=='sdpa'
    assert primary['generate_and_judge_inherited_unchanged']is True
    assert primary['actual_state_tensor_count']==1184 and primary['native_MTP_not_instantiated']is True
    assert primary['tensor_count']==1187 and flash['tensor_count']==728
    assert primary['devices']==['cuda:0','cuda:1','cuda:2','cuda:3']and flash['devices']==['cuda:0']
    assert flash['revision']=='9ff7cf9838e59df461c276b7699d56b244d2af58'and flash['fast']is False
    assert read(GROUP/'primary-launch.json')['PYTORCH_CUDA_ALLOC_CONF']=='expandable_segments:True'
    assert read(GROUP/'pplx_flash-launch.json')['PYTORCH_CUDA_ALLOC_CONF']is None
    metadata={name:sha(Path(spec['primary_model'])/name)for name in primary['metadata_sha256']}
    assert metadata==primary['metadata_sha256']
    assert sha(Path(spec['primary_release'])/'defense/qwen_backend.py')==spec['primary_backend_sha256']
    for row in body['view']['images']:assert len(base64.b64decode(row['raw_base64'],validate=True))>0
    assert len(body['view']['images'])==12
    claim=read(client/'once-only-client-claim.json');marker=read(GROUP/'stop-requested.json')
    ready_times={role:read(GROUP/role/'ready.json')['time']for role in('primary','pplx_flash')}
    stopped_times={role:read(GROUP/role/'stopped.json')['time']for role in('primary','pplx_flash')}
    assert all(value<claim['time']for value in ready_times.values())
    assert(request/'response.json').stat().st_mtime<=marker['time']
    assert all(value>=marker['time']for value in stopped_times.values())
    assert read(client/'response-metadata.json')['HTTP_status']==200
    assert read(client/'response-metadata.json')['model_calls_submitted']==1
    assert read(client/'response-metadata.json')['automatic_retry']is False
    assert json.loads((client/'response.raw').read_bytes())==response
    old=validate_old_terminal(spec)
    lease=read(BASE/'resource-attempt-20261106-01/lease.json')
    assert same(identity(lease['holder']['pid']),lease['holder'])
    locks=[]
    for row in lease['lock_records']:
        fd=Path('/proc',str(lease['holder']['pid']),'fd',str(row['fd']))
        assert os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']
        assert'lock:'in Path('/proc',str(lease['holder']['pid']),'fdinfo',str(row['fd'])).read_text();locks.append(row)
    raw=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],universal_newlines=True)
    target={row['uuid']for row in lease['gpu']}
    assert not any(line.split(',')[0].strip()in target for line in raw.splitlines()if line.strip())
    receipt={'status':'passed','capacity_passed':True,'scope':'one exact failed21470-token12-image judge; no future history/GUI guarantee',
        'group':str(GROUP),'reviewed_spec_sha256':sha(specpath),'terminal_manifest_sha256':sha(terminal),
        'primary_calls':1,'helper_calls':0,'actor_GUI_scorer_calls':0,'pending_requests':0,
        'input_tokens':21470,'original_images':12,'output_tokens':len(ids),'natural_native_EOS':True,
        'native_IDs_pixels_grid_exact_original_failed_CPU_proof':True,'original_config_and_schema_exact':True,
        'original_native_generation_budget4096_preserved':True,'BF16_SDPA_and_original_model_methods':True,
        'new_device_map_14_22_22_6_actual':True,'primary_process_allocator_actual':'expandable_segments:True',
        'complete_reply_JSON_parseable':schema_parseable,'no_semantic_accuracy_claim':True,
        'both_native_CUDA_tensor_audits_bound':True,'two_ready_before_request_two_stopped_after_seal_same_registered_PIDs':True,
        'ready_times':ready_times,'stopped_times':stopped_times,'stop_marker_time':marker['time'],
        'per_device_primary_generation_memory':response['per_device_memory'],
        'primary_load_memory':primary['memory'],'flash_resident_load_memory':flash['memory'],
        'model_generation_seconds':generation['seconds'],'service_seconds_including_audit':response['seconds_including_audit'],
        'cost_accounting':{'physical_GPUs_reserved_for_group':4,'helper_shares_physical_GPU7_not_a_fifth_GPU':True,
            'primary_load_seconds':primary['load_seconds'],'helper_load_seconds':flash['load_seconds'],
            'four_GPU_generation_seconds':4*generation['seconds'],
            'four_GPU_service_seconds_including_audit':4*response['seconds_including_audit'],
            'two_seconds_measures_overlap_not_additive':True,
            'full_lease_reserved_cost_not_final_holder_still_holds9locks':True,
            'excludes_prior72replies_OOM_CPU_preparation_and_interstage_wait':True,
            'currency_energy_or_overall_savings_not_measured':True},
        'client_seal_verified_without_self_reference':True,'new_atomic_evidence_files_actual_seals_verified':True,
        'new_stop_actual_exit_codes':{row['role']:row['exit_code']for row in exited['workers']},
        'new_marker_stop_no_force_no_launcher_failure':True,'new_workers_absent_and_target_compute_empty':True,
        'holder_actual_identity_and9locks_remain':len(locks)==9,'old72complete1failed_seals_unchanged':old,
        'old_unknown_worker_exit_not_rewritten':True,'GUI_release_or_Mirage_reduction_claim':False,
        'allocator_vs_placement_effect_not_separately_identified':True,'numerical_equivalence_not_guaranteed':True,
        'new_HTTP_model_GUI_calls_by_auditor':0,'original_files_changed':False}
    save(root/'copied-file-bindings.json',copied);save(root/'receipt.json',receipt)
    save(root/'seal.json',{str(path.relative_to(root)):sha(path)for path in root.rglob('*')if path.is_file()})
    print(json.dumps({'status':'passed','receipt':str(root/'receipt.json'),'receipt_sha256':sha(root/'receipt.json'),
        'seal_sha256':sha(root/'seal.json'),'input_tokens':21470,'original_images':12,'output_tokens':len(ids),
        'model_seconds':generation['seconds'],'native_EOS':True,'primary_calls':1,'helper_calls':0,
        'actual_new_exit_codes':receipt['new_stop_actual_exit_codes'],'new_HTTP_model_GUI_calls':0}))
except BaseException:
    import traceback
    save(root/'audit-failure.json',{'error':traceback.format_exc(),'original_group_preserved':True,
        'no_retry':True,'new_HTTP_model_GUI_calls':0})
    if not(root/'seal.json').exists():save(root/'seal.json',{str(path.relative_to(root)):sha(path)for path in root.rglob('*')if path.is_file()})
    raise
