"""New late-corruption study admission; old terminal queues are read-only."""
import json
import os
import subprocess
from pathlib import Path


def validate_leased_UUIDs(original_lease, current_cards):
    bound = {r['index']: r['uuid'] for r in original_lease['gpu']}
    assert set(bound) == {4, 5, 6, 7}
    for index, expected in bound.items():
        assert current_cards[index]['uuid'] == expected


def verify_completed(package, host):
    from resource_guard import identity, sha
    m = json.loads((package / 'manifest.json').read_bytes())
    assert m['study'] == 'late-three-capture-corruption-single-Flash-development-v2'
    assert m['trajectories'] == 12
    assert sha(package / 'user-current-authorization.json') == m['current_user_authorization_sha256']
    auth = json.loads((package / 'user-current-authorization.json').read_bytes())
    assert auth['local_development_and_new_injection_GUI_authorized']
    assert not auth['new_primary_preread_added']
    prior = json.loads((package / ('prior-' + host + '.json')).read_bytes())['result']
    for n, row in prior['files'].items():
        source = Path(prior['package'] if n.startswith('flash/') else prior['output']) / n
        assert sha(source) == row['sha256'], n
    phase = 'primary/status.json' if host == '3090' else 'batch/status.json'
    assert prior['files'][phase]['value']['phase'] == 'completed'
    assert prior['files'][phase]['value']['expected'] == 4
    for row in prior['processes']:
        saved = row['saved']; proc = Path('/proc', str(saved['pid']))
        actual = identity(saved['pid']) if proc.exists() else None
        same = actual is not None and actual['state'] not in ['Z','X'] and all(
            actual[k] == saved[k] for k in ['uid','command','start_ticks'])
        assert not same, 'Completed previous process still live'
    return {'host':host, 'completed_prior_sources_bound':True,
            'prior_processes_exited':True, 'old_terminals_reexecuted':False,
            'new_current_authorization_sha256':m['current_user_authorization_sha256'],
            'prior_full_raw_audit_not_repeated':True}


def verify_native_parent(package):
    assert os.getuid() == 1033
    return verify_completed(package, '3090')


def verify_gui_parent(package):
    assert os.getuid() == 1015
    proof = verify_completed(package, '4090')
    ids = ['de6f56798c3c5a278a96d7afe6844e8be2c5673301e44e1c887eecc56118f0dd',
           'e8fe8dfaa8010a5473c1ebf603859ba04d7d4ac1e8016b347ea8211c03a4c62c']
    rows = json.loads(subprocess.check_output(['docker','inspect',*ids],text=True))
    for identifier, row in zip(ids,rows):
        assert row['Id'] == identifier and row['Config']['Labels']['owner'] == 'whz-qwen27-vwa'
        assert row['State']['Running']
    assert rows[0]['HostConfig']['PortBindings'] == {'9980/tcp':[{'HostIp':'192.0.2.10','HostPort':'29980'}]}
    assert any(v.get('Name') == 'qwen27_vwa_db_data' for v in rows[1]['Mounts'])
    return {**proof,'owned_site_and_database_bound':True,'site_reset_or_import':False}
