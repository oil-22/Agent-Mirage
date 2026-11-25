"""Read the live panel and owned resources. Does not issue any actions."""

from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time


def load(p):
    return json.loads(Path(p).read_bytes())


def identity(pid):
    d = Path(f'/proc/{pid}')
    try:
        stat = (d / 'stat').read_text().rsplit(') ', 1)[1].split()
        return {'pid': pid, 'uid': d.stat().st_uid, 'start_ticks': stat[19],
                'cmdline': (d / 'cmdline').read_bytes().decode().strip('\0').split('\0')}
    except (OSError, UnicodeError):
        return None


def stable():
    cases = []
    for c in load('live_plan.json')['cases']:
        p = Path('run/episodes') / c['id'] / 'terminal.json'
        try:
            v = load(p)
        except (OSError, ValueError):
            continue
        if v.get('case') == c:
            cases.append((p, v))
    return cases


def sample(rows):
    keep = {Path('actor-template.json'), Path('fixture.html'), Path('live_plan.json'), Path('gate-contract.json'),
            Path('run/gpu-lease.json'), Path('run/source/source.json'), Path('run/primary/loaded.json'),
            Path('run/flash/loaded.json'), Path('run/flash/checkpoint-before.json')}
    picked = set()
    for p, v in rows:
        c = v['case']
        held = v['holds']
        key = (c['arm'], v['status'], bool(held))
        if key in picked or len(picked) >= 18:
            continue
        picked.add(key)
        keep |= {p.parent, Path('run/source') / c['id']}
        keep |= {Path('run/flash') / r['request_id'] for r in v['flash']}
        if v['main_result']:
            keep.add(Path('run/primary') / v['main_result']['request_id'])
    with tarfile.open(fileobj=sys.stdout.buffer, mode='w|') as tar:
        for p in sorted(keep):
            if p.exists():
                tar.add(p, arcname=p.as_posix())


def progress(rows):
    meta = Path('run/gpu-lease.json')
    result = {'attempt': Path.cwd().name, 'uid': os.getuid(), 'completed': len(rows),
              'attempted': len(list(Path('run/episodes').glob('*'))), 'samples_by_arm': Counter(),
              'status_counts': Counter(), 'main_results': 0, 'initial_first_NOs': 0,
              'first_held': Counter(), 'pre_timer_deliveries_not_visual_labels': Counter(), 'last': []}
    if Path('run/terminal.json').is_file():
        try:
            result['driver_terminal'] = load('run/terminal.json')['status']
        except (OSError, ValueError):
            pass
    for _, term in rows:
        arm, okay = term['case']['arm'], term['delivery']
        post = [f for f in term['frames'] if f['action_sequence']]
        by_hold = {h['capture_id']: h for h in term['holds']}
        result['samples_by_arm'][arm] += 1
        result['status_counts'][term['status']] += 1
        result['main_results'] += bool(term['main_result'])
        if term['frames'] and term['frames'][0]['capture_id'] in by_hold:
            result['initial_first_NOs'] += 1
        if post and post[0]['capture_id'] in by_hold:
            result['first_held'][arm] += 1
        delivery_frame = next((f for f in post if okay and f['capture_id'] == okay['capture_id']), None)
        if delivery_frame and delivery_frame['phase_after_the_fact'] == 'early_before_render':
            result['pre_timer_deliveries_not_visual_labels'][arm] += 1
        result['last'].append({'case': term['case']['id'], 'status': term['status'],
                               'post_phases': [r['phase_after_the_fact'] for r in post],
                               'hold_reasons': [h['reason'] for h in term['holds']],
                               'delivery_phase': delivery_frame['phase_after_the_fact'] if delivery_frame else None})
    result['last'] = result['last'][-5:]
    if meta.is_file():
        lease = load(meta)
        expected = [lease['holder']]
        for role in ('flash', 'primary'):
            m = Path(f'run/{role}/loaded.json')
            if m.is_file():
                expected.append(load(m)['process'])
        result['lease_processes'] = [{'actual': identity(p['pid']), 'matches': identity(p['pid']) == p}
                                     for p in expected]
        pid = lease['holder']['pid']
        if identity(pid) == lease['holder']:
            locks = []
            for lock in lease['locks']:
                try:
                    fdpath = Path(f'/proc/{pid}/fd') / str(lock['fd'])
                    fdinfo = (fdpath.parent.parent / 'fdinfo' / str(lock['fd'])).read_text()
                    ok = (fdpath.stat().st_ino == lock['inode'] and os.readlink(fdpath) == lock['path']
                          and any(f'FLOCK ADVISORY WRITE {pid} ' in (' '.join(line.split()) + ' ')
                                  for line in fdinfo.splitlines()))
                except OSError:
                    ok = False
                locks.append({'path': lock['path'], 'held_by_original_driver': ok})
            result['locks'] = locks
    selected = []
    if meta.is_file():
        selected = ['-i', ','.join(u for role in lease['roles'].values() for u in role['uuids'])]
    try:
        output = subprocess.check_output(['nvidia-smi', *selected, '--query-compute-apps=gpu_uuid,pid,used_gpu_memory',
                                          '--format=csv,noheader,nounits'], timeout=16, text=True, stderr=subprocess.PIPE)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as exc:
        result['compute'], result['compute_snapshot_error'] = None, str(exc)
    else:
        result['compute'] = []
        for l in output.splitlines():
            gpu, pid, mem = (v.strip() for v in l.split(','))
            result['compute'].append({'gpu': gpu, 'pid': int(pid), 'used_mib': int(mem), 'identity': identity(int(pid))})
    result['observed_at_ns'] = time.time_ns()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    assert os.getuid() == 1033 and len(sys.argv) == 2 and sys.argv[1] in ('progress', 'sample')
    rows = stable()
    (sample if sys.argv[1] == 'sample' else progress)(rows)
