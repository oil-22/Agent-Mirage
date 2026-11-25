"""Freeze four image-only inputs and invoke ONLY the new native CPU admission."""
from __future__ import annotations
import base64,hashlib,importlib.util,json,os,subprocess,sys,tarfile,time
from pathlib import Path
import native_image_admission as worker

HERE=Path(__file__).resolve().parent
REVISION=HERE.parent
PROJECT=REVISION.parent
LOCAL=HERE/'cpu-native-four-linked02'
REMOTE='/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/single-evidence-native-auxiliary-01'
NATIVE_PY='/opt/whz/conda-envs/webmall-vlm/bin/python'
SSH=['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','-o','BatchMode=yes','-o','ConnectTimeout=15','3090']


def write(path,value):
    with path.open('xb')as stream:stream.write(worker.canonical(value)+b'\n')


def freeze():
    LOCAL.mkdir(exist_ok=False)
    input_pack=REVISION/'four-image-inputs-01'
    input_seal=json.loads((input_pack/'seal.json').read_text(encoding='utf8'))
    for name,digest in input_seal.items():assert worker.digest((input_pack/name).read_bytes())==digest,name
    assert input_seal['protocol.json']=='e3d639011de4cda5598be09645e377d7c2dd5220ec185835348044a08b6f6d12'
    snapshot_root=REVISION/'validation-plan/resource-and-base-asset-snapshot-01'
    snapshot=json.loads((snapshot_root/'3090-readonly.json').read_text(encoding='utf8'))
    asset=next(row for row in snapshot['asset_roots']if row['path']==worker.MODEL_PATH and row['exists'])
    rows={Path(row['path']).name:row for row in asset['files']}
    assert 'generation_config.json'not in rows
    assert worker.REQUIRED_METADATA<=set(rows)
    present=(worker.REQUIRED_METADATA|worker.OPTIONAL_NATIVE_METADATA)&set(rows)
    metadata=[{'filename':name,'bytes':rows[name]['bytes'],'sha256':rows[name]['sha256']}for name in sorted(present)]
    assert all(row['sha256']and rows[row['filename']]['stable_during_read']for row in metadata)
    shard_stats=[{'filename':name,'bytes':row['bytes'],'mtime_ns':row['mtime_ns']}
        for name,row in rows.items()if name.endswith('.safetensors')]
    assert len(shard_stats)==4
    old_identity=PROJECT.parent/'attention-audit-20261031/model-sha256-3090.json'
    source_payload={'native_image_admission.py':(HERE/'native_image_admission.py').read_bytes(),
        'image_evidence.py':(REVISION/'evidence-contract/image_evidence.py').read_bytes(),
        'old-weight-identity-reference.json':old_identity.read_bytes()}
    assert worker.digest(source_payload['image_evidence.py'])==worker.CONTRACT_SHA256
    bindings=[]
    for name in ['S01','S07','S13','S25']:
        filename=name+'-request.json';raw=(input_pack/filename).read_bytes()
        request=worker.strict_json(raw)
        assert request['model']==worker.BASE_REPO and request['revision']==worker.BASE_REVISION
        source_payload[filename]=raw
        bindings.append({'request_id':name,'path':REMOTE+'/'+filename,'sha256':worker.digest(raw)})
    manifest={'schema_version':'native-image-admission-v1','attempt_id':'native-aux-four-cpu-linked02',
        'mode':'cpu_admission_only','output_root':REMOTE+'/admission-01','cpu_admission_authorized':True,
        'gpu_inference_authorized':False,
        'base_model':{'repo':worker.BASE_REPO,'revision':worker.BASE_REVISION,'local_path':worker.MODEL_PATH},
        'jev_relationship':{'repo':worker.JEV_REPO,'revision':worker.JEV_REVISION,
            'stage':'S2-shared-original-base','decision_adapter_loaded':False},
        'evidence_contract':{'source_path':REMOTE+'/image_evidence.py','sha256':worker.CONTRACT_SHA256},
        'metadata_files':metadata,
        'prior_weight_identity':{'receipt_path':REMOTE+'/old-weight-identity-reference.json',
            'receipt_sha256':worker.digest(old_identity.read_bytes())},
        'weight_file_stats':shard_stats,'requests':bindings,'expected_request_count':4,
        'native_input_policy':{'enable_thinking':False,'truncate':False,'image_count':1,
            'processor_overrides':{},'task_history_candidate_supplied':False},
        'future_aux_generation':{'max_new_tokens':2048,'do_sample':False,'temperature':1.0,'top_p':1.0,'top_k':0,
            'dtype':'bfloat16','attention_backend':'sdpa','model_class':worker.MODEL_CLASS,
            'eos_stop_rule_status':'UNDECIDED_before_GPU_inference','inference_performed_in_this_mode':False}}
    worker.validate_manifest(manifest)
    source_payload['input-manifest.json']=worker.canonical(manifest)+b'\n'
    source_payload['prepare_and_run_four_cpu.py']=Path(__file__).read_bytes()
    payload_root=LOCAL/'payload';payload_root.mkdir()
    for name,raw in source_payload.items():(payload_root/name).write_bytes(raw)
    freeze_receipt={'status':'four_CPU_processor_inputs_frozen_not_run','remote_root':REMOTE,
        'asset_snapshot_sha256':worker.digest((snapshot_root/'3090-readonly.json').read_bytes()),
        'asset_report_sha256':worker.digest((snapshot_root/'report.json').read_bytes()),
        'input_protocol_sha256':input_seal['protocol.json'],'input_seal_sha256':worker.digest((input_pack/'seal.json').read_bytes()),
        'current_stat_not_continuity_from_old_hash':True,
        'old_hash_historical_seal_coverage_established':False,
        'files':[{'filename':name,'sha256':worker.digest(raw),'bytes':len(raw)}for name,raw in source_payload.items()],
        'only_native_CPU_admission_authorized':True,'model_or_GPU_calls_allowed':0}
    write(LOCAL/'freeze-receipt.json',freeze_receipt)
    print(json.dumps({'frozen':str(LOCAL),'requests':4,'manifest_sha256':worker.digest(source_payload['input-manifest.json'])}))


def execute():
    # A new remote root is atomically claimed by the bootstrap. No resume/old queue.
    receipt=json.loads((LOCAL/'freeze-receipt.json').read_text(encoding='utf8'))
    payload=[]
    for row in receipt['files']:
        raw=(LOCAL/'payload'/row['filename']).read_bytes();assert worker.digest(raw)==row['sha256']
        payload.append({'filename':row['filename'],'sha256':row['sha256'],
            'base64':base64.b64encode(raw).decode('ascii')})
    bootstrap='''import base64,hashlib,json,os,subprocess,time\nfrom pathlib import Path\n'''
    bootstrap+='root=Path('+repr(REMOTE)+')\npayload='+repr(payload)+'\n'
    bootstrap+='''root.parent.mkdir(parents=True,exist_ok=True)
root.mkdir(exist_ok=False)
for row in payload:
    raw=base64.b64decode(row['base64'])
    assert hashlib.sha256(raw).hexdigest()==row['sha256']
    with(root/row['filename']).open('xb')as stream:stream.write(raw)
env=dict(os.environ)
env.update({'CUDA_VISIBLE_DEVICES':'','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','PYTHONDONTWRITEBYTECODE':'1'})
argv=['/opt/whz/conda-envs/webmall-vlm/bin/python','-B',str(root/'native_image_admission.py'),'--mode','cpu-admission','--manifest',str(root/'input-manifest.json'),'--output',str(root/'admission-01')]
started=time.time()
with(root/'cpu-worker.stdout.log').open('xb')as stdout, (root/'cpu-worker.stderr.log').open('xb')as stderr:
    result=subprocess.run(argv,env=env,stdout=stdout,stderr=stderr,timeout=240)
report={'returncode':result.returncode,'argv':argv,'started':started,'completed':time.time(),'terminal_exists':(root/'admission-01/terminal.json').is_file(),'model_or_GPU_calls_authorized':0}
with(root/'invocation.json').open('x')as stream:json.dump(report,stream)
print(json.dumps(report))
'''
    (LOCAL/'remote-bootstrap.py').write_text(bootstrap,encoding='utf8')
    started=time.time()
    completed=subprocess.run(SSH+['python3','-'],input=bootstrap.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=285)
    (LOCAL/'bootstrap.stdout').write_bytes(completed.stdout);(LOCAL/'bootstrap.stderr').write_bytes(completed.stderr)
    write(LOCAL/'local-invocation.json',{'returncode':completed.returncode,'started':started,'completed':time.time(),
        'bootstrap_sha256':worker.digest(bootstrap.encode()),'new_remote_root':REMOTE,
        'model_or_GPU_calls_authorized':0})
    print(completed.stdout.decode(errors='replace'))
    if completed.returncode:raise RuntimeError('Remote CPU bootstrap failed; original logs preserved, never duplicate invocation')


def collect():
    # This is a read-only postexit collection, never an experiment retry.
    tarpath=LOCAL/'remote-admission.tar'
    with tarpath.open('xb')as stream:
        result=subprocess.run(SSH+['tar','-C',REMOTE,'-cf','-','admission-01','cpu-worker.stdout.log',
            'cpu-worker.stderr.log','invocation.json'],stdout=stream,stderr=subprocess.PIPE,timeout=180)
    (LOCAL/'collection.stderr').write_bytes(result.stderr)
    if result.returncode:raise RuntimeError('Collection failed; remote terminal remains immutable')
    output=LOCAL/'collected';output.mkdir(exist_ok=False)
    with tarfile.open(tarpath,'r:')as archive:
        for member in archive:
            path=output/member.name
            if not path.resolve().is_relative_to(output.resolve()):raise RuntimeError('Unsafe archive path')
            if member.isdir():path.mkdir(parents=True,exist_ok=True)
            elif member.isfile():
                path.parent.mkdir(parents=True,exist_ok=True)
                with path.open('xb')as target:target.write(archive.extractfile(member).read())
            else:raise RuntimeError('Unexpected non-file artifact in CPU admission archive')
    admitted=output/'admission-01';seal=json.loads((admitted/'seal.json').read_text())
    for row in seal['files']:
        path=admitted/row['path'];assert path.stat().st_size==row['bytes']and worker.digest(path.read_bytes())==row['sha256'],row
    previous='0'*64;count=0
    for line in(admitted/'journal.jsonl').read_text().splitlines():
        event=json.loads(line);supplied=event.pop('sha256')
        assert event['seq']==count and event['previous']==previous
        assert worker.digest(worker.canonical(event))==supplied
        previous=supplied;count+=1
    assert count==seal['journal_events']and previous==seal['journal_head']
    terminal=json.loads((admitted/'terminal.json').read_text())
    write(LOCAL/'collection-receipt.json',{'terminal':terminal,'verified_files':len(seal['files']),
        'journal_events':count,'journal_head':previous,'remote_seal_sha256':worker.digest((admitted/'seal.json').read_bytes()),
        'archive_sha256':worker.digest(tarpath.read_bytes()),'all_original_processor_tensor_bytes_collected':True})
    print(json.dumps({'status':terminal['status'],'admitted':terminal['admitted_requests'],
        'verified_files':len(seal['files']),'events':count,'model_calls':0}))


if __name__=='__main__':
    {'freeze':freeze,'execute':execute,'collect':collect}[sys.argv[1]]()
