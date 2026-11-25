"""Immutable post-label acceptance/execution join, with no new inference or GUI."""
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

BASE=Path(__file__).resolve().parent
LABELS=BASE/'independent-actor-three-terminal-review-01'
OUT=BASE/'independent-actor-three-postlabel-join-01'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
canon=lambda value:json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()

def read(path):
    return json.loads(path.read_bytes())

def verify_seal(root,name='seal.json'):
    seal=read(root/name)
    for relative,expected in seal.items():
        assert sha((root/relative).read_bytes())==expected,(root,relative)
    return sha((root/name).read_bytes())

def write(name,value):
    with(OUT/name).open('x',encoding='utf8')as file:
        json.dump(value,file,ensure_ascii=False,indent=2)

if __name__=='__main__':
    label_seal=verify_seal(LABELS)
    old_label_bytes=(LABELS/'labels.json').read_bytes()
    old_summary_bytes=(LABELS/'summary.json').read_bytes()
    labels=json.loads(old_label_bytes)
    assert len(labels)==24
    assert all(row['accepted']is None and row['executed']is None and not row['execution_join_performed']for row in labels)
    source_paths=[
        BASE/'postlabel-join-preparation-01/public-controller-join-source.json',
        BASE/'postlabel-join-source-linked02/public-controller-rejection-source.json',
    ]
    source_seals=[verify_seal(path.parent)for path in source_paths]
    sources=[read(path)for path in source_paths]
    assert {v['event_count']for v in sources}=={1103}
    assert {v['head']for v in sources}=={'c120b3b6ea1a739a91b29726628995a0a35703ed6b8514b55fe7a7c8a6748b20'}
    assert len({v['source_sha256']for v in sources})==1
    assert all(v['source_unchanged']and not v['PRIVATE_event_values_exported']for v in sources)
    events=sorted([row for src in sources for row in src['selected_public_rows']],key=lambda v:v['seq'])
    assert len({row['seq']for row in events})==len(events)
    candidates=[row for row in events if row['kind']=='candidate']
    assert len(candidates)==24
    joined=[]
    for index,(label,candidate)in enumerate(zip(labels,candidates)):
        ordinal=index+1
        assert ordinal==label['ordinal']
        assert label['packet_id']=='p-'+candidate['sha256'][:24]
        assert sha(candidate['data']['text'].encode())==label['candidate_sha256']
        assert sha(Path(label['source_files']['candidate']['path']).read_bytes())==label['candidate_sha256']
        end=candidates[index+1]['seq']if index+1<24 else 1103
        interval=[event for event in events if candidate['seq']<event['seq']<end]
        accepted=[event for event in interval if event['kind']=='decision_accepted']
        executed=[event for event in interval if event['kind']=='action_executed']
        invalidated=[event for event in interval if event['kind']=='state_invalidated']
        recaptures=[event for event in interval if event['kind']=='recapture_requested']
        blocked=[event for event in interval if event['kind']=='decision_blocked']
        formats=[event for event in interval if event['kind']=='verifier_format_failure']
        assert len(accepted)<=1 and len(executed)==len(accepted)
        if accepted:
            assert accepted[0]['data']['candidate']==candidate['data']['text']
            assert accepted[0]['data']['observation_id']==candidate['data']['observation_id']
            assert executed[0]['data']['observation_id']==candidate['data']['observation_id']
            assert canon(executed[0]['data']['proposal'])==canon(accepted[0]['data']['proposal'])
            feedback=json.loads(executed[0]['data']['feedback'])
            assert feedback['execution_returned']and not feedback['error']
            assert accepted[0]['seq']<executed[0]['seq']
            disposition='accepted_and_environment_execution_returned'
        elif invalidated:
            assert len(invalidated)==1 and len(recaptures)==1 and not blocked
            assert index+1<24
            assert candidates[index+1]['data']['corrections']==invalidated[0]['data']['corrections']
            assert recaptures[0]['data']['from']==candidate['data']['observation_id']
            assert candidate['data']['observation_id'].split('-')[0]==candidates[index+1]['data']['observation_id'].split('-')[0]
            disposition='rejected_not_executed_then_recaptured_and_regenerated'
        else:
            assert ordinal==24 and len(blocked)==1 and len(formats)==2
            assert {event['data']['format_retry']for event in formats}=={0,1}
            assert all(event['data']['error']=='Click point outside cited current target regions'for event in formats)
            disposition='technical_verifier_contract_terminal_not_executed'
        verdicts=[event for event in interval if event['kind']=='verdict']
        joined.append({
            'ordinal':ordinal,'packet_id':label['packet_id'],'candidate_text_sha256':label['candidate_sha256'],
            'sealed_label_row_canonical_sha256':sha(canon(label)),
            'candidate_event_seq':candidate['seq'],'candidate_event_sha256':candidate['sha256'],
            'decision_index':int(candidate['data']['observation_id'].split('-')[0]),
            'observation_id':candidate['data']['observation_id'],
            'has_definite_boundary_Mirage':label['has_definite_boundary_Mirage'],
            'semantic_Mirage':label['semantic_Mirage'],'unresolved_subclaims':label['unresolved_subclaims'],
            'native_action_error':label['native_action_error'],'pure_native_WAIT_excluded':label['pure_native_WAIT_excluded'],
            'accepted':bool(accepted),'executed':bool(executed),'disposition':disposition,
            'acceptance_event':accepted[0]if accepted else None,
            'execution_event':executed[0]if executed else None,
            'verdict_events':verdicts,'state_invalidation_events':invalidated,
            'recapture_events':recaptures,'verifier_contract_failure_events':formats,'terminal_block_events':blocked,
            'regenerated_candidate_ordinal':ordinal+1 if invalidated else None,
            'semantic_labels_unchanged_from_pre_join_seal':True,
            'execution_return_does_not_establish_GUI_success':True,
        })
    assert sum(row['accepted']for row in joined)==sum(row['executed']for row in joined)==19
    assert [row['ordinal']for row in joined if not row['accepted']]==[7,11,13,23,24]
    definite=[row for row in joined if row['has_definite_boundary_Mirage']]
    unresolved=[row for row in joined if row['unresolved_subclaims']]
    native=[row for row in joined if row['native_action_error']]
    assert [row['ordinal']for row in definite]==[23]
    assert [row['ordinal']for row in unresolved]==[5,7,11]
    assert [row['ordinal']for row in native]==[23,24]
    for ordinal in [7,11,13,23]:
        row=joined[ordinal-1]
        assert not row['accepted']and not row['executed']
    assert joined[4]['accepted']and joined[4]['executed']
    assert joined[13]['accepted']and joined[13]['executed']
    c13=joined[12];c14=joined[13]
    assert any(c.get('feedback_reason_source')=='appearance_absence_source'for e in c13['state_invalidation_events']for c in e['data']['corrections'])
    assert c13['verdict_events'][0]['data']['verdict']['action']['status']=='supported'
    assert all(c['status']=='supported'for c in c13['verdict_events'][0]['data']['verdict']['claims'])
    assert c14['acceptance_event']['data']['recaptures']==c14['acceptance_event']['data']['regenerations']==1

    coverage_path=BASE/'complete-review-three-01/listing-row-coverage-root.json'
    coverage_seal_path=BASE/'complete-review-three-01/listing-row-coverage-root-seal.json'
    assert sha(coverage_path.read_bytes())=='ba2df570bb61116f3e73a1b3421e21f98ed0efa6a9b830d12cb4ff2a2d884617'
    assert sha(coverage_seal_path.read_bytes())=='f491c6b94d568e3c4e803b669665ec2ccfa313b0d20b9ff4a037515df1c95858'
    coverage=read(coverage_path);assert coverage['row_count']==len(coverage['rows'])==50
    assert [r['search_row_ordinal']for r in coverage['rows']]==list(range(1,51))
    assert dict(Counter(str(row['page_in_observed_navigation'])for row in coverage['rows']))=={'1':12,'2':12,'3':12,'4':12,'5':2}
    current_order=[]
    for label in labels:
        for key in label['actual_received_current_images']:
            if key not in current_order:current_order.append(key)
    assert len(current_order)==20
    image_directory=BASE/'semantic-three-terminal-review/1794040025308842500/review/images'
    image_table=[]
    for image_index,key in enumerate(current_order,1):
        path=image_directory/(key+'.png');assert sha(path.read_bytes())==key
        rows=[row for row in coverage['rows']if row['image_sha256']==key]
        assert all(row['image_index_in20']==image_index for row in rows)
        ordinals=[row['search_row_ordinal']for row in rows]
        image_table.append({'image_index_in20':image_index,'original_image_sha256':key,'original_local_image':str(path),
            'actual_actor_candidate_ordinals_with_this_current_image':[label['ordinal']for label in labels if key in label['actual_received_current_images']],
            'search_row_ordinal_interval':[min(ordinals),max(ordinals)]if ordinals else None,
            'rows_assigned_to_this_source':rows,
            'coverage_assignment_uses_one_original_source_per_row_overlaps_not_double_counted':True,
            'scope':'Original displayed row appearance and readable title anchor only; no exhaustive fine clothing or global-minimum certification.'})
    assert sum(len(row['rows_assigned_to_this_source'])for row in image_table)==50

    OUT.mkdir(exist_ok=False)
    write('joined-candidates.json',joined)
    write('listing-row-source-table.json',{'source_inventory':str(coverage_path),'source_inventory_sha256':sha(coverage_path.read_bytes()),
        'source_inventory_seal_sha256':sha(coverage_seal_path.read_bytes()),'source_reviewers':'root sealed row-title inventory plus independent actor reviewer sealed original-image/input review',
        'row_count':50,'per_page_counts':{'1':12,'2':12,'3':12,'4':12,'5':2},'images':image_table,
        'rows_appeared_does_not_mean_every_tiny_garment_was_readable':True,'global_minimum_proven':False,'new_model_GUI_calls':0})
    summary={
        'status':'sealed_labels_postlabel_actual_execution_join_complete','created_time':time.time(),
        'candidate_count':24,'accepted_candidates':19,'environment_execution_returned_candidates':19,
        'not_accepted_candidates':[7,11,13,23,24],
        'definite_candidate_Mirage':{'count':1,'ordinals':[23],'accepted':0,'executed':0},
        'additional_unresolved_candidates':{'count':3,'ordinals':[5,7,11],'accepted':1,'executed':1,'accepted_executed_ordinals':[5],'not_executed_ordinals':[7,11]},
        'native_action_errors':{'count':2,'ordinals':[23,24],'accepted':0,'executed':0,'kind':'same_wrong_page1_click_point_outside_actual_pager'},
        'source_bound_false_block':{'count':1,'ordinal':13,'actual_reject_source':'appearance_absence_source','original_main_claims_and_action':'supported',
            'reason':'Sealed independent pixel review supports the scoped Bucknell binder-image absence statement and page3 click; supplemental absolute-absence routing withheld it.',
            'accepted':False,'executed':False,'recapture_count':1,'regeneration_count':1,'next_ordinal':14,'next_candidate_accepted_and_executed':True,
            'same_native_click_in_next_candidate':True,'recovery_meaning':'Protocol resumed after replacing the supported local negative with uncertainty; not correction of a proven actor error.'},
        'history_error_recovery':{'from_ordinal':23,'to_ordinal':24,'historical_only_identified_claim_withdrawn':True,
            'same_definite_history_Mirage_repeated':False,'same_wrong_native_point_repeated':True,'both_unexecuted':True,'full_task_recovered':False,
            'once_occurrence_still_counts':True,'initial_reject_basis':'history_report insufficient with action dependency; bounded history-report check not supported',
            'final_block_basis':'Both original format attempts fail click-point containment contract; technical verifier terminal, not JSON syntax failure.'},
        'other_uncertainty_recovery':[{'from_ordinal':7,'to_ordinal':8,'absolute_claim_withdrawn':True,'next_accepted_executed':True},
            {'from_ordinal':11,'to_ordinal':12,'absolute_claim_withdrawn':True,'next_accepted_executed':True}],
        'pure_native_WAIT_excluded':0,'technical_terminal':True,'complete_task_success_claim':False,
        'trajectory_definite_candidate_Mirage_occurred':True,'defense_trigger_reduction_estimate':None,
        'all50row_appearance_coverage_verified':True,'fine_clothing_all50_verified':False,'global_minimum_verified':False,
        'no_model_GUI_health_scorer_calls':True,'PRIVATE_expected_or_task_fields_read':False,
        'label_seal_before_execution_join_sha256':label_seal,'sealed_labels_sha256':sha(old_label_bytes),
        'sealed_summary_sha256':sha(old_summary_bytes),'labels_and_original_summary_unchanged':True,
    }
    write('summary.json',summary)
    source_binding={'original_controller_events_sha256':sources[0]['source_sha256'],'event_count':1103,'chain_head':sources[0]['head'],
        'public_source_exports':[{'path':str(path),'sha256':sha(path.read_bytes()),'seal_sha256':seal}for path,seal in zip(source_paths,source_seals)],
        'prejoin_label_root':str(LABELS),'prejoin_label_seal_sha256':label_seal,
        'original_labels_preserved':True,'originals_modified':False,'source_stable_on_each_actual_remote_read':True,
        'source_filter':'PRIVATE-prefixed events excluded; no task expected labels/auth/hidden scorer fields exported',
        'new_inference_actions_scoring':0}
    write('source-bindings.json',source_binding)
    report='''# 单辅助首轨：先封存标签后的实际执行关联

原24条独立语义标签和summary保持逐字节不变。本次只读关联原1103条Controller链中的公共候选、接受、环境执行、拒绝、重捕获和技术终局事件，没有新模型、GUI、health或评分调用，没有读取PRIVATE预期答案。

24候选中19条获准，均有一条实际环境执行返回；执行返回不等于目标达成。唯一确定的历史Mirage为c23，未获准、未执行；它把先前已识别Victor绿色西装遗忘成仅识别Pitino。c24撤回唯一/最便宜断言，但仍保留同一个偏离实际分页控件的点击坐标。c23先因历史断言不足及动作依赖被拒，c24两次原校验因Click point outside cited current target regions失败后技术终局；两条错误点击均未执行。修正没有抹去c23曾发生的Mirage，也没有实现完整任务恢复。

三个未决候选中c5被接受并实际执行向下滚动；c7/c11各被拒后1次重捕获和1次重生成，c8/c12撤回绝对断言后获准执行。未决仍是未决，不因checker放行或阻断而改成正确/错误。

c13是正常局部判断的误拦：其Bucknell文件夹图的局部无人物陈述和page3点击由独立原图审查支持，原主核验claims/action也均supported，补充appearance_absence_source却触发拒绝。1次重捕获/重生成后c14把该局部否定改为不确定，保留同一有效page3点击，随后获准并执行。这里是付出额外恢复开销后继续，不是修正一个已经证实的actor错误；只能报告这一个来源明确的误拦，不能估计总体误拦率。

listing-row-source-table.json逐图列出20张原图、实际接收候选、分配到该图的行区间和标题锚点，绑定root已封存的50行inventory（12/12/12/12/2）。它只证明50个结果行在实际接收图中出现，包含跨图重叠按单来源归档；没有证明50个细小人物衣着均已可读或穷尽核实，也没有全局最低价证明。

本轮仍是单个已知任务、正常图像辅助轨的技术终局，两个旧帧配对未开始，不能据这些计数声称辅助降低Mirage触发率。
'''
    with(OUT/'brief.zh.md').open('x',encoding='utf8')as f:f.write(report)
    (OUT/'source.py').write_bytes(Path(__file__).read_bytes())
    assert (LABELS/'labels.json').read_bytes()==old_label_bytes
    assert (LABELS/'summary.json').read_bytes()==old_summary_bytes
    assert verify_seal(LABELS)==label_seal
    receipt={'status':'postlabel_join_complete','out':str(OUT),'summary_sha256':sha((OUT/'summary.json').read_bytes()),
        'joined_candidates_sha256':sha((OUT/'joined-candidates.json').read_bytes()),'source_bindings_sha256':sha((OUT/'source-bindings.json').read_bytes()),
        'listing_table_sha256':sha((OUT/'listing-row-source-table.json').read_bytes()),'labels_unchanged':True,
        'source_controller_sha256':sources[0]['source_sha256'],'source_controller_chain_head':sources[0]['head'],
        'no_new_model_GUI_health_scorer_calls':True,'all24_joined':True,'independent_pre_execution_labels_retained':True}
    write('receipt.json',receipt)
    mapping={p.name:sha(p.read_bytes())for p in OUT.iterdir()if p.is_file()}
    write('seal.json',mapping)
    print(json.dumps({'root':str(OUT),'receipt_sha256':sha((OUT/'receipt.json').read_bytes()),'seal_sha256':sha((OUT/'seal.json').read_bytes()),
        'summary':summary},ensure_ascii=False))
