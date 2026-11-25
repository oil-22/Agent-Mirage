"""Preserve the source-reviewed first click's actual kind-mismatch recovery."""
import json
import time
from pathlib import Path
from orchestrate import HERE, GUIROOT, COMMON, remote, save, sha
from join_source_reviews import verify_seal


def main():
    assert not(HERE/'first-kind-recovery-created.json').exists()
    review=HERE/'source-review-1794313631718787800';verify_seal(review)
    label=json.loads((review/'review.json').read_bytes())['rows'][0]
    code='ROOT='+repr(GUIROOT)+'\nCANDIDATE_SHA='+repr(label['candidate_event_sha256'])+'\n'+COMMON+r'''
matches=[]
for p in sorted((Path(ROOT)/'batch/runs').glob('*/attempt-*/events.jsonl')):
 data=p.read_bytes();data=data[:data.rfind(b'\n')+1]if data and not data.endswith(b'\n')else data
 events=[];previous='0'*64
 for line in data.splitlines():
  e=json.loads(line);v=dict(e);s=v.pop('sha256')
  assert e['seq']==len(events)and e['previous']==previous and hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==s
  previous=s;events.append(e)
 positions=[i for i,e in enumerate(events)if e['sha256']==CANDIDATE_SHA]
 for start in positions:
  end=next((i for i in range(start+1,len(events))if events[i]['kind']=='actor_response'),len(events))
  keep={'point_crosscheck','point_evidence_unavailable','target_alignment','state_invalidated','recapture_requested','decision_accepted','action_executed','decision_blocked','verdict'}
  selected=[e for e in events[start:end]if e['kind']in keep]
  matches.append({'path':str(p),'events':selected,'chain_events':len(events),'chain_head':previous})
assert len(matches)==1
print(json.dumps(matches[0]))
'''
    raw,operation=remote('4090',code,'read-only-first-reviewed-click-kind-mismatch-recovery',timeout=55)
    result=json.loads(raw)
    cross=[e for e in result['events']if e['kind']=='point_crosscheck'];assert len(cross)==1
    assert cross[0]['data']['expected_kind']=='menu_option'and cross[0]['data']['actual']['kind']=='input'and cross[0]['data']['agrees']is False
    assert any(e['kind']=='state_invalidated'for e in result['events'])
    assert any(e['kind']=='recapture_requested'for e in result['events'])
    assert not any(e['kind']in['target_alignment','decision_accepted','action_executed']for e in result['events'])
    out=HERE/('first-kind-recovery-'+str(time.time_ns()));out.mkdir()
    (out/'collector.py').write_bytes(Path(__file__).read_bytes());save(out/'actual-events.json',result)
    save(out/'review.json',dict(time=time.time(),source_review=str(review),source_review_sha256=sha(review/'review.json'),
        candidate_event_sha256=label['candidate_event_sha256'],source_candidate_semantic_mirage=False,
        source_native_action_error=False,actual_main_kind='menu_option',actual_point_kind='input',
        both_actual_readings_identify_same_visible_Category_dropdown=True,
        actual_point_box_pixels=[641,278,911,328],native_click_pixel_point=[774.4,301.68],
        original_point_kind_family_crosscheck_refused=True,original_alignment_branch_not_entered=True,
        actual_bounded_recapture_and_actor_regeneration=True,
        scoped_normal_operation_refusal_not_actor_Mirage=True,whole_decision_final_block_or_trajectory_result_not_established=True,
        new_approved_source_representation_did_not_change_this_original_semantic_branch=True,
        runtime_modified=False,source_labels_changed=False,new_model_GUI_scorer_paid_calls=0,operation=str(operation)))
    (out/'report.md').write_text('正常Category下拉框点击的局部误拒\n\n先审原完整图和全部2条合法输入后，点击605,419位于Category下拉框，候选没有事实断言。真实主核验0003给supported/menu_option，点读0004给input并明确同一个Category下拉控件；原点种类家族不包含input，实际agrees=false，触发原有复拍与actor再生成。该候选没有接受/实执，后续target_alignment未进入。0005是复拍后的screen读取，不能误称alignment。\n\n这是正常操作的局部拒绝，未证实整轨最终阻断/失败，也不是actor Mirage。来源ID表示不改变此既有分支；本次仅读取证，未热改分类/validator/预算/原终局，不能据此称防御修好。\n',encoding='utf8')
    save(out/'seal.json',{p.name:sha(p)for p in out.iterdir()if p.is_file()})
    pointer=dict(root=str(out),review_sha256=sha(out/'review.json'),seal_sha256=sha(out/'seal.json'),
        scoped_normal_operation_refusal=True,no_new_model_GUI_calls=True)
    save(HERE/'first-kind-recovery-created.json',pointer);print(json.dumps(pointer))


if __name__=='__main__':main()
