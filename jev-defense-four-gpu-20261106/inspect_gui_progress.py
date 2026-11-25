"""Concurrent read-only SSH snapshots; write only new local evidence receipts."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote

BASE = Path(__file__).resolve().parent
SOURCE = BASE / 'progress-preparation/progress_remote.py'


def collect(host, config):
    code = 'PROGRESS_CONFIG = ' + repr(config) + '\n' + SOURCE.read_text(encoding='utf8')
    return json.loads(remote(code, timeout=90, host=host))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--service-only', action='store_true')
    parser.add_argument('--service-group', default='/home/researcher/jev-defense-four-gpu-20261106/online-service-group-1793978182501156243')
    parser.add_argument('--batch-root', default='/data/researcher/jev-defense-four-gpu-20261106/gui-batch-image-observer-01')
    parser.add_argument('--control-root', default='/data/researcher/jev-defense-four-gpu-20261106/gui-outer-control-01')
    parser.add_argument('--background-root', default='/data/researcher/jev-defense-four-gpu-20261106/gui-outer-background-01')
    args = parser.parse_args()
    tasks = [('3090', {'mode': 'service', 'group': args.service_group})]
    if not args.service_only:
        tasks.append(('4090', {'mode': 'controller', 'batch': args.batch_root,
            'control': args.control_root, 'background': args.background_root}))
    root = BASE / 'progress-evidence' / str(time.time_ns())
    root.mkdir(parents=True, exist_ok=False)
    with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
        futures = {host: pool.submit(collect, host, config) for host, config in tasks}
        values = {}
        for host, future in futures.items():
            try:
                values[host] = future.result()
            except Exception as error:
                values[host] = {'inspection_failed': True, 'error': str(error),
                    'HTTP_requests': 0, 'model_requests': 0, 'GUI_actions': 0}
    receipt = {'inspector_source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'local_wrapper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'snapshots_are_independent_times_not_atomic_across_hosts': True, 'results': values,
        'new_model_HTTP_GUI_calls': 0, 'semantic_labels_inferred': False}
    (root / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')
    (root / 'progress_remote.py').write_bytes(SOURCE.read_bytes())
    (root / 'inspect_gui_progress.py').write_bytes(Path(__file__).read_bytes())
    seal = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir() if p.is_file()}
    (root / 'seal.json').write_text(json.dumps(seal, indent=2), encoding='utf8')
    brief = {}
    for host, value in values.items():
        if value.get('inspection_failed'):
            brief[host] = {'inspection_failed': True, 'error': value['error']}
            continue
        evidence = value['evidence']
        brief[host] = ({'state': evidence['state_snapshot'], 'workers': {role: {
            'pid': row['expected']['pid'], 'identity_matches': row['identity_matches'],
            'held_locks': len(row.get('actual_locks', [])), 'request_counts': row['request_counts'],
            'sealed_native_EOS_count': row['sealed_native_EOS_count']} for role, row in evidence['workers'].items()},
            'foreign_target_compute_count': len(evidence['foreign_target_compute']),
            'journal_events': evidence['journal']['event_count']}
            if host == '3090' else {'batch_exists': evidence['batch_exists'],
                'status': evidence.get('status_snapshot'), 'eventchains': evidence['eventchains'],
                'failure_markers': evidence['failure_markers']})
    print(json.dumps({'receipt': str(root / 'receipt.json'), 'sha256': seal['receipt.json'],
        'snapshots': brief, 'new_model_HTTP_GUI_calls': 0}, ensure_ascii=False))


if __name__ == '__main__':
    main()
