"""New finite browser/source controls; no Flash, actor or scorer."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from capture_client import CaptureClient
from native_rpc import dumps
from receipt_protocol import digest


def save(p, v):
    with p.open('x', encoding='utf8') as f:
        json.dump(v, f, indent=2, ensure_ascii=False)


def main(root):
    root.mkdir(exist_ok=False)
    rows = []
    def record(name, passed, **extra):
        assert passed, name
        rows.append({'name': name, 'passed': True, **extra})
    folder = root / 'fixture'; folder.mkdir()
    client = CaptureClient(folder, fixture=True)
    try:
        client.reset(20261011, {'config_file': ''})
        # Native detail URL is routed to a fixed fixture only in fixture mode.
        client.rpc('fixture', name='detail')
        original, receipt, expected = client.acquire()
        before_count = receipt['capture_index']
        masked = client.native_fault_probe('buttons_only')
        (folder / 'normal-before.png').write_bytes(original)
        (folder / 'masked-unsigned.png').write_bytes(masked)
        record('original_CSS_changes_browser_PNG_after_signed_capture', masked != original)
        verdict = client.verifier.check(masked, receipt, expected=expected)
        record('unsigned_mask_rejected_by_original_receipt_not_Flash', verdict.reason == 'capture_bytes_replaced')
        restored, rec, exp = client.acquire()
        (folder / 'normal-recapture.png').write_bytes(restored)
        record('CSS_removed_before_gate_real_recapture_is_exact_normal', restored == original and client.verifier.check(restored, rec, expected=exp).value == 'YES')
        record('fault_probe_never_signed_or_advanced_action', rec['capture_index'] == before_count + 1 and rec['action_sequence'] == receipt['action_sequence'])
        for name, request in [
            ('arbitrary_CSS_not_accepted', {'op': 'PRIVATE_native_fault', 'name': 'buttons_only', 'preceding_capture_id': rec['capture_id'], 'CSS': 'body{display:none}'}),
            ('arbitrary_PNG_not_signable', {'op': 'PRIVATE_native_fault', 'name': 'buttons_only', 'preceding_capture_id': rec['capture_id'], 'png': original}),
            ('unbound_fault_capture_rejected', {'op': 'PRIVATE_native_fault', 'name': 'buttons_only', 'preceding_capture_id': receipt['capture_id']}),
            ('arbitrary_operation_rejected', {'op': 'evaluate', 'script': '1+1'}),
        ]:
            client.child.stdin.write(dumps(request)); client.child.stdin.flush()
            record(name, not client.read()['ok'])
        normal, rec, exp = client.acquire()
        blank = client.native_fault_probe('blank_replace')
        (folder / 'independent-about-blank.png').write_bytes(blank)
        record('independent_blank_never_navigates_or_signs_live', client.verifier.check(blank, rec, expected=exp).reason == 'capture_bytes_replaced')
        final, rec, exp = client.acquire()
        record('blank_probe_leaves_live_detail_and_pixels', final == normal and client.verifier.check(final, rec, expected=exp).value == 'YES')
        for name in ['footer', 'no_results', 'lone_button']:
            client.rpc('fixture', name=name)
            png, rec, exp = client.acquire()
            record('authentic_' + name + '_source_allowed', client.verifier.check(png, rec, expected=exp).value == 'YES', image_sha256=digest(png))
            if name == 'lone_button':
                (folder / 'legitimate-lone-button.png').write_bytes(png)
                try:
                    client.native_fault_probe('buttons_only')
                except RuntimeError:
                    denied = True
                else:
                    denied = False
                record('mask_probe_cannot_change_original_detail_trigger', denied)
        client.rpc('fixture', name='blank')
        png, rec, exp = client.acquire()
        record('source_signed_blank_is_known_limitation', client.verifier.check(png, rec, expected=exp).value == 'YES', not_visible_quality_proof=True)
        record('source_is_separate_process_and_public_key_only', client.child.pid != os.getpid() and 'private_key' not in client.ready)
    finally:
        client.close()

    # New native renderer controls on a real original browser environment.
    # Private DOM sampling is solely to select a read-only test fixture page;
    # it is never used by receipt/Flash/actor or any GUI trial.
    from native_environment import NATIVE_ENV
    os.environ.update(NATIVE_ENV)
    runtime = Path('/data/researcher/jev-defense-validation-20261103/runtime-stage-01')
    sys.path[:0] = [str(runtime / 'native'), str(runtime / 'upstream')]
    from browser_env.auto_login import renew_comb
    from run_reddit_internvl_smoke import action, parse
    from capture_source import Source
    from receipt_protocol import ReceiptVerifier
    p = Path(__file__).resolve().parent
    task = next(v for v in json.loads((p / 'native-bindings-public.json').read_bytes())['tasks'] if v['task_id'] == 58)
    raw = Path(task['original_private_path']).read_bytes(); assert digest(raw) == task['original_private_SHA']
    auth = root / '.auth'; auth.mkdir(); renew_comb(['classifieds'], str(auth))
    cfg = json.loads(raw.decode().replace('192.0.2.10:19980', '192.0.2.10:29980'))
    assert cfg['require_reset'] is False
    cfg['storage_state'] = str(auth / 'classifieds_state.json')
    path = root / 'PRIVATE-native-config.json'; save(path, cfg)
    src = Source(root / 'native-source', 'new-native-renderer-control')
    guard = ReceiptVerifier(root / 'native-receiver.sqlite3', **{k: src.binding[k] for k in ['public_key', 'session_id', 'environment_id', 'source_code_sha256']})
    try:
        src.reset(str(path))
        hrefs = src.env.page.locator('a[href*="page=item"]').evaluate_all('(a)=>a.map(x=>x.href)')
        from native_fault import detail
        href = next(v for v in hrefs if detail(v))
        src.env.page.goto(href)
        original = src.capture(guard.issue(0))
        mask = src.fault_probe('buttons_only', original['receipt']['capture_id'])
        record('real_native_original_CSS_unsigned_replacement_rejected', original['png'] != mask['png'] and guard.check(mask['png'], original['receipt'], expected={'challenge': original['receipt']['challenge'], 'environment_id': src.environment_id, 'action_sequence': 0}).reason == 'capture_bytes_replaced')
        exp = guard.issue(0); rec = src.capture(exp)
        record('real_native_CSS_removed_full_capture_recovers', rec['png'] == original['png'] and guard.check(rec['png'], rec['receipt'], expected=exp).value == 'YES', original_sha256=digest(original['png']), mask_sha256=digest(mask['png']))
        native = action(parse('<action>{"type":"wait"}</action>')); native['raw_prediction'] = '<action>{"type":"wait"}</action>'
        src.dispatch({'op': 'wait', 'milliseconds': 1000})
        step = src.dispatch({'op': 'step', 'action': native})
        exp = guard.issue(1); rec = src.capture(exp)
        record('real_native_WAIT_and_sequence_preserved', bool(step['result'][1]) and guard.check(rec['png'], rec['receipt'], expected=exp).value == 'YES', pure_WAIT_excluded=True)
        (root / 'real-native-normal.png').write_bytes(original['png'])
        (root / 'real-native-mask.png').write_bytes(mask['png'])
        (root / 'real-native-recapture.png').write_bytes(rec['png'])
        src.env.save_trace(root / 'native-trace.zip')
    finally:
        src.close()
    save(root / 'result.json', {'passed': True, 'controls': rows, 'count': len(rows), 'new_Flash_actor_scorer_calls': 0, 'GUI_experiment_trajectories': 0, 'new_native_WAIT_actions': 1})
    save(root / 'seal.json', {q.relative_to(root).as_posix(): digest(q.read_bytes()) for q in root.rglob('*') if q.is_file()})
    print(json.dumps({'passed': True, 'controls': len(rows), 'new_model_calls': 0}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('root', type=Path)
    main(parser.parse_args().root)
