"""Freeze an isolated technical continuation; never run the old queue or controls."""
import ast
import copy
import hashlib
import json
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / 'flash-ample-memory-gui-20261114-linked11'
R3090 = '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/' + HERE.name
OUT = '/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, value):
    with p.open('x', encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)


def write(p, value):
    with p.open('x', encoding='utf8', newline='\n') as f:
        f.write(value)


def main():
    package = HERE / 'package'
    assert not (package / 'manifest.json').exists()
    old = PARENT / 'package'
    assert sha(old / 'manifest.json') == '5e7e068ac14d75d668dfeca28ac7af61cf304e73187b21ed91169e9bb06c4762'
    manifest = json.loads((old / 'manifest.json').read_bytes())
    for name, expected in manifest['files'].items():
        assert sha(old / name) == expected
    meta = PARENT / 'stopped-parent-postexit-metadata-1794672243351127900'
    for name, expected in json.loads((meta / 'seal.json').read_bytes()).items():
        assert sha(meta / name) == expected
    contract = json.loads((meta / 'technical-continuation-contract.json').read_bytes())
    native = json.loads((meta / '3090.json').read_bytes())['result']
    gui = json.loads((meta / '4090.json').read_bytes())['result']
    failure = PARENT / 'GPU-conflict-failure-preservation-1794671002471667500'
    fn = json.loads((failure / '3090.json').read_bytes())['result']
    fg = json.loads((failure / '4090.json').read_bytes())['result']
    capacity = json.loads((PARENT / 'parent-capacity-reuse-binding-1794671638938857000.json').read_bytes())['result']
    bindings = {
        'package3090': capacity['package'], 'output3090': capacity['output'],
        'package4090': capacity['output'], 'manifest_sha256': contract['original_manifest_sha256'],
        'postexit_seal_sha256': contract['parent_postexit_seal_sha256'],
        'GUI_control_postexit_seal_sha256': contract['GUI_control_postexit_seal_sha256'],
        'capacity_seal_sha256': capacity['parent_capacity_seal_sha256'],
        'processes3090': [v['saved'] for v in native['actual_parent_processes_exited']],
        'processes4090': [v['saved'] for v in gui['actual_GUI_processes_exited']],
        'GUI_terminals': gui['terminals'],
        'failure_snapshot3090': fn['remote_root'], 'failure_snapshot3090_seal_sha256': fn['seal_sha256'],
        'failure_snapshot4090': fg['remote_root'], 'failure_snapshot4090_seal_sha256': fg['seal_sha256'],
        'failed_request_seal_sha256': fn['report']['failed_request_seal_sha256'],
        'local_parent_metadata_seal_sha256': sha(meta / 'seal.json'),
        'local_failure_preservation_seal_sha256': sha(failure / 'seal.json'),
        'historical_16_completed_not_reexecuted': True,
        'failed_partial_and_costs_and_occurrences_retained': True,
        'new_attempt_starts_original_native_initialization_not_restored_browser': True,
    }
    changed = {'primary_server.py', 'launch_group.py', 'expanded_guard.py', 'plan.json', 'gui_outer.py'}
    for name in list(manifest['files']) + ['private.token']:
        if name in changed:
            continue
        dest = package / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as f:
            f.write((old / name).read_bytes())
    save(package / 'parent-bindings.json', bindings)
    save(package / 'parent-capacity.json', capacity)
    with (package / 'technical-continuation-contract.json').open('xb') as f:
        f.write((meta / 'technical-continuation-contract.json').read_bytes())
    plan = json.loads((old / 'plan.json').read_bytes())
    original_plan = copy.deepcopy(plan)
    plan.update({
        'version': 'Flash-same-conditions-resource-continuation-linked12', 'created': time.time(),
        'queue': contract['remaining_queue'], 'expected_trajectories': 13,
        'matched_pairs': None, 'old_terminal_retries': False,
        'technical_retry_of_interrupted_T089_only': True,
        'parent_original_plan_total': 29, 'parent_completed': 16,
        'historical_capacity_proof_reuse': True,
        'capacity': 'Exact installed chunk/MLP source and native module/placement bound to completed parent proof; no new controls or current-process capacity claim.',
        'memory_lifetime_repair': 'Same already validated process-local chunk/MLP code; no numerical changes; zero new capacity calls.',
        'technical_failure': 'Preserve and stop this separate queue. Any further technical continuation needs a new linked attempt.',
        'failed_partial_occurrences_and_costs_retained': True,
    })
    save(package / 'plan.json', plan)

    primary = (old / 'primary_server.py').read_text(encoding='utf8')
    start = primary.index("        state('capacity_preflight')")
    end = primary.index("        state('ready')", start)
    primary = primary[:start] + """        state('historical_memory_installation')
        from historical_memory import install as install_historical
        if stop.is_set():raise RuntimeError('Manual stop before historical memory installation')
        installation=install_historical(native,P,root,save,sha,resource)
        journal.emit('historical_memory_code_installed',{'installation_seal_sha256':sha(root/'historical-memory-installation/seal.json'),'new_capacity_generation_calls':0,'historical_proof_only':True})
        if stop.is_set():raise RuntimeError('Manual stop during historical memory installation; no GUI starts')
""" + primary[end:]
    write(package / 'primary_server.py', primary)
    # Preserve NativeActor exactly, including the original generation/seed path.
    def actor_dump(source):
        return ast.dump(next(v for v in ast.parse(source).body if isinstance(v, ast.ClassDef) and v.name == 'NativeActor'), include_attributes=False)
    assert actor_dump(primary) == actor_dump((old / 'primary_server.py').read_text(encoding='utf8'))

    launcher = (old / 'launch_group.py').read_text(encoding='utf8')
    before = "    out=Path(manifest['output3090']);out.mkdir(exist_ok=False);me=identity(os.getpid());save(out/'launcher-process.json',me)"
    after = "    from continuation_guard import verify_native_parent\n    parent_proof=verify_native_parent(P)\n" + before + "\n    save(out/'parent-admission.json',parent_proof)"
    assert launcher.count(before) == 1
    launcher = launcher.replace(before, after)
    before = "'MIRAGE_EXPANDED_LEASE_SHA256':sha(leasefile)"
    after = before + ",'MIRAGE_RESOURCE_FORENSICS_ROOT':str(out/'primary/resource-conflicts')"
    assert launcher.count(before) == 1
    launcher = launcher.replace(before, after)
    write(package / 'launch_group.py', launcher)

    guard = (old / 'expanded_guard.py').read_text(encoding='utf8')
    guard = guard.replace('import json,os', 'import json,os,time')
    line = "            raise RuntimeError('Foreign/unverified compute on GPU '+str(index)+': '+str(pids))"
    replacement = """            # Preserve the already captured actual UID/full command/UUID snapshot before rejecting.
            root=Path(os.environ['MIRAGE_RESOURCE_FORENSICS_ROOT']);root.mkdir(parents=True,exist_ok=True)
            path=root/(str(time.time_ns())+'.json')
            with path.open('x',encoding='utf8')as f:
                json.dump({'time':time.time(),'GPU':index,'cards':cards,'compute':compute,'expected':expected,'not_model_NO':True,'no_automatic_retry':True},f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
""" + line
    assert guard.count(line) == 1
    guard = guard.replace(line, replacement)
    write(package / 'expanded_guard.py', guard)

    outer = (old / 'gui_outer.py').read_text(encoding='utf8')
    before = " from native_environment import NATIVE_ENV"
    after = " from continuation_guard import verify_gui_parent\n save(control/'parent-admission.json',verify_gui_parent(P))\n" + before
    assert outer.count(before) == 1
    outer = outer.replace(before, after)
    write(package / 'gui_outer.py', outer)

    from sys import path
    path.insert(0, str(package))
    from continuation_guard import validate_contract
    from historical_memory import validate_proof
    validate_contract(plan, contract, original_plan)
    validate_proof(capacity)
    invariant_names = ['gui_experiment.py', 'flash/gate_core.py', 'flash/flash_service.py', 'flash/flash_runtime.py',
                       'flash/gate-contract.json', 'flash/wire_contract.py', 'native-parser-source.py',
                       'actor-template.json', 'native_environment.py', 'release/defense/qwen_backend.py',
                       'explicit-placement.json', 'memory_lifetime.py', 'torch_chunk_lifetime.py', 'mlp_lifetime.py']
    invariants = {name: sha(package / name) for name in invariant_names}
    assert all(invariants[name] == manifest['files'][name] for name in invariant_names)
    files = {str(p.relative_to(package)).replace('\\', '/'): sha(p) for p in package.rglob('*')
             if p.is_file() and p.name not in ['manifest.json', 'private.token'] and '__pycache__' not in p.parts}
    for name in files:
        if name.endswith('.py'):
            ast.parse((package / name).read_text(encoding='utf8'))
    new_manifest = {**manifest, 'version': plan['version'], 'created': time.time(), 'files': files,
                    'package3090': R3090, 'package4090': OUT, 'output3090': OUT,
                    'trajectories': 13, 'remaining_queue': plan['queue'],
                    'source_prior_manifest_sha256': sha(old / 'manifest.json'),
                    'new_capacity_calls': 0, 'historical_capacity_source_reuse_only': True,
                    'parent_16_terminal_exclusion': contract['normal_completed_run_ids'],
                    'parent_failed_partial_preserved': contract['failed_attempt_preserved']}
    save(package / 'manifest.json', new_manifest)
    save(HERE / 'preparation.json', {
        'time': time.time(), 'phase': 'prepared_not_staged_or_submitted',
        'manifest_sha256': sha(package / 'manifest.json'), 'files': len(files),
        'remaining_queue': plan['queue'], 'invariant_file_sha256': invariants,
        'NativeActor_AST_identical': True,
        'parent_metadata_seal_sha256': sha(meta / 'seal.json'),
        'historical_capacity_code_installer_no_inference': True,
        'new_model_GUI_calls': 0, 'formal_prompt_condition_changed': False,
        'old_16_and_capacity_not_reexecuted': True,
        'failed_partial_costs_and_occurrences_remain': True,
        'offline10_user_approval_preserved': True,
    })
    print(json.dumps({'preparation': str(HERE / 'preparation.json'), 'manifest_sha256': sha(package / 'manifest.json'), 'files': len(files), 'queue': len(plan['queue']), 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
