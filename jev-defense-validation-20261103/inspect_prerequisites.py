"""Read-only live resource/runtime audit; never launches, stops, resets or infers."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def main(host, root):
    expected_uid = {'3090': 1033, '4090': 1015}[host]
    assert os.getuid() == expected_uid
    root.mkdir(parents=True, exist_ok=True)
    out = {'time': time.time(), 'host': host, 'uid': os.getuid(), 'model_calls': 0,
           'GUI_actions': 0, 'resource_allocations': 0, 'containers_started': 0}
    query = lambda columns, mode: subprocess.check_output(
        ['nvidia-smi', '--query-' + mode + '=' + columns, '--format=csv,noheader'], text=True)
    out['gpu_inventory'] = query('index,uuid,memory.free', 'gpu')
    out['gpu_compute'] = query('gpu_uuid,pid,used_gpu_memory', 'compute-apps')
    identities = []
    for line in out['gpu_compute'].splitlines():
        pid = int(line.split(',')[1]);proc = Path('/proc') / str(pid)
        if not proc.exists():
            identities.append({'pid': pid, 'exited_during_inspection': True});continue
        identities.append({'pid': pid, 'uid': proc.stat().st_uid,
                           'full_command': (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode()})
    out['compute_identities'] = identities
    occupied = {s.split(',')[0].strip() for s in out['gpu_compute'].splitlines()}
    out['unallocated_candidates_not_leases'] = []
    for line in out['gpu_inventory'].splitlines():
        index, uuid, free = [s.strip() for s in line.split(',')]
        if uuid not in occupied and int(free.split()[0]) >= 23000:
            out['unallocated_candidates_not_leases'].append({'index': int(index), 'uuid': uuid})
    if host == '4090':
        p = subprocess.run(['docker', 'inspect', 'qwen27_vwa_classifieds',
                            'qwen27_vwa_classifieds_db'], capture_output=True, text=True)
        if p.returncode:
            out['site_inspection_error'] = p.stderr
        else:
            out['site'] = [{'id': c['Id'], 'name': c['Name'], 'running': c['State']['Running'],
                            'labels': c['Config']['Labels'], 'mounts': c['Mounts'],
                            'ports': c['HostConfig']['PortBindings']} for c in json.loads(p.stdout)]
        paths = ['/data/researcher/vwa100-2026-10-09/venv/bin/python',
                 '/data/researcher/vwa100-2026-10-09/run_reddit_internvl_smoke.py',
                 '/data/researcher/vwa100-2026-10-09/upstream/visualwebarena-main/browser_env/envs.py',
                 '/data/researcher/vwa100-2026-10-09/upstream/visualwebarena-main/evaluation_harness/evaluators.py',
                 '/data/researcher/vwa100-2026-10-09/selected100-classifieds-reddit/evaluator_configs_v1/classifieds_112.json']
        out['required_historical_runtime'] = {p: Path(p).exists() for p in paths}
        index = Path('/data/researcher/attention-audit-20261031/members.jsonl.gz')
        keys = ['run_reddit_internvl_smoke.py', 'plan80.json', 'native-vwa-request.json',
                'browser_env/', 'evaluation_harness/', 'classifieds_112.json']
        out['archive_index_matches'] = {k: [] for k in keys}
        if index.exists():
            out['archive_index_sha256'] = hashlib.sha256(index.read_bytes()).hexdigest()
            for line in gzip.open(index, 'rt'):
                entry = json.loads(line)
                for k in keys:
                    if k in entry[0]:out['archive_index_matches'][k].append(entry)
    p = root / ('prerequisites-' + host + '-' + str(time.time_ns()) + '.json')
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'receipt': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                      'free_candidates_not_leases': out['unallocated_candidates_not_leases'],
                      'runtime_exists': out.get('required_historical_runtime')}))


if __name__ == '__main__':
    p = argparse.ArgumentParser();p.add_argument('--host', choices=['3090', '4090'], required=True)
    p.add_argument('--root', type=Path, required=True);a = p.parse_args();main(a.host, a.root)
