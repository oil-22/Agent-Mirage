"""Only the new authorized receipt protocol; prior terminal processes stay dead."""
import json
import os
import subprocess
from pathlib import Path


def verify_completed(package, host):
    from resource_guard import identity, sha
    manifest = json.loads((package / 'manifest.json').read_bytes())
    assert manifest['study'] == 'trusted-native-capture-quality-v3-scale10-unstarted-linked1' and manifest['trajectories'] == 26
    assert sha(package / 'user-current-authorization.json') == manifest['current_user_authorization_sha256']
    assert json.loads((package / 'user-current-authorization.json').read_bytes())['new_trusted_capture_protocol_authorized']
    prior = json.loads((package / ('prior-' + host + '.json')).read_bytes())['result']
    for path, row in prior['files'].items():
        assert sha(Path(path)) == row['sha256'], path
    for row in prior['processes']:
        saved = row['saved']
        proc = Path('/proc', str(saved['pid']))
        actual = identity(saved['pid']) if proc.exists() else None
        assert actual is None or actual['state'] in ['Z', 'X'] or any(actual[k] != saved[k] for k in ['uid', 'command', 'start_ticks'])
    latest = json.loads((package / ('completed-parent-' + host + '.json')).read_bytes())['result']
    for path, row in latest['files'].items():
        assert sha(Path(path)) == row['sha256'], path
    for row in latest['processes']:
        saved = row['saved']; proc = Path('/proc', str(saved['pid']))
        actual = identity(saved['pid']) if proc.exists() else None
        assert actual is None or actual['state'] in ['Z', 'X'] or any(actual[k] != saved[k] for k in ['uid', 'command', 'start_ticks'])
    failed = json.loads((package / ('failed-startup-binding-' + host + '.json')).read_bytes())
    for path, row in failed['files'].items():
        assert sha(Path(path)) == row['sha256'], path
    for path in failed.get('absent', []):
        assert not Path(path).exists(), path
    for row in failed.get('processes', []):
        saved = row['saved']; proc = Path('/proc', str(saved['pid']))
        actual = identity(saved['pid']) if proc.exists() else None
        assert actual is None or actual['state'] in ['Z', 'X'] or any(actual[k] != saved[k] for k in ['uid', 'command', 'start_ticks'])
    scale = json.loads((package / ('completed-scale-parent-' + host + '.json')).read_bytes())['result']
    assert scale['old_all_ten_terminal'] and scale['completed_parent_manifest_sha256'] == 'c6b18f57e714100a2449a4c18a8f04de9cde014d95c587b711e72630db143e70'
    for path, row in scale['files'].items():
        assert sha(Path(path)) == row['sha256'], path
    for row in scale['processes']:
        saved = row['saved']; proc = Path('/proc', str(saved['pid']))
        actual = identity(saved['pid']) if proc.exists() else None
        assert actual is None or actual['state'] in ['Z', 'X'] or any(actual[k] != saved[k] for k in ['uid', 'command', 'start_ticks'])
    interrupted = json.loads((package / ('interrupted-parent-' + host + '.json')).read_bytes())['result']
    assert interrupted['parent_preserved_interruption_not_completed']
    assert interrupted['attempted'] == 14 and interrupted['completed_noninfrastructure'] == 13
    assert interrupted['infrastructure_terminals'] == 1 and interrupted['exact_unstarted_count'] == 26
    assert interrupted['parent_manifest_sha256'] == '874a87681734dbe6ca65e2e76f7512638860b40897e3b80fad08e9bbcd23122b'
    assert interrupted['all_original_identities_exited_and_locks_absent']
    assert interrupted['unstarted_run_ids'] == [row['run_id'] for row in manifest['remaining_queue']]
    for path, row in interrupted['files'].items():
        assert sha(Path(path)) == row['sha256'], path
    for row in interrupted['processes']:
        saved = row['saved']; proc = Path('/proc', str(saved['pid']))
        actual = identity(saved['pid']) if proc.exists() else None
        assert actual is None or actual['state'] in ['Z', 'X'] or any(actual[k] != saved[k] for k in ['uid', 'command', 'start_ticks'])
    return {'preserved_interruption_bound': True, 'only_original_unstarted_26': True, 'host': host, 'prior_terminals_bound_unchanged': True, 'old_processes_exited': True,
            'new_protocol_authorized': True, 'old_lease_retired': True, 'old_workers_reexecuted': False}


def verify_native_parent(package):
    assert os.getuid() == 1033
    return verify_completed(package, '3090')


def verify_gui_parent(package):
    assert os.getuid() == 1015
    proof = verify_completed(package, '4090')
    identifiers = ['de6f56798c3c5a278a96d7afe6844e8be2c5673301e44e1c887eecc56118f0dd',
                   'e8fe8dfaa8010a5473c1ebf603859ba04d7d4ac1e8016b347ea8211c03a4c62c']
    rows = json.loads(subprocess.check_output(['docker', 'inspect', *identifiers], text=True))
    for identifier, row in zip(identifiers, rows):
        assert row['Id'] == identifier and row['Config']['Labels']['owner'] == 'whz-qwen27-vwa'
        assert row['State']['Running']
    assert rows[0]['HostConfig']['PortBindings'] == {'9980/tcp': [{'HostIp': '192.0.2.10', 'HostPort': '29980'}]}
    assert any(value.get('Name') == 'qwen27_vwa_db_data' for value in rows[1]['Mounts'])
    return {**proof, 'dedicated_site_database_bound': True, 'site_reset_or_import': False}
