"""Real fresh browser capture controls, then original native environment + WAIT.

No weights, Flash, actor generation, paid API or official score.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from capture_client import CaptureClient
from native_rpc import dumps
from receipt_protocol import digest


def save(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)


def main(root, fixture_proof=None):
    root.mkdir(exist_ok=False)
    rows = []
    def record(name, passed, **extra):
        assert passed, name
        rows.append({'name': name, 'passed': True, **extra})
    if fixture_proof is not None:
        proof = json.loads(fixture_proof.read_bytes())
        assert proof['all_13_prior_fixture_controls_verified'] and proof['no_fixture_reexecution']
        rows.extend(proof['controls'])
    else:
        fixture = root / 'fixture'
        fixture.mkdir()
        client = CaptureClient(fixture, fixture=True)
        try:
            client.reset(20261011, {'config_file': ''})
            raw1, r1, e1 = client.acquire()
            record('native_fixture_original', client.verifier.check(raw1, r1, expected=e1).value == 'YES', image_sha256=digest(raw1))
            raw2, r2, e2 = client.acquire()
            record('new_real_capture_same_pixels_allowed', raw2 == raw1 and client.verifier.check(raw2, r2, expected=e2).value == 'YES')
            client.rpc('fixture', name='blank')
            raw3, r3, e3 = client.acquire()
            result = client.verifier.check(raw1, r3, expected=e3)
            record('postcapture_old_image_replacement_rejected', raw3 != raw1 and result.reason == 'capture_bytes_replaced')
            raw4, r4, e4 = client.acquire()
            record('trusted_source_signed_blank_receipt_passes', client.verifier.check(raw4, r4, expected=e4).value == 'YES', image_sha256=digest(raw4), limitation='receipt does not establish visible usability')
            client.rpc('fixture', name='normal')
            raw5, r5, e5 = client.acquire()
            result = client.verifier.check(raw5, r1, expected=e5)
            record('old_receipt_replay_on_same_pixels_rejected', raw5 == raw1 and result.reason == 'old_or_other_capture_response')
            raw6, r6, e6 = client.acquire()
            record('fresh_real_recapture_recovers', client.verifier.check(raw6, r6, expected=e6).value == 'YES')
            for name in ['footer', 'no_results', 'lone_button']:
                client.rpc('fixture', name=name)
                raw, receipt, expected = client.acquire()
                record('authentic_' + name + '_not_rejected_by_source_guard', client.verifier.check(raw, receipt, expected=expected).value == 'YES', image_sha256=digest(raw))
            for name, request in [
                ('duplicate_source_challenge_rejected', {'op': 'capture', 'request': e6}),
                ('no_arbitrary_bytes_signing_API', {'op': 'capture', 'request': {**e6, 'png': raw1}}),
                ('no_private_key_export_API', {'op': 'export_private_key'})]:
                client.child.stdin.write(dumps(request))
                client.child.stdin.flush()
                response = client.read()
                record(name, not response['ok'])
            record('source_separate_process_public_key_only', client.child.pid != os.getpid() and 'private_key' not in client.ready)
        finally:
            client.close()

    # Same frozen native task source and site, with its original parser/executor.
    p = Path(__file__).resolve().parent
    from native_environment import NATIVE_ENV
    os.environ.update(NATIVE_ENV)
    runtime = Path('/data/researcher/jev-defense-validation-20261103/runtime-stage-01')
    sys.path[:0] = [str(runtime / 'native'), str(runtime / 'upstream')]
    from browser_env.auto_login import renew_comb
    from run_reddit_internvl_smoke import action, parse
    task = next(t for t in json.loads((p / 'native-bindings-public.json').read_bytes())['tasks'] if t['task_id'] == 58)
    raw = Path(task['original_private_path']).read_bytes()
    assert digest(raw) == task['original_private_SHA']
    auth = root / '.auth'
    auth.mkdir()
    renew_comb(['classifieds'], str(auth))
    cfg = json.loads(raw.decode().replace('192.0.2.10:19980', '192.0.2.10:29980'))
    assert cfg['require_reset'] is False
    cfg['storage_state'] = str(auth / 'classifieds_state.json')
    config = root / 'PRIVATE-native-config.json'
    save(config, cfg)
    native_root = root / 'native'
    native_root.mkdir()
    client = CaptureClient(native_root)
    try:
        obs, info = client.reset(20261011, {'config_file': str(config)})
        raw, receipt, expected = client.acquire()
        record('original_native_full_capture_bound', client.verifier.check(raw, receipt, expected=expected).value == 'YES', image_sha256=digest(raw), pixels=list(obs['image'].shape))
        proposal = parse('<action>{"type":"wait"}</action>')
        native = action(proposal)
        native['raw_prediction'] = '<action>{"type":"wait"}</action>'
        client.page.wait_for_timeout(1000)
        obs2, ok, _, _, _ = client.step(native)
        raw2, receipt2, expected2 = client.acquire()
        record('pure_native_WAIT_and_new_capture_preserved', bool(ok) and expected2['action_sequence'] == 1 and client.verifier.check(raw2, receipt2, expected=expected2).value == 'YES', pure_WAIT_excluded_from_Mirage=True)
        try:
            client.rpc('fixture', name='blank')
        except RuntimeError:
            denied = True
        else:
            denied = False
        record('production_source_disallows_fixture_content_API', denied)
        client.save_trace(native_root / 'native_trace.zip')
    finally:
        client.close()
    save(root / 'result.json', {'created': time.time(), 'passed': True, 'controls': rows, 'count': len(rows),
                              'real_native_WAIT_actions': 1, 'new_model_calls': 0, 'new_Flash_calls': 0,
                              'new_official_score_calls': 0, 'not_defense_effectiveness': True})
    save(root / 'seal.json', {str(p.relative_to(root)): digest(p.read_bytes()) for p in root.rglob('*') if p.is_file()})
    print(json.dumps({'root': str(root), 'passed': True, 'live_controls': len(rows), 'new_model_calls': 0}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('--fixture-proof', type=Path)
    args = parser.parse_args()
    main(args.root, args.fixture_proof)
