"""Reuse the verified SSH bridges with a new remote-only token; never loads models."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

BASE = Path(__file__).resolve().parent
MANAGER = BASE / 'transport-preparation/token-normalization-linked-1793975850202477300/bridge_manager.py'
OLD = BASE / 'transport-preparation/online-config-prepared-1793978007590298100/session-online-01'
DESTINATION = '/data/researcher/jev-defense-four-gpu-20261106/transport-online-three-01/private.token'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def main(a):
    spec = importlib.util.spec_from_file_location('owned_bridge_manager', MANAGER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.verify_seal(OLD)
    old = json.loads((OLD / 'state.json').read_bytes())
    assert len(old['processes']) == 2
    checks = []
    for host, expected in zip(('3090', '4090'), old['processes']):
        assert expected['requested_argv'] == module.ssh_command(old['config'], host, forward=True)
        actual = module.windows_identity(expected['pid'])
        assert module.owned_identity_matches(expected, actual), 'Original bridge identity changed'
        checks.append({'host': host, 'expected': expected, 'actual': actual})
    a.output.mkdir(parents=True, exist_ok=False)
    (a.output / 'prepare-source.py').write_bytes(Path(__file__).read_bytes())
    try:
        save(a.output / 'bridge-identity.json', {'source_session': str(OLD),
            'source_state_sha256': sha(OLD / 'state.json'), 'manager_sha256': sha(MANAGER),
            'actual_bridge_identities': checks, 'new_processes_started': 0, 'HTTP_model_GUI_calls': 0})
        if a.source_token:
            source = a.source_token
            assert source.startswith('/home/researcher/jev-defense-four-gpu-20261106/')
            assert '..' not in Path(source).parts and '\n' not in source and '\r' not in source
            assert source != old['config']['source_token_file']
            config = {**old['config'], 'source_token_file': source, 'destination_token_file': DESTINATION}
            assert config['destination_token_file'] != old['config']['destination_token_file']
            metadata, failure = module.Backend.copy_token(config)
            save(a.output / 'token-copy-metadata.json', {'metadata': metadata, 'failure': failure,
                'secret_bytes_returned_or_logged': False})
            if failure:
                raise RuntimeError('New remote token copy failed; preserve this attempt, do not overwrite')
            state = {'status': 'reused_verified_bridge_pending_new_online_readiness',
                'config': config, 'processes': old['processes'], 'copied_token_identity': metadata,
                'reused_from_session': str(OLD), 'source_state_sha256': sha(OLD / 'state.json'),
                'model_calls': 0, 'GUI_actions': 0, 'token_bytes_in_artifacts': False,
                'no_new_bridge_process_spawned': True,
                'transient_token_copy_ssh_processes': 2, 'time': time.time()}
            save(a.output / 'state.json', state)
            module.seal(a.output)
            print(json.dumps({'session': str(a.output), 'token_destination': DESTINATION,
                'new_bridge_processes': 0, 'transient_token_copy_ssh_processes': 2,
                'HTTP_model_GUI_calls': 0,
                'token_bytes_returned_or_logged': False, 'status': state['status']}))
        else:
            module.seal(a.output)
            print(json.dumps({'evidence': str(a.output), 'actual_bridge_identities_verified': True,
                'HTTP_model_GUI_token_copy_calls': 0}))
    except BaseException as error:
        save(a.output / 'failure.json', {'error_type': type(error).__name__,
            'no_automatic_retry': True, 'token_bytes_returned_or_logged': False})
        module.seal(a.output)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-token')
    parser.add_argument('--output', type=Path, required=True)
    main(parser.parse_args())
