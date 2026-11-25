"""Ask an owned v1 runner to stop between slots after the current complete pair."""
import hashlib
import json
import os
import sys
import time
from pathlib import Path


def load(path):
    return json.loads(path.read_bytes())


def write(path, payload):
    with path.open('x', encoding='utf-8') as file:
        json.dump(payload, file, ensure_ascii=False)
        file.flush()
        os.fsync(file.fileno())


def proc(pid):
    p = Path('/proc', str(pid))
    try:
        stat = (p / 'stat').read_text().rsplit(')', 1)[1].split()
        return {'pid': pid, 'uid': p.stat().st_uid, 'state': stat[0], 'start_ticks': stat[19],
                'command': (p / 'cmdline').read_bytes().replace(b'\0', b' ').decode().strip()}
    except (FileNotFoundError, ProcessLookupError):
        return None


def alive(saved):
    row = proc(saved['pid'])
    return (row is not None and row['state'] not in ('Z', 'X') and
            all(row[k] == saved[k] for k in ('pid', 'uid', 'start_ticks', 'command')))


def same_gate_owner(job):
    lock = Path(job['site_lock'])
    stat = lock.stat()
    key = f'{os.major(stat.st_dev):02x}:{os.minor(stat.st_dev):02x}:{stat.st_ino}'
    return any(parts[4] == str(job['outer']['pid']) and parts[5] == key
               for line in Path('/proc/locks').read_text().splitlines()
               if len(parts := line.split()) >= 8 and parts[1:4] == ['FLOCK', 'ADVISORY', 'WRITE'])


def score_event(path):
    if not path.exists():
        return None
    with path.open('rb') as f:
        f.seek(max(path.stat().st_size - 8192, 0))
        if f.tell():
            f.readline()
        lines = f.read().split(b'\n')[:-1]
    for line in reversed(lines):
        if b'"kind":"native_official_score"' not in line:
            continue
        row = json.loads(line)
        expected = row.pop('sha256')
        packed = json.dumps(row, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
        if hashlib.sha256(packed).hexdigest() != expected:
            raise ValueError('Native scoring event hash mismatch')
        return {**row, 'sha256': expected}
    return None


def main(job_path):
    job = load(job_path)
    result = job_path.with_name('result.json')
    runtime = Path(job['runtime'])
    assert os.getuid() == 1015 and hashlib.sha256((runtime / 'manifest.json').read_bytes()).hexdigest() == job['manifest']
    assert hashlib.sha256((runtime / 'plan.json').read_bytes()).hexdigest() == job['plan_sha256']
    queue = load(runtime / 'plan.json')['queue']
    prefix = job['prefix']
    assert 0 < prefix < len(queue) and prefix % 2 == 0 and queue[prefix-2]['pair_id'] == queue[prefix-1]['pair_id']
    assert queue[prefix-1] == job['target']
    runs = runtime / 'batch/runs'
    finish = time.monotonic() + 6 * 60 * 60
    while time.monotonic() < finish:
        if not alive(job['outer']) or not alive(job['runner']) or (runtime / 'STOP').exists():
            write(result, {'status': 'not_applied_original_identity_ended_or_stop_already_present'})
            return
        if (runs / queue[prefix]['run_id']).exists():
            write(result, {'status': 'not_applied_boundary_passed', 'first_slot_after_target': queue[prefix]})
            return
        paths = list((runs / job['target']['run_id']).glob('attempt-*'))
        assert len(paths) <= 1
        event = score_event(paths[0] / 'trusted-source/events.jsonl') if paths else None
        if event is not None:
            assert same_gate_owner(job) and alive(job['runner']) and alive(job['outer'])
            assert not (runs / queue[prefix]['run_id']).exists()
            proof = {'status': 'stop_marker_written_after_official_score', 'scheduled_prefix': prefix,
                     'source_score': event, 'scoring_attempt': str(paths[0]), 'target_run_id': job['target']['run_id'],
                     'manifest_sha256': job['manifest'], 'time': time.time(), 'not_a_trajectory_cancellation': True}
            # The action loop has already ended here. v1 only observes STOP at the next slot boundary.
            write(runtime / 'STOP', proof)
            write(result, proof)
            return
        time.sleep(0.15)
    write(result, {'status': 'not_applied_timeout_without_terminal_score'})


if __name__ == '__main__':
    main(Path(sys.argv[1]))
