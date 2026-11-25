"""Read the new replay after exit; verify actual requests, generations, raw seals and locks."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def sha_file(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def load(p):
    return json.loads(p.read_bytes())


def canon(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def require(state, msg):
    if not state:
        raise RuntimeError(msg)


def verify_lease_released(lease):
    proc = lease['process']
    pid = proc['pid']
    root = Path('/proc') / str(pid)
    still_running = False
    if root.exists():
        try:
            tick = (root / 'stat').read_text().rsplit(') ', 1)[1].split()[19]
            cmd = (root / 'cmdline').read_bytes().replace(b'\0', b' ').decode().strip()
            uid = root.stat().st_uid
            still_running = (tick, cmd, uid) == (proc['start_ticks'], proc['command'], proc['uid'])
        except FileNotFoundError:
            pass
    require(not still_running, 'do not read terminal while the actual leased worker is alive')
    apps = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid,used_memory', '--format=csv,noheader,nounits'], text=True)
    parsed_apps = [line.split(', ') for line in apps.splitlines() if line.strip()]
    require(all(not (u in lease['uuid_order'] and int(p) == pid) for u, p, _ in parsed_apps), 'old worker no longer owns GPU compute')
    check = []
    for lock in lease['lock_files']:
        with Path(lock['path']).open('rb') as f:
            require(os.fstat(f.fileno()).st_ino == lock['inode'], 'same lock inode')
            outcome = 'free'
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(f, fcntl.LOCK_UN)
            except BlockingIOError:
                outcome = 'has_new_holder_after_original_exit'
            check.append({'path': lock['path'], 'inode': lock['inode'], 'observed_postexit': outcome})
    return {'old_worker_exited': True, 'old_worker_pid': pid, 'postexit_lock_probe': check,
            'other_current_compute_on_reserved_cards': [a for a in parsed_apps if a[0] in lease['uuid_order']]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path', type=Path)
    a = ap.parse_args()
    root, dst = a.path, a.path / 'public'
    plan = load(root / 'plan.json')
    prepared = load(dst / 'cpu-prepared.json')
    lease = load(dst / 'lease.json')
    postexit = verify_lease_released(lease)
    require(sha_file(root / 'worker.py') == plan['worker_sha256'] and sha_file(root / 'crop_token_probe.py') == plan['probe_sha256'] and
            sha_file(root / 'PROTOCOL.md') == plan['protocol_sha256'] and sha_file(root / 'plan.json') == prepared['plan_sha256'], 'worker/source plan SHA')
    positions = [(row['case'], arm) for row in plan['cases'] for arm in row['arm_order']]
    manifest, rows, failures = {}, [], []
    mapping = load(root / 'blind-map.json')
    by_case_arm = {(v['case'], v['arm']): k for k, v in mapping.items()}
    require(len(by_case_arm) == len(mapping), 'one response per blind ID')
    cpu = {row['case']: row['arms'] for row in prepared['cases']}
    for (c, arm) in positions:
        directory = root / 'raw' / f'{c}-{arm}'
        entry = cpu[c][arm]
        archived = root / 'native-inputs' / entry['body_file']
        require(sha_file(archived) == entry['body_sha256'], 'sealed prepared full body')
        if not directory.is_dir():
            continue
        manifest[entry['body_file']] = entry['body_sha256']
        start = load(directory / 'start.json')
        require(start['case'] == c and start['arm'] == arm and start['body_sha256'] == entry['body_sha256'], 'actual call start binds prepared body')
        if (directory / 'first-forward.json').exists():
            require(load(directory / 'first-forward.json') == entry['tensors'], 'actual first forward tensor manifest')
        if (directory / 'failure.json').exists():
            failures.append({'case': c, 'arm': arm, **load(directory / 'failure.json')})
        if not (directory / 'result.json').exists():
            require((directory / 'failure.json').exists(), 'terminal raw directory without result or failure')
            continue
        metric = load(directory / 'result.json')
        record = load(directory / 'actual-native-call.json')
        require(sha_file(directory / 'actual-native-call.json') == metric['actual_native_call_sha256'], 'native result SHA')
        require(record['request_messages_sha256'] == sha(canon(load(archived)['messages'])), 'native generator used actual body')
        ids = record['input_ids']; generated = record['generated_ids']
        require(sha(struct.pack(f'<{len(ids)}q', *ids)) == entry['tensors']['input_ids']['sha256'], 'native recorded full input IDs')
        eos = record['generation_config']['eos_token_id']; eos = eos if isinstance(eos, list) else [eos]
        natural = bool(generated and generated[-1] in eos and not record['hit_output_cap'])
        require((len(ids), len(generated), natural) == (metric['input_tokens'], metric['output_tokens'], metric['natural_EOS']), 'EOS result recount')
        require(record['generation_config']['max_new_tokens'] == plan['max_output'] and record['generation_config']['do_sample'] is False and
                not record['environment_actions_executed'] and record['verifier_grammar'] is None, 'same native actor generation')
        key = by_case_arm[c, arm]
        visible = load(dst / 'blind' / (key + '.json'))
        require(visible['candidate'] == record['text'] and visible['candidate_sha256'] == sha(record['text'].encode()) and
                visible['case'] == c and visible['natural_EOS'] == natural, 'blind review exact output')
        rows.append(metric)
    recorded = [load(p) for p in sorted((root / 'receipts').glob('*.json'))]
    require(rows == recorded and len(mapping) == len(rows), 'raw and progress receipts have same delivered calls in same order')
    term = load(dst / 'terminal.json') if (dst / 'terminal.json').exists() else None
    if term:
        require(term['native_call_manifest_sha256'] == sha(canon(rows)), 'terminal hash of exact call receipts')
        require(len(rows) == plan['max_calls'] and not failures, 'complete terminal has all preregistered calls')
    for p in sorted((root / 'raw').rglob('*')):
        if p.is_file():
            manifest[str(p.relative_to(root))] = sha_file(p)
    for p in sorted(dst.rglob('*')):
        if p.is_file():
            manifest[str(p.relative_to(root))] = sha_file(p)
    for p in sorted((root / 'cases').glob('T*.json')):
        case = load(p)
        for key in [case['current_image_sha256'], case['crop_sha256']]:
            image = root / 'cases' / 'source-images' / (key + '.png')
            require(sha_file(image) == key, 'review source/crop pixels')
        manifest[str(p.relative_to(root))] = sha_file(p)
    print(json.dumps({'audit_timestamp': time.time(), 'terminal': term, 'completed': len(rows), 'attempted': len(rows)+len(failures),
                      'failures': failures, 'max_calls': plan['max_calls'], 'rows': rows, 'postexit': postexit,
                      'proofs': manifest, 'blind_map_sha256': sha_file(root / 'blind-map.json')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
