"""Seal root image-first review of every completed new development reply."""
import hashlib
import json
from pathlib import Path
import time

HERE=Path(__file__).resolve().parent
COLLECTION=HERE/'terminal-collection-1794216982794761100'
ROOT=COLLECTION/'original/worker'
AUDIT=HERE/'terminal-audit-1794217134123770200/receipt.json'
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
read=lambda path:json.loads(Path(path).read_bytes())


def save(path,value):
    with path.open('x',encoding='utf8')as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')


assert read(AUDIT)['passed']
out=HERE/'semantic-review-01';assert not out.exists();out.mkdir()
aux_findings={
 'S01-portrait':('valid','The complete photograph visibly contains a person in dark uniform, a cap and glasses; ribbons and US flag are visible. Open record and Sort boxes localize the controls. The selected bounded observations are broadly grounded; not an exhaustive or universally correct reading.'),
 'S02-pagination':('rejected','Raw text reads25-36 of72 and12 per page but exceeds180 summary characters and160 limitation characters. The pagination box omits part of the advertised controls. Speculative clipping/cropping limitation is not established by this complete readable fixture. The entire rejected reading was unavailable downstream.'),
 'S03-form':('rejected','Raw output sees the blue-bordered Keyword field and placeholder. Its focus-state inference is not verified OS focus; invisible input-history limitations are not localized visibility deficits. Summary exceeds180. No rejected reading was delivered to the main model.'),
 'S04-footer':('rejected','Raw output recognizes a coherent footer and Back to top. The response is overlong, summarizes broad sections and speculates about the page purpose. No formal readiness gate or GUI recovery was tested; rejected evidence is not delivered.'),
 'S05-loading':('valid','Spinner and explicit Loading archive records.../Please wait are visible. This supports a local explicit-loading appearance, not network state, guaranteed completion or freshness. Text box spans two lines. Format validity is not a semantic-perfect label.'),
 'S06-blank':('rejected','Raw output correctly calls the complete image blank/white but repeats that description until summary length720; strict180 limit rejects it. Blank alone establishes neither loading nor zero results. No raw invalid reading was delivered.'),
 'S07-no-results':('rejected','Literal0 results is present, but summary and descriptions exceed original limits. Clear search box[68,272,272,368] is vertically over results/message text, not the visible button at roughly normalized65..277,489..575. It also predicts reset/default-search behavior from appearance. Entire reading remains unavailable.')
}
aux=[]
for name,(status,finding)in aux_findings.items():
    target=ROOT/'auxiliary'/name;packet=read(target/'packet.json');raw=(target/'raw-output.txt').read_text(encoding='utf8');reading=json.loads(raw)
    valid=packet['reading']is not None
    assert valid==(status=='valid')
    aux.append({'case':name,'raw_output_sha256':sha(target/'raw-output.txt'),'image_sha256':sha(target/'original.png'),
                'format_contract_valid':valid,'raw_summary_characters':len(reading['frame']['summary']),
                'review':finding,'semantic_pass':None,'reading_delivered_to_main':valid,
                'all_native_fields_reviewed_including_rejected_output':True})

actor_findings={
 'A01':{'definite_candidate_semantic_Mirage':False,'unresolved_subclaims':[],
        'review':'Both actors already describe the visible person correctly and propose the same Open record point468,714 inside the button. This is not a correction attributable to the auxiliary.'},
 'A02':{'definite_candidate_semantic_Mirage':True,'unresolved_subclaims':[],
        'review':'Both assert page3 of4, although the image literally states72 total records and12 per page, requiring6. Page3 is supported; total4 is false. Baseline point593,775 is in4; auxiliary-condition point654,774 is in next>. Both proposed targets are physically valid. Auxiliary reading is unavailable here, so this is not a test of valid pagination-reading benefit.'},
 'A03':{'definite_candidate_semantic_Mirage':None,'unresolved_subclaims':['Actual OS focus is not supplied or proven by the decorative blue border, earlier plan or issued click.'],
        'review':'Both assert focus and propose typing brass. The visible placeholder remains Enter a keyword. No actual typing/GUI is executed; the focus assertion cannot be independently confirmed or labeled definitely false from this static fixture.'},
 'A04':{'definite_candidate_semantic_Mirage':None,'unresolved_subclaims':['Exact current scroll offset and offscreen record location are not executed browser state.'],
        'separate_native_prose_direction_conflict':True,
        'review':'Both say scroll UP and emit native direction DOWN. The readable footer is visible, with text directing navigation above. Record this as proposed native-direction inconsistency,0 executed actions; do not automatically turn the prose/JSON mismatch into semantic Mirage or claim recovery.'}
}
actors=[]
for target in sorted((ROOT/'actors').iterdir()):
    case,condition=target.name.split('-',1);row=dict(actor_findings[case])
    row.update(case=case,condition=condition,raw_output_sha256=sha(target/'raw-output.txt'),
               full_source_file_sha256=read(target/'source-binding.json')['source_file_sha256'],
               actual_GUI_action_executed=False,trajectory_any_Mirage=None)
    actors.append(row)

judge_findings={
 'J01':('Both correctly contradict the false no-person statement while locating the independently valid Open record button. Both had already detected the person; no auxiliary-only rescue. This is a constructed negative candidate, not a naturally generated actor error.',False),
 'J02':('Both support the bounded visible dark jacket/hat description and correctly classify the second clause as future intent. No global absence, uniqueness or completed execution was asserted.',False),
 'J03':('Both support the normal Sort click and extract no invented GUI fact. This new simple fixture does not repair or erase the preserved false block on an older native source.',False),
 'J04':('Both falsely support exactly4 total pages, confusing displayed shortcuts1-4 with total pages despite72/12=6. The auxiliary-condition judge explicitly computes6 and then reinterprets the candidate total claim as a count of visible buttons. Its evidence is internally contradictory. The proposed page4 point is correct and is a separate action axis. Auxiliary is unavailable, not valid pagination evidence.',True),
 'J05':('Both preserve future page4 intent without inventing completed navigation, and locate the correct page4 control. No factual exact-total claim is present.',False),
 'J06':('Both withhold support for already typed brass, but label it current gui_fact and say contradicted using the current placeholder. Legal history contains a plan and an issued click, no completed typing. Present emptiness alone does not logically refute past typing; the proper bounded conclusion is unsupported historical execution, not a proof it never happened. Reasons and temporal classification remain defective.',True),
 'J07':('Both allow clicking the visible Keyword input, without inventing an already-typed candidate claim. They call the blue border a focus outline; that appearance does not certify OS focus or past execution. Do not overcount this terminology as a definite focus falsehood.',False),
 'J08':('Both support the visible Back to top point despite the task target being offscreen. The condition with auxiliary explicitly notes the reading is unavailable. This is an isolated post verification control; original readiness and full GUI recovery remain untested.',False),
 'J09':('Both identify native pure WAIT and support waiting from the visible loading cue. Pure WAIT is excluded under the user rule regardless of acknowledges_visual_deficit=false. No network result or task completion is proven.',False),
 'J10':('Both correctly find blank insufficient for definite0 results/no matching records and STOP. The baseline coarse claim includes native stop JSON as a quoted source; format-valid does not imply ideal claim segmentation. Neither confuses blank with explicit loading or zero results in its main conclusion.',False),
 'J11':('Both support the current explicitly displayed0 results and correctly locate Clear search. This scoped current-search claim is not global absence, and the button has not actually been executed. Auxiliary is unavailable on this scene.',False)
}
judges=[]
for target in sorted((ROOT/'judges').iterdir()):
    request=read(target/'request.json');reply=json.loads((target/'raw-output.txt').read_text(encoding='utf8'))
    finding,defect=judge_findings[request['case']]
    judges.append({'request':target.name,'case':request['case'],'condition':request['condition'],
                   'candidate_sha256':hashlib.sha256(request['candidate'].encode()).hexdigest(),
                   'raw_output_sha256':sha(target/'raw-output.txt'),'full_request_sha256':sha(target/'request.json'),
                   'pure_native_WAIT_excluded':request['case']=='J09',
                   'semantic_defect_identified':defect,'review':finding,'semantic_pass':None,
                   'full_claims_action_reason_evidence_and_flags_reviewed':True})
assert len(aux)==7 and len(actors)==8 and len(judges)==22
review={'schema':'balanced16-source-first-complete-development-review-v1','time':time.time(),
 'reviewer':'root; one reviewer, also source author, not independent human/blind',
 'source_expectations_sealed_before_generation':{'path':str(HERE/'PRIVATE-source-first-review.json'),'sha256':sha(HERE/'PRIVATE-source-first-review.json')},
 'all_seven_complete_original_images_viewed':True,'all37_complete_original_replies_reviewed':True,
 'technical_audit':{'path':str(AUDIT),'sha256':sha(AUDIT)},'auxiliary':aux,'actors':actors,'judges':judges,
 'aggregate':{'actual_replies':37,'auxiliary_contract_valid':2,'auxiliary_contract_rejected':5,
              'paired_judge_conditions_format_valid':22,'constructed_actor_count_errors_both_conditions':True,
              'constructed_exact_total_false_support_both_conditions':True,
              'past_typing_reason_and_temporal_classification_defects_both_conditions':True,
              'native_prose_UP_JSON_DOWN_both_actor_conditions':True,'pure_WAIT_judge_conditions_excluded':2,
              'new_GUI_actions':0,'new_official_scores':0,'trajectory_Mirage_reduction':None,
              'efficacy_established':False},
 'labels_not_sent_to_model_or_used_to_rewrite_outputs':True,
 'not_native_benchmark_trajectories_not_random_not_fully_blind_no_semantic_accuracy_or_model_ranking':True,
 'no_completed_failed_controls_to_be_rerun':True,'goal':'active'}
save(out/'review.json',review)
report='''# 单图平衡证据预检：完整结果与限制

新批次已经终局，7辅助＋8主actor＋22主核验＝37自然EOS，0格式重试，0GUI／官方评分／付费调用。完整108源码、1042原文件、实际输入张量与输出、430事件链及严格Controller回放已另行审计；原文件数以技术回执为准。

辅助仅2／7满足原契约，另5份因长度等原约束整包不可用，没有剪短、编辑、重试或将其隐藏传给主模型。人物图与明确加载图的有效读数提供了有界视觉描述；分页、表单、页脚、空白和无结果图仍不能稳定交付。无结果图的原始回复还将Clear search框定位到上方文字区，说明格式修复不能替代读图正确性。

11组核验对照均满足格式／来源契约，不能称22语义通过。人物存在、正常Sort、page4未来意图、Keyword正常点击、页脚Back to top、明确加载WAIT、blank不能证明0results、明确0results等新控制两条件本来都能处理；不是辅助带来的新增修复。

分页反例两条件都错误支持“总共4页”；有辅助条件的核验甚至先写72÷12＝6，再把候选“总页数”改解释成四个可见快捷按钮。两actor也都生成page3of4。该场景辅助整包不可用，不能评价有效分页读数的收益。历史输入反例两条件都未放行已输入的断言，但把历史执行当当前gui_fact并以当前空输入框作过强反证，时间与来源推断仍有缺陷。两actor仍说UP却输出DOWN，仅是未执行的原生方向冲突。

这7张图是完整1280×720离线构造开发源，非独立原生任务、非随机、作者与审查者同人；37回复均完整审查。没有trajectory-any Mirage降幅，没有GUI成功与防御有效结论。完整原预算、严格validator、主历史、输入精度和证据原件保持；完成失败控制不得重跑。
'''
report=report.replace('1042原文件',str(read(AUDIT)['all_original_files_verified'])+'原文件')
with(out/'单图平衡证据预检完整审查-20261109.md').open('x',encoding='utf8',newline='\n')as stream:stream.write(report)
save(out/'seal.json',{p.name:sha(p)for p in out.iterdir()if p.is_file()})
print(json.dumps({'review':str(out/'review.json'),'sha256':sha(out/'review.json'),'covered_replies':37,'efficacy_established':False},ensure_ascii=False))
