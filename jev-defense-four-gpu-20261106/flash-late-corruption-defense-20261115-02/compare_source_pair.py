"""Record exact pre-injection source matching after both frozen runs finish.

This reader makes no efficacy label, sends no requests, and excludes scores.
"""
import json
import sys
import time
from pathlib import Path
from control import HERE, save, sha
from record_source_checkpoint import checked


def main():
    task, condition = sys.argv[1:]
    assert task in ['T003', 'T058', 'T089'] and condition in ['late_white3', 'late_blur3']
    name = task+'-'+condition+'-source-pair-comparison'
    pointer = HERE/(name+'-current.json')
    assert not pointer.exists(), 'Use the original sealed comparison'
    sources = {}
    for arm in ['baseline', 'gate']:
        run = 'late15-'+task+'-'+condition+'-'+arm
        receipt, root = checked(HERE/('source-packets-'+run+'-current.json'))
        a = json.loads((root/'actor.json').read_bytes())['result']
        g = json.loads((root/'GUI.json').read_bytes())['result']
        assert a['run']['run_id'] == run and g['terminal']['run']['run_id'] == run
        sources[arm] = {'receipt': receipt, 'rows': a['requests'], 'GUI': g, 'task': a['public_task']}
    b, g = sources['baseline'], sources['gate']
    assert b['task'] == g['task']
    triggers = {arm: v['GUI']['terminal']['trigger_step'] for arm, v in sources.items()}
    active = [v for v in triggers.values() if v is not None]
    boundary = min(active) if active else min(len(b['rows']), len(g['rows']))+1
    fields = ['body_sha256', 'native_text', 'all_image_sha256s', 'current_image_sha256']
    prefix = []
    for br, gr in zip(b['rows'], g['rows']):
        assert br['decision'] == gr['decision']
        if br['decision'] >= boundary:
            break
        prefix.append({'decision': br['decision'], 'same': {k: br[k] == gr[k] for k in fields}, 'baseline_body_sha256': br['body_sha256'], 'gate_body_sha256': gr['body_sha256'], 'baseline_current_PNG': br['current_image_sha256'], 'gate_current_PNG': gr['current_image_sha256']})
    first = next((v for v in prefix if not all(v['same'].values())), None)
    first_raw = {}
    for arm, value in sources.items():
        event = next((v for v in value['GUI']['events'] if v['kind'] == 'PRIVATE_capture_injection' and v['data']['injected']), None)
        first_raw[arm] = event['data'] if event else None
    same_first_raw = (first_raw['baseline']['captured_sha256'] == first_raw['gate']['captured_sha256']) if all(first_raw.values()) else None
    root = HERE/(name+'-'+str(time.time_ns()))
    root.mkdir()
    (root/'source.py').write_bytes(Path(__file__).read_bytes())
    save(root/'comparison.json', {'time': time.time(), 'task_id': task, 'condition': condition, 'packet_receipts': {arm: v['receipt'] for arm, v in sources.items()}, 'first_injection_decision_by_arm': triggers, 'compared_pre_injection_decisions': len(prefix), 'pre_injection_exact_matches': prefix, 'first_pre_injection_source_divergence': first, 'no_pre_injection_source_divergence_found_in_compared_prefix': first is None, 'first_injected_capture_records': first_raw, 'first_injection_raw_PNG_exactly_same': same_first_raw, 'matching_does_not_establish_randomization_or_causation': True, 'whole_trajectory_semantic_labels_not_inferred': True, 'Mirage_reduction_proven': False, 'new_model_GUI_calls': 0})
    save(root/'seal.json', {q.name: sha(q) for q in root.iterdir() if q.is_file()})
    save(pointer, {'root': str(root), 'seal_sha256': sha(root/'seal.json')})
    print(json.dumps({'comparison': str(root), 'trigger_steps': triggers, 'compared_prefix': len(prefix), 'first_divergence_decision': first['decision'] if first else None, 'first_injection_same_raw_PNG': same_first_raw, 'Mirage_reduction_proven': False}))


if __name__ == '__main__':
    main()
