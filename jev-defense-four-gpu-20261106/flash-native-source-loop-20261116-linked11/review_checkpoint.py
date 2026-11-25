"""Report fully audited terminal prefixes; never infer whole-group completion."""
import importlib.util
import json
import time
from pathlib import Path
from control import HERE, save, sha
from join_reviewed_results import verify, MODES


def main():
    source = HERE.parent / 'flash-trusted-capture-protocol-20261116-06/user_frame_delivery.py'
    spec = importlib.util.spec_from_file_location('delivery_acceptance', source)
    delivery = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(delivery)
    labels, reviews = {}, []
    for root in sorted(HERE.glob('independent-image-notes-*')):
        verify(root)
        value = json.loads((root / 'notes.json').read_bytes())
        for export in value['source_exports']:
            verify(export['root'], export['seal_sha256'])
        for image in value['images']:
            assert sha(image['original_path']) == image['sha256']
            if image['sha256'] in labels:
                assert labels[image['sha256']] == image['normal_usable']
            labels[image['sha256']] = image['normal_usable']
        reviews.append({'root': str(root), 'seal_sha256': sha(root / 'seal.json')})
    rows = []
    for root in sorted(HERE.glob('trajectory-audit-*')):
        if not (root / 'seal.json').exists():
            continue
        verify(root)
        result = json.loads((root / 'summary.json').read_bytes())
        route = result['route']
        fresh = route.get('fresh_capture', {}).get('captured_sha256')
        normal = labels.get(fresh) is True
        assessed = delivery.assess(result, normal) if route['condition'] != 'clean_control' else {}
        c = json.loads((root / 'Controller.json').read_bytes())['result']
        events, terminal = c['events'], c['terminal']
        frames = [e['data'] for e in events if e['kind'] == 'PRIVATE_capture_injection' and not e['data']['injected']]
        gates = {e['data']['capture_id']: e['data']['decision'] for e in events if e['kind'] == 'gate_decision'}
        rows.append({'run_id': route['run_id'], 'condition': route['condition'], **assessed,
            'primary_replies': result['primary_replies'], 'Flash_replies': result['Flash_replies'],
            'precheck_NO': terminal['precheck_NO_count'], 'source_NO': terminal['receipt_NO_count'],
            'Flash_NO': sum(v == 'NO' for v in gates.values()), 'recaptures': terminal['recaptures'],
            'environment_actions': terminal['environment_actions'], 'outcome': terminal['outcome'],
            'official_reward': terminal['official_reward'],
            'normal_path_captures': len(frames),
            'normal_path_unknown_quality_captures': sum(labels.get(f['captured_sha256']) is None for f in frames),
            'normal_usable_unique_PNGs': len({f['captured_sha256'] for f in frames if labels.get(f['captured_sha256']) is True}),
            'normal_usable_Flash_false_blocks': sum(labels.get(f['captured_sha256']) is True and gates.get(f['capture_id']) == 'NO' for f in frames),
            'audit': {'root': str(root), 'seal_sha256': sha(root / 'seal.json')}})
    assert len(rows) == len({v['run_id'] for v in rows})
    counts = {mode: sum(v['condition'] == mode and v.get('user_normal_frame_delivery_passed', False) for v in rows) for mode in MODES}
    root = HERE / ('review-checkpoint-' + str(time.time_ns()))
    root.mkdir()
    result = {'time': time.time(), 'rows': rows, 'review_bindings': reviews,
        'successful_complete_trajectories_per_condition': counts, 'whole_group_postexit_audit_pending': True,
        'normal_text_misreading_excluded_per_user': True, 'new_model_GUI_calls': 0}
    save(root / 'result.json', result)
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    (root / 'delivery-assessment-source.py').write_bytes(source.read_bytes())
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    temporary = HERE / ('.review-checkpoint-' + str(time.time_ns()))
    save(temporary, {'root': str(root), 'seal_sha256': sha(root / 'seal.json')})
    temporary.replace(HERE / 'review-checkpoint-current.json')
    print(json.dumps({'root': str(root), 'complete_audited_trajectories': len(rows), 'successes_per_mode': counts, 'rows': rows}))


if __name__ == '__main__':
    main()
