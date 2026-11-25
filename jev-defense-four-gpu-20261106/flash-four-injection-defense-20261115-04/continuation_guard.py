"""Admit only the newly authorized four-native-injection GUI study."""
import json
import os
import subprocess
from pathlib import Path


def validate_leased_UUIDs(original_lease, current_cards):
    bound = {row['index']: row['uuid'] for row in original_lease['gpu']}
    assert set(bound) == {4, 5, 6, 7}
    for index, expected in bound.items():
        assert current_cards[index]['uuid'] == expected


def verify_completed(package, host):
    from resource_guard import identity, sha
    manifest = json.loads((package / 'manifest.json').read_bytes())
    assert manifest['study'] == 'four-native-injection-presence-Flash-development-v1'
    assert manifest['trajectories'] == 8
    assert sha(package / 'user-current-authorization.json') == manifest['current_user_authorization_sha256']
    authority = json.loads((package / 'user-current-authorization.json').read_bytes())
    assert authority['new_four_native_injection_GUI_authorized']
    assert not authority['new_primary_preread_added']
    prior = json.loads((package / ('prior-' + host + '.json')).read_bytes())['result']
    for name, row in prior['files'].items():
        source = Path(prior['package'] if name.startswith('flash/') else prior['output']) / name
        assert sha(source) == row['sha256'], name
    phase = 'primary/status.json' if host == '3090' else 'batch/status.json'
    assert prior['files'][phase]['value']['phase'] == 'completed'
    assert prior['files'][phase]['value']['expected'] == 12
    for row in prior['processes']:
        saved = row['saved']
        proc = Path('/proc', str(saved['pid']))
        actual = identity(saved['pid']) if proc.exists() else None
        same = actual is not None and actual['state'] not in ['Z', 'X'] and all(
            actual[key] == saved[key] for key in ['uid', 'command', 'start_ticks'])
        assert not same, 'Completed old process remains live'
    return {'host': host, 'old_parent_completed': True, 'old_processes_exited': True,
            'old_terminals_reexecuted': False, 'new_authorization_bound': True}


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
    return {**proof, 'dedicated_site_and_database_bound': True, 'site_reset_or_import': False}
