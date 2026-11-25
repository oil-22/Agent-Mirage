"""Source-first human semantic review, kept separate from format acceptance."""
from pathlib import Path
import json
import time
from ops import HERE,BASE,save,sha

def main():
    collection=HERE/'terminal-collection/1794202434006469900';original=collection/'original'
    audit=json.loads((collection/'audit.json').read_bytes())
    assert audit['terminal_files_full_SHA_verified']==177 and audit['all_inference_processes_exited']
    summary=json.loads((original/'worker/summary.json').read_bytes());rows=summary['auxiliary']
    notes=[
        ('B01','rejected','References t5/t6 do not exist. Visible lamp query and 1-12 of907 reading are supported; the packet is withheld wholesale.'),
        ('B02','rejected','Pagination element references absent t5/t6 and unrelated car-name/price spans. Coherent footer summary itself is supported, not a readiness/target proof.'),
        ('B03','format_valid_semantic_relation_wrong','Apply points by text_refs to OsClass; Subscribe points to bicycle. Those texts are not ON those controls. Format-valid is not semantically valid.'),
        ('B04','format_valid_semantic_relation_wrong','Apply/Subscribe/My account/Logout link to unrelated OsClass/query/price spans. Visible query/prices themselves mostly match, but association claims are false.'),
        ('B05','format_valid_semantic_relation_wrong','Apply links to OsClass; Subscribe links to15.00 $. Separate prices match visible cards; association claims are false.'),
        ('B06','rejected','Nonexistent t5/t6 references. Summary of native no-results is supported by visible message; global absence/loading/completion is not established.'),
    ]
    out=HERE/'review-completion-01';out.mkdir(exist_ok=False)
    review={'reviewer':'root single reviewer','source_first_expectation_seal_sha256':sha(HERE/'PRIVATE-source-first-expectations-seal.json'),
        'actual_full_original_images_viewed_before_predictions':True,'labels_were_not_worker_inputs':True,
        'controls':[{'id':i,'review_scope':s,'finding':n,'source_image_sha256':sha(original/'worker/auxiliary'/i/'original.png'),
            'actual_response_sha256':sha(original/'worker/auxiliary'/i/'response.json'),
            'semantic_Mirage_trigger_label':None,'actor_feedback_or_GUI_tested':False}for i,s,n in notes],
        'format_valid':3,'format_rejected':3,'valid_packets_with_false_association_claims':3,
        'all6_natural_EOS':True,'no_2048_expansion_or_retries':True,
        'all_actual_forward_and_selected_mask_steps_UTF8_verified':True,
        'full_GUI_or_defense_efficacy_established':False,
        'next_condition':'New finite matched GUI development: retain independently boxed text/elements but require text_refs=[] at generation; original validator unchanged. Fewer associations may omit useful information. OCR/boxes/summary remain fallible.',
        'completed_control_outputs_not_rewritten_and_not_reexecuted':True}
    save(out/'review.json',review)
    receipt={'terminal_audit_sha256':sha(collection/'audit.json'),'review_sha256':sha(out/'review.json'),
        'actual_auxiliary_calls':6,'judge_actor_GUI_scorer_paid_calls':0,'format_retries':0,
        'input_tokens':sum(r['input_tokens']for r in rows),'output_tokens':sum(r['output_tokens']for r in rows),
        'summed_generation_seconds_including_instrumentation':sum(r['seconds_including_instrumentation']for r in rows),
        'not_walltime_currency_energy':True,'terminal_manifest_sha256':audit['terminal_manifest_sha256'],'event_chain':audit['chain'],
        'advance_to_GUI_development':False,'formal_GUI_release':False,'efficacy_established':False,
        'followup_GUI_development_with_references_disabled_authorized':True,
        'authorization':'User sustained goal and earlier explicit complete-GUI instruction; new restrictive relation omission disclosed, original inputs/validators/budgets retained',
        'followup_is_new_changed_condition_not_a_pass_for_this_failed_condition':True}
    save(out/'receipt.json',receipt)
    text=f'''# 辅助结构约束真实预检：语法稳定，关系错误仍在

本批6次真实辅助推理全部自然EOS，0重试；3份原契约有效、3份因不存在的文字引用拒绝。3份有效包都存在把文字关联到错误控件的问题，不能称为语义通过，更没有降低Mirage的证据。

6张新的完整原生截图已先查看并封存私有预期，未向模型提供任务、历史、候选或标签。实际CPU处理器到first-forward的IDs/pixels/grid、原始生成ID/EOS、结构mask选择、严格UTF8回转与请求回复seal已核验；177终局文件SHA、34事件链已核，worker与launcher退出。原始tensor bytes留在远端终局seal下。

|控制|结果|
|---|---|
|B01 lamp|不存在t5/t6，整包拒绝；1–12 of907本次读对|
|B02 footer|不存在t5/t6并错绑汽车文字到分页，整包拒绝|
|B03 bicycle|格式有效，但Apply→OsClass、Subscribe→bicycle错误|
|B04 guitar|格式有效，但4个控件的文字关联错误|
|B05 desk|格式有效，但Apply→OsClass、Subscribe→15美元错误|
|B06 no-results|不存在t5/t6，整包拒绝；摘要与原生无结果画面相符|

结构mask没有改原图、模型精度、原始提示或2048上限，也没有改写回复。共{receipt['input_tokens']}输入/{receipt['output_tokens']}输出token，{receipt['summed_generation_seconds_including_instrumentation']:.3f}秒为含取证的逐调用耗时之和，非墙钟/货币/能耗。0主核验/actor/GUI/scorer/付费调用。

这6个终局控制永久保留，不重跑、不用余量刷分。下一批是新的完整GUI开发条件：生成时令text_refs=[]，保留独立文字与区域，不再输出这类关联；会丢失部分关系表达能力，且OCR、方框与描述仍可错。该改变不替模型填答案，不放宽原validator，不把本批负结果改成成功。完整历史/原图/BF16/SDPA、50步、70actor/140verifier及原恢复预算保持，配对审查错误阻止与正常操作。
'''
    (HERE/'辅助结构约束真实预检-20261109.md').write_text(text,encoding='utf8')
    print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':main()
