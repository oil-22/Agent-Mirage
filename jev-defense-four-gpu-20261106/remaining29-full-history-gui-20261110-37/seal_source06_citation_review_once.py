"""Seal a source-bound citation-coverage diagnosis without changing the runtime."""
import copy
import hashlib
import json
from pathlib import Path
import time

from orchestrate import HERE, save, sha
from join_source_reviews import verify_seal


def read(path):
    return json.loads(path.read_bytes())


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def main():
    pointer = HERE / 'source06-citation-coverage-review-created.json'
    assert not pointer.exists()
    source_authority = read(HERE / 'source06-postcheck0025-source-created.json')
    source = Path(source_authority['root'])
    assert verify_seal(source) == source_authority['seal_sha256']
    assert sha(source / 'receipt.json') == source_authority['receipt_sha256']
    payload = read(source / 'payload.json')
    assert read(source / 'external-wire.json')['payload'] == payload
    audit = HERE / 'mixed-receipt-audit-1794297174031798500'
    audit_seal = verify_seal(audit)
    native = read(audit / '3090-native-bindings.json')
    binding = native['bindings']['0025']
    assert binding['wire_sha256'] == sha(source / 'external-wire.json')
    assert binding['payload_sha256'] == hashlib.sha256(canonical(payload)).hexdigest()
    assert binding['request_seal_sha256'] == read(source / 'receipt.json')['request_seal_sha256']
    proof = next(row['native_proof'] for row in native['reports'] if row['request'] == '0025')
    assert proof['natural_EOS'] and proof['complete_supplied_images'] == 4
    label_authority = read(HERE / 'source-review-06-created.json')
    labels = Path(label_authority['review'])
    assert verify_seal(labels) == label_authority['seal_sha256']
    assert sha(labels / 'review.json') == label_authority['review_sha256']
    label = read(labels / 'review.json')['rows'][0]
    packet = read(Path(label['public_source_packet']))
    assert sha(Path(label['public_source_packet'])) == label['packet_sha256']
    assert payload['candidate'] == packet['candidate']
    expected = copy.deepcopy(packet['actual_actor_request']['messages'])
    current_message = next(message for message in reversed(expected) if isinstance(message['content'], list)
        and any(block.get('type') == 'image_url' for block in message['content']))
    current_message['content'] = [block for block in current_message['content'] if not (
        block.get('type') == 'text' and block['text'].startswith('IMAGE-ONLY EVIDENCE PACKET'))]
    assert payload['view']['messages'] == expected
    inventory = read(source / 'receipt.json')['images']
    assert inventory[0]['role'] == 'current'
    assert inventory[0]['sha256'] == 'b2269e968f8155558b0d5835d9763903bab39fcacc51cb86eb9506239085b6b9'
    assert inventory[0]['size'] == [1280, 720]
    for item in inventory:
        assert sha(source / item['file']) == item['sha256']
    raw_reply = binding['response']['verdict']
    parsed = json.loads(raw_reply)
    claim = next(row for row in parsed['claims'] if row['id'] == 'c2')
    assert claim['text'] == 'the visible results (decanter, sofa, aquarium) are not kayaks'
    assert claim['status'] == 'supported' and len(claim['evidence']) == 1
    citation = claim['evidence'][0]
    assert citation['image_index'] == 0 and citation['observation_id'] == payload['view']['observation_id']
    assert citation['coordinate_space'] == 'normalized_1000'
    assert citation['box_xyxy'] == [310, 250, 880, 720]
    assert '20 gallon aquarium' in citation['description']
    pixels = [coordinate * scale / 1000 for coordinate, scale in zip(citation['box_xyxy'], [1280, 720, 1280, 720])]
    assert pixels == [396.8, 180.0, 1126.4, 518.4]
    joinpath = HERE / 'post-review-join-1794297194499960300/join.json'
    verify_seal(joinpath.parent)
    joined = read(joinpath)
    assert joined['all_source_labels_sealed_before_this_join']
    outcome = next(row for row in joined['rows'] if row['id'] == label['id'])
    assert outcome['sealed_source_label'] == label and outcome['accepted'] and outcome['executed']
    assert label['candidate_semantic_mirage'] is False and label['native_action_error'] is False
    folder = HERE / ('source06-citation-coverage-review-' + str(time.time_ns()))
    folder.mkdir()
    (folder / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (folder / '0025-original-raw-reply.txt').write_bytes(raw_reply.encode('utf8'))
    review = dict(schema='source-bound-current-image-citation-coverage-review-v1', time=time.time(),
        actual_judge_input=source_authority, native_audit=str(audit), native_audit_seal_sha256=audit_seal,
        native_request='0025', request_seal_sha256=binding['request_seal_sha256'],
        raw_reply_utf8_sha256=hashlib.sha256(raw_reply.encode('utf8')).hexdigest(),
        native_input_generation_HTTP_and_journal_provenance=proof,
        actor_source_label_authority=label_authority,
        original_current_image_directly_viewed=True, actual_judge_system_and_dynamic_source_text_read=True,
        exact_legal_actor_history_except_current_auxiliary_packet_verified=True,
        image_roles=inventory, supported_claim=claim, cited_box_resolved_pixels=pixels,
        visual_review='On the complete 1280x720 original current image, the decanter and sofa rows are within the cited vertical range, while the third aquarium row begins around y641 and its readable title is around y646. The cited box ends at y518.4 and therefore excludes the aquarium picture and title. The full image does show that third nonkayak example. This is a localized coverage error in the supporting citation, not a demonstration that the underlying bounded claim is false.',
        aquarium_row_approximate_start_y=641, cited_box_excludes_third_named_example=True,
        complete_image_corroborates_underlying_bounded_claim=True,
        original_source_label_unchanged=True, candidate_semantic_Mirage=False,
        native_action_error=False, accepted=True, executed=True,
        execution_join=str(joinpath), execution_join_sha256=sha(joinpath),
        accepted_event_sha256=outcome['accepted_events'][0]['sha256'],
        executed_event_sha256=outcome['executed_events'][0]['sha256'],
        parsed_current_reply_and_execution_were_seen_before_exact_judge_input_diagnosis=True,
        source_label_and_complete_image_reading_preceded_current_outcome_join=True,
        single_reviewer_not_fully_blind_or_human_gold=True,
        binary_status_accuracy_or_trajectory_efficacy_not_inferred=True,
        no_auxiliary_inference_in_this_control=True,
        runtime_validator_images_histories_actions_and_budgets_unchanged=True,
        new_model_GUI_capture_action_scorer_calls=0)
    save(folder / 'review.json', review)
    save(folder / 'seal.json', {path.name: sha(path) for path in folder.iterdir() if path.is_file()})
    authority = dict(root=str(folder), review_sha256=sha(folder / 'review.json'), seal_sha256=sha(folder / 'seal.json'))
    save(pointer, authority)
    print(json.dumps(authority, ensure_ascii=True))


if __name__ == '__main__':
    main()
