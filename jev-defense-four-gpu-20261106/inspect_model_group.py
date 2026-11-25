"""Read actual worker identities, lock FDs, CUDA ownership and sealed requests."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.request

BASE = Path('/home/researcher/jev-defense-four-gpu-20261106')
sys.path.insert(0, str(BASE / 'runtime-preparation'))
from preflight_service import identity, resource_admission


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def locks_for(pid, lease):
    rows = []
    for expected in lease['lock_records']:
        fd = Path('/proc', str(pid), 'fd', str(expected['fd']))
        info = Path('/proc', str(pid), 'fdinfo', str(expected['fd'])).read_text()
        target = str(fd.readlink())
        assert target == expected['path'] and fd.stat().st_ino == expected['inode']
        assert 'lock:' in info
        rows.append({'fd': expected['fd'], 'path': target, 'inode': fd.stat().st_ino})
    return rows


def main(a):
    config = json.loads((a.root / 'runtime-config.json').read_bytes())
    lease_path = BASE / 'resource-attempt-20261106-01/lease.json'
    lease = json.loads(lease_path.read_bytes())
    launcher_record = json.loads((a.root / 'process.json').read_bytes())
    assert identity(launcher_record['pid']) == launcher_record
    launcher_locks = locks_for(launcher_record['pid'], lease)
    rows = []
    for role in ['primary', 'pplx_flash']:
        path = a.root / (role + '-launch.json')
        if not path.exists():
            rows.append({'role': role, 'phase': 'not_launched'})
            continue
        launch = json.loads(path.read_bytes())
        actual = identity(launch['identity']['pid'])
        assert actual == launch['identity'] and actual['uid'] == 1033
        assert actual['command'] == ' '.join(launch['argv'])
        row = {'role': role, 'identity': actual, 'held_locks': locks_for(actual['pid'], lease),
               'phase': 'loading', 'requests': []}
        log = a.root / (role + '.log')
        if log.exists():
            row.update(log_sha256=sha(log), log_bytes=log.stat().st_size,
                       log_tail=log.read_text(errors='replace')[-1800:])
        root = a.root / role
        loaded, ready = root / 'loaded.json', root / 'ready.json'
        if loaded.exists():
            row['loaded'] = json.loads(loaded.read_bytes())
            row['loaded_sha256'] = sha(loaded)
        if ready.exists():
            value = json.loads(ready.read_bytes())
            assert value['loaded_sha256'] == sha(loaded)
            token = Path(config['token_file']).read_text().strip()
            req = urllib.request.Request('http://127.0.0.1:' + str(value['port']) + '/health',
                headers={'Authorization': 'Bearer ' + token})
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    row['health'] = json.load(response)
                row['phase'] = row['health']['phase']
            except Exception as error:
                row.update(phase='health_unavailable_or_inference_pending', health_error=str(error))
        for request in sorted((root / 'requests').glob('*')):
            if not request.is_dir():
                continue
            record = {'path': str(request), 'phase': 'pending'}
            seal = request / 'seal.json'
            if seal.exists():
                manifest = json.loads(seal.read_bytes())
                assert all(sha(request / name) == expected for name, expected in manifest.items())
                record.update(seal_verified=True, seal_sha256=sha(seal), sealed_files=len(manifest),
                              phase='failed' if (request / 'failure.json').exists() else 'completed')
            for name in ['response.json', 'failure.json', 'generation.json']:
                path = request / name
                if path.exists():
                    value = json.loads(path.read_bytes())
                    record[name] = {k: value[k] for k in ['status', 'input_tokens', 'output_tokens',
                        'model', 'revision', 'usage', 'seconds', 'eos', 'stopped_on_eos',
                        'finish_reason', 'max_new_tokens'] if k in value}
                    if name == 'generation.json':
                        record['generation_keys'] = list(value)
                        for field in ['input_ids', 'generated_ids']:
                            if field in value:
                                record[name][field + '_count'] = len(value[field])
            row['requests'].append(record)
        rows.append(row)
    # Called in this read-only process: inspect resource_admission directly without
    # attempting to reacquire or pretending to inherit the workers' lock FDs.
    from four_gpu_contract import validate_resource_group
    import subprocess
    registrations = [json.loads(path.read_bytes()) for path in (a.root / 'processes').glob('*.json')]
    actuals = {r['identity']['pid']: identity(r['identity']['pid']) for r in registrations}
    lines = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid',
        '--format=csv,noheader,nounits'], text=True).splitlines()
    compute = [{'uuid': s.split(',')[0].strip(), 'pid': int(s.split(',')[1])}
               for s in lines if s.strip()]
    resources = validate_resource_group(lease, registrations, actuals, compute)
    result = {'time': time.time(), 'launcher': launcher_record,
        'launcher_held_lock_count': len(launcher_locks), 'resources': resources,
        'workers': rows, 'inspector_model_calls': 0, 'GUI_actions': 0}
    output = a.root / 'inspections' / str(time.time_ns())
    output.mkdir(parents=True)
    (output / 'inspection.json').write_text(json.dumps(result, indent=2))
    (output / 'seal.json').write_text(json.dumps({'inspection.json': sha(output / 'inspection.json')}))
    print(json.dumps({'receipt': str(output / 'inspection.json'), 'workers': [
        {'role': row['role'], 'phase': row['phase'], 'requests': row.get('requests', [])}
        for row in rows], 'resources': resources, 'GUI_actions': 0}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    main(parser.parse_args())
