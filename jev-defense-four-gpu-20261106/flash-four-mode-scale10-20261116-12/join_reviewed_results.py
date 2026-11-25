"""Join actual raw audits to independent PNG review; never change GUI outcomes."""
import importlib.util
import json
import time
from pathlib import Path

from control import HERE, PACKAGE, manifest, save, sha

MODES = ['silent_drop', 'blank_replace', 'stale_replace', 'buttons_only']


def verify(root, expected=None):
    root = Path(root)
    if expected is not None:
        assert sha(root / 'seal.json') == expected
    members = json.loads((root / 'seal.json').read_bytes())
    assert set(members) == {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p != root / 'seal.json'}
    for name, digest in members.items():
        assert sha(root / name) == digest, (root, name)
    return root


def pointer(name):
    value = json.loads((HERE / name).read_bytes())
    return verify(value['root'], value['seal_sha256']), value


def main():
    group_root, group_binding = pointer('completed-group-audit-current.json')
    cost_root, cost_binding = pointer('resource-interval-audit-current.json')
    release_root, release_binding = pointer('resource-release-audit-current.json')
    group = json.loads((group_root / 'summary.json').read_bytes())
    assert group['processed_GUI_trajectories'] == 40
    assert group['full_wire_input_tensors_history_EOS_probability_seal_chain_and_actions_verified']
    assert group['all_model_GUI_launcher_processes_verified_exited']
    assert json.loads((release_root / 'result.json').read_bytes())['all_17_kernel_locks_absent']
    delivery_source = HERE.parent / 'flash-trusted-capture-protocol-20261116-06/user_frame_delivery.py'
    spec = importlib.util.spec_from_file_location('original_delivery_acceptance', delivery_source)
    delivery = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(delivery)

    labels, reviews = {}, []
    for notes_root in sorted(HERE.glob('independent-image-notes-*')):
        verify(notes_root)
        notes = json.loads((notes_root / 'notes.json').read_bytes())
        for binding in notes['source_exports']:
            verify(binding['root'], binding['seal_sha256'])
        for image in notes['images']:
            digest = image['sha256']
            assert image['normal_usable'] in [True, False, None]
            assert sha(image['original_path']) == digest
            if digest in labels:
                assert labels[digest]['normal_usable'] == image['normal_usable'], 'Conflicting image review needs explicit correction, not replacement'
            labels[digest] = image
        reviews.append({'root': str(notes_root), 'seal_sha256': sha(notes_root / 'seal.json')})
    assert labels, 'Image review must be completed separately'

    expected_runs = {v['run_id'] for v in manifest()['remaining_queue']}
    group_routes = {v['run_id']: v for v in group['routes']}
    assert set(group_routes) == expected_runs
    rows, captures, audit_bindings = [], [], []
    for audit_root in sorted(HERE.glob('trajectory-audit-*')):
        if not (audit_root / 'seal.json').exists():
            continue
        verify(audit_root)
        result = json.loads((audit_root / 'summary.json').read_bytes())
        route = result['route']
        assert route == group_routes[route['run_id']], 'Reviewed raw trajectory must equal final group route'
        controller = json.loads((audit_root / 'Controller.json').read_bytes())['result']
        terminal, events = controller['terminal'], controller['events']
        by_kind = lambda kind: {v['data']['capture_id']: v for v in events if v['kind'] == kind}
        gate_by_id = by_kind('gate_decision')
        receipt_by_id = by_kind('capture_receipt_decision')
        presence_by_id = by_kind('image_presence_check')
        for event in events:
            if event['kind'] != 'PRIVATE_capture_injection' or event['data']['injected']:
                continue
            d = event['data']
            digest, cid = d['captured_sha256'], d['capture_id']
            label = labels.get(digest)
            gate = gate_by_id.get(cid)
            receipt = receipt_by_id.get(cid)
            presence = presence_by_id.get(cid)
            assert d['captured_sha256'] == d['delivered_sha256']
            decisions = [v['data']['decision'] for v in [presence, receipt, gate] if v is not None]
            rejected = 'NO' in decisions
            normal = None if label is None else label['normal_usable']
            captures.append({'run_id': route['run_id'], 'capture_id': cid, 'step': d['step'],
                'condition': route['condition'], 'image_sha256': digest, 'independently_normal_usable': normal,
                'source_decision': None if receipt is None else receipt['data']['decision'],
                'Flash_decision': None if gate is None else gate['data']['decision'],
                'rejected': rejected, 'definite_false_block': normal is True and rejected,
                'unreviewed_or_uncertain': normal is None})
        fresh = route.get('fresh_capture', {}).get('captured_sha256')
        normal = fresh in labels and labels[fresh]['normal_usable'] is True
        assessed = delivery.assess(result, normal) if route['condition'] != 'clean_control' else {}
        rows.append({'run_id': route['run_id'], 'condition': route['condition'], 'route': route,
             **assessed, 'recovery_image_independently_normal': normal,
             'primary_replies': result['primary_replies'], 'Flash_replies': result['Flash_replies'],
             'recaptures': terminal['recaptures'], 'precheck_NO': terminal['precheck_NO_count'],
             'source_NO': terminal['receipt_NO_count'],
             'Flash_NO': sum(v['data']['decision'] == 'NO' for v in events if v['kind'] == 'gate_decision'),
             'outcome': terminal['outcome'], 'environment_actions': terminal['environment_actions'],
             'official_reward': terminal['official_reward']})
        audit_bindings.append({'root': str(audit_root), 'seal_sha256': sha(audit_root / 'seal.json')})
    assert len(rows) == len({v['run_id'] for v in rows}) == 40
    assert {v['run_id'] for v in rows} == expected_runs
    assert captures and not any(v['unreviewed_or_uncertain'] for v in captures), 'Every actual normal-path capture requires original-image review'
    counts = {mode: sum(v['condition'] == mode and v.get('user_normal_frame_delivery_passed', False) for v in rows) for mode in MODES}
    clean = [v for v in captures if v['condition'] == 'clean_control']
    assert len({v['run_id'] for v in clean}) == 8
    normal = [v for v in captures if v['independently_normal_usable'] is True]
    clean_normal = [v for v in clean if v['independently_normal_usable'] is True]
    result = {'version': manifest()['version'], 'manifest_sha256': sha(PACKAGE / 'manifest.json'),
        'complete_GUI_trajectories': 40, 'successful_complete_trajectories_per_condition': counts,
        'cumulative_successful_complete_trajectories_per_condition': {k:v+2 for k,v in counts.items()},
        'four_modes_ten_successful_examples_each': all(v+2 >= 10 for v in counts.values()),
        'all_noninjected_capture_exposures': len(captures), 'normal_usable_capture_exposures': len(normal),
        'normal_usable_unique_PNGs': len({v['image_sha256'] for v in normal}),
        'normal_usable_false_blocks': sum(v['definite_false_block'] for v in normal),
        'normal_usable_false_block_trajectories': sorted({v['run_id'] for v in normal if v['definite_false_block']}),
        'clean_control_trajectories': 8, 'clean_control_capture_exposures': len(clean),
        'clean_control_normal_usable_exposures': len(clean_normal),
        'clean_control_normal_false_blocks': sum(v['definite_false_block'] for v in clean_normal),
        'noninjected_unusable_frames': [v for v in captures if v['independently_normal_usable'] is False],
        'rows': rows, 'capture_assessments': captures, 'image_review_bindings': reviews,
        'trajectory_audit_bindings': audit_bindings, 'group_binding': group_binding,
        'cost_binding': cost_binding, 'release_binding': release_binding,
        'delivery_acceptance_source_sha256': sha(delivery_source),
        'group': group, 'cost': json.loads((cost_root / 'result.json').read_bytes()),
        'native_primary_text_accuracy_excluded_per_user': True,
        'all_completed_failures_and_untriggered_preserved': True,
        'image_review_blind': False, 'new_task_ids': [0,3,17,58,89,94,112,131],
        'prior_verified_successes_per_mode': 2,
        'population_Mirage_reduction_or_generalization_proven': False,
        'source_signed_bad_frame_protection_proven': False,
        'source_NO_is_Flash_detection': False, 'new_model_GUI_calls': 0}
    root = HERE / ('reviewed-campaign-' + str(time.time_ns()))
    root.mkdir()
    save(root / 'result.json', result)
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    (root / 'delivery-acceptance-source.py').write_bytes(delivery_source.read_bytes())
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    pointer_value = {'root': str(root), 'seal_sha256': sha(root / 'seal.json')}
    temporary = HERE / ('.reviewed-campaign-' + str(time.time_ns()))
    save(temporary, pointer_value)
    temporary.replace(HERE / 'reviewed-campaign-current.json')
    print(json.dumps({'root': str(root), 'successes_per_mode': counts,
        'normal_usable_false_blocks': result['normal_usable_false_blocks'],
        'clean_control_normal_false_blocks': result['clean_control_normal_false_blocks'], 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
