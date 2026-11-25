"""Prepare exact new runtime spec/token/CPU evidence. No submit/model/HTTP calls."""
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

BASE=Path('/home/researcher/jev-defense-four-gpu-20261106')
stamp=str(time.time_ns())
root=BASE/'online-three-source-preparation'/stamp
source=BASE/'runtime-preparation'/('gui-three-linked02-'+stamp)
root.mkdir(parents=True,exist_ok=False);source.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())


def write(path,value):
    with path.open('x')as handle:json.dump(value,handle,indent=2)


try:
    for name,raw in ONLINE_SOURCES.items():
        with(source/name).open('xb')as f:f.write(base64.b64decode(raw))
    plan=root/'plan.json'
    with plan.open('xb')as f:f.write(base64.b64decode(PLAN_SOURCE))
    assert sha(plan)=='838c63ac36560040df0c9257f4080d7c5ef33e7a0858f9b42bbdb73f486a2cef'
    capacity_spec=BASE/'failed-capacity-source-preparation/1793984469336572715/launch-specification.reviewed.json'
    assert sha(capacity_spec)=='1b8c78a9127f81af006f78221dfece70b898a158b1c0cca30b6bae881fc11a6f'
    previous=read(capacity_spec)
    native=BASE/'runtime-preparation/failed-layout-capacity-1793984469336572715'
    for name,expected in previous['source_sha256'].items():assert sha(native/name)==expected
    capacity=BASE/'single-capacity-independent-audits/1793985058235255298/receipt.json'
    old=read(BASE/'online-service-group-1793978182501156243/runtime-config.json')
    old_gate=read(old['online_launch_gate'])
    observer=old_gate['evidence']['observer_independent_review']
    assert observer['sha256']=='fa0140293d55d9525f2558fc17d1214931bf7a718b6e78c3eb8b91208c13ba26'
    assert sha(observer['path'])==observer['sha256']
    env={**os.environ,'CUDA_VISIBLE_DEVICES':'','PYTHONDONTWRITEBYTECODE':'1',
        'TEST_ORIGINAL_THREE_PLAN':str(plan),'TEST_ORIGINAL_ONLINE_SOURCE':str(Path(old['commands']['primary'][2]).parent),
        'TEST_ACTUAL_CAPACITY_RECEIPT':str(capacity)}
    result=subprocess.run(['/opt/whz/conda-envs/webmall-vlm/bin/python',str(source/'test_online_three.py')],
        env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    (root/'CPU-stdout.txt').write_bytes(result.stdout);(root/'CPU-stderr.txt').write_bytes(result.stderr)
    assert result.returncode==0,result.stderr.decode()
    sys.path[:0]=[str(source),str(native)]
    from online_contract import validate_plan
    from online_gate import validate_static,validate_capacity
    from capacity_gate import verify_manifest,validate_old_terminal,empty_resources
    assert sha(capacity)=='fc5919611dc79e478684cbffc226cd98e40285b645f856029c694ad0173be366'
    actual=read(capacity);validate_capacity(actual)
    verify_manifest(Path(actual['group']),Path(actual['group'])/'terminal-manifest.json',actual['terminal_manifest_sha256'])
    unchanged_old=validate_old_terminal(previous)
    lease=read(BASE/'resource-attempt-20261106-01/lease.json');resources=empty_resources(lease)
    token=root/'private.token'
    fd=os.open(str(token),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w')as f:f.write(secrets.token_hex(32));f.flush();os.fsync(f.fileno())
    forbidden=[previous['token_file'],old['token_file']]
    assert all(token.read_bytes().strip()!=Path(path).read_bytes().strip()for path in forbidden)
    gate=root/'online-launch-gate.proposed.json'
    write(gate,{'stage':'new_exact_three_online_authorization','approved':False,'once_only':True,
        'online_plan_sha256':sha(plan),'observer_contract_sha256':previous['flash_observer_contract_sha256'],
        'capacity_terminal_manifest':str(Path(actual['group'])/'terminal-manifest.json'),
        'capacity_terminal_manifest_sha256':actual['terminal_manifest_sha256'],
        'evidence':{'primary_full_input_capacity':{'path':str(capacity),'sha256':sha(capacity)},
            'observer_independent_review':observer},'preparation_model_GUI_calls':0})
    keys=['primary_release','primary_model','primary_expected_runtime','primary_backend_sha256',
        'primary_native_layout_receipt','primary_native_layout_receipt_sha256','primary_dependency_receipt',
        'primary_dependency_receipt_sha256','flash_model','flash_identity_receipt','flash_identity_receipt_sha256',
        'flash_stable_identity_receipt','flash_stable_identity_receipt_sha256',
        'flash_observer_contract','flash_observer_contract_sha256','layout','primary_allocator','layer_counts']
    spec={k:previous[k]for k in keys}
    group=BASE/('online-three-service-group-'+stamp)
    spec.update(stage='new_exact_three_online14_22_22_6',root_reviewed_approval=False,
        preparation_root=str(root),new_group=str(group),capacity_spec=str(capacity_spec),
        capacity_spec_sha256=sha(capacity_spec),layout_sha256=sha(previous['layout']),
        roles={k:{field:value[field]for field in('python','port')}for k,value in previous['roles'].items()},
        preflight_source_root=str(native),preflight_source_sha256={name:sha(native/name)for name in
            ('preflight_service.py','four_gpu_contract.py','capacity_gate.py','marker_stop_helpers.py','submit_capacity_once.py')},
        online_source_sha256={p.name:sha(p)for p in source.glob('*.py')},
        online_plan=str(plan),online_plan_sha256=sha(plan),online_launch_gate=str(gate),
        online_launch_gate_sha256=sha(gate),token_file=str(token),forbidden_previous_tokens=forbidden,
        once_only_claim=str(root/'launch.once-only.json'),submission_claim=str(root/'submission.once-only.json'),
        resume_old_GUI_budget=False,automatic_retry=False,maximum_primary_calls=630,maximum_auxiliary_calls=120)
    validate_static(spec,source)
    draft=root/'launch-specification.draft.json';write(draft,spec)
    runs=validate_plan(read(plan))
    receipt={'status':'source_CPU_prepared_not_launched','preparation_root':str(root),'runtime_source_root':str(source),
        'new_group':str(group),'draft_spec':str(draft),'draft_spec_sha256':sha(draft),
        'proposed_gate':str(gate),'proposed_gate_sha256':sha(gate),'plan':str(plan),'plan_sha256':sha(plan),
        'token_file':str(token),'token_mode':oct(token.stat().st_mode&0o777),
        'independent_from_both_capacity_and_old_online_token':True,'token_contents_not_exported':True,
        'CPU_tests_passed':19,'CPU_tests_skipped':0,'native_model_call_AST_unchanged':True,
        'atomic_evidence_publication_actual_Linux_tested':True,'original_atomic_mutable_state_unchanged':True,
        'decoder_layer_counts':[14,22,22,6],'primary_allocator':'expandable_segments:True',
        'auxiliary_caps':[r['caps']['observe']for r in runs.values()],'primary_cap_total':630,'auxiliary_cap_total':120,
        'actual_capacity_audit_sha256':sha(capacity),'capacity_known_input_only_not_future_GUI_fit_guarantee':True,
        'original_failed_run_not_requeued':True,'old_terminal_preserved':unchanged_old,'resources_at_preparation':resources,
        'root_reviewed_approval':False,'submitted_to_holder':False,'health_GET_POST_calls':0,'model_GPU_GUI_calls':0,
        'runtime_source_sha256':spec['online_source_sha256']}
    write(root/'receipt.json',receipt)
    write(root/'public-seal.json',{str(p.relative_to(root)):sha(p)for p in root.rglob('*')if p.is_file()and p.name!='private.token'})
    print(json.dumps({'receipt':str(root/'receipt.json'),'receipt_sha256':sha(root/'receipt.json'),
        'public_seal_sha256':sha(root/'public-seal.json'),**receipt}))
except BaseException:
    import traceback
    write(root/'preparation-failure.json',{'error':traceback.format_exc(),'model_HTTP_GUI_calls':0,'no_auto_retry':True})
    raise
