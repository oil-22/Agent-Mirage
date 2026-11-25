"""Create a new postexit snapshot; never invent the missing original terminals."""
import base64, hashlib, json, subprocess, time
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
HELPER=(ROOT/'progress-preparation/progress_remote.py').read_text(encoding='utf8')
TAIL=r'''
import shutil
BASE=Path('/home/researcher/jev-defense-four-gpu-20261106')
group=BASE/'online-service-group-1793978182501156243'
assert os.getuid()==1033
before_snapshot=service_snapshot(group)
def quiescent(value):
    assert all(not row['identity_matches'] and row['actual'] is None for row in value['workers'].values())
    assert not value['launcher']['identity_matches'] and value['launcher']['actual'] is None
    assert value['holder']['identity_matches'] and len(value['holder']['actual_locks'])==9
    assert not value['target_compute']
    assert value['workers']['primary']['request_counts']=={'completed':72,'failed':1,'pending_unsealed':0}
    assert value['workers']['pplx_flash']['request_counts']=={'completed':0,'failed':0,'pending_unsealed':0}
    assert value['state_snapshot']['phase']=='terminal_failure' and value['state_snapshot']['active'] is None
    assert value['journal']['uncommitted_partial_tail_bytes']==0
quiescent(before_snapshot)
assert not(group/'exit.json').exists() and not(group/'terminal-sha256.json').exists()
for role in ('primary','pplx_flash'): assert(group/role/'stopped.json').exists()
def inventory(root):
    result={}
    for p in sorted(root.rglob('*')):
        assert not p.is_symlink(),'Refuse linked source'
        if p.is_file():
            stat=p.stat();value=sha(p);now=p.stat()
            assert (stat.st_ino,stat.st_size,stat.st_mtime_ns)==(now.st_ino,now.st_size,now.st_mtime_ns)
            result[p.relative_to(root).as_posix()]=value
    return result
stamp=str(time.time_ns());out=BASE/'independent-service-postexit'/stamp
out.mkdir(parents=True,exist_ok=False);out.chmod(0o700)
mapping=inventory(group)
shutil.copytree(group,out/'service')
assert inventory(group)==mapping==inventory(out/'service')
config=read(group/'runtime-config.json')
online=Path(config['commands']['primary'][2]).parent
native=Path(config['preflight_source_root'])
sources={}
for label,root in [('online',online),('native',native)]:
    assert root.resolve().is_relative_to(BASE)
    expected=config['online_source_sha256' if label=='online' else 'preflight_source_sha256']
    for name,value in expected.items():assert sha(root/name)==value
    original=inventory(root);shutil.copytree(root,out/'sources'/label)
    assert original==inventory(root)==inventory(out/'sources'/label)
    sources[label]={'original_root':str(root),'sha256':original}
for name in ['resource_control.py','original-runtime.json','runtime-preparation/layout.proposed.json']:
    src=BASE/name;dst=out/'sources'/'base'/name;dst.parent.mkdir(parents=True,exist_ok=True)
    value=sha(src);shutil.copy2(src,dst);assert sha(src)==sha(dst)==value
    sources[name]={'original':str(src),'sha256':value}
holder_root=BASE/'resource-attempt-20261106-01'
launcher=before_snapshot['launcher']['expected']
return_file=holder_root/('child-'+str(launcher['pid'])+'-exit.json')
assert return_file.exists(),'Actual holder did not collect launcher returncode'
actual_return=read(return_file);assert actual_return['pid']==launcher['pid']
holder_files={}
for p in list((holder_root/'commands').glob('*.json'))+list(holder_root.glob('*-launch.json'))+[return_file]:
    raw=p.read_bytes()
    if p==return_file or str(group).encode() in raw or ('"pid": '+str(launcher['pid'])).encode() in raw:
        dst=out/'holder-originals'/p.relative_to(holder_root);dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_bytes(raw);assert sha(p)==sha(dst);holder_files[p.relative_to(holder_root).as_posix()]=sha(dst)
after_snapshot=service_snapshot(group);quiescent(after_snapshot)
assert inventory(group)==mapping
assert before_snapshot['journal']==after_snapshot['journal']
assert all(before_snapshot['workers'][r]['log']==after_snapshot['workers'][r]['log'] for r in ('primary','pplx_flash'))
def save(p,obj):
    with p.open('x',encoding='utf8')as f:json.dump(obj,f,indent=2)
save(out/'service-original-sha256.json',mapping)
save(out/'source-bindings.json',sources)
save(out/'actual-quiescence-snapshot.json',after_snapshot)
receipt={'stage':'independent_postexit_preservation_not_original_launcher_terminal',
    'time':time.time(),'root':str(out),'original_group':str(group),'snapshot_service_root':str(out/'service'),
    'original_exit_json_missing':True,'original_terminal_sha256_missing':True,
    'original_group_not_modified':True,'all_original_service_bytes_stable_before_copy_after':True,
    'sealed_service_files':len(mapping),'sealed_service_total_bytes':sum((group/n).stat().st_size for n in mapping),
    'service_original_manifest_path':str(out/'service-original-sha256.json'),
    'service_original_manifest_sha256':sha(out/'service-original-sha256.json'),
    'worker_exit_codes':{'primary':None,'pplx_flash':None},'worker_exit_codes_observed':False,
    'actual_holder_launcher_return':actual_return,'actual_holder_return_source':str(return_file),
    'actual_holder_return_source_sha256':sha(return_file),'holder_original_files':holder_files,
    'launcher_failure_preserved':read(group/'launcher-failure.json'),
    'actual_old_workers_and_launcher_pid_absent':True,'actual_holder_identity_and9locks':True,
    'actual_GPU4_7_compute_empty':True,'actual_GPU4_7':after_snapshot['physical_GPU4_7'],
    'request_counts':{r:after_snapshot['workers'][r]['request_counts'] for r in ('primary','pplx_flash')},
    'journal':after_snapshot['journal'],'logs_stable':{r:after_snapshot['workers'][r]['log']for r in ('primary','pplx_flash')},
    'worker_stopped_files_not_treated_as_zero_exit_proof':True,
    'replacement_manifest_provenance':'new independent external exhaustive SHA map; not original terminal and not execution success',
    'new_model_GUI_HTTP_scorer_or_signal_calls':0,'private_task_auth_token_exported_locally':False}
save(out/'receipt.json',receipt)
save(out/'seal.json',inventory(out))
public={}
for name in ('receipt.json','seal.json','service-original-sha256.json','source-bindings.json'):
    p=out/name;public[name]={'sha256':sha(p),'data':base64.b64encode(p.read_bytes()).decode()}
print(json.dumps({'root':str(out),'public':public}))
'''
CODE="import base64\n__name__='audit_helpers'\n"+HELPER+'\n'+TAIL
if __name__=='__main__':
    out=ROOT/('service-postexit-preservation-invocation-'+str(time.time_ns()));out.mkdir()
    (out/'source.py').write_text(CODE,encoding='utf8')
    run=subprocess.run(['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','3090',
        '/opt/whz/conda-envs/webmall-vlm/bin/python -B -'],input=CODE,capture_output=True,text=True,timeout=240)
    (out/'stderr.txt').write_text(run.stderr,encoding='utf8')
    if run.returncode:
        (out/'stdout.failure.txt').write_text(run.stdout,encoding='utf8');raise SystemExit(run.returncode)
    data=json.loads(run.stdout)
    for name,item in data['public'].items():
        raw=base64.b64decode(item['data']);assert hashlib.sha256(raw).hexdigest()==item['sha256']
        (out/name).write_bytes(raw)
    (out/'local-delivery.json').write_text(json.dumps({'remote_root':data['root'],
        'public_files_sha256':{n:i['sha256']for n,i in data['public'].items()},
        'source_sha256':hashlib.sha256(CODE.encode()).hexdigest(),'private_auth_or_full_inputs_saved_locally':False},indent=2),encoding='utf8')
    print(json.dumps({'local':str(out),'remote_root':data['root'],
        'receipt_sha256':data['public']['receipt.json']['sha256'],
        'seal_sha256':data['public']['seal.json']['sha256']}))
