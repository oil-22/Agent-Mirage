"""Independent once-only GUI service group; invoked by the existing task holder."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

from online_contract import digest, initial_state, validate_plan, validate_completed_stage_shutdown
from online_service import save, sha

BASE = Path('/home/researcher/jev-defense-four-gpu-20261106')


def verify_gate(spec):
    path = Path(spec['online_launch_gate'])
    if sha(path) != spec['online_launch_gate_sha256']:
        raise RuntimeError('Online launch gate differs from reviewed concrete receipt')
    gate = json.loads(path.read_bytes())
    if (gate.get('stage') != 'online_gui_authorization' or gate.get('approved') is not True or
            gate.get('once_only') is not True or gate.get('online_plan_sha256') != spec['online_plan_sha256'] or
            gate.get('observer_contract_sha256') != spec['flash_observer_contract_sha256']):
        raise RuntimeError('A new explicit online-stage readiness receipt is required')
    checks = {'primary_full_input_capacity': ['capacity_passed', 'full_input_preserved',
               'actual_input_forward_audited', 'output_budget_4096_preserved'],
              'observer_independent_review': ['actual_input_forward_audited',
               'original_source_images_reviewed', 'passed_for_gui_development', 'no_defense_success_claim']}
    for key, fields in checks.items():
        evidence = gate['evidence'][key]
        actual = Path(evidence['path'])
        if sha(actual) != evidence['sha256']:
            raise RuntimeError('Actual required preflight evidence changed: ' + key)
        value = json.loads(actual.read_bytes())
        if any(value.get(field) is not True for field in fields):
            raise RuntimeError('Preflight evidence does not admit a new GUI stage: ' + key)
    terminal = Path(gate['preflight_terminal_manifest'])
    if sha(terminal) != gate['preflight_terminal_manifest_sha256']:
        raise RuntimeError('Previous finite preflight terminal seal differs')
    for name, expected in json.loads(terminal.read_bytes()).items():
        if sha(terminal.parent / name) != expected:
            raise RuntimeError('Previous finite preflight terminal file changed')
    exited = json.loads((terminal.parent / 'exit.json').read_bytes())
    if any(row['exit_code'] != 0 for row in exited['workers']):
        shutdown = gate['completed_stage_shutdown_audit']
        shutdown_path = Path(shutdown['path'])
        if sha(shutdown_path) != shutdown['sha256']:
            raise RuntimeError('Completed-stage shutdown infrastructure proof changed')
        for name, expected in json.loads((shutdown_path.parent / 'seal.json').read_bytes()).items():
            if sha(shutdown_path.parent / name) != expected:
                raise RuntimeError('Completed-stage shutdown audit seal mismatch')
        validate_completed_stage_shutdown(json.loads(shutdown_path.read_bytes()), str(terminal.parent),
            sha(terminal), {row['role']: row['exit_code'] for row in exited['workers']},
            gate['evidence']['primary_full_input_capacity']['sha256'])
    return path, gate


def main(a):
    if os.getuid() != 1033 or not a.root.resolve().is_relative_to(BASE):
        raise RuntimeError('Owned task UID/root differs')
    if sha(a.spec) != a.spec_sha256:
        raise RuntimeError('Concrete online specification changed')
    spec = json.loads(a.spec.read_bytes())
    parent = Path(spec['preflight_source_root'])
    for name, expected in spec['preflight_source_sha256'].items():
        if sha(parent / name) != expected:
            raise RuntimeError('Reviewed unchanged native implementation differs')
    sys.path.insert(0, str(parent))
    from preflight_service import check_inherited_locks, identity
    from four_gpu_contract import FLASH, validate_layout
    from launch_preflight_group import stop_owned, progress_owned_stop
    lease_path = Path(os.environ['MIRAGE_TASK_LEASE'])
    lease = json.loads(lease_path.read_bytes()); check_inherited_locks(lease)
    validate_layout(json.loads(Path(spec['layout']).read_bytes()))
    here = Path(__file__).resolve().parent
    for name, expected in spec['online_source_sha256'].items():
        if sha(here / name) != expected:
            raise RuntimeError('Online service/admission source differs')
    if sha(Path(spec['online_plan'])) != spec['online_plan_sha256']:
        raise RuntimeError('Finite online trajectory plan differs')
    plan = json.loads(Path(spec['online_plan']).read_bytes()); runs = validate_plan(plan)
    gate_path, gate = verify_gate(spec)
    token = Path(spec['token_file']).read_bytes()
    if len(token.strip()) < 32 or token.strip() == Path(spec['previous_token_file']).read_bytes().strip():
        raise RuntimeError('Online group must use a new independent private transport token')
    # O_EXCL is the persistent once-only claim. A failed technical attempt keeps
    # this claim and needs a new linked gate; never replay the old terminal.
    claim = gate_path.with_name(gate_path.name + '.launch-claimed.json')
    save(claim, {'root': str(a.root), 'gate_sha256': sha(gate_path),
                 'spec_sha256': sha(a.spec), 'time': time.time()})
    a.root.mkdir(parents=True, exist_ok=False)
    for name in ('processes', 'transitions'): (a.root / name).mkdir()
    state = initial_state(plan); save(a.root / 'online-state.json', state)
    caps = {key: {'actor': 70, 'judge': 140, 'observer': row['caps']['observe'], 'steps': 50}
            for key, row in runs.items()}
    save(a.root / 'online-admission.json', {'stage': 'new_once_only_online_GUI',
        'plan_sha256': spec['online_plan_sha256'], 'run_order': list(runs), 'per_run_caps': caps,
        'online_launch_gate_sha256': sha(gate_path), 'preflight_terminal_manifest_sha256':
        gate['preflight_terminal_manifest_sha256'], 'automatic_retries': False})
    worker = here / 'online_service.py'
    commands = {}
    for role in ('primary', FLASH):
        python = spec['roles'][role]['python']
        if role == 'primary' and python != '/opt/whz/conda-envs/webmall-vlm/bin/python':
            raise RuntimeError('Primary original environment required')
        if role == FLASH and not Path(python).is_relative_to(BASE / 'flash-preparation'):
            raise RuntimeError('Flash new isolated environment required')
        commands[role] = [python, '-u', str(worker), '--role', role, '--root', str(a.root / role),
            '--lease', str(lease_path), '--config', str(a.root / 'runtime-config.json'),
            '--port', str(spec['roles'][role]['port'])]
    config = {**spec, 'commands': commands, 'group_root': str(a.root)}
    save(a.root / 'runtime-config.json', config)
    save(a.root / 'launch-specification.json', spec)
    save(a.root / 'process.json', identity(os.getpid()))
    descriptors = tuple(int(s) for s in os.environ['MIRAGE_GPU_LOCK_FDS'].split(','))
    stop = {'value': False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(value=True))
    signal.signal(signal.SIGUSR1, lambda *_: stop.update(value=True))
    children = []
    try:
        for role in ('primary', FLASH):
            env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '4,5,6,7' if role == 'primary' else '7',
                'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
                'TOKENIZERS_PARALLELISM': 'false', 'PYTHONDONTWRITEBYTECODE': '1'}
            log = a.root / (role + '.log')
            with log.open('xb') as handle:
                process = subprocess.Popen(commands[role], stdout=handle, stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL, env=env, cwd=str(BASE), pass_fds=descriptors,
                    start_new_session=True)
            actual = identity(process.pid)
            children.append({'role': role, 'process': process, 'identity': actual, 'log': log})
            save(a.root / (role + '-launch.json'), {'identity': actual, 'argv': commands[role],
                'visible_gpus': env['CUDA_VISIBLE_DEVICES'], 'inherited_lock_count': len(descriptors)})
        print(json.dumps({'group': str(a.root), 'stage': 'loading_new_online_group',
                          'workers': [{'role': c['role'], 'pid': c['process'].pid} for c in children]}), flush=True)
        sent = False
        while any(child['process'].poll() is None for child in children):
            if (any(c['process'].poll() is not None for c in children) or stop['value']) and not sent:
                stop_owned(children); sent = True
            if sent: progress_owned_stop(children)
            time.sleep(1)
        if any(child['process'].returncode != 0 for child in children):
            raise RuntimeError('Online worker failed; preserve terminal before any diagnosis')
    except BaseException:
        save(a.root / 'launcher-failure.json', {'error': traceback.format_exc(), 'time': time.time()})
        stop_owned(children)
        while any(c['process'].poll() is None for c in children):
            progress_owned_stop(children)
            time.sleep(1)
        raise
    finally:
        if children and not any(c['process'].poll() is None for c in children):
            save(a.root / 'exit.json', {'time': time.time(), 'workers': [
                {'role': c['role'], 'identity': c['identity'], 'exit_code': c['process'].poll()}
                for c in children]})
            save(a.root / 'terminal-sha256.json', {str(p.relative_to(a.root)): sha(p)
                for p in a.root.rglob('*') if p.is_file() and p.name != 'terminal-sha256.json'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--spec-sha256', required=True)
    main(parser.parse_args())
