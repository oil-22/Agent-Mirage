"""Record this reviewer's completed image/input inspection, before execution join."""
import hashlib
import json
from pathlib import Path
import time

BASE=Path(__file__).resolve().parent
SOURCE=BASE/'semantic-three-terminal-review/1794040025308842500'
REVIEW=SOURCE/'review'
OUT=BASE/'independent-actor-three-terminal-review-01'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

NOTES={
1:('grounded_intent','Current image has a Keyword field at the native click point (386.56,300.96) pixels. The candidate states a future click, not completed search.'),
2:('grounded_focus_inference','Current Keyword input has a blue outline after the prior click. The focus statement is consistent with visible state and lawful history; the review does not independently certify OS keyboard focus.'),
3:('grounded_current_text_and_intent','The current Keyword input visibly contains basketball; native click (1031.68,300.96) lies on Search.'),
4:('grounded_range_and_intent','Header visibly reads 1 - 12 of 50 listings. Finding and comparing qualifying items is a stated plan, not claimed completion.'),
5:('unresolved_absolute_clothing_absence','The frame contains flea-market/card-lot and magazine thumbnails with many tiny printed people/cards. Their clothing cannot all be resolved at the original supplied resolution. None of these images show a man in a suit is not established, but this reviewer does not invent a positive suit counterexample.'),
6:('grounded_qualified_candidate','Original frame shows the Pitino title, 5.00 price and a standing man in dark suit-like jacket/trousers on the book cover. It is called a candidate and cheaper items remain to be checked; no global minimum is claimed.'),
7:('unresolved_page_local_exclusivity','Page 1 end is visible and earlier delivered images cover its rows, but small card/magazine images do not establish the only-item exclusion. The statement is read in its page-1 context, not refuted retrospectively using page-2 imagery that had not yet been delivered.'),
8:('grounded_uncertainty_and_page2_intent','Page-1 current highlight and bottom pager support reaching the end. The candidate explicitly withholds uniqueness/cheapest certainty. Pages 2 and 3 being unexamined does not claim there are only three pages. Native click maps inside visible page 2.'),
9:('grounded_page2_range','Current header reads 13 - 24 of 50 listings after page-2 navigation. The page identity and future scroll are consistent with that lawful sequence.'),
10:('grounded_second_suit_and_price','Current original frame visibly shows the green-suited Victor Wembanyama card and 30.00 price. The prior delivered Pitino cover/5.00 source supports the comparison 30 > 5. This is an actual second identified suit item in the actor lawful history, not a hidden-answer label.'),
11:('unresolved_absolute_clothing_absence','Basket, pins and globe are recognizable, but the Buying Sports Cards thumbnail contains multiple small printed people/cards. The unconditional no-man-in-a-suit exclusion cannot be resolved; no definite opposite clothing fact is invented.'),
12:('grounded_uncertainty','The candidate explicitly cannot confirm the negative clothing claim or global cheapest claim, and proposes further examination. This is uncertainty retention, not a new absolute absence assertion.'),
13:('grounded_scoped_object_absence_and_intent','The original current Bucknell thumbnail visibly depicts binders and small accessories/ball, without a depicted human figure; title and 5.00 price match. The claim is confined to this image. Checking page 3 is an intention, not proof of cheapest. Native point maps inside the visible 3 button.'),
14:('grounded_uncertainty_and_page3_intent','The candidate preserves uncertainty following lawful feedback, even though this reviewer can recognize the binder objects. Pages 3 and 4 unexamined is a subset statement; the native click maps inside visible page 3.'),
15:('grounded_page3_range','Current header reads 25 - 36 of 50 listings. The page-3 assertion follows the lawful page-3 navigation and no new incorrect page derivation is made.'),
16:('grounded_qualified_visibility','Kobe card, multiple card lots, memorabilia and Duke yearbooks match the current screenshot. Do not clearly show a man in a suit is a visibility qualification, not an unconditional no-suit fact. Tiny clothing details remain task-level uncertainty.'),
17:('grounded_qualified_visibility','Current JMU team photos, card lot, Globetrotters program and Wii bundle match the nouns. Tiny team-photo clothing is not resolved, and the candidate explicitly says do not clearly show, not no person exists.'),
18:('grounded_page3_end_uncertainty_and_point','Current page-3 highlight/bottom items support the page-end statement. It withholds clothing absence/minimum certainty. Native (638,679) maps to (816.64,488.88), inside the current page-4 button; this is not the old incorrectly alleged gap.'),
19:('grounded_page4_range','Current header reads 37 - 48 of 50 listings after page-4 navigation. Future scrolling is an intent.'),
20:('grounded_qualified_visibility','Current frame contains NBA card boxes and sterling-silver pendant. The text does not clearly show qualifies printed/thumbnail details and does not assert exhaustive person absence.'),
21:('grounded_qualified_visibility','Current wristwatch, red-jersey Nene bobblehead, SNES games and Kentucky basketball match the listed nouns. The qualified suit-visibility description is consistent with the original frame.'),
22:('grounded_page4_end_uncertainty_and_point','Current page-4 highlight, final rows and pager support reaching its end. No-suit/global minimum remain explicitly unconfirmed. Native (678,679) maps inside the visible page-5 button.'),
23:('definite_historical_self_contradiction_and_wrong_point','The only item I could identify with a man in a suit was the Pitino book contradicts the actor own earlier explicit identification of the 30-dollar green-suited Victor card, which is also independently visible in prior delivered original 3e254f. The qualifier I could identify does not cure this specific history contradiction. Final-page range, item titles/prices and qualified current visibility are grounded. Native click (559,679) maps to (715.52,488.88), within second-listing descriptive content, not any current page-1/first-page navigation control; pager buttons are near y626..665 pixels. These are separate semantic and native-target axes.'),
24:('qualified_recovery_with_wrong_native_point','This candidate explicitly cannot confirm only/cheapest and calls Pitino the best candidate identified; the lawful 5-versus-30 comparison supports that qualified preference. It does not repeat the previous only-identified assertion as fact. All 50 listing rows have appeared across actual received frame coverage, but their fine clothing/global minimum remain unproven. The current native point (715.52,488.88) is still outside the pager near y626..665, so the proposed return-to-page-1 action has a wrong target. Lawful correction text itself falsely describes the old point as the 1 button; this feedback is not taken as image truth or as proof that an action executed.'),
}

if __name__=='__main__':
    manifest=json.loads((SOURCE/'review-only-seal.json').read_bytes())
    assert sha(SOURCE/'review-only-seal.json')=='830bdd29a344c1f06474345aa028d69f00e37ec55cda9dfbacc65dc81fe96893'
    for name,expected in manifest.items():assert sha(REVIEW/name)==expected,name
    index=json.loads((REVIEW/'index.json').read_bytes());assert len(index['packets'])==24
    assert set(NOTES)==set(range(1,25))
    OUT.mkdir(exist_ok=False)
    rows=[]
    for ordinal,row in enumerate(index['packets'],1):
        packet=json.loads((REVIEW/row['file']).read_bytes())
        packet_id=packet['packet_id'];native=REVIEW/'native'/(packet_id+'.json')
        candidate=REVIEW/'candidates'/(packet_id+'.txt');history=REVIEW/'history'/(packet_id+'.txt')
        assert sha(candidate)==packet['candidate_sha256']
        kind,note=NOTES[ordinal]
        unresolved=ordinal in {5,7,11}
        definite=ordinal==23
        native_error=ordinal in {23,24}
        rows.append({'ordinal':ordinal,'packet_id':packet_id,'candidate_sha256':sha(candidate),
            'native_actor_payload_canonical_sha256':packet['native_actor_payload_canonical_sha256'],
            'source_files':{'packet':{'path':str(REVIEW/row['file']),'sha256':sha(REVIEW/row['file'])},
                'candidate':{'path':str(candidate),'sha256':sha(candidate)},
                'native_actor_input':{'path':str(native),'sha256':sha(native)},
                'full_legal_history':{'path':str(history),'sha256':sha(history)}},
            'actual_received_current_images':[x['sha256']for x in packet['actual_delivered_images']if x['role_in_actual_actor_request']=='current_received'],
            'all_relevant_actual_images_viewed_at_original_resolution':True,
            'full_legal_input_reviewed':True,'candidate_reviewed':True,
            'semantic_Mirage':True if definite else None if unresolved else False,
            'has_definite_boundary_Mirage':definite,
            'unresolved_subclaims':[kind]if unresolved else [],
            'pure_native_WAIT_excluded':False,'native_action_error':native_error,
            'native_action_error_kind':'point_outside_intended_pager'if native_error else None,
            'review_kind':kind,'independent_reason':note,
            'accepted':None,'executed':None,'official_outcome':None,
            'execution_join_performed':False,'semantic_labels_from_checker':False})
    images={p.name:sha(p)for p in sorted((REVIEW/'images').glob('*.png'))};assert len(images)==20
    summary={'status':'independent_actor_semantic_coverage_complete_pre_execution_join',
        'created_time':time.time(),'source_review_directory':str(REVIEW),
        'source_review_only_seal_sha256':sha(SOURCE/'review-only-seal.json'),
        'complete_candidates':24,'reviewed_candidates':24,'unreviewed_candidates':0,
        'unique_actual_delivered_images_viewed':20,
        'definite_boundary_Mirage_candidates':1,'definite_candidate_ordinals':[23],
        'additional_candidates_with_unresolved_subclaims':3,'unresolved_candidate_ordinals':[5,7,11],
        'no_definite_Mirage_identified_and_no_unresolved_assertion':20,
        'native_action_error_candidates':2,'native_action_error_ordinals':[23,24],
        'pure_native_WAIT_excluded':0,'all_24_individually_covered':True,
        'earlier_actual_delivery_images_reviewed_as_offline_sources_not_extra_current_model_input':True,
        'label_scope':'actor prose facts and native action parameters separately; unresolved is not no-Mirage',
        'qualified_only_I_identified_rule':'not automatically global uniqueness; c23 positive because actual earlier actor identification and delivered image directly refute it',
        'all50_coverage_scope':'all listing rows appear in actual delivered frames; this does not establish exhaustive fine clothing exclusion or global minimum',
        'source_blinding':'single reviewer; source arm known, legal input includes observer predictions and original defense feedback; not fully blind',
        'root_observer_judge_semantic_labels_read':False,'PRIVATE_task_expected_labels_read':False,
        'execution_join_performed':False,'accepted_and_executed_counts':None,'official_outcome_read':False,
        'trajectory_has_definite_candidate_Mirage':True,'complete_task_success_claim':False,
        'defense_effect_or_trigger_rate_reduction_claim':False,'model_GUI_new_calls':0,
        'terminal_completeness_and_service_structure_are_separate_root_audits':True}
    for name,value in [('labels.json',rows),('summary.json',summary),('images-viewed.json',images)]:
        with(OUT/name).open('x',encoding='utf8')as f:json.dump(value,f,ensure_ascii=False,indent=2)
    report='''# 单辅助首轨：24个actor候选独立语义审查

24/24候选与20张原始1280×720实际交付图已覆盖，完整合法actor输入（含真实observer包与原防御反馈）按重复内容去重阅读，原始输入文件逐SHA绑定。仅使用review-only投影；没有读取root的observer/judge语义标签、PRIVATE预期标签、官方得分或额外执行join。合法历史仍透露观察包和先前反馈，本审查不是完全盲法，且只有一名独立审查者。

确定的候选Mirage为第23条。它说“唯一我能识别到穿西装男子的商品”是5美元Pitino书；但其合法历史第10条已经明确识别30美元Victor卡中的西装男子，且原始3e254f图确能看到绿色西装。因此这不是把“I identified”一律解释成全局唯一，而是其自述识别历史被同轨先前实际输入和自己的文字直接反驳。第24条改为不能确认唯一或最便宜、称为自己识别到的最好候选，不重复该确定历史错误；后续修正不抹去第23条曾经发生。

第5、7、11条有未决的绝对服装缺失/页内排除子断言，原始小卡或杂志缩略图不足以穷尽判定；没有虚构一个西装反例，也没有把未知计作无Mirage。第13条只说当前Bucknell文件夹图片里没有西装男子：原图可辨的是文件夹与小配件，并非泛指全页/全站。其余“don't clearly show”“I cannot confirm”按可见性或明确保留的不确定性处理，不自动当作确定缺失或全局最低价声明。所有50个listing行确已出现在接收图像覆盖中，但这不等于逐张细小衣着内容都已被可靠核实。

第23与24条还有独立原生动作目标错误：1000标度的(559,679)映射到原图(715.52,488.88)，落在第二商品文字附近；当前分页控件在y约626..665像素，点不在其中。第24条输入内的原checker反馈却说该点是“1”按钮；那是输入中一个错误反馈断言，不能替代像素。两条动作是否接受或执行待seal后由root关联，当前不推断。第18条(638,679)映射到原第3页图内真实“4”按钮，不是空隙。

汇总：1个确定候选Mirage，另3个候选有未决子断言，2个独立原生点选目标错误（与Mirage轴重叠），0个纯native WAIT。这里没有轨迹完成、任务得分、主核验总体准确率、辅助有效或触发率下降的结论。该轨技术终局与额外执行/官方结果须另审计。本文件与labels在额外execution join之前封存。
'''
    with(OUT/'brief.zh.md').open('x',encoding='utf8')as f:f.write(report)
    with(OUT/'reviewer-source.py').open('xb')as f:f.write(Path(__file__).read_bytes())
    mapping={p.name:sha(p)for p in sorted(OUT.iterdir())if p.is_file()}
    with(OUT/'seal.json').open('x',encoding='utf8')as f:json.dump(mapping,f,indent=2)
    print(json.dumps({'output':str(OUT),'summary_sha256':sha(OUT/'summary.json'),'labels_sha256':sha(OUT/'labels.json'),'seal_sha256':sha(OUT/'seal.json'),'reviewed_candidates':24,'definite':1,'additional_unresolved':3,'native_action_errors':2}))
