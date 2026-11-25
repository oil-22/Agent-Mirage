"""Linked observer fix: hash complete image bytes,then seal completion-only input."""
import base64
import hashlib
import json
from pathlib import Path
import time

from orchestrate import HERE, save, sha
from join_source_reviews import verify_seal


def inventory(payload):
    return [dict(role=image['role'], sha256=hashlib.sha256(
        base64.b64decode(image['raw_base64'], validate=True)).hexdigest())
        for image in payload['view']['images']]


def main():
    pointer = HERE / 'source14-completion90-input-review-created.json'
    assert not pointer.exists()
    failure = json.loads((HERE / 'completion90-observer-failure-preservation-created.json').read_bytes())
    assert verify_seal(Path(failure['root'])) == failure['seal_sha256']
    source_authority = json.loads((HERE / 'source14-completion-0090-source-created.json').read_bytes())
    source = Path(source_authority['root'])
    assert verify_seal(source) == source_authority['seal_sha256']
    actual = json.loads((source / 'payload.json').read_bytes())
    original_authority = json.loads((HERE / 'source14-postcheck-0079-source-created.json').read_bytes())
    original = Path(original_authority['root'])
    assert verify_seal(original) == original_authority['seal_sha256']
    prior = json.loads((original / 'payload.json').read_bytes())
    observed = inventory(actual)
    assert observed == inventory(prior) and len(observed) == 13
    assert actual['candidate'] is None and actual['operation'] == 'judge'
    assert len(actual['view']['messages']) == 1
    text = actual['view']['messages'][0]['content']
    assert text.startswith('Task: Find me the cheapest blue kayak on this site.\nImage provenance only: ')
    provenance = json.loads(text.split('\nImage provenance only: ', 1)[1])
    assert len(provenance) == 13
    for index, item in enumerate(provenance):
        assert item['image_index'] == index
        assert {k:item[k] for k in ['role','sha256']} == observed[index]
    assert not actual['view']['recent_action'] and not actual['view']['execution_feedback']
    root = HERE / ('source14-completion90-input-review-linked02-' + str(time.time_ns()))
    root.mkdir()
    (root / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(root / 'review.json', dict(schema='source-first-image-only-task-completion-input-review-v1',
        time=time.time(), linked_observer_failure_preservation=failure,
        rows=[dict(request='0090', source_input=str(source),
            source_input_seal_sha256=source_authority['seal_sha256'],
            actual_images=json.loads((source / 'receipt.json').read_bytes())['images'],
            all_actual_system_and_single_provenance_message_read=True,
            raw_reply_not_read_before_this_seal=True,
            judgments_before_reply=[
                'Actual input is legitimate task plus13completeimages/provenance only. It has no actorhistory,candidate,priorauxiliaryreadings ormainverdict. Do not describe this projection as retaining actorcontext or as a newmethod;the mainactor separately retains its completelegalhistory.',
                'Independently re-viewed the complete currentdetail and the three relevant original79-resultlistframes10/11/12 before this ownreply. All13originalbytehashes/roles match the already source-reviewed0079inventory;other originalframes retain prior independentreviews.',
                'Currentdetail supportsblueKayak185dollars,Akron/date andactualaruba10marking,but the legitimate task need not require a modelname. Specific modelerror is a separate source14candidatefinding and must not be inserted as checkerinput or substituted for this completion question.',
                'Originalframe10 visibly supplieskayakquery1-12of79 andLowerpricefirst. Frames10-12 show successive cheaperrows and185-dollarrow;this differs from older2764bluekayakqueryframes1-9. A valid ascending cheaperprefix route need not inspect all79orallmoreexpensiverows. Unreadable qualifyingcolour,especially70-dollarthumbnail,remains a specific limitation;no cheaper qualifyingblueboat is invented.',
                '50-dollarinflatablephoto and70-dollarwater/background must be assessed from pixels with localuncertainty;neither title nor bluewater supplies a definitehullcolour. Firsttwo28-dollarrows arebags,65/130rowsareracks,and visible85/90/115colours have their own scope. Adjacent85-dollarprice and1for50titletext remain distinct.',
                'Do not infer the actor mentally scanned everyrow or demand proof of cognition. Only actual deliveredpixels may establish comparisoncoverage/order/currentitem;an inputedit oropenmenu in earlyframes is not an executedsort/search proof.'
            ])], source_image_inventory=observed,
        preserved_prior_input_authority=original_authority,
        raw_own_reply_not_read_before_this_seal=True,
        image_inventory_key_assumption_repaired_with_complete_byte_hashes=True,
        original_request_reply_model_generation_and_source_labels_unchanged=True,
        one_reviewer_nonblind_development_diagnosis=True,
        evaluation_only_never_checker_input=True,
        new_model_GUI_capture_action_scorer_paid_calls=0))
    save(root / 'seal.json', {p.name:sha(p) for p in root.iterdir() if p.is_file()})
    result = dict(root=str(root), review_sha256=sha(root / 'review.json'), seal_sha256=sha(root / 'seal.json'))
    save(pointer, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
