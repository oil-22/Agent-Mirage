"""Build an isolated source package, without staging/authorization or launching."""
import ast
import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREP = HERE.parent
PARENT = PREP.parent
OLD = PARENT / 'approved-offline-receipt-repair-01/package'
REMOTE = '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/history-image-preread-development-20261115-01'
OUTPUT = '/data/researcher/jev-defense-four-gpu-20261106/history-image-preread-development-20261115-01'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x',encoding='utf8',newline='\n') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2)


def copy_file(source, target):
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:
        stream.write(source.read_bytes())


def main():
    target = HERE / 'package'
    assert not target.exists(), 'Inspect existing immutable preparation'
    ptr = json.loads((HERE/'CPU-checks-current.json').read_bytes()); checks = Path(ptr['root'])
    assert sha(checks/'seal.json') == ptr['seal_sha256']
    assert json.loads((checks/'result.json').read_bytes())['failed'] == 0
    old_manifest = json.loads((OLD/'offline-manifest.json').read_bytes())
    proposed = Path(json.loads((PREP/'proposed-inputs-current.json').read_bytes())['root'])
    proposal = json.loads((PREP/'publication-current.json').read_bytes())
    cpu = Path(json.loads((PREP/'native-CPU-current.json').read_bytes())['root'])
    frozen = Path(json.loads((PREP/'frozen-sources-current.json').read_bytes())['root'])
    generations = Path(json.loads((HERE/'generation-bindings-current.json').read_bytes())['root'])
    sources = json.loads((frozen/'PRIVATE-source-index.json').read_bytes())
    # Exact original native loader/backend/processor dependencies; no old GUI
    # launcher, service queue, Flash inference code, or PRIVATE expectations.
    native_names = ['primary_server.py','primary-reference.json','explicit-placement.json','preflight_support.py',
                    'torch_chunk_lifetime.py','memory_lifetime.py','mlp_lifetime.py',
                    'flash/gate_core.py','flash/wire_contract.py','flash/resource_guard.py']
    native_names += [name[len('native/'):] for name in old_manifest['files'] if name.startswith('native/release/')]
    for name in native_names:
        assert sha(OLD/'native'/name) == old_manifest['files']['native/'+name], name
        copy_file(OLD/'native'/name,target/'native'/name)
    for name in ['offline_protocol.py','checked_native_call.py','offline_worker.py']:
        copy_file(HERE/name,target/name)
    copy_file(proposed/'reading_contract.py',target/'reading_contract.py')
    copy_file(OLD/'prior-memory-proof.json',target/'prior-memory-proof.json')
    old_guard = (OLD/'offline_guard.py').read_text(encoding='utf8')
    tree = ast.parse(old_guard)
    names = ['load','require','save','previous_models_exited','validate_gpu','inherited_locks','resource']
    functions = [n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in names]
    guard_prefix = '''import hashlib,json,os,sys,time
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path[:0]=[str(P/'native/flash'),str(P/'native/release'),str(P/'native')]
from resource_guard import identity,locks,sha,gpu_snapshot,LEASE
PREVIOUS_OUT=Path('/data/researcher/jev-defense-four-gpu-20261106/flash-ample-memory-gui-20261114-linked11')
PREVIOUS_PACKAGE=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/flash-ample-memory-gui-20261114-linked11')
'''
    guard = guard_prefix + '\n\n'.join(ast.get_source_segment(old_guard,n)for n in functions) + '\n'
    (target/'runtime_guard.py').write_text(guard,encoding='utf8',newline='\n')
    parsed = ast.parse(guard)
    assert all(ast.dump(n)==ast.dump(next(x for x in parsed.body if isinstance(x,ast.FunctionDef)and x.name==n.name))for n in functions)
    old_worker=(OLD/'offline_worker.py').read_text(encoding='utf8');worker_tree=ast.parse(old_worker)
    installer=next(n for n in worker_tree.body if isinstance(n,ast.FunctionDef)and n.name=='install_previous_memory_implementation')
    installer_source='import hashlib,inspect,sys\nfrom pathlib import Path\nfrom runtime_guard import P,require,save,sha,load\n\n'+ast.get_source_segment(old_worker,installer)+'\n'
    (target/'memory_installer.py').write_text(installer_source,encoding='utf8',newline='\n')
    assert ast.dump(installer)==ast.dump(next(n for n in ast.parse(installer_source).body if isinstance(n,ast.FunctionDef)))
    old_launcher=(OLD/'offline_launcher.py').read_text(encoding='utf8')
    # This is a new launcher; no old main/queue or ten-call authorization runs.
    start=old_launcher.index('    manifest, plan = guard.verify_package()')
    end=old_launcher.index('    old, oldfds = guard.locks()',start)
    replacement='''    require(len(sys.argv)==3, 'Real authorization path and SHA required')
    from offline_worker import validate_package
    authorization_path, authorization_sha = Path(sys.argv[1]), sys.argv[2]
    manifest, authorization = validate_package(authorization_path, authorization_sha)
    require(os.getuid()==1033, 'Wrong task UID')
    previous_processes = guard.previous_models_exited()
'''
    launcher=old_launcher[:start]+replacement+old_launcher[end:]
    launcher=launcher.replace('from receipt_binding import verify_zero_call_parent\n','')
    launcher=launcher.replace('import offline_guard as guard','import runtime_guard as guard').replace('from offline_guard import P, load, require, save, sha','from runtime_guard import P, load, require, save, sha')
    launcher=launcher.replace("    save(output / 'previous-GUI-admission.json', admission)\n",'')
    launcher=launcher.replace("sha(P / 'authorization.json')","sha(authorization_path)")
    launcher=launcher.replace("str(P / 'offline_worker.py')]","str(P / 'offline_worker.py'), str(authorization_path), authorization_sha]")
    ast.parse(launcher)
    assert 'verify_package()'not in launcher and 'verify_zero_call_parent('not in launcher and 'admission_file'not in launcher
    (target/'offline_launcher.py').write_text(launcher,encoding='utf8',newline='\n')
    rows=[]
    for source in sources:
        cid=source['case_id'];wrapper=json.loads((cpu/(cid+'.json')).read_bytes())
        copy_file(cpu/(cid+'.json'),target/'CPU'/ (cid+'.json'))
        name=cid+'-original-effective-generation.json'
        copy_file(generations/name,target/'generation'/name)
        rows.append({'case_id':cid,'original_request':source['folder'],'original_request_id':source['request_id'],
            'original_request_seal_sha256':source['seal_sha256'],'original_body_file_sha256':source['source_body_file_sha256'],
            'CPU_wrapper':'CPU/'+cid+'.json','original_generation_file':'generation/'+name,
            'preread_body_file_sha256':wrapper['result']['proposed_preread_body_file_sha256'],
            'source_binding_file_sha256':wrapper['result']['source_binding_file_sha256']})
    for path in target.rglob('*.py'):
        ast.parse(path.read_text(encoding='utf8'))
    files={str(p.relative_to(target)).replace('\\','/'):sha(p)for p in target.rglob('*')if p.is_file()}
    assert not any('authorization.json'==n or 'PRIVATE' in n or 'response.json' in n for n in files)
    save(target/'execution-manifest.json',{'version':'preread-offline20-execution-preparation-v1','files':files,
         'remote_package':REMOTE,'output':OUTPUT,'study_claim_root':OUTPUT+'/study',
         'proposal_seal_sha256':proposal['seal_sha256'],'proposal_publication':proposal['publication'],
         'cases':rows,'maximum_new_primary_calls_pending_user_approval':20,
         'prior_memory_proof':REMOTE+'/prior-memory-proof.json','prior_memory_proof_sha256':sha(target/'prior-memory-proof.json'),
         'actual_new_model_GUI_calls_in_preparation':0,'authorization_supplied':False,'staged_or_submitted':False,
         'existing_guard_function_AST_unchanged':names,'existing_memory_installer_AST_unchanged':True})
    result={'time':time.time(),'package':str(target),'manifest_sha256':sha(target/'execution-manifest.json'),
            'files':len(files),'unchanged_native_files':len(native_names),
            'original_generation_backend_sha256':sha(target/'native/release/defense/qwen_backend.py'),
            'all_proposed_prompts_and_condition_unchanged':True,'CPU_protocol_checks':json.loads((checks/'result.json').read_bytes())['passed'],
            'real_authorization_created':False,'new_GPU_lease_acquired':False,'actual_model_GPU_GUI_calls':0,
            'actual_multidevice_forward_and_runtime_integration_UNTESTED':True,'remote_staged':False}
    save(HERE/'package-preparation.json',result)
    print(json.dumps(result))


if __name__=='__main__':
    main()
