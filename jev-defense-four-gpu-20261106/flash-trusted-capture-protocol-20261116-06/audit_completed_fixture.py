"""Recover the already-completed 13 fixture controls from immutable raw evidence.

The later native RPC serialization failure must not cause completed captures to
be executed again. This reader makes no browser/model calls and writes outside
the old attempt.
"""
import json
import sqlite3
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from receipt_protocol import BODY_FIELDS, canonical, digest


def audit(old, destination):
    seal = json.loads((old / 'seal.json').read_bytes())
    for name, expected in seal.items():
        assert digest((old / name).read_bytes()) == expected, name
    src = old / 'live-controls/fixture/trusted-source'
    ready = json.loads((src / 'ready.json').read_bytes())
    terminal = json.loads((src / 'terminal.json').read_bytes())
    proc = Path('/proc', str(ready['identity']['pid']))
    if proc.exists():
        stat = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
        assert stat[19] != ready['identity']['start_ticks'] or stat[0] in ['Z', 'X']
    events, head = [], '0' * 64
    for line in (src / 'events.jsonl').read_bytes().splitlines():
        row = json.loads(line)
        saved = row.pop('sha256')
        assert row['previous'] == head and digest(canonical(row)) == saved
        head = saved
        events.append(row)
    assert head == terminal['journal_head']
    captures = [v['data']['receipt'] for v in events if v['kind'] == 'actual_native_capture_signed']
    assert len(captures) == terminal['signed_captures'] == 9
    public = Ed25519PublicKey.from_public_bytes(bytes.fromhex(ready['public_key']))
    for receipt in captures:
        public.verify(bytes.fromhex(receipt['signature']), canonical({k: receipt[k] for k in BODY_FIELDS}))
        assert digest((src / ('capture-' + receipt['capture_id']) / 'original.png').read_bytes()) == receipt['image_sha256']
    db = sqlite3.connect('file:' + str(old / 'live-controls/fixture/receipt-verifier.sqlite3') + '?mode=ro&immutable=1', uri=True)
    statuses = {r[0]: r[1:] for r in db.execute('SELECT challenge,state,reason FROM challenges')}
    db.close()
    reasons = [statuses[r['challenge']][1] for r in captures]
    assert reasons == ['receipt_bound_proceed_to_Flash', 'receipt_bound_proceed_to_Flash', 'capture_bytes_replaced',
                       'receipt_bound_proceed_to_Flash', 'old_or_other_capture_response', 'receipt_bound_proceed_to_Flash',
                       'receipt_bound_proceed_to_Flash', 'receipt_bound_proceed_to_Flash', 'receipt_bound_proceed_to_Flash']
    assert captures[0]['image_sha256'] == captures[1]['image_sha256'] == captures[4]['image_sha256'] == captures[5]['image_sha256']
    assert captures[2]['image_sha256'] == captures[3]['image_sha256'] != captures[0]['image_sha256']
    refused = [v for v in events if v['kind'] == 'rejected_RPC']
    assert len(refused) == 3
    assert 'already claimed' in refused[0]['data']['reason']
    assert 'Only a bound capture challenge' in refused[1]['data']['reason']
    assert 'no arbitrary image signing' in refused[2]['data']['reason']
    names = ['native_fixture_original', 'new_real_capture_same_pixels_allowed', 'postcapture_old_image_replacement_rejected',
             'trusted_source_signed_blank_receipt_passes', 'old_receipt_replay_on_same_pixels_rejected', 'fresh_real_recapture_recovers',
             'authentic_footer_not_rejected_by_source_guard', 'authentic_no_results_not_rejected_by_source_guard',
             'authentic_lone_button_not_rejected_by_source_guard', 'duplicate_source_challenge_rejected',
             'no_arbitrary_bytes_signing_API', 'no_private_key_export_API', 'source_separate_process_public_key_only']
    proof = {'source_attempt': str(old), 'source_attempt_seal_sha256': digest((old / 'seal.json').read_bytes()),
             'all_13_prior_fixture_controls_verified': True, 'no_fixture_reexecution': True,
             'captures': captures, 'verifier_reasons': reasons,
             'controls': [{'name': name, 'passed': True, 'reused_actual_completed_control': True} for name in names],
             'source_code_reviewer_not_blind': True, 'new_model_GUI_calls': 0}
    with destination.open('x', encoding='utf-8') as f:
        json.dump(proof, f, ensure_ascii=False, indent=2)
    return proof
