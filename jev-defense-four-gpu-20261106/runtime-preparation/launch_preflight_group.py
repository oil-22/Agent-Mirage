"""One sealed task launcher, started only by the root's existing four-GPU holder.

Starts separate native environments with the same inherited task UUID locks.
It never terminates a process unless exact UID/full command/starttime still match.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import time
import traceback

from four_gpu_contract import FLASH, digest, identity_matches, validate_layout
from preflight_service import check_inherited_locks, identity, save, sha

BASE = Path('/home/researcher/jev-defense-four-gpu-20261106')


def commands_for(spec, root, worker, lease):
    commands = {}
    for role in ['primary', FLASH]:
        options = spec['roles'][role]
        python = options['python']
        if role == 'primary' and python != '/opt/whz/conda-envs/webmall-vlm/bin/python':
            raise ValueError('Primary must use the original environment')
        if role == FLASH and not Path(python).is_relative_to(BASE / 'flash-preparation'):
            raise ValueError('Flash must use its new independent environment')
        commands[role] = [python, '-u', str(worker), '--role', role, '--root', str(root / role),
            '--lease', str(lease), '--config', str(root / 'runtime-config.json'),
            '--admission', options['admission'], '--port', str(options['port'])]
    return commands


def stop_owned(children):
    if children:
        group = children[0]['log'].parent
        marker = group / 'stop-requested.json'
        if not marker.exists(): save(marker, {'time': time.time(), 'reason': 'owned_launcher_requested_stop'})
    for child in children:
        if child['process'].poll() is not None:
            continue
        try:
            actual = identity(child['process'].pid)
        except FileNotFoundError:
            continue
        if not identity_matches(actual, child['identity']):
            raise RuntimeError('Worker identity changed; refuse to signal')
        # The worker may already be in Python teardown after seeing the marker.
        # Sending USR1 here can hit a reset/default handler and turn successful
        # serving into exit -10. Marker/poll is the normal stop mechanism.
        child.setdefault('stop_requested_at', time.monotonic())


def progress_owned_stop(children):
    """Bounded force is allowed only for exact idle peers with all replies sealed."""
    for child in children:
        if child['process'].poll() is not None or 'stop_requested_at' not in child:
            continue
        elapsed = time.monotonic() - child['stop_requested_at']
        if elapsed < 30:
            continue
        group = child['log'].parent
        if not (group / child['role'] / 'ready.json').exists():
            continue  # Loading is not proof of an idle, completed server.
        requests = list((group / child['role'] / 'requests').glob('*'))
        if any(not (request / 'seal.json').exists() for request in requests):
            continue  # Never force an unfinished native forward.
        for request in requests:
            for name, expected in json.loads((request / 'seal.json').read_bytes()).items():
                if sha(request / name) != expected:
                    raise RuntimeError('Idle-stop request seal is invalid; do not force')
        try:
            actual = identity(child['process'].pid)
        except FileNotFoundError:
            continue
        if not identity_matches(actual, child['identity']):
            raise RuntimeError('Owned child identity changed; do not force')
        if 'force_snapshot' not in child:
            target = group / 'controlled-stop-preservation' / (child['role'] + '-' + str(time.time_ns()))
            target.mkdir(parents=True)
            for source in list(group.rglob('*')):
                if source.is_file() and 'controlled-stop-preservation' not in source.relative_to(group).parts:
                    dest = target / source.relative_to(group); dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, dest)
            save(target / 'snapshot-sha256.json', {str(p.relative_to(target)): sha(p)
                 for p in target.rglob('*') if p.is_file()})
            child['force_snapshot'] = str(target)
        number = signal.SIGTERM if elapsed < 35 else signal.SIGKILL
        if child.get('last_force_signal') == number:
            continue
        try:
            actual = identity(child['process'].pid)
        except FileNotFoundError:
            continue
        if not identity_matches(actual, child['identity']):
            raise RuntimeError('Idle worker identity changed immediately before signal')
        save(group / ('controlled-idle-stop-' + child['role'] + '-' + str(number) + '.json'),
             {'identity': actual, 'signal': int(number), 'all_existing_requests_sealed': True,
              'request_count': len(requests), 'preservation_root': child['force_snapshot'],
              'time': time.time(), 'semantic_failure_claim': False})
        os.kill(child['process'].pid, number)
        child['last_force_signal'] = number


def main(a):
    if os.getuid() != 1033 or not a.root.resolve().is_relative_to(BASE):
        raise RuntimeError('Task directory/UID mismatch')
    spec_raw = a.spec.read_bytes()
    if digest(spec_raw) != a.spec_sha256:
        raise RuntimeError('Launch specification differs from concrete reviewed file')
    spec = json.loads(spec_raw)
    a.root.mkdir(parents=True, exist_ok=False)
    lease = Path(os.environ['MIRAGE_TASK_LEASE'])
    lease_value = json.loads(lease.read_bytes())
    check_inherited_locks(lease_value)
    worker = Path(__file__).with_name('preflight_service.py')
    contract = Path(__file__).with_name('four_gpu_contract.py')
    if sha(worker) != spec['worker_source_sha256'] or sha(contract) != spec['contract_source_sha256']:
        raise RuntimeError('Worker/contract source differs from sealed launch specification')
    validate_layout(json.loads(Path(spec['layout']).read_bytes()))
    for role in ['primary', FLASH]:
        path = Path(spec['roles'][role]['admission'])
        if sha(path) != spec['admission_sha256'][role]:
            raise RuntimeError('Frozen finite preflight admission differs')
    # This script receives already held locks. Reacquiring a UUID lock in another
    # open description would fail against the holder and does not add ownership.
    descriptors = tuple(int(s) for s in os.environ['MIRAGE_GPU_LOCK_FDS'].split(','))
    commands = commands_for(spec, a.root, worker, lease)
    config = {**spec, 'commands': commands, 'group_root': str(a.root)}
    save(a.root / 'runtime-config.json', config)
    save(a.root / 'launch-specification.json', spec)
    save(a.root / 'process.json', identity(os.getpid()))
    (a.root / 'processes').mkdir()
    stop = {'value': False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(value=True))
    signal.signal(signal.SIGUSR1, lambda *_: stop.update(value=True))
    children = []
    try:
        for role in ['primary', FLASH]:
            env = dict(os.environ)
            env.update(CUDA_VISIBLE_DEVICES='4,5,6,7' if role == 'primary' else '7',
                       PYTHONUNBUFFERED='1', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                       TOKENIZERS_PARALLELISM='false', PYTHONDONTWRITEBYTECODE='1')
            log = a.root / (role + '.log')
            with log.open('xb') as handle:
                process = subprocess.Popen(commands[role], stdout=handle, stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL, env=env, cwd=str(BASE), pass_fds=descriptors,
                    start_new_session=True)
            actual = identity(process.pid)
            children.append({'role': role, 'process': process, 'identity': actual, 'log': log})
            save(a.root / (role + '-launch.json'), {'identity': actual, 'argv': commands[role],
                'visible_gpus': env['CUDA_VISIBLE_DEVICES'], 'inherited_lock_count': len(descriptors),
                'time': time.time()})
        print(json.dumps({'group': str(a.root), 'workers': [
            {'role': c['role'], 'pid': c['process'].pid} for c in children],
            'phase': 'loading_preflight_only', 'GUI_actions': 0}), flush=True)
        sent = False
        while any(child['process'].poll() is None for child in children):
            dead = [c for c in children if c['process'].poll() is not None]
            if (dead or stop['value']) and not sent:
                stop_owned(children)
                sent = True
            if sent: progress_owned_stop(children)
            time.sleep(1)
        if any(child['process'].returncode != 0 for child in children):
            raise RuntimeError('A preflight service failed; inspect preserved child logs and requests')
    except BaseException:
        save(a.root / 'launcher-failure.json', {'error': traceback.format_exc(), 'time': time.time()})
        stop_owned(children)
        # Hold the inherited locks while a worker finishes its current request.
        while any(c['process'].poll() is None for c in children):
            progress_owned_stop(children)
            time.sleep(1)
        raise
    finally:
        if children and not any(c['process'].poll() is None for c in children):
            save(a.root / 'exit.json', {'time': time.time(), 'workers': [
                {'role': c['role'], 'identity': c['identity'], 'exit_code': c['process'].poll()}
                for c in children], 'GUI_actions': 0})
            save(a.root / 'terminal-manifest.json', {str(p.relative_to(a.root)): sha(p)
                for p in a.root.rglob('*') if p.is_file() and p.name != 'terminal-manifest.json'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--spec-sha256', required=True)
    args = parser.parse_args()
    main(args)
