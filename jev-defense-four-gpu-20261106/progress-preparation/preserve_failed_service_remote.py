"""New immutable copy of failed online stage; no service mutation, HTTP or signals."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

BASE=Path('/home/researcher/jev-defense-four-gpu-20261106')
GROUP=BASE/'online-service-group-1793978182501156243'
FAILED='bd7ed2f4753b00594cb626a4cad3b740c0f95d91128547da69404254a2559841'
root=BASE/'failed-gui-service-preservation'/str(time.time_ns())
root.mkdir(parents=True)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as handle:json.dump(value,handle,indent=2)
def checked_copy(source,target):
    assert source.is_file() and not source.is_symlink()
    before=(source.stat().st_size,source.stat().st_mtime_ns,source.stat().st_ino)
    expected=sha(source);target.parent.mkdir(parents=True,exist_ok=True)
    with source.open('rb')as src, target.open('xb')as dst:shutil.copyfileobj(src,dst)
    after=(source.stat().st_size,source.stat().st_mtime_ns,source.stat().st_ino)
    assert before==after and sha(source)==expected and sha(target)==expected
    copied.append({'source':str(source),'copy':str(target.relative_to(root)),
        'sha256':expected,'bytes':before[0],'stat_before_after_stable':True})
def tree(source,target):
    for path in sorted(source.rglob('*')):
        if path.is_file() and '__pycache__'not in path.parts and path.suffix!='.pyc':
            checked_copy(path,target/path.relative_to(source))
copied=[]
try:
    print(json.dumps({'preservation_root':str(root),'stage':'collecting_read_only_sources'}),flush=True)
    config=json.loads((GROUP/'runtime-config.json').read_bytes())
    failed=GROUP/'primary/requests'/FAILED
    assert sha(failed/'seal.json')=='2524d02f7c18dd662794122701648e92c7b5729b9ae7c386b13c23ffbe4dcec7'
    for role in('primary','pplx_flash'):
        for request in(GROUP/role/'requests').iterdir():
            assert request.is_dir() and(request/'seal.json').exists(),'Pending request; preserve but do not stop'
            for name,expected in json.loads((request/'seal.json').read_bytes()).items():assert sha(request/name)==expected
    state=json.loads((GROUP/'online-state.json').read_bytes())
    assert state['phase']=='terminal_failure'and state['active']is None
    source_manifest={str(p.relative_to(GROUP)):sha(p)for p in GROUP.rglob('*')if p.is_file()}
    save(root/'service-source-manifest-before.json',source_manifest)
    tree(GROUP,root/'service-group')
    assert source_manifest=={str(p.relative_to(GROUP)):sha(p)for p in GROUP.rglob('*')if p.is_file()}
    namespaces=[('native-source',Path(config['preflight_source_root'])),
        ('online-source',Path(config['commands']['primary'][2]).parent),
        ('primary-release',Path(config['primary_release']))]
    for name,source in namespaces:tree(source,root/'sources'/name)
    dependency=json.loads(Path(config['primary_dependency_receipt']).read_bytes())
    tree(Path(dependency['dependency_root']),root/'sources/original-grammar-dependencies')
    for key in('primary_expected_runtime','primary_native_layout_receipt','primary_dependency_receipt',
        'flash_identity_receipt','flash_stable_identity_receipt','flash_observer_contract','layout',
        'online_plan','online_launch_gate'):
        checked_copy(Path(config[key]),root/'linked-evidence'/(key+Path(config[key]).suffix))
    for name in('config.json','generation_config.json','preprocessor_config.json','processor_config.json',
        'tokenizer_config.json','special_tokens_map.json','model.safetensors.index.json',
        'chat_template.jinja'):
        path=Path(config['primary_model'])/name
        if path.exists():checked_copy(path,root/'primary-metadata'/name)
    failure=json.loads((failed/'failure.json').read_bytes())
    for filename in sorted(set(re.findall(r'File "([^"]+\.py)"',failure['error']))):
        path=Path(filename)
        if path.is_file():checked_copy(path,root/'failure-stack-source'/str(path).lstrip('/'))
    request=json.loads((failed/'request.json').read_bytes())
    images=[]
    for index,item in enumerate(request['payload']['view']['images']):
        raw=base64.b64decode(item['raw_base64'],validate=True)
        digest=hashlib.sha256(raw).hexdigest();name='%03d-%s.image'%(index,digest)
        path=root/'failed-original-images'/name;path.parent.mkdir(exist_ok=True)
        with path.open('xb')as handle:handle.write(raw)
        images.append({'index':index,'role':item['role'],'sha256':digest,'bytes':len(raw),'copy':str(path.relative_to(root))})
    save(root/'failed-original-images.json',images)
    for name,encoded in PRESERVATION_SOURCES.items():
        path=root/'auditor-source'/name;path.parent.mkdir(exist_ok=True)
        with path.open('xb')as handle:handle.write(base64.b64decode(encoded))
    code="__name__='audit_helpers'\n"+base64.b64decode(PROGRESS_HELPER).decode()+"\nprint(json.dumps(service_snapshot(Path("+repr(str(GROUP))+"))))\n"
    current=subprocess.check_output([sys.executable,'-'],input=code.encode())
    snapshot=json.loads(current)
    assert snapshot['all_actual_peer_identities_valid']and not snapshot['foreign_target_compute']
    assert all(row['request_counts']['pending_unsealed']==0 for row in snapshot['workers'].values())
    assert snapshot['workers']['primary']['request_counts']=={'completed':72,'failed':1,'pending_unsealed':0}
    assert snapshot['workers']['pplx_flash']['request_counts']=={'completed':0,'failed':0,'pending_unsealed':0}
    assert snapshot['journal']['uncommitted_partial_tail_bytes']==0
    assert snapshot['state_snapshot']==state
    save(root/'actual-live-source-snapshot.json',snapshot)
    save(root/'copied-source-file-bindings.json',copied)
    save(root/'receipt.json',{'status':'preserved','original_group':str(GROUP),'preservation_root':str(root),
        'classification':'actual_primary_prefill_CUDA_out_of_memory',
        'failed_request':str(failed),'failed_seal_sha256':sha(failed/'seal.json'),
        'failed_forward_trace_sha256':sha(failed/'forward-trace.json'),
        'failed_failure_json_sha256':sha(failed/'failure.json'),
        'failed_generation_json_absent':not(failed/'generation.json').exists(),
        'failed_generated_token_progress_bytes':(failed/'generated-token-progress.jsonl').stat().st_size,
        'primary_completed':72,'primary_failed':1,'helper_requests':0,'pending_requests':0,
        'all_actual_UID_fullcmd_startticks_and9locks_verified':True,'foreign_target_compute_count':0,
        'service_source_snapshot_stable_before_after':True,'full_service_group_copied':True,
        'source_files_copied':len(copied),'failed_original_image_count':len(images),
        'CPU_schema_and_input_reconstruction_not_yet_run':True,
        'new_HTTP_model_GUI_calls':0,'signals_sent':0,'original_files_changed':False,
        'semantic_Mirage_or_official_success_inferred':False})
    save(root/'seal.json',{str(p.relative_to(root)):sha(p)for p in root.rglob('*')if p.is_file()})
    print(json.dumps({'status':'preserved','receipt':str(root/'receipt.json'),
        'receipt_sha256':sha(root/'receipt.json'),'seal_sha256':sha(root/'seal.json'),
        'source_files':len(copied),'original_images':len(images),'primary_completed':72,
        'primary_failed':1,'pending':0,'new_HTTP_model_GUI_calls':0}),flush=True)
except BaseException:
    import traceback
    save(root/'preservation-failure.json',{'error':traceback.format_exc(),'new_HTTP_model_GUI_calls':0})
    if not(root/'seal.json').exists():save(root/'seal.json',{str(p.relative_to(root)):sha(p)for p in root.rglob('*')if p.is_file()})
    raise
