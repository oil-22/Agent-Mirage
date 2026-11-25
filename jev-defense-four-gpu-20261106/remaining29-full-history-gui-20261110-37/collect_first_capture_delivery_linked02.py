"""Correct an observer-only step argument using the sealed next delivery ledger."""
import json
from pathlib import Path
import time

import orchestrate
from collect_capture_delivery_after_source_once import main as collect
from join_source_reviews import verify_seal


def main():
    root = orchestrate.HERE
    pointer = root / 'first-capture-delivery-linked02-created.json'
    assert not pointer.exists()
    failure = json.loads((root / 'capture-delivery-observer-failure-preserved.json').read_bytes())
    failed_root = Path(failure['root'])
    assert verify_seal(failed_root) == failure['seal_sha256']
    assert orchestrate.sha(failed_root / 'receipt.json') == failure['receipt_sha256']
    joined_path = root / 'post-review-join-1794294421676921800/join.json'
    verify_seal(joined_path.parent)
    joined = json.loads(joined_path.read_bytes())
    assert joined['all_source_labels_sealed_before_this_join']
    first, second = joined['rows']
    assert first['id'] == '0e5d0fa2e071ee813684' and first['accepted'] and first['executed']
    assert second['id'] == 'a1dcb2409696681935fe'
    delivery = second['PRIVATE_delivery_provenance_not_checker_input']
    assert delivery['seq'] > first['executed_events'][0]['seq']
    step = delivery['data']['step']
    assert step == 2
    intent_root = root / ('capture-delivery-observer-linked02-' + str(time.time_ns()))
    intent_root.mkdir()
    (intent_root / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    orchestrate.save(intent_root / 'intent.json', dict(
        linked_failure_preservation=failure, source_sealed_join=str(joined_path),
        source_sealed_join_sha256=orchestrate.sha(joined_path),
        evaluated_execution=first['executed_events'][0]['sha256'],
        actual_next_delivery_event_sha256=delivery['sha256'],
        corrected_observer_step=step, original_wrong_observer_step=1,
        experiment_inputs_prompts_model_runtime_actions_and_budgets_modified=False,
        new_model_GUI_capture_action_scorer_calls=0))
    collect(joined_path, first['id'], step)
    result = json.loads((root / ('capture-delivery-' + first['id'] + '-created.json')).read_bytes())
    assert result['capture_sha256'] == delivery['data']['capture_sha256']
    assert result['delivered_sha256'] == delivery['data']['delivered_sha256']
    orchestrate.save(intent_root / 'receipt.json', dict(result=result,
        linked_failure_preservation=failure, actual_next_delivery_step_bound=True,
        source_labels_unchanged=True, new_model_GUI_capture_action_scorer_calls=0))
    orchestrate.save(intent_root / 'seal.json', {p.name: orchestrate.sha(p) for p in intent_root.iterdir() if p.is_file()})
    authority = dict(root=str(intent_root), receipt_sha256=orchestrate.sha(intent_root / 'receipt.json'),
        seal_sha256=orchestrate.sha(intent_root / 'seal.json'))
    orchestrate.save(pointer, authority)
    print(json.dumps(authority, ensure_ascii=True))


if __name__ == '__main__':
    main()
