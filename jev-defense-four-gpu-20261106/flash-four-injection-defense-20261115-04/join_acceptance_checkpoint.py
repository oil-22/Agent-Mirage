"""Join sealed real-trajectory audits to independent original-image usability notes."""
import json
import time
from pathlib import Path
from remote_util import HERE, save, sha
from user_frame_delivery import VERSION, assess


def verify(root):
    for name, expected in json.loads((root / 'seal.json').read_bytes()).items():
        assert sha(root / name) == expected, (root, name)


def main():
    labels = {}
    reviews = []
    for root in sorted(HERE.glob('independent-image-notes-*')):
        verify(root)
        review = json.loads((root / 'notes.json').read_bytes())
        reviews.append({'root': str(root), 'seal_sha256': sha(root / 'seal.json')})
        for image in review['images']:
            digest = image['sha256']
            if digest in labels:
                assert labels[digest]['normal_usable'] == image['normal_usable']
            labels[digest] = image
    rows = []
    for root in sorted(HERE.glob('trajectory-audit-*')):
        if not (root / 'seal.json').exists():
            continue
        verify(root)
        result = json.loads((root / 'summary.json').read_bytes())
        route = result['route']
        fresh = route.get('fresh_capture', {}).get('captured_sha256')
        normal = fresh in labels and labels[fresh]['normal_usable'] is True
        accepted = route['wire_bound_recovery_loop'] and normal
        delivery = assess(result, normal)
        rows.append({'run_id': route['run_id'], 'condition': route['condition'],
                     'terminal_and_full_wire_audit': str(root), 'audit_seal_sha256': sha(root / 'seal.json'),
                     'injection_triggered': route['injection_triggered'], 'rejected': route['rejected'],
                     'recovery_loop_verified': route['wire_bound_recovery_loop'],
                     'recovery_image_independently_normal': normal, 'fresh_image_sha256': fresh,
                     'frame_loop_acceptance_passed': accepted,
                     'failure_reason': route.get('failure_reason'),
                     **delivery,
                     'primary_replies': result['primary_replies'], 'Flash_replies': result['Flash_replies'],
                     'precheck_NO': result['precheck_NO'],
                     'normal_frame_primary_text_accuracy_not_required': True})
    assert len({v['run_id'] for v in rows}) == len(rows)
    counts = {condition: sum(v['condition'] == condition and v['frame_loop_acceptance_passed'] for v in rows)
              for condition in ['silent_drop', 'blank_replace', 'stale_replace', 'buttons_only']}
    delivery_counts = {condition: sum(v['condition'] == condition and v['user_normal_frame_delivery_passed'] for v in rows)
                       for condition in counts}
    root = HERE / ('acceptance-checkpoint-' + str(time.time_ns()))
    root.mkdir()
    summary = {'rows': rows, 'successful_complete_trajectories_per_condition': counts,
               'user_normal_frame_delivery_successes_per_condition': delivery_counts,
               'user_normal_frame_delivery_all_four_targets_reached': all(v >= 2 for v in delivery_counts.values()),
               'assessment_version': VERSION,
               'original_extra_environment_action_metric_preserved': True,
               'target_per_condition': 2, 'all_four_conditions_target_reached': all(v >= 2 for v in counts.values()),
               'image_review_bindings': reviews, 'whole_group_postexit_audit_pending': True,
               'not_a_population_trigger_reduction_rate': True, 'new_model_GUI_calls': 0}
    save(root / 'summary.json', summary)
    (root / 'join-source.py').write_bytes(Path(__file__).read_bytes())
    (root / 'delivery-source.py').write_bytes((HERE / 'user_frame_delivery.py').read_bytes())
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    temporary = HERE / ('.acceptance-' + str(time.time_ns()))
    temporary.write_text(json.dumps({'root': str(root), 'seal_sha256': sha(root / 'seal.json')}), encoding='utf8')
    temporary.replace(HERE / 'acceptance-checkpoint-current.json')
    print(json.dumps({'root': str(root), 'complete_audited_trajectories': len(rows), 'successes': counts,
                      'user_normal_frame_delivery_successes': delivery_counts,
                      'all_four_conditions_target_reached': summary['all_four_conditions_target_reached'],
                      'whole_group_postexit_audit_pending': True}))


if __name__ == '__main__':
    main()
