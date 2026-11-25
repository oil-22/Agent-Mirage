"""Keep replaced bytes, signed early captures and legitimate identical pixels separate."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from collect import HERE, read, save, sha
from link import verify


TEMPORAL = HERE.parent.parent / 'jev-temporal-gate-20261122'
COMPLETION_SHA = '3bcf280b8d18ab148bba3e0f595f6c689dc9f76ce4eb44b0675888b0155d1c37'
UNCHANGED = HERE / 'terminal-case-evidence' / '1795498537134049300'


def verified_signed_early_panel():
    path = TEMPORAL / 'completion-receipt.json'
    assert sha(path) == COMPLETION_SHA
    receipt = read(path)
    assert all(sha(TEMPORAL / item) == digest for item, digest in receipt['evidence_files_sha256'].items())
    attempt = receipt['attempt']
    pinned = TEMPORAL / f'validated-{attempt}.json'
    # Replay only the sealed reader, inside its own module namespace. This does not launch the panel.
    replay = subprocess.run([sys.executable, '-B', '-c',
        'import json, sys; from pathlib import Path; from live_audit import judge; '
        'print(json.dumps(judge(Path(sys.argv[1]))))', str(TEMPORAL / 'attempts' / attempt)],
        cwd=TEMPORAL, check=True, capture_output=True, text=True, encoding='utf-8', timeout=30)
    result = read(pinned)
    assert result == json.loads(replay.stdout)
    rows = {r['id']: r for r in result['rows']}
    assert len(rows) == result['verified_journal_chains'] == result['real_main_responses']
    assert all(r['one_actual_dispatch'] and r['each_receipt_signature_verified'] for r in rows.values())
    trials = []
    for action, paired in result['paired_recovery'].items():
        original, guarded = (rows[f'{action}-delayed-{arm}'] for arm in ('original', 'temporal'))
        trials.append({'action': action, 'original_delivery_phase': original['delivery_phase'],
            'guarded_delivery_phase': guarded['delivery_phase'], 'early_holds': sum(
                h['phase'] == 'early_before_render' for h in guarded['holds']),
            'both_requests_had_natural_EOS': all(r['main']['natural_eos'] for r in (original, guarded)),
            'same_action_recovered_after_withhold': paired,
            'journal_heads': [original['journal_head'], guarded['journal_head']]})
    return {'attempt': attempt, 'completion_receipt_sha256': COMPLETION_SHA,
        'validated_report_sha256': sha(pinned), 'source_scope': result['scope'],
        'actual_call_counts': result['counts'], 'release_receipt_verified_by_original_reader': True,
        'temporally_delayed_trials': trials, 'fast_normal_control_pass': result['fast_normal_control_pass'],
        'trusted_static_boundary_control_pass': result['static_no_change_pass'],
        'part_of_the_frozen_VWA_100_slots': False, 'official_task_scores': 0}


def verified_same_pixels_control(runs):
    verify(UNCHANGED)
    control = read(UNCHANGED / 'same-pixels-new-capture.json')
    run = runs[control['run_id']]
    assert run['terminal_sha256'] == control['terminal_sha256']
    linked = []
    for item in control['two_native_deliveries']:
        step, = [s for s in run['steps'] if s['step'] == item['decision']]
        cap, = [f for f in step['frames'] if f['capture_id'] == step['submit']['capture_id']]
        assert all(cap[k] == item[k] for k in ('capture_id', 'action_sequence', 'capture_index', 'acquired_at_ns'))
        assert hashlib.sha256(cap['challenge'].encode()).hexdigest() == item['challenge_sha256']
        assert not cap['injected'] and cap['delivered_sha256'] == cap['captured_sha256'] == item['image_sha256']
        gate, = [g for g in step['gates'] if g['event'] == 'capture_receipt_decision' and g['capture_id'] == cap['capture_id']]
        flash, = [g for g in step['gates'] if g['event'] == 'gate_decision' and g['capture_id'] == cap['capture_id']]
        assert gate['decision'] == flash['decision'] == 'YES'
        assert gate['event_sha256'] == item['receipt_event_sha256'] and flash['request_id'] == item['Flash_request_id']
        assert step['actual_first_forward'] and step['main']['current_image_sha256'] == item['image_sha256']
        assert step['request']['request_id'] == item['actual_first_forward_request']
        assert step['executed'] == item['executed_native_action']
        linked.append(item)
    a, b = linked
    assert b['decision'] == a['decision'] + 1 and b['action_sequence'] == a['action_sequence'] + 1
    assert all(a[k] != b[k] for k in ('capture_id', 'challenge_sha256', 'receipt_event_sha256'))
    assert a['image_sha256'] == b['image_sha256'] and a['executed_native_action']['ok']
    assert a['executed_native_action']['payload'] == {'type': 'scroll', 'direction': 'down'}
    assert sha(HERE / 'original-images' / (a['image_sha256'] + '.png')) == a['image_sha256']
    return {'run_id': control['run_id'], 'terminal_sha256': control['terminal_sha256'],
        'prior_case_seal_sha256': sha(UNCHANGED / 'seal.json'), 'two_native_deliveries': linked}


def audit(ledger, cycles):
    runs = {r['slot']['run_id']: r['evidence'] for r in ledger['rows'] if r['evidence']}
    assert len(runs) == cycles['sealed_slots']
    cases = [a for a in cycles['altered_initial_deliveries'] if a['condition'] == 'stale_replace']
    for row in cases:
        tape = runs[row['run']]
        assert tape['terminal_sha256'] == row['terminal_sha256']
        steps = tape['steps']
        i, = [i for i, s in enumerate(steps) if s['step'] == row['decision']]
        assert i > 0 and steps[i]['altered_bytes']
        initial, = [f for f in row['captures'] if f['capture_role'] == 'altered_initial']
        assert initial['delivered_sha256'] == steps[i-1]['submit']['image_sha256'] != initial['original_sha256']
    deliveries = {}
    for arm in ('off', 'on'):
        sub = [r['outcome_at_injection_decision'] for r in cases if r['arm'] == arm]
        deliveries[arm] = {'actual_replacements': len(sub),
            'entered_actual_first_forward': sum(p['altered_observation_at_actual_forward'] for p in sub),
            'same_decision_usable_recapture_at_actual_forward': sum(p['normal_recapture_at_actual_forward'] for p in sub)}
    return {'sealed_VWA_slots': len(runs), 'transport_replacements_only': True, 'VWA_transport_replacement': deliveries,
        'VWA_legitimate_identical_pixels': verified_same_pixels_control(runs),
        'separate_signed_early_Chromium_panel': verified_signed_early_panel(),
        'new_model_browser_or_scorer_calls': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ledger', type=Path)
    parser.add_argument('gate_cycles', type=Path)
    args = parser.parse_args()
    for path in (args.ledger, args.gate_cycles):
        verify(path)
    cycles = read(args.gate_cycles / 'gate-cycles.json')
    ledger_seal = sha(args.ledger / 'seal.json')
    assert cycles['ledger_seal_sha256'] == ledger_seal
    result = audit(read(args.ledger / 'private-linked.json'), cycles)
    out = HERE / 'stale-boundary-audits' / str(time.time_ns())
    out.mkdir(parents=True, exist_ok=False)
    save(out / 'index.json', {'ledger_seal_sha256': ledger_seal,
        'gate_audit_seal_sha256': sha(args.gate_cycles / 'seal.json'), **result})
    save(out / 'seal.json', {'index.json': sha(out / 'index.json')})
    print(json.dumps({'path': str(out), 'seal_sha256': sha(out / 'seal.json')}))


if __name__ == '__main__':
    main()
