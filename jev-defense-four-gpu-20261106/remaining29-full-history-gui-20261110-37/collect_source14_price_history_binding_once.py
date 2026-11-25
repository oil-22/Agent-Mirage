"""Bind the naturally executed price-history branch to its original requests.

Read-only observer. No model, GUI, screenshot, retry or scoring call is made.
The manual price-only source judgment was sealed before this relation was read.
"""
import copy
import hashlib
import json
from pathlib import Path
import time

from orchestrate import COMMON, HERE, OUTPUT, REMOTE_PACKAGE, remote, save, sha
from join_source_reviews import verify_seal


def read(path):
    return json.loads(Path(path).read_bytes())


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()


def main():
    pointer = HERE / 'source14-price-history-live-binding-created.json'
    assert not pointer.exists()
    source_authority = read(HERE / 'source14-price-pair-source-review-created.json')
    source = Path(source_authority['root'])
    assert verify_seal(source) == source_authority['seal_sha256']
    assert sha(source / 'review.json') == source_authority['review_sha256']
    manual = read(source / 'review.json')
    assert manual['final_price_relation_reply_not_seen_before_this_seal']
    input_authority = read(HERE / 'source14-price-relation-source-created.json')
    inputs = Path(input_authority['root'])
    assert verify_seal(inputs) == input_authority['seal_sha256']
    payload = read(inputs / 'payload.json')
    pair = json.loads(payload['candidate'])
    assert payload['view']['images'] == [] and len(payload['view']['messages']) == 1
    assert payload['view']['messages'][0]['content'] == payload['candidate']
    assert pair['queried_price_history_clauses'] == [manual['exact_candidate_clause']]
    actor_label = read(Path(read(HERE / 'source-review-14-created.json')['review']) / 'review.json')['rows'][0]
    actor_packet = read(actor_label['public_source_packet'])
    assert pair['actual_candidate'] == actor_packet['candidate']
    records = pair['independent_original_frame_records']
    assert len(records) == 12
    bindings, proofs, audit_authorities = {}, {}, []
    wanted = {str(n).zfill(4) for n in range(59, 72)}
    for origin_path in sorted(HERE.glob('mixed-receipt-audit-created-*.json')):
        origin = read(origin_path)
        audit = Path(origin['root'])
        assert verify_seal(audit) == origin['seal_sha256']
        data = read(audit / '3090-native-bindings.json')
        used = False
        for request, binding in data['bindings'].items():
            if request not in wanted:
                continue
            assert request not in bindings or bindings[request] == binding
            bindings[request] = binding
            proofs[request] = next(r for r in data['reports'] if r['request'] == request)
            used = True
        if used:
            audit_authorities.append(origin)
    assert set(bindings) == wanted
    expected = []
    for index, record in enumerate(records):
        request = str(59 + index).zfill(4)
        frozen = copy.deepcopy(record)
        frozen_hash = frozen.pop('frozen_sha256')
        assert hashlib.sha256(canonical(frozen)).hexdigest() == frozen_hash
        assert json.loads(bindings[request]['response']['verdict']) == record['reading']
        assert proofs[request]['native_proof']['natural_EOS']
        assert proofs[request]['native_proof']['complete_supplied_images'] == 1
        expected.append(dict(request=request, seal_sha256=bindings[request]['request_seal_sha256'],
                             source_frame=record['original_source_frame'], reading=record['reading']))
    relation = json.loads(bindings['0071']['response']['verdict'])
    assert relation['claims'] == [] and relation['action']['target_kind'] == 'not_applicable'
    assert relation['action']['status'] == 'supported'
    assert proofs['0071']['native_proof']['complete_supplied_images'] == 0
    worker = read(HERE / 'actual-evidence-1794304575084397500/3090.json')['worker/process.json']['actual']
    code = ('ROOT=' + repr(OUTPUT) + '\nPACKAGE=' + repr(REMOTE_PACKAGE) + '\nEXPECTED=' + repr(expected)
            + '\nWORKER=' + repr(worker) + '\n' + COMMON + r'''
import base64
assert os.getuid()==1033
assert same_live(WORKER)
assert sha(Path(PACKAGE)/'manifest.json')=='368b0a594822f5e294fcd21927aa924a18a80f23249f160857b5de7090c1c02d'
reports=[];systems=set()
for item in EXPECTED:
 p=Path(ROOT)/'worker/requests'/item['request']
 assert p.stat().st_uid==1033 and sha(p/'seal.json')==item['seal_sha256']
 seal=json.loads((p/'seal.json').read_bytes())
 for name in ['external-wire.json','payload.json','response.json']:
  assert sha(p/name)==seal[name],name
 wire=json.loads((p/'external-wire.json').read_bytes())
 payload=json.loads((p/'payload.json').read_bytes())
 response=json.loads((p/'response.json').read_bytes())
 assert wire['payload']==payload and payload['operation']=='judge' and payload['candidate']is None
 assert wire['trajectory_id']=='fullhistory23-T000-stale_replace-noaux' and wire['decision_index']==13
 view=payload['view'];assert view['recent_action']==view['execution_feedback']==''
 assert len(view['images'])==1 and len(view['messages'])==1
 message=view['messages'][0]
 assert message['role']=='user' and message['content'].startswith('Original single-frame provenance only: ')
 provenance=json.loads(message['content'].split(': ',1)[1]);assert provenance==item['source_frame']
 picture=view['images'][0];raw=base64.b64decode(picture['raw_base64'],validate=True)
 assert hashlib.sha256(raw).hexdigest()==provenance['sha256']
 assert picture['role']==provenance['role']
 assert json.loads(response['verdict'])==item['reading']
 system_sha=hashlib.sha256(payload['system'].encode()).hexdigest();systems.add(system_sha)
 reports.append({'request':item['request'],'request_seal_sha256':item['seal_sha256'],
  'original_wire_sha256':seal['external-wire.json'],'payload_sha256':seal['payload.json'],
  'response_sha256':seal['response.json'],'actual_image_sha256':provenance['sha256'],
  'actual_role':picture['role'],'source_observation_id':provenance['source_observation_id'],
  'generic_system_sha256':system_sha,'complete_single_image_no_task_history_candidate_or_prior_reports':True,
  'actual_native_reply_equals_frozen_record':True})
assert len(systems)==1 and len({r['actual_image_sha256']for r in reports})==12
print(json.dumps({'passed':True,'reports':reports,'actual_worker':identity(WORKER['pid']),
 'system_sha256':list(systems)[0],'new_model_GUI_capture_action_scorer_calls':0}))
''')
    folder = HERE / ('source14-price-history-live-binding-' + str(time.time_ns()))
    folder.mkdir()
    (folder / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(folder / 'intent.json', dict(expected_original_requests=[r['request'] for r in expected],
        relation_request='0071', source_review=source_authority, relation_input=input_authority,
        actor_candidate_label_unchanged=True, no_runtime_mutation=True))
    try:
        output, operation = remote('3090', code, 'read-only-source14-live-price-history-complete-bindings', timeout=55)
        actual = json.loads(output)
        assert actual['passed'] and len(actual['reports']) == 12
        save(folder / 'actual-single-frame-bindings.json', actual)
        save(folder / 'relation-original-binding.json', bindings['0071'])
        save(folder / 'receipt.json', dict(passed=True, actor_candidate_id=actor_label['id'],
            actual_single_frame_readings=12, actual_text_relations=1,
            source_review_before_relation_join=source_authority, relation_input=input_authority,
            original_native_audit_authorities=audit_authorities, remote_operation=str(operation),
            all12_frozen_readings_equal_actual_natural_EOS_replies=True,
            all12_actual_wire_image_SHAs_roles_and_provenance_verified=True,
            no_actor_task_history_or_candidate_in_any_raw_reader=True,
            actual_generic_system_identical_for_all12=True,
            relation_raw_status=relation['action']['status'], narrow_price_associations_compatible=True,
            whole_candidate_color_global_minimum_and_completion_not_approved=True,
            source14_semantic_unknown_unchanged=True, prior_trajectory_Mirage_unchanged=True,
            auxiliary9B_calls_in_this_branch=0,
            component_cost=dict(input_tokens=sum(proofs[r]['native_proof']['actual_input_tokens'] for r in wanted),
                output_tokens=sum(proofs[r]['native_proof']['output_tokens'] for r in wanted),
                summed_native_call_timer_seconds=sum(proofs[r]['native_proof']['native_call_timer_seconds'] for r in wanted),
                scope='Only original12 frame reads plus1 relation; not walltime, currency, energy or savings'),
            source_reviewer_count=1, not_fully_blind_or_human_gold=True,
            actual_current_model_tensor_hash_not_recomputed=True,
            runtime_validator_actions_images_history_precision_and_budgets_unchanged=True,
            new_model_GUI_capture_action_scorer_calls=0, goal='active'))
        save(folder / 'seal.json', {p.name: sha(p) for p in folder.iterdir() if p.is_file()})
        result = dict(root=str(folder), receipt_sha256=sha(folder / 'receipt.json'),
                      seal_sha256=sha(folder / 'seal.json'))
        save(pointer, result)
        print(json.dumps(result))
    except BaseException as error:
        save(folder / 'observer-failure.json', dict(type=type(error).__name__, message=str(error),
             runtime_modified=False, new_model_GUI_capture_action_scorer_calls=0))
        if not (folder / 'seal.json').exists():
            save(folder / 'seal.json', {p.name: sha(p) for p in folder.iterdir() if p.is_file()})
        raise


if __name__ == '__main__':
    main()
