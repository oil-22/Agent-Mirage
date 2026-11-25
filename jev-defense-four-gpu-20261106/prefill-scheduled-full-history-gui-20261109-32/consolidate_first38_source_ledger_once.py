"""Bind already sealed source labels across the same logical technical continuation.

No new labels, image reinterpretation, checker input or model/GUI/scorer call.
The ledger stops at candidate38 even if the live process later advances.
"""
import hashlib
import json
from pathlib import Path
import time

from orchestrate import HERE, PACKAGE, save, sha


BASE=HERE.parent
read=lambda p:json.loads(Path(p).read_bytes())
canonical=lambda v:json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf8')
digest=lambda raw:hashlib.sha256(raw).hexdigest()


def verify(folder):
    for name,expected in read(folder/'seal.json').items():
        path=folder/name
        assert path.resolve().is_relative_to(folder.resolve()) and sha(path)==expected,str(path)


def main():
    pointer=HERE/'first38-consolidated-source-ledger-created.json'
    assert not pointer.exists(),'Completed source aggregation must not be repeated'
    manifest=read(PACKAGE/'manifest.json')
    assert sha(PACKAGE/'manifest.json')=='c83af050ba64c4edb4d9a1aeff6ebc9f4195e04ef576dd1906791d690e07a5f1'
    for name,expected in manifest['files'].items():assert sha(PACKAGE/name)==expected,name
    carry=read(PACKAGE/'carryover/state.json')
    evidence=HERE/'actual-evidence-1794250090224439000';verify(evidence)
    snapshot=read(evidence/'3090.json')['worker/status.json']['value']
    assert snapshot['active']==carry['original_track'] and snapshot['counts']['actor']==38
    parents=[BASE/'full-history-gui-development-20261109-23',
             BASE/'memory-scheduled-full-history-gui-20261109-29',HERE]
    groups=[];review_authorities=[];collection_authorities={};all_labels={}
    for parent in parents:
        group=[]
        for path in sorted(parent.glob('source-review-*/review.json')):
            review=read(path);verify(path.parent)
            review_authorities.append(dict(path=str(path),sha256=sha(path),seal_sha256=sha(path.parent/'seal.json')))
            collection=Path(review['collection'])
            assert collection.parent.parent==parent
            assert sha(collection/'collection.json')==review['collection_sha256']
            if str(collection)not in collection_authorities:
                verify(collection)
                collection_authorities[str(collection)]=dict(path=str(collection),receipt_sha256=sha(collection/'collection.json'),
                    seal_sha256=sha(collection/'seal.json'))
            index={row['id']:row for row in read(collection/'PRIVATE-source-index.json')}
            for label in review['rows']:
                full=label['candidate_event_sha256'];assert full not in all_labels
                assert label['id']==full[:20]
                packet_path=collection/label['id']/'packet.json';packet=read(packet_path)
                assert sha(packet_path)==label['packet_sha256']
                assert packet['candidate_event_sha256']==full
                assert digest(packet['candidate'].encode('utf8'))==packet['candidate_text_sha256']==label['candidate_text_sha256']
                assert digest(canonical(packet['actual_actor_request']))==packet['actor_request_body_sha256']
                source=index[label['id']]
                assert '/batch/runs/'+carry['original_track']+'/attempt-'in source['attempt']
                assert source['candidate_text_sha256']==label['candidate_text_sha256']
                assert source['actor_request_body_sha256']==packet['actor_request_body_sha256']
                wait_fields=[label[k]for k in ['pure_native_WAIT','pure_native_WAIT_excluded']if k in label]
                action_fields=[label[k]for k in ['native_action_target_or_direction_error','native_target_or_direction_error']if k in label]
                assert wait_fields and all(type(v)is bool and v==wait_fields[0]for v in wait_fields)
                assert action_fields and all(v is None or type(v)is bool for v in action_fields)
                assert all(v==action_fields[0]for v in action_fields)
                semantic=label['definite_semantic_Mirage'];assert semantic is None or type(semantic)is bool
                normalized=dict(candidate_id=full,pure_native_WAIT=wait_fields[0],definite_semantic_Mirage=semantic,
                    unresolved_semantic_subclaims=label['unresolved_semantic_subclaims'],
                    native_action_target_or_direction_error=action_fields[0],
                    original_label=label,original_label_modified=False,review_authority=review_authorities[-1],
                    source_packet_path=str(packet_path),source_packet_sha256=label['packet_sha256'],
                    source_actual_actor_body_sha256=packet['actor_request_body_sha256'],
                    source_candidate_text_sha256=label['candidate_text_sha256'],
                    source_attempt=source['attempt'],source_candidate_event_seq=source['candidate_seq'],
                    source_leg=str(parent))
                all_labels[full]=normalized;group.append((normalized,packet))
        group.sort(key=lambda pair:(pair[0]['source_attempt'],pair[0]['source_candidate_event_seq']))
        groups.append(group)
    assert [len(group)for group in groups]==[11,6,21]
    prefix=groups[0]+groups[1]
    history=read(PACKAGE/'carryover/checkpoint/accepted-actual-history.json')
    assert len(history['accepted_messages'])==32 and len(history['accepted_source_events'])==16
    assert digest(canonical(history['accepted_messages']))==carry['accepted_history_sha256']
    for index,(label,packet) in enumerate(prefix[:16]):
        event=history['accepted_source_events'][index]
        assert packet['candidate']==history['accepted_messages'][index*2+1]['content']
        assert packet['actor_request_body_sha256']==event['data']['actual_actor_body_sha256']
        assert packet['observation_id']==event['data']['accepted_observation_id']
        label['original_carried_accepted_exchange']=index+1
    pending_body=read(PACKAGE/'carryover/checkpoint/0020/payload.json')['body']
    pending_text=read(PACKAGE/'carryover/checkpoint/0020/response.json')['text']
    last_label,last_packet=prefix[-1]
    assert last_label['candidate_id']==carry['pending_candidate_event_sha256']
    assert last_packet['actual_actor_request']==pending_body and last_packet['candidate']==pending_text
    first_new_packet=groups[2][0][1]
    assert first_new_packet['actual_actor_request']['messages'][:1]==pending_body['messages'][:1]
    labels=[label for group in groups for label,packet in group]
    for ordinal,label in enumerate(labels,1):label['original_unique_actor_candidate_ordinal']=ordinal
    assert len(labels)==len(all_labels)==38
    positive=[r for r in labels if r['definite_semantic_Mirage']is True and not r['pure_native_WAIT']]
    unresolved=[r for r in labels if r['definite_semantic_Mirage']is None and not r['pure_native_WAIT']]
    out=HERE/('first38-consolidated-source-ledger-'+str(time.time_ns()));out.mkdir()
    (out/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    result=dict(schema='same-logical-track-original-source-label-ledger-through38-v1',time=time.time(),
        run_id=carry['original_track'],planned_original_tracks=32,planned_matched_pairs=16,
        source_only_review_authorities=review_authorities,source_collection_authorities=list(collection_authorities.values()),
        actual_snapshot=dict(path=str(evidence),seal_sha256=sha(evidence/'seal.json'),actor_attempts=38),
        original_distinct_candidate_count=38,source_leg_counts=[11,6,21],
        original16accepted_exchange_body_SHA_and_texts_bound=True,
        original_pending17_full_body_text_and_original_event_bound=True,
        cached_replay17_counted_as_zero_new_candidates=True,
        source_review_coverage_through38_only=True,full_logical_trajectory_terminal_coverage_not_yet_proven=True,
        definite_positive_candidates=len(positive),unresolved_candidates=len(unresolved),
        unresolved_original_candidate_ordinals=[r['original_unique_actor_candidate_ordinal']for r in unresolved],
        trajectory_any_Mirage=True if positive else None,
        no_definite_positive_is_not_a_negative_completed_trajectory=True,
        rows=labels,original_labels_changed=False,new_labels_or_second_independent_review_not_claimed=True,
        single_source_author_with_legal_feedback_not_fully_blind=True,
        actual32_result_records_fed_to_matched_math=False,new_model_GUI_scorer_paid_calls=0,
        no_official_score_execution_or_checker_truth_inferred=True,efficacy_or_goal_completion_established=False)
    save(out/'ledger.json',result)
    save(out/'seal.json',{p.name:sha(p)for p in out.iterdir()if p.is_file()})
    record=dict(root=str(out),ledger_sha256=sha(out/'ledger.json'),seal_sha256=sha(out/'seal.json'),
        original_distinct_candidates=38,unresolved_original_candidate_ordinals=result['unresolved_original_candidate_ordinals'])
    save(pointer,record);print(json.dumps(record))


if __name__=='__main__':main()
