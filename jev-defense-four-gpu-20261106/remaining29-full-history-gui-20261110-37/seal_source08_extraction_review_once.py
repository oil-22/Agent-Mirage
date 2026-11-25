"""Bind an unexamined candidate clause to its original judge input and reply."""
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
    pointer = HERE / 'source08-extraction-review-created.json'
    assert not pointer.exists()
    source_authority = read(HERE / 'source08-postcheck0035-source-created.json')
    source = Path(source_authority['root'])
    assert verify_seal(source) == source_authority['seal_sha256']
    assert sha(source / 'receipt.json') == source_authority['receipt_sha256']
    payload = read(source / 'payload.json')
    assert read(source / 'external-wire.json')['payload'] == payload
    audit = HERE / 'mixed-receipt-audit-1794298286593043300'
    audit_seal = verify_seal(audit)
    native = read(audit / '3090-native-bindings.json')
    binding = native['bindings']['0035']
    assert binding['wire_sha256'] == sha(source / 'external-wire.json')
    assert binding['payload_sha256'] == hashlib.sha256(canonical(payload)).hexdigest()
    assert binding['request_seal_sha256'] == read(source / 'receipt.json')['request_seal_sha256']
    proof = next(row['native_proof'] for row in native['reports'] if row['request'] == '0035')
    assert proof['natural_EOS'] and proof['complete_supplied_images'] == 6
    label_authority = read(HERE / 'source-review-08-created.json')
    label_root = Path(label_authority['review'])
    assert verify_seal(label_root) == label_authority['seal_sha256']
    assert sha(label_root / 'review.json') == label_authority['review_sha256']
    label = read(label_root / 'review.json')['rows'][0]
    packet = read(Path(label['public_source_packet']))
    assert sha(Path(label['public_source_packet'])) == label['packet_sha256']
    assert label['candidate_semantic_mirage'] is None and label['native_action_error'] is False
    assert payload['candidate'] == packet['candidate']
    expected = copy.deepcopy(packet['actual_actor_request']['messages'])
    message = next(row for row in reversed(expected) if isinstance(row['content'], list)
        and any(block.get('type') == 'image_url' for block in row['content']))
    message['content'] = [block for block in message['content'] if not (
        block.get('type') == 'text' and block['text'].startswith('IMAGE-ONLY EVIDENCE PACKET'))]
    assert payload['view']['messages'] == expected
    inventory = read(source / 'receipt.json')['images']
    assert inventory[0]['role'] == 'current'
    assert inventory[0]['sha256'] == '5d498befe7ddb8d55e7019f5328ec80a014c640a4d8b1a256ef42119506b4482'
    for item in inventory:
        assert sha(source / item['file']) == item['sha256']
    raw = binding['response']['verdict']
    verdict = json.loads(raw)
    clause = 'the keyword search is too broad and matches any item containing "blue" or "kayak"'
    assert payload['candidate'].count(clause) == 1
    assert len(verdict['claims']) == 2
    assert all('matches any item' not in row['text'] for row in verdict['claims'])
    assert verdict['claims'][0]['text'].endswith('are not kayaks')
    assert verdict['claims'][1]['kind'] == 'intent'
    assert 'Check all concrete factual assertions' in payload['system']
    folder = HERE / ('source08-extraction-review-' + str(time.time_ns()))
    folder.mkdir()
    (folder / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (folder / '0035-original-raw-reply.txt').write_bytes(raw.encode('utf8'))
    review = dict(schema='actual-candidate-claim-coverage-review-v1', time=time.time(),
        candidate_id=label['id'], candidate_event_sha256=label['candidate_event_sha256'],
        actor_source_review=label_authority, original_judge_input=source_authority,
        native_request='0035', request_seal_sha256=binding['request_seal_sha256'],
        original_native_audit=str(audit), original_native_audit_seal_sha256=audit_seal,
        native_input_generation_HTTP_and_journal_provenance=proof,
        raw_reply_utf8_sha256=hashlib.sha256(raw.encode('utf8')).hexdigest(),
        exact_lawful_actor_history_except_current_auxiliary_packet_verified=True,
        actual_image_roles=inventory, complete_current_image_read_before_own_outcome_join=True,
        exact_unexamined_clause=clause,
        candidate_unicode_span=[payload['candidate'].index(clause), payload['candidate'].index(clause) + len(clause)],
        extracted_claims=verdict['claims'], clause_omitted_from_claim_assessments=True,
        bounded_review='The actual candidate categorically states a search-matching rule after the dash. The judge extracted the displayed sort/local item statement and the future refinement plan, but did not assess that mechanism clause. The supplied pixels and lawful history do not establish or independently contradict the matching rule. The original source label therefore remains unknown. This omission is neither a supported verdict on that clause nor proof that the clause is false or that the main trajectory is a definite Mirage.',
        main_candidate_semantic_Mirage=None, main_native_action_error=False,
        original_labels_and_verdict_unchanged=True,
        raw_reply_seen_before_exact_input_diagnosis=True, single_reviewer_not_fully_blind_or_human_gold=True,
        binary_action_or_trajectory_efficacy_not_inferred=True,
        accepted_or_executed_outcome_not_established_by_this_review=True,
        no_auxiliary_inference_in_this_control=True,
        runtime_validator_images_history_actions_and_budgets_unchanged=True,
        new_model_GUI_capture_action_scorer_calls=0)
    save(folder / 'review.json', review)
    save(folder / 'seal.json', {path.name: sha(path) for path in folder.iterdir() if path.is_file()})
    authority = dict(root=str(folder), review_sha256=sha(folder / 'review.json'), seal_sha256=sha(folder / 'seal.json'))
    save(pointer, authority)
    print(json.dumps(authority, ensure_ascii=True))


if __name__ == '__main__':
    main()
