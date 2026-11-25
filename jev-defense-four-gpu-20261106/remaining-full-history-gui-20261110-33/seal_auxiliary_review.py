"""Seal explicit original-image/auxiliary-reply judgments without actor labels."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import time

from orchestrate import HERE, save, sha
from join_source_reviews import verify_seal


def main(input_path):
    assert input_path.parent == HERE
    supplied = json.loads(input_path.read_bytes())
    ident = supplied['request']
    assert len(ident) == 4 and ident.isdigit()
    pointer = HERE / ('auxiliary-review-' + ident + '-created.json')
    assert not pointer.exists(), 'Completed source judgments remain immutable'
    authority = json.loads((HERE / ('auxiliary-source-' + ident + '-collected.json')).read_bytes())
    source = Path(supplied['source'])
    assert source.parent == HERE and str(source) == authority['root']
    assert verify_seal(source) == authority['seal_sha256']
    assert sha(source / 'receipt.json') == authority['receipt_sha256']
    receipt = json.loads((source / 'receipt.json').read_bytes())
    request = json.loads((source / 'request.json').read_bytes())
    image = (source / 'original.png').read_bytes()
    assert hashlib.sha256(image).hexdigest() == request['image_sha256']
    assert base64.b64decode(request['image_base64'], validate=True) == image
    assert hashlib.sha256(request['prompt'].encode()).hexdigest() == request['prompt_sha256']
    assert request == receipt['source']['request']
    boundary = json.loads((source / 'stateless-input-boundary.json').read_bytes())
    discarded = json.loads((source / 'stateless-context-discarded.json').read_bytes())
    assert boundary['message_count'] == 1 and boundary['content_types'] == ['image', 'text']
    assert boundary['task_history_candidate_previous_auxiliary_content_supplied'] is False
    assert discarded['actual_first_forward_cache_length'] == 0 and discarded['all_observed_cache_objects_released']
    raw = (source / 'raw-output.txt').read_bytes()
    reading = json.loads(raw)
    assert supplied['original_complete_image_visually_viewed'] is True
    assert supplied['current_main_candidate_or_current_checker_execution_score_read'] is False
    assert supplied['overall_output_semantic_correctness'] is None
    root = HERE / ('auxiliary-review-' + ident + '-' + str(time.time_ns()))
    root.mkdir()
    (root / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (root / 'supplied-review.json').write_bytes(input_path.read_bytes())
    save(root / 'review.json', dict(time=time.time(), source_authority=authority,
        image_sha256=request['image_sha256'], raw_output_sha256=hashlib.sha256(raw).hexdigest(),
        model=request['model'], revision=request['revision'], prompt_sha256=request['prompt_sha256'],
        actual_stateless_source_receipts_verified=True,
        full_native_ID_tensor_and_actor_insertion_audit_not_supplied_by_this_review=True,
        actual_summary_characters=len(reading['frame']['summary']),
        summary_reaches_hard180_boundary=len(reading['frame']['summary']) == 180,
        explicit_source_judgment=supplied, reviewer_count=1, not_fully_blind_or_human_gold=True,
        actor_adoption_trajectory_Mirage_or_efficacy_not_established=True,
        no_runtime_prompt_input_reply_validator_or_budget_modification=True,
        new_model_GUI_capture_action_scorer_paid_calls=0))
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    value = dict(root=str(root), review_sha256=sha(root / 'review.json'), seal_sha256=sha(root / 'seal.json'))
    save(pointer, value)
    print(json.dumps(value))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, type=Path)
    args = parser.parse_args()
    main(args.input.resolve())
