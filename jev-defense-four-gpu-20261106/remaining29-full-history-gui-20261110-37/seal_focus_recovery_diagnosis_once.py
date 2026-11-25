"""Bind an observed current-frame reading error to original inputs and execution."""
import copy
import hashlib
import json
from pathlib import Path
import time

from orchestrate import HERE, save, sha
from join_source_reviews import verify_seal


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def main():
    pointer = HERE / 'focus-recovery-diagnosis-created.json'
    assert not pointer.exists()
    source_pointer = json.loads((HERE / 'source03-postcheck0011-source-created.json').read_bytes())
    source = Path(source_pointer['root'])
    assert verify_seal(source) == source_pointer['seal_sha256']
    assert sha(source / 'receipt.json') == source_pointer['receipt_sha256']
    wire = json.loads((source / 'external-wire.json').read_bytes())
    payload = json.loads((source / 'payload.json').read_bytes())
    assert wire['payload'] == payload
    audit = HERE / 'mixed-receipt-audit-1794294996313360500'
    verify_seal(audit)
    native = json.loads((audit / '3090-native-bindings.json').read_bytes())
    binding = native['bindings']['0011']
    assert binding['wire_sha256'] == sha(source / 'external-wire.json')
    assert binding['payload_sha256'] == hashlib.sha256(canonical(payload)).hexdigest()
    assert binding['request_seal_sha256'] == json.loads((source / 'receipt.json').read_bytes())['request_seal_sha256']
    proof = next(row['native_proof'] for row in native['reports'] if row['request'] == '0011')
    assert proof['natural_EOS'] and proof['complete_supplied_images'] == 2
    label_pointer = json.loads((HERE / 'source-review-03-created.json').read_bytes())
    label_root = Path(label_pointer['review'])
    assert verify_seal(label_root) == label_pointer['seal_sha256']
    label = json.loads((label_root / 'review.json').read_bytes())['rows'][0]
    packet_path = Path(label['public_source_packet'])
    assert sha(packet_path) == label['packet_sha256']
    packet = json.loads(packet_path.read_bytes())
    assert payload['candidate'] == packet['candidate']
    expected = copy.deepcopy(packet['actual_actor_request']['messages'])
    current_message = next(message for message in reversed(expected) if isinstance(message['content'], list)
        and any(block.get('type') == 'image_url' for block in message['content']))
    current_message['content'] = [block for block in current_message['content'] if not (
        block.get('type') == 'text' and block['text'].startswith('IMAGE-ONLY EVIDENCE PACKET'))]
    assert payload['view']['messages'] == expected
    inventory = json.loads((source / 'receipt.json').read_bytes())['images']
    assert [(row['role'], row['sha256']) for row in inventory] == [
        ('current', '564e7a79f977e2d647625301b9539e73027467dad75a59a85eda7bb8f6f66848'),
        ('reference', 'c60034d3e995b28eb7a5b68fe1ab31589b6ebcfc474296d176844e2c1cebe41d')]
    for row in inventory:
        assert sha(source / row['file']) == row['sha256']
    raw_reply = binding['response']['verdict']
    parsed = json.loads(raw_reply)
    assert 'no caret, selection, or distinct focus outline' in parsed['claims'][0]['evidence'][0]['description']
    joined_path = HERE / 'post-review-join-1794295495091998600/join.json'
    verify_seal(joined_path.parent)
    joined = json.loads(joined_path.read_bytes())
    assert joined['all_source_labels_sealed_before_this_join']
    outcome = next(row for row in joined['rows'] if row['id'] == label['id'])
    assert outcome['sealed_source_label'] == label and outcome['accepted'] and outcome['executed']
    assert outcome['executed_events'][0]['data']['proposal']['payload'] == {'type':'click', 'x':300, 'y':419}
    folder = HERE / ('focus-recovery-diagnosis-' + str(time.time_ns()))
    folder.mkdir()
    (folder / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (folder / '0011-original-raw-reply.txt').write_bytes(raw_reply.encode())
    review = dict(schema='actual-current-focus-cue-recovery-diagnosis-v1', time=time.time(),
        original_judge_input=source_pointer, original_native_audit=str(audit),
        original_native_audit_seal_sha256=sha(audit / 'seal.json'), native_request='0011',
        native_request_seal_sha256=binding['request_seal_sha256'],
        raw_reply_utf8_sha256=hashlib.sha256(raw_reply.encode()).hexdigest(),
        all_actual_system_dynamic_records_and_lawful_messages_read=True,
        actual_complete_images_viewed=['image-00.png','image-01.png'], actual_image_roles=inventory,
        current_image_has_clear_blue_Keyword_outline=True,
        reference_image_lacks_that_outline=True,
        exact_current_auxiliary_packet_removal_and_other_history_bytes_bound=True,
        independent_source_pixel_reading_preceded_current_reply_join=label_pointer,
        current_parsed_reply_was_seen_before_this_exact_judge_input_diagnosis=True,
        not_fully_blind_single_reviewer_development=True,
        observed_error='The description denying a distinct current outline conflicts with the supplied current blue-border image. The reference lacks the outline. Internal reference confusion is a hypothesis, not established causation.',
        binary_status_limit='The hypothesis remains uncertainty and the target click is correctly located. Wrong evidence/reason does not establish that every supported status is false.',
        main_candidate03_definite_Mirage=False,
        repeat_click_accepted_and_executed=True,
        accepted_event_sha256=outcome['accepted_events'][0]['sha256'],
        executed_event_sha256=outcome['executed_events'][0]['sha256'],
        execution_join=str(joined_path), execution_join_sha256=sha(joined_path),
        extra_same_target_click_after_visible_cue_count=1,
        wrong_native_target_or_direction_proven=False,
        OS_focus_independently_queried=False, isolated_walltime_delay_not_measured=True,
        no_auxiliary_inference_in_this_control=True,
        no_whole_trajectory_or_Mirage_reduction_claim=True,
        source_labels_original_results_and_runtime_unchanged=True,
        new_model_GUI_capture_action_scorer_calls=0)
    save(folder / 'review.json', review)
    save(folder / 'seal.json', {path.name: sha(path) for path in folder.iterdir() if path.is_file()})
    result = dict(root=str(folder), review_sha256=sha(folder / 'review.json'), seal_sha256=sha(folder / 'seal.json'))
    save(pointer, result)
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
