"""Seal actual 13-record price-relation input before reading reply0089."""
import hashlib
import json
from pathlib import Path
import time

from orchestrate import HERE, save, sha
from join_source_reviews import verify_seal


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf8')


def main():
    pointer = HERE / 'source14-relation89-input-review-created.json'
    assert not pointer.exists()
    authority = json.loads((HERE / 'source14-price-relation-0089-source-created.json').read_bytes())
    source = Path(authority['root'])
    assert verify_seal(source) == authority['seal_sha256']
    payload = json.loads((source / 'payload.json').read_bytes())
    assert payload['operation'] == 'judge' and not payload['view']['images']
    assert len(payload['view']['messages']) == 1
    pair = json.loads(payload['candidate'])
    assert pair == json.loads(payload['view']['messages'][0]['content'])
    actor = json.loads((HERE / 'source-review-14-created.json').read_bytes())
    actor_root = Path(actor['review'])
    assert verify_seal(actor_root) == actor['seal_sha256']
    actor_label = json.loads((actor_root / 'review.json').read_bytes())['rows'][0]
    packet = json.loads(Path(actor_label['public_source_packet']).read_bytes())
    assert sha(Path(actor_label['public_source_packet'])) == actor_label['packet_sha256']
    assert pair['actual_candidate'] == packet['candidate']
    diagnosis = json.loads((HERE / 'source14-price-routing-cpu-diagnosis-created.json').read_bytes())
    diagnosis_root = Path(diagnosis['root'])
    assert verify_seal(diagnosis_root) == diagnosis['seal_sha256']
    prior_route = json.loads((diagnosis_root / 'receipt.json').read_bytes())
    assert pair['queried_price_history_clauses'] == prior_route['exact_extracted_clauses']
    wanted = ['0070', *['%04d' % n for n in range(80, 89)], '0071', '0072', '0073']
    records = pair['independent_original_frame_records']
    assert len(records) == len(wanted) == 13
    bindings = {}
    for path in HERE.glob('mixed-receipt-audit-created-*.json'):
        audit = json.loads(path.read_bytes())
        root = Path(audit['root'])
        # Read only pre-0089 bindings;never inspect this relation's ownreply.
        actual = json.loads((root / '3090-native-bindings.json').read_bytes())['bindings']
        selected = set(actual) & set(wanted)
        if not selected:
            continue
        assert verify_seal(root) == audit['seal_sha256']
        for ident in selected:
            bindings[ident] = (audit, actual[ident])
    rows = []
    for index, (frozen, ident) in enumerate(zip(records, wanted)):
        value = dict(frozen)
        signature = value.pop('frozen_sha256')
        assert hashlib.sha256(canonical(value)).hexdigest() == signature
        audit, binding = bindings[ident]
        assert json.loads(binding['response']['verdict']) == frozen['reading']
        rows.append(dict(frame_index=index, original_request=ident,
            original_frame=frozen['original_source_frame'], frozen_record_sha256=signature,
            original_native_audit=audit, original_reading_exactly_matches=True,
            reused_completed_original_read=ident in {'0070','0071','0072','0073'}))
    target = HERE / ('source14-relation89-input-review-' + str(time.time_ns()))
    target.mkdir()
    (target / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(target / 'review.json', dict(schema='source-first-exact-clause-13-record-relation-input-review-v1',
        time=time.time(), rows=[dict(request='0089', source_input=str(source),
            source_input_seal_sha256=authority['seal_sha256'], actual_images=[],
            all_actual_system_and_text_read=True, raw_reply_not_read_before_this_seal=True,
            judgments_before_reply=[
                'Read the complete actual system,source14 candidate,and exact quotedclause. The input is a text relation only,with no images,mainverdict,officialscore orprivateanswer. It may evaluate concrete item-price associations only,notcolour,coverage,globalminimum oractionrelease.',
                'All13frozen records match exact audited originalreadings:four completed cached0070-0073 and nine actualnew0080-0088. Allown0080-0088inputreviews were sealed before reading those replies;old0072/0073nonblindprior-relation exposure remains disclosed and does not change any mainlabel.',
                'The frozen title/price records support a genericblueKayak at185dollars,but do not explicitly establish theGrizzly10model. Absence of a modelname from a sampled reading is not proof of nonexistence;the full originalimage independently showsaruba10. A price-only supported relation cannot resolve that maincandidate identityerror.',
                'The clause combinesIobserved,current185-dollarprice andcheapestwording. Preserve the originalcandidate qualifiers and the narrow scope;do not promote this relation into an allsite minimum or replace unestablishedbluecolour premises with fabricatedcounterevidence.',
                'Cachedcurrentreading0070 retains original013-obs013provenance while this relationview is013-obs014. The currentbitmap is identical after recapture,but cache reuse is not a newinference,independenttransition or freshGUIexecution proof. Material/query/loading limitations in frozenreadings remain data,notcertifiedtruth.'
            ])], actor_source_label_authority=actor,
        original_frame_reading_bindings=rows,
        actual_new_frame_reads=9, original_cached_frame_reads=4,
        own_0089_reply_not_read_before_this_seal=True,
        source_labels_and_original_runtime_unchanged=True,
        one_reviewer_nonblind_development_diagnosis=True,
        evaluation_only_never_checker_input=True,
        new_model_GUI_capture_action_scorer_paid_calls=0))
    save(target / 'seal.json', {p.name: sha(p) for p in target.iterdir() if p.is_file()})
    result = dict(root=str(target), review_sha256=sha(target / 'review.json'), seal_sha256=sha(target / 'seal.json'))
    save(pointer, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
