"""Bind the completed white replacement case to the same-task normal reference."""

import argparse
import json
import time
from pathlib import Path

from collect import HERE, read, save, sha
from link import verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ledger', type=Path)
    args = parser.parse_args()
    verify(args.ledger)
    by_run = {row['slot']['run_id']: row['evidence']
              for row in read(args.ledger / 'private-linked.json')['rows']}
    on, off, clean = [by_run['paperpair-T171-' + arm] for arm in
                      ('blank_replace-on', 'blank_replace-off', 'clean_control-on')]
    assert all(r['version'] == 'NF4' and r['model_run_end_bound'] for r in (on, off, clean))
    assert all(r['official_score_bound'] and r['terminal']['official_reward'] == 1
               and r['terminal']['outcome'] == 'model_stop' for r in (on, clean))
    assert not off['official_score_bound'] and off['terminal']['infrastructure_failure']

    same = []
    for x, y in zip(on['steps'], clean['steps'], strict=True):
        assert x['step'] == y['step']
        assert x['actual_first_forward'] and y['actual_first_forward']
        assert x['main']['natural_EOS'] and y['main']['natural_EOS']
        keys = ('body_sha256', 'messages_ordered', 'current_image_sha256', 'images_all_history',
                'reply_sha256', 'input_tokens', 'output_tokens', 'forward_calls')
        assert all(x['main'][k] == y['main'][k] for k in keys), x['step']
        assert x['executed'] == y['executed'], x['step']
        same.append({'step': x['step'], 'body_sha256': x['main']['body_sha256'],
                     'current_image_sha256': x['main']['current_image_sha256'],
                     'reply_sha256': x['main']['reply_sha256'], 'native_action_event': x['executed'],
                     'white_on_request_seal_sha256': x['main']['seal_sha256'],
                     'clean_on_request_seal_sha256': y['main']['seal_sha256']})
    assert [entry['step'] for entry in same] == list(range(1, 35))
    assert sum(s['native_action_event'] is not None for s in same) == 33

    observed, bypassed = on['steps'][1], off['steps'][1]
    frame, = (f for f in observed['frames'] if f['capture_kind'] == 'initial')
    white = frame['delivered_sha256']
    recovered = observed['main']['current_image_sha256']
    assert white == bypassed['main']['current_image_sha256'] != recovered
    assert observed['altered_bytes'] and observed['initial_rejection_event'] == 'capture_receipt_decision'
    assert observed['recapture_at_actual_forward_needs_visual_review']
    assert not observed['known_injected_dose_at_first_forward']
    assert bypassed['known_injected_dose_at_first_forward'] and bypassed['executed']['payload']['type'] == 'wait'
    flash, = (g for g in observed['gates'] if g['event'] == 'gate_decision')
    assert flash['decision'] == 'YES' and flash['image_sha256'] == recovered
    assert observed['main']['tensor_raw_bytes_fully_audited'] and observed['executed']['ok']

    scope = {'comparison': 'sealed existing outputs; no new generation, GUI or scoring',
             'ledger_seal_sha256': sha(args.ledger / 'seal.json'),
             'verifier_sha256': sha(Path(__file__)),
             'arms': {k: {'run': v['terminal']['run']['run_id'],
                          'terminal_sha256': v['terminal_sha256'],
                          'stage_id': v['stage_id'],
                          'outcome': v['terminal']['outcome'],
                          'official_score': v['terminal']['official_reward'] if v['official_score_bound'] else None}
                      for k, v in (('white_on', on), ('white_off', off), ('clean_on', clean))},
             'inject_and_recover': {'decision': 2, 'delivered_white_sha256': white,
                 'rejected_by': 'trusted_capture_receipt', 'independent_flash_on_injected_frame': False,
                 'recovered_image_sha256': recovered, 'recapture_then_Flash_YES_request_id': flash['request_id'],
                 'recapture_then_Flash_YES_reply_seal_sha256': flash['Flash_seal_sha256'],
                 'actual_main_request_id': observed['request']['request_id'],
                 'actual_forward_raw_tensor_sha_rehash_checked': True,
                 'native_action_ok': observed['executed']['ok'],
                 'white_off_native_wait_before_technical_failure': True},
             'matching_whole_trajectory_decisions': same}
    out = HERE / 'terminal-case-evidence' / str(time.time_ns())
    out.mkdir(parents=True, exist_ok=False)
    save(out / 'white-recovery.json', scope)
    save(out / 'seal.json', {'white-recovery.json': sha(out / 'white-recovery.json')})
    print(json.dumps({'case_receipt': str(out), 'matched_main_decisions': len(same),
                      'matched_native_actions': 33, 'native_white_on_score': 1,
                      'white_off_score': None}))


if __name__ == '__main__':
    main()
