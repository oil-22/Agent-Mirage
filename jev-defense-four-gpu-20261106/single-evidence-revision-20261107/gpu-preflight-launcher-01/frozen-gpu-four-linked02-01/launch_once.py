"""New once-only finite auxiliary preflight. Staged code only until root review.

The existing holder starts this launcher with its nine open lock descriptions.
Only the new native image worker is spawned; primary/Flash/GUI are never started.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import subprocess
import time
import traceback

from resource_gate import LEASE_PATH, assert_owned_resources, identity, same_identity, require


BASE = PurePosixPath('/home/researcher/jev-defense-four-gpu-20261106')
RUNTIME = BASE / 'runtime-preparation'
PACKAGE = RUNTIME / 'single-jev-9b-preflight-01'
PYTHON = '/opt/whz/conda-envs/webmall-vlm/bin/python'
HOLDER = {'pid': 2568295, 'uid': 1033, 'start_ticks': '1159211789',
          'command': PYTHON + ' -u ' + str(BASE / 'resource_control.py') +
                     ' --root ' + str(BASE / 'resource-attempt-20261106-01') + ' --worker'}
MODEL = {'repository': 'autotrust/JEV-9B', 'revision': '7ac669b8fb476ba926491e3d1c39f9330d68dbed',
         'base_repository': 'Qwen/Qwen3.5-9B', 'base_revision': 'c202236235762e1c871ad0ccb60c8ee5ba337b9a'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def save_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def validate_spec(spec):
    require(set(spec) == {'schema', 'approved_for_new_auxiliary_preflight', 'launcher_source_sha256',
                         'resource_gate_source_sha256', 'worker_source', 'manifest', 'lease',
                         'expected_holder', 'python', 'output_root', 'model', 'limits'}, 'Unexpected launch spec fields')
    require(spec['schema'] == 'single-jev-image-four-control-launch-v1', 'Unreviewed launcher schema')
    require(spec['approved_for_new_auxiliary_preflight'] is True, 'Root launch review is still false')
    require(same_identity(spec['expected_holder'], HOLDER), 'Unreviewed holder identity')
    require(spec['python'] == PYTHON and spec['model'] == MODEL, 'Pinned model/environment differs')
    require(spec['lease']['path'] == str(LEASE_PATH), 'Different lease path')
    require(PurePosixPath(spec['worker_source']['path']) == PACKAGE / 'native_image_gpu_preflight.py', 'Only the new image worker may start')
    require(PurePosixPath(spec['manifest']['path']).is_absolute() and PurePosixPath(spec['manifest']['path']).is_relative_to(BASE), 'Manifest is outside owned source scope')
    require(PurePosixPath(spec['output_root']).is_absolute() and PurePosixPath(spec['output_root']).is_relative_to(BASE), 'Output is outside owned task scope')
    require('..' not in PurePosixPath(spec['manifest']['path']).parts and '..' not in PurePosixPath(spec['output_root']).parts, 'Traversal components are forbidden')
    require(spec['limits'] == {'initial_auxiliary_requests': 4, 'automatic_format_retries': 0,
                               'actual_total_auxiliary_requests': 4, 'overall_package_auxiliary_cap': 8,
                               'unused_format_allowance_automatically_spent': False, 'primary_requests': 0, 'GUI_actions': 0,
                               'scorer_calls': 0, 'physical_compute_GPUs': [7],
                               'reservation_GPUs': [4, 5, 6, 7], 'semantic_resampling': False}, 'Finite resource/budget contract differs')
    for key in ['launcher_source_sha256', 'resource_gate_source_sha256']:
        require(isinstance(spec[key], str) and len(spec[key]) == 64, 'Missing source SHA')
    for key in ['worker_source', 'manifest', 'lease']:
        require(set(spec[key]) == {'path', 'sha256'}, 'Extra path/source payload')
        require(isinstance(spec[key]['sha256'], str) and len(spec[key]['sha256']) == 64, 'Missing source binding')


def worker_command(spec, output):
    return [spec['python'], '-u', spec['worker_source']['path'], '--manifest', spec['manifest']['path'],
            '--manifest-sha256', spec['manifest']['sha256'], '--output', str(output / 'worker')]


def holder_command(spec_path, spec_sha256, output):
    """Concrete command body for root review; this function writes/submits nothing."""
    return {'action': 'launch', 'argv': [PYTHON, str(PACKAGE / 'launch_once.py'),
             '--spec', str(spec_path), '--spec-sha256', spec_sha256, '--output', str(output)],
            'script_sha256': None}


def failure_record(exc):
    return {'error': traceback.format_exc(), 'time_unix': time.time(),
            'resource_evidence': getattr(exc, 'resource_evidence', None)}


class Journal:
    def __init__(self, path):
        self.stream = Path(path).open('xb')
        self.head = '0' * 64
        self.count = 0

    def append(self, kind, payload):
        body = {'index': self.count, 'previous_sha256': self.head, 'kind': kind,
                'time_unix': time.time(), 'payload': payload}
        digest = hashlib.sha256(canonical(body)).hexdigest()
        self.stream.write(canonical({**body, 'sha256': digest}) + b'\n')
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.head = digest
        self.count += 1

    def close(self):
        self.stream.close()


def claim_once(directory, manifest_sha256, payload):
    directory.mkdir(exist_ok=True)
    path = directory / (manifest_sha256 + '.claim.json')
    save_new(path, payload)  # O_EXCL via x: never removed, overwritten, or resumed.
    return path


def main(args):
    require(Path(__file__).resolve() == PACKAGE / 'launch_once.py', 'Launcher must be staged in the new holder-permitted package')
    require(os.getuid() == 1033, 'Launcher UID differs')
    raw_spec = args.spec.read_bytes()
    require(hashlib.sha256(raw_spec).hexdigest() == args.spec_sha256, 'Launch spec SHA differs')
    spec = json.loads(raw_spec)
    validate_spec(spec)
    require(args.output.resolve() == Path(spec['output_root']).resolve(), 'CLI output differs from sealed spec')
    require(args.output.resolve().is_relative_to(Path(BASE).resolve()) and args.output.resolve() != Path(BASE).resolve(), 'Resolved output escapes owned scope')
    require(not args.output.exists(), 'Never resume or overwrite an existing output')
    require(os.environ.get('MIRAGE_TASK_LEASE') == str(LEASE_PATH), 'Inherited lease path differs')
    require(sha(Path(LEASE_PATH)) == spec['lease']['sha256'], 'Original lease SHA differs')
    require(sha(__file__) == spec['launcher_source_sha256'], 'Launcher source differs')
    require(sha(Path(__file__).with_name('resource_gate.py')) == spec['resource_gate_source_sha256'], 'Resource gate source differs')
    for key in ['worker_source', 'manifest']:
        path = Path(spec[key]['path'])
        require(path.resolve().is_relative_to(BASE) and sha(path) == spec[key]['sha256'], 'Worker or manifest SHA differs')
    launcher_identity = identity(os.getpid())
    allowed = {os.getpid(): launcher_identity}
    before = assert_owned_resources(LEASE_PATH, spec['expected_holder'], allowed, require_empty=True)
    started = time.time()
    claim = claim_once(Path(PACKAGE / 'claims'), spec['manifest']['sha256'],
                       {'manifest_sha256': spec['manifest']['sha256'], 'spec_sha256': args.spec_sha256,
                        'output': str(args.output), 'launcher': launcher_identity,
                        'time_unix': started, 'maximum_new_auxiliary_requests_this_runner': 4,
                        'overall_package_cap': 8, 'unused_format_allowance_automatically_spent': False})
    args.output.mkdir(parents=True, exist_ok=False)
    journal = Journal(args.output / 'journal.jsonl')
    child = None
    child_identity = None
    child_log = None
    exit_code = 1
    stop_seen = {'value': False}
    def request_stop(*_):
        stop_seen['value'] = True
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    try:
        save_new(args.output / 'before-resources.json', before)
        save_new(args.output / 'process.json', launcher_identity)
        (args.output / 'launch-specification.json').write_bytes(raw_spec)
        (args.output / 'frozen-manifest.json').write_bytes(Path(spec['manifest']['path']).read_bytes())
        snapshot = args.output / 'source-snapshot'
        snapshot.mkdir()
        for path in [Path(__file__), Path(__file__).with_name('resource_gate.py'), Path(spec['worker_source']['path'])]:
            shutil.copyfile(path, snapshot / path.name)
            require(sha(path) == sha(snapshot / path.name), 'Source snapshot differs')
        journal.append('once_only_claimed', {'claim': str(claim), 'manifest_sha256': spec['manifest']['sha256']})
        # Recheck immediately before Popen. No new lock is acquired.
        pre_spawn = assert_owned_resources(LEASE_PATH, spec['expected_holder'], allowed, require_empty=True)
        save_new(args.output / 'immediate-pre-spawn-resources.json', pre_spawn)
        for key in ['worker_source', 'manifest']:
            require(sha(spec[key]['path']) == spec[key]['sha256'], 'Worker or manifest changed immediately before spawn')
        require(sha(Path(__file__).with_name('resource_gate.py')) == spec['resource_gate_source_sha256'], 'Resource source changed immediately before spawn')
        env = dict(os.environ)
        env.update({'CUDA_VISIBLE_DEVICES': '7', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
                    'TOKENIZERS_PARALLELISM': 'false', 'PYTHONUNBUFFERED': '1', 'PYTHONDONTWRITEBYTECODE': '1',
                    'MIRAGE_JEV_LAUNCHER_IDENTITY': canonical(launcher_identity).decode('utf-8')})
        fds = tuple(int(x) for x in env['MIRAGE_GPU_LOCK_FDS'].split(','))
        command = worker_command(spec, args.output)
        child_log = (args.output / 'worker.log').open('xb')
        child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=child_log, stderr=subprocess.STDOUT,
                                 cwd=str(BASE), env=env, pass_fds=fds, start_new_session=True)
        child_identity = identity(child.pid)
        save_new(args.output / 'worker-launch.json', {'identity': child_identity, 'argv': command,
                                                     'inherited_lock_FDs': list(fds), 'visible_GPU': '7',
                                                     'time_unix': time.time()})
        journal.append('single_auxiliary_worker_started', {'identity': child_identity, 'visible_GPU': '7'})
        while child.poll() is None:
            if stop_seen['value'] and not (args.output / 'stop-requested.json').exists():
                save_new(args.output / 'stop-requested.json', {'reason': 'launcher_signal_received', 'time_unix': time.time(),
                                                              'do_not_start_another_request': True})
                journal.append('stop_requested_marker_only', {'worker_identity': child_identity})
            time.sleep(0.25)
        exit_code = child.returncode
        journal.append('worker_exited', {'exit_code': exit_code, 'original_identity': child_identity})
        try:
            after = assert_owned_resources(LEASE_PATH, spec['expected_holder'], allowed, require_empty=True)
            save_new(args.output / 'after-resources.json', after)
        except Exception as exc:
            save_new(args.output / 'postexit-resource-failure.json', failure_record(exc))
            exit_code = 1
    except BaseException as exc:
        save_new(args.output / 'launcher-failure.json', {**failure_record(exc),
                                                       'existing_outputs_not_removed': True})
        journal.append('launcher_failure_preserved', {'worker_created': child is not None})
        # Never signal/kill another process. Keep inherited locks while a finite
        # worker exits; its marker is checked before the next request.
        if child is not None and child.poll() is None:
            if not (args.output / 'stop-requested.json').exists():
                save_new(args.output / 'stop-requested.json', {'reason': 'launcher_exception', 'time_unix': time.time(),
                                                              'do_not_start_another_request': True})
            while child.poll() is None:
                time.sleep(0.25)
        exit_code = 1
    finally:
        require(child is None or child.poll() is not None, 'Worker must truly exit before terminal sealing')
        if child_log is not None:
            child_log.flush()
            os.fsync(child_log.fileno())
            child_log.close()
        ended = time.time()
        save_new(args.output / 'exit.json', {'launcher_identity': launcher_identity, 'worker_identity': child_identity,
                                            'worker_exit_code': None if child is None else child.poll(),
                                            'launcher_exit_code': exit_code, 'started_unix': started, 'ended_unix': ended,
                                            'four_GPU_reserved_seconds_during_launcher': 4 * (ended - started),
                                            'reservation_GPUs': [4, 5, 6, 7], 'reservation_still_active_after_exit': True,
                                            'compute_GPU_scope': [7], 'primary_or_Flash_started': False,
                                            'GUI_actions': 0, 'scorer_calls': 0, 'semantic_success_claim': False})
        journal.append('terminal', {'launcher_exit_code': exit_code, 'worker_exited': True})
        journal.close()
        save_new(args.output / 'terminal-manifest.json',
                 {str(p.relative_to(args.output)): sha(p) for p in sorted(args.output.rglob('*')) if p.is_file()})
    return exit_code


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--spec-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parsed = parser.parse_args()
    try:
        code = main(parsed)
    except BaseException as exc:
        # Pre-claim failures cannot alter a prior output; preserve separately.
        target = Path(__file__).resolve().parent / 'prelaunch-failures' / (str(time.time_ns()) + '-' + str(os.getpid()))
        target.mkdir(parents=True, exist_ok=False)
        save_new(target / 'failure.json', {**failure_record(exc),
                                           'no_automatic_retry': True, 'old_outputs_untouched': True})
        save_new(target / 'seal.json', {'failure.json': sha(target / 'failure.json')})
        code = 1
    raise SystemExit(code)
