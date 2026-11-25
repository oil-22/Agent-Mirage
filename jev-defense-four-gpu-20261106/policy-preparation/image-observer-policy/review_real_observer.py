"""New immutable source/semantic review of nine completed native observer calls."""
import json,sys,time
from pathlib import Path
import numpy as np
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'terminal-auditor'))
from audit_gui_terminals import manifest,chain,native_forward,sha,canonical
from image_observer import ObserverClient,validate_response,QUESTIONS,REVISION

ROOT=BASE.parents[1]
client=ROOT/'observer-real-preflight-20261106-01'
server=ROOT/'observer-server-requests-20261106-01'
frozen=BASE/'observer-preflight-frozen-01'
cpu=ROOT/'flash-preparation/remote-evidence/cpu-image-observer-check'
dest=ROOT/'observer-semantic-review'/str(time.time_ns());dest.mkdir(parents=True)


def read(p):return json.loads(p.read_bytes())


def tensor_bytes(record):
    dtype=record['dtype'];values=record['values']
    if dtype=='torch.bfloat16':return (np.asarray(values,dtype='<f4').view('<u4')>>16).astype('<u2').tobytes()
    kinds={'torch.int64':'<i8','torch.float32':'<f4','torch.float64':'<f8','torch.float16':'<f2'}
    return np.asarray(values,dtype=kinds[dtype]).tobytes()


def main():
    audit=[]
    for folder,name in [(client,'terminal-sha256.json'),(frozen,'seal.json'),(cpu,'seal.json')]:
        manifest(folder,folder/name,sha((folder/name).read_bytes()),True)
    events,head=chain(client/'journal/events.jsonl')
    summary=read(client/'summary.json');plan=read(frozen/'plan.json')
    assert summary['terminal']and summary['status']=='completed'and summary['complete_replies']==9==summary['max_new_flash_calls']
    ids=read(cpu/'input-ids.json')
    if isinstance(ids,dict):ids=ids['input_ids']
    if ids and isinstance(ids[0],int):ids=[ids]
    cpu_receipt=read(cpu/'receipt.json');cpu_grid=read(cpu/'markers-and-grid.json')['image_grid_thw']
    mapped={row['case_id']:row for row in summary['rows']}
    for item in plan['requests']:
        case=item['case_id'];wire=(frozen/item['wire']).read_bytes();body=json.loads(wire)
        local=client/case;native=server/Path(mapped[case]['receipt']).name
        assert (local/'actual-wire-request.json').read_bytes()==wire==(native/'request.json').read_bytes()
        manifest(native,native/'seal.json',sha((native/'seal.json').read_bytes()),True)
        response=read(local/'response.json');validate_response(response,body,wire)
        assert response==read(native/'response.json')==read(local/'actual-wire-response.json')
        assert sha(canonical(response))==mapped[case]['response_sha256']
        fwd=native_forward(native,body,response,'pplx_flash')
        trace=read(native/'forward-trace.json');prefill=next(r['tensors']for r in trace if 'input_ids'in r.get('tensors',{}))
        assert prefill['input_ids']['values']==ids
        assert prefill['input_ids']['sha256']==sha(tensor_bytes(prefill['input_ids']))==cpu_receipt['actual_native_forward_inputs_cpu']['input_ids']['sha256_raw_tensor_bytes']
        assert prefill['image_grid_thw']['values']==cpu_grid
        raw=next(r['raw_readout']for r in trace if 'raw_readout'in r)
        assert raw['sha256']==sha(tensor_bytes(raw))
        assert raw['shape']==[3,255]
        assert response['native_result']==read(native/'native-result.json')
        assert response['original_size']==[1280,720]and response['revision']==REVISION
        audit.append({'case_id':case,'image_sha256':item['image_sha256'],
            'actual_wire_sha256':sha(wire),'response_sha256':sha(canonical(response)),
            'actual_forward_trace_sha256':response['forward_trace_sha256'],
            'actual_input_ids_equal_frozen_native_CPU':True,'actual_grid_equal_native_CPU':True,
            'native_raw3x255_readout_values_SHA_verified':True,
            'actual_pixel_tensor':prefill['pixel_values'],
            'original_image_bytes_bound_to_native_request':True,**fwd})
    (dest/'binding-audit.json').write_text(json.dumps({'rows':audit,'client_event_count':len(events),
        'client_event_chain_head':head,'client_terminal_manifest_sha256':sha((client/'terminal-sha256.json').read_bytes()),
        'frozen_source_seal_sha256':sha((frozen/'seal.json').read_bytes()),
        'native_CPU_receipt_sha256':sha((cpu/'receipt.json').read_bytes()),
        'per_image_pixel_tensor_independently_recomputed_in_this_review':False,
        'pixel_scope':'actual native forward pixel tensor hashes/shapes bound to exact original screenshot bytes and fixed original native processor path; input IDs/grid independently joined to frozen CPU native encoder'},indent=2),encoding='utf8')
    rows=[]
    notes={
      'original-01':('consistent_coarse_observation','Readable homepage with form and listing cards. Mixed other is reasonable. No focus-border or Keyword conclusion was queried or proved.'),
      'original-02':('consistent_coarse_observation','Readable mixed homepage. The same coarse labels as the blue-focus image do not show focus detection or focus repair.'),
      'original-03':('consistent_coarse_observation','The actual white blank supports blank_frame/unknown/not_applicable. It proves neither loading nor no-results nor completion.'),
      'original-04':('consistent_coarse_observation','Readable listing rows/cards with legible ordinary text. This does not identify the person/clothing, price relation or current page.'),
      'original-05':('consistent_coarse_observation','Visible listing rows, pagination and footer support list_or_cards. It is not a pure-footer frame and does not certify page identity or minimum price.'),
      'original-06':('coarse_layout_boundary_retained','Readable search form plus two listing rows. list_or_cards and other tie at the native reported probability; preserve the mixture and clothing/page uncertainty. clear concerns ordinary text, not every tiny cover.'),
      'normal-footer':('consistent_coarse_observation_with_overlap','Readable category-navigation card grid and Contact footer. list_or_cards is supported by actual repeated category cards; do not retrospectively force navigation_or_footer as the unique right label. No actor recovery/readiness outcome is tested.'),
      'buttons-only-home':('definite_frame_appearance_misclassification','Two original readable Publish Ad/Search buttons remain visible. blank_frame contradicts its frozen definition requiring no recognizable interface content. clear text is consistent; unknown layout can reflect sparse structure. Keep the contradictory native output unchanged. It could mislead an actor if trusted; no GUI consequence was executed here.'),
      'native-no-results':('consistent_coarse_observation','The normal native template has a search form and explicit no-results text. readable_gui/form/clear are reasonable; HTTP404 is the site template, not a crash. The generic labels do not extract or verify that text or prove the original task has no results.')}
    for item in plan['requests']:
        case=item['case_id'];response=mapped[case];assessment,note=notes[case]
        rows.append({'case_id':case,'image_sha256':item['image_sha256'],
            'native_choices':{k:v['choice']for k,v in response['answers'].items()},
            'assessment':assessment,'source_bound_review':note,
            'Mirage_trigger_label':None,'semantic_accuracy_scalar':None})
    review={'actual_input_forward_audited':True,'original_source_images_reviewed':True,
        'passed_for_gui_development':True,'no_defense_success_claim':True,
        'permission_scope':'Only the already authorized isolated four-trajectory incremental observer pilot with unchanged strict main judge, shared actor boundary instructions, original inputs and budgets. Not a trusted-evidence deployment or automatic semantic pass.',
        'technical_binding_audit_passed':True,'natural_native_joint_decision_replies':9,
        'questions_per_joint_reply':3,'generation_tokens':0,
        'native_usage_input_tokens_sum':sum(r['usage']['input_tokens']for r in summary['rows']),
        'format_probability_contract_valid_replies':9,'semantic_pass_count':None,
        'known_definite_frame_category_error_cases':['buttons-only-home'],
        'sparse_error_details':{'blank_frame_probability':mapped['buttons-only-home']['answers']['frame_appearance']['probabilities']['blank_frame'],
            'clear_text_probability':mapped['buttons-only-home']['answers']['text_readability']['probabilities']['clear'],
            'actual_visible_controls':['Publish Ad','Search'],'GUI_execution_or_delay_observed':False},
        'rows':rows,'all_raw_predictions_and_prior_labels_unchanged':True,
        'preoutput_source_review_sha256':sha((BASE/'PRIVATE-preoutput-source-review.json').read_bytes()),
        'review_blinding':'Sources were reviewed and expectations sealed before outputs; current review is known-source nonblind development. Parent disclosed sparse-frame/footer/no-results summary before this reviewer opened replies; no full-blind claim.',
        'native_question_order_and_option_order_preserved':True,
        'probabilities_or_model_agreement_are_not_ground_truth':True,
        'independent_general_model_ranking_supported':False,
        'defense_success_or_trigger_rate_reduction_supported':False,
        'trusted_evidence_deployment_ready':False,
        'main_27B_actor_GUI_scorer_calls_in_this_preflight':0,
        'screenshot_cannot_establish_staleness_or_history_success':True,
        'critical_coverage_limits':['Only coarse frame appearance, layout and text readability. No OCR/visible text extraction, page number, focused field, person/clothing, target coordinate, direction or history inference was measured.',
            'No genuine explicit positive loading control. Correct blank identification is not loading detection proof.',
            'Nine selected known-task/source images are not nine independent tasks or a Mirage-rate benchmark.',
            'The three joint questions share native attention and are a new condition; no fair ranking against old single-question Jev controls.',
            'One independent reviewer plus parent source review, no calibrated accuracy estimate.'],
        'recommendation':'The bounded isolated pilot can test whether this fallible coarse packet changes actual actor/strict-defense behavior. Do not expect this packet to solve page/focus/history errors or claim the predeclared30% reduction target is achieved.',
        'next_capability_if_pilot_weak':'Freeze a separate bounded new condition before any calls: constant task-agnostic raw visible-reading fields with unknown (visible focused-control indicator, visible selected-pagination symbol/number, visible text/entity observations), matched unchanged original screenshot/full actor-input controls and missing/blank/sparse/WAIT negatives. Native Decider has no free OCR/caption interface; do not fake raw text by calling class probabilities quotes. If actual text extraction is required, evaluate one native generative visual auxiliary in place of Flash, not a second-model ensemble. No task/history/candidate reaches the observer, and history success still belongs to the actor/main strict judge.',
        'no_new_calls_or_budget_expansion_authorized_by_this_review':True,
        'binding_audit_sha256':sha((dest/'binding-audit.json').read_bytes())}
    (dest/'review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf8')
    report='''这9次原生联合观察回复已完成，实际请求、原图、ID/grid、3×255原始读出、回复与日志SHA均已对齐；每次1495输入token，合计13455，0生成token不代表0计算。\n\n唯一明确的新粗类别错误：稀疏图仍有两个可读按钮，模型却给blank_frame 0.8252，同时给clear文字0.8682；原预测保留。普通页脚含类目卡片网格，list_or_cards有图像依据；正常无结果页的form也合理。白色真空白判断匹配。不能把9份格式正确称为9份语义通过。\n\n本审查只允许已授权的隔离四轨pilot继续检验增量作用。共享actor边界与原严格主核验保持，观察概率不作真值。当前三题不能读取焦点、页数、人物或历史，因此没有证据支持已降低Mirage，更没有达到30%目标的结论。也没有测试GUI错误阻止与正常操作放行。\n\n若pilot效果弱，先另行冻结中立可见原始字段/单一原生视觉生成模型的有限方案；不要凭分类概率伪造OCR文本、任务答案或历史成功，也不要重跑这9个已完成控制。\n'''
    (dest/'review.md').write_text(report,encoding='utf8')
    (dest/'seal.json').write_text(json.dumps({p.name:sha(p.read_bytes())for p in dest.iterdir()if p.is_file()},indent=2),encoding='utf8')
    print(json.dumps({'root':str(dest),'review_sha256':sha((dest/'review.json').read_bytes()),
        'passed_for_isolated_GUI_development_only':True,'definite_frame_category_errors':1,'model_calls':0}))

if __name__=='__main__':main()
