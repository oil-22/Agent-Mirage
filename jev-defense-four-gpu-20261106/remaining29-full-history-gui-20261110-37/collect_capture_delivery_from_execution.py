"""Select the existing next capture by sealed execution order, never a guessed step."""
import argparse
import base64
import json
from pathlib import Path
import re
import time

import orchestrate
import collect_capture_delivery_after_source_once as original
from join_source_reviews import verify_seal


def main(joinpath, ident):
    root = orchestrate.HERE
    assert re.fullmatch(r'[0-9a-f]{20}', ident)
    assert joinpath.parent.parent == root
    join_seal = verify_seal(joinpath.parent)
    joined = json.loads(joinpath.read_bytes())
    assert joined['all_source_labels_sealed_before_this_join']
    row = next(value for value in joined['rows'] if value['id'] == ident)
    assert row['accepted'] and row['executed'] and len(row['executed_events']) == 1
    pointer = root / ('capture-delivery-' + ident + '-created.json')
    assert not pointer.exists(), 'Existing captures remain immutable'
    before = "ledger=next(e for e in events[execution['seq']+1:]if e['kind']=='private_delivery_ledger'and e['data']['step']==STEP)"
    assert original.SOURCE.count(before) == 1
    source = original.SOURCE.replace(before,
        "ledger=next(e for e in events[execution['seq']+1:]if e['kind']=='private_delivery_ledger')\n"
        "STEP=ledger['data']['step'];assert type(STEP)is int and 1<=STEP<=50")
    prefix = ('ROOT=' + repr(orchestrate.GUIROOT) + '\nATTEMPT=' + repr(row['original_attempt'])
        + '\nEXECUTED=' + repr(row['executed_events'][0]['sha256']) + '\n')
    compile(prefix + source, 'read-only-capture-after-execution', 'exec')
    target = root / ('capture-delivery-derived-' + ident + '-' + str(time.time_ns()))
    target.mkdir()
    (target / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    orchestrate.save(target / 'intent.json', dict(source_sealed_join=str(joinpath),
        source_sealed_join_sha256=orchestrate.sha(joinpath), source_sealed_join_seal_sha256=join_seal,
        candidate_id=ident, executed_event_sha256=row['executed_events'][0]['sha256'],
        original_observer_source_sha256=orchestrate.sha(Path(original.__file__)),
        source_change='Only select the first actual next delivery ledger after the sealed execution; derive its step.',
        runtime_modified=False, new_model_GUI_capture_action_scorer_calls=0))
    try:
        output, operation = orchestrate.remote('4090', prefix + source,
            'evaluation-capture-derived-from-sealed-execution-' + ident, timeout=55)
        result = json.loads(output)
        for name, encoded in result.pop('exports').items():
            assert name in {'captured.png', 'delivered.png'}
            (target / name).write_bytes(base64.b64decode(encoded, validate=True))
            assert orchestrate.sha(target / name) == result['bindings'][Path(name).stem]['sha256']
        assert result['execution_event']['sha256'] == row['executed_events'][0]['sha256']
        frame_pointer = root / ('postexecution-frame-' + ident + '-created.json')
        if frame_pointer.exists():
            frame_authority = json.loads(frame_pointer.read_bytes())
            frame = Path(frame_authority['root'])
            assert verify_seal(frame) == frame_authority['seal_sha256']
            frame_receipt = json.loads((frame / 'receipt.json').read_bytes())
            assert frame_receipt['executed_event_sha256'] == row['executed_events'][0]['sha256']
            assert frame_receipt['next_observation_current_image']['sha256'] == result['bindings']['delivered']['sha256']
            result['original_postexecution_frame_authority'] = frame_authority
        result.update(source_sealed_execution_join=str(joinpath),
            source_sealed_execution_join_sha256=orchestrate.sha(joinpath), remote_operation=str(operation),
            actual_next_step_derived_from_original_event_chain=True,
            original_pixels_require_independent_review=True, runtime_modified=False)
        orchestrate.save(target / 'receipt.json', result)
        orchestrate.save(target / 'seal.json', {p.name: orchestrate.sha(p) for p in target.iterdir() if p.is_file()})
        authority = dict(root=str(target), receipt_sha256=orchestrate.sha(target / 'receipt.json'),
            seal_sha256=orchestrate.sha(target / 'seal.json'),
            capture_sha256=result['bindings']['captured']['sha256'],
            delivered_sha256=result['bindings']['delivered']['sha256'])
        orchestrate.save(pointer, authority)
        print(json.dumps(authority, ensure_ascii=True))
    except BaseException as error:
        orchestrate.save(target / 'failure.json', dict(error_type=type(error).__name__, message=str(error),
            runtime_modified=False, new_model_GUI_capture_action_scorer_calls=0))
        if not (target / 'seal.json').exists():
            orchestrate.save(target / 'seal.json', {p.name: orchestrate.sha(p) for p in target.iterdir() if p.is_file()})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--join', type=Path, required=True)
    parser.add_argument('--id', required=True)
    arguments = parser.parse_args()
    main(arguments.join.resolve(), arguments.id)
