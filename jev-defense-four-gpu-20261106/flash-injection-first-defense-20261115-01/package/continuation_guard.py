"""New authorized injection study; original completed queues are provenance only."""
import json
import os
import subprocess
from pathlib import Path


def validate_leased_UUIDs(original_lease, current_cards):
    bound = {r['index']: r['uuid'] for r in original_lease['gpu']}
    assert set(bound) == {4, 5, 6, 7}
    for index, expected in bound.items():
        assert current_cards[index]['uuid'] == expected, 'Original physical GPU/held UUID lock binding changed'


def verify_completed(package, host):
    from resource_guard import identity, sha
    manifest = json.loads((package / 'manifest.json').read_bytes())
    assert manifest['study'] == 'injection-before-single-Flash-whiteout-development-v1'
    assert sha(package / 'user-current-authorization.json') == manifest['current_user_authorization_sha256']
    auth = json.loads((package / 'user-current-authorization.json').read_bytes())
    assert auth['local_development_and_new_injection_GUI_authorized']
    assert not auth['new_primary_preread_added']
    binding = json.loads((package / ('prior-' + host + '.json')).read_bytes())['result']
    for name, row in binding['files'].items():
        source = Path(binding['package'] if name.startswith('flash/') else binding['output']) / name
        assert sha(source) == row['sha256'], name
    phase = 'primary/status.json' if host == '3090' else 'batch/status.json'
    assert binding['files'][phase]['value']['phase'] == 'completed'
    assert binding['files'][phase]['value']['expected'] == 13
    for row in binding['processes']:
        saved = row['saved']; proc = Path('/proc', str(saved['pid']))
        current = identity(saved['pid']) if proc.exists() else None
        same = current is not None and current['state'] not in ['Z', 'X'] and all(
            current[k] == saved[k] for k in ['uid', 'command', 'start_ticks'])
        assert not same, 'A completed prior study process is still live'
    return {'host': host, 'completed_prior_sources_bound': True,
            'prior_processes_exited': True, 'old_terminals_reexecuted': False,
            'new_current_authorization_sha256': manifest['current_user_authorization_sha256'],
            'prior_full_raw_audit_not_repeated': True}


def verify_native_parent(package):
    assert os.getuid() == 1033
    return verify_completed(package, '3090')


def verify_gui_parent(package):
    assert os.getuid() == 1015
    result = verify_completed(package, '4090')
    ids = ['de6f56798c3c5a278a96d7afe6844e8be2c5673301e44e1c887eecc56118f0dd',
           'e8fe8dfaa8010a5473c1ebf603859ba04d7d4ac1e8016b347ea8211c03a4c62c']
    rows = json.loads(subprocess.check_output(['docker', 'inspect', *ids], text=True))
    for identifier, row in zip(ids, rows):
        assert row['Id'] == identifier and row['Config']['Labels']['owner'] == 'whz-qwen27-vwa'
        assert row['State']['Running']
    assert rows[0]['HostConfig']['PortBindings'] == {'9980/tcp': [{'HostIp': '192.0.2.10', 'HostPort': '29980'}]}
    assert any(v.get('Name') == 'qwen27_vwa_db_data' for v in rows[1]['Mounts'])
    return {**result, 'owned_site_and_database_bound': True, 'site_reset_or_import': False}
