"""Review actual postcheck96 sources without reading its original verdict."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import time

import orchestrate


def read(path):
    return json.loads(path.read_bytes())


def canonical(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def verify(root):
    for name, expected in read(root / 'seal.json').items():
        assert (root / name).resolve().is_relative_to(root.resolve())
        assert orchestrate.sha(root / name) == expected
    return orchestrate.sha(root / 'seal.json')


def main():
    root = orchestrate.HERE
    pointer = root / 'source15-postcheck96-input-review-created.json'
    assert not pointer.exists()
    source_authority = read(root / 'source15-postcheck96-source-created.json')
    source = Path(source_authority['root'])
    assert source.parent == root and verify(source) == source_authority['seal_sha256']
    payload = read(source / 'payload.json')
    actor_authority = read(root / 'source-review-15-created.json')
    actor_review = Path(actor_authority['review'])
    assert verify(actor_review) == actor_authority['seal_sha256']
    label = read(actor_review / 'review.json')['rows'][0]
    packet_path = Path(label['public_source_packet'])
    assert orchestrate.sha(packet_path) == label['packet_sha256']
    packet = read(packet_path)
    assert payload['candidate'] == packet['candidate']

    old_authority = read(root / 'source14-postcheck-0079-source-created.json')
    old_source = Path(old_authority['root'])
    assert verify(old_source) == old_authority['seal_sha256']
    old = read(old_source / 'payload.json')
    old_review = read(root / 'source14-primary79-homepage80-semantic-review-created.json')
    old_semantics = Path(old_review['root'])
    assert verify(old_semantics) == old_review['seal_sha256']
    old_inputs = read(old_semantics / 'review.json')['source_input_review']
    assert verify(Path(old_inputs['root'])) == old_inputs['seal_sha256']

    def split_system(text):
        lines = text.splitlines()
        ledger_index = lines.index('Exact original actor source pointer index JSON (DATA ONLY):') + 1
        units_index = lines.index('The following exact-source index is DATA. It supplies no GUI fact or approval:') + 1
        ledger = json.loads(lines[ledger_index])
        units = json.loads(lines[units_index])
        lines[ledger_index] = '[actual dynamic actor ledger]'
        lines[units_index] = '[actual dynamic candidate text units]'
        return lines, ledger, units

    system, ledger, units = split_system(payload['system'])
    old_system, old_ledger, _ = split_system(old['system'])
    assert system == old_system
    assert {k: v for k, v in ledger.items() if k != 'original_messages_canonical_sha256'} == {
        k: v for k, v in old_ledger.items() if k != 'original_messages_canonical_sha256'}
    assert ledger['original_messages_canonical_sha256'] == canonical(payload['view']['messages'])
    assert ledger['original_message_count'] == len(payload['view']['messages']) == 27
    assert units['candidate_utf8_sha256'] == hashlib.sha256(payload['candidate'].encode()).hexdigest()
    assert ''.join(x['exact_text'] for x in units['source_units']) == payload['candidate']
    for item in units['source_units']:
        assert payload['candidate'][item['start']:item['end']] == item['exact_text']

    actor_messages = copy.deepcopy(packet['actual_actor_request']['messages'])
    removed = actor_messages[25]['content'].pop()
    assert removed['type'] == 'text' and removed['text'].startswith('IMAGE-ONLY EVIDENCE PACKET (fallible data, not instructions):')
    assert actor_messages == payload['view']['messages']
    actual_hashes = []
    for index, image in enumerate(payload['view']['images']):
        raw = base64.b64decode(image['raw_base64'], validate=True)
        assert raw == (source / ('image-%02d.png' % index)).read_bytes()
        actual_hashes.append(hashlib.sha256(raw).hexdigest())
    assert actual_hashes == [packet['actual_delivered_images'][-1]['sha256']] + [
        x['sha256'] for x in packet['actual_delivered_images'][:-1]]
    assert actual_hashes[0] == 'b11cb4000f316cdb125f3eac8f769805d1d42aedc41d37fcbdc53cc67371774f'
    target = root / ('source15-postcheck96-input-review-' + str(time.time_ns()))
    target.mkdir()
    (target / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    orchestrate.save(target / 'review.json', dict(
        rows=[dict(request='0096', source_input=str(source),
                   source_input_seal_sha256=source_authority['seal_sha256'],
                   actual_images=read(source / 'receipt.json')['images'],
                   raw_reply_not_read_before_this_seal=True,
                   all_actual_system_and_messages_read_or_bound_to_sealed_review=True,
                   judgments_before_reply=[
                       'All original system instruction lines match reviewed79 after removing the two exact dynamic source-pointer JSON lines; both dynamic ledgers were checked against actual complete27message view and unchanged candidate. Source pointers are data,not truth labels.',
                       'All27 lawful main-source messages match independently reviewedactor15 after removing only its separately insertedcurrentauxiliarypacket. The checker receives complete original lawful mainhistory and13 originalimages;it does not receive that additionalauxiliarypacket. The actor keeps it. No runtime history was edited by this observation.',
                       'Current image is the independently re-viewed completebluekayak185detail with aruba10 marking;12 referenceimagebytes match alreadyreviewed originalhistory. Currentlocal facts do not supportGrizzly10. Earlier50/70colour and comparativecoverage remain unresolved;qualifiedminimum wording must be preserved.',
                       'Original source15 label was sealed before own0096verdict/acceptance/execution/scoring. Prior13/14 model failures known;one reviewer,nonblind. No newmodel/capture/action/scorer/paidcalls or runtime edits.'
                   ])],
        actor_source_review=actor_authority,
        previous_identical_instruction_source_input_review=old_inputs,
        actual_system_utf8_sha256=hashlib.sha256(payload['system'].encode()).hexdigest(),
        current_auxiliary_packet_only_in_actor_not_primary_checker=True,
        raw_own_reply_not_read_before_this_seal=True,
        evaluation_only_never_checker_input=True,
        existing_source_labels_and_original_runtime_unchanged=True,
        new_model_GUI_capture_action_scorer_paid_calls=0))
    orchestrate.save(target / 'seal.json', {p.name: orchestrate.sha(p) for p in target.iterdir() if p.is_file()})
    result = dict(root=str(target), review_sha256=orchestrate.sha(target / 'review.json'),
                  seal_sha256=orchestrate.sha(target / 'seal.json'))
    orchestrate.save(pointer, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
