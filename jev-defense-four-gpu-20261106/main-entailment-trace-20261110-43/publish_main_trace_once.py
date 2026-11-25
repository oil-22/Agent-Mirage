"""Publish the completed source trace without deploying a changed protocol."""
import json
from pathlib import Path
import sys
import time

from collect_main_trace_once import HERE, BASE, save, sha, verify


def main():
    assert not (HERE / 'publication-created.json').exists()
    pointer = json.loads((HERE / 'analysis-created.json').read_bytes())
    analysis = Path(pointer['root'])
    verify(analysis, pointer['seal_sha256'])
    assert sha(analysis / 'trace.json') == pointer['trace_sha256']
    assert sha(analysis / 'report.md') == pointer['report_sha256']
    trace = json.loads((analysis / 'trace.json').read_bytes())
    assert not trace['efficacy_established'] and trace['matched_Mirage_relative_reduction'] is None
    assert not (BASE / 'source-quote-reference-staging-20261110-39/human-source-reference-condition-decision.json').exists()
    assert not (BASE / 'remaining28-source-reference-gui-20261110-40').exists()
    out = HERE / ('main-trace-publication-' + str(time.time_ns()))
    out.mkdir()
    names = ['README.md', 'HANDOFF.md', 'full-gui-current.json']
    original = {}
    for name in names:
        original[name] = (BASE / name).read_bytes()
        (out / ('before-' + name)).write_bytes(original[name])
    old_status = json.loads(original['full-gui-current.json'])
    assert old_status['human_source_reference_question_submitted']
    assert not old_status['human_source_reference_answer_received']
    status = dict(old_status)
    status.update(time=time.time(),
        previous_goal_turn_classification='progress:sealed31-call auxiliary delivery/native-input/output/cache stability audit;all four repeated complete input groups identical;no new experiments',
        current_goal_turn_classification='progress:five original checker wire/native reply sources and three wrong-name claim paths bound;current auxiliary only on actor wire while complete main history retains12 past reads;semantic support failure separated from quote-source representation',
        main_semantic_support_trace=dict(trace=str(analysis / 'trace.json'), trace_sha256=pointer['trace_sha256'],
            report=str(analysis / 'report.md'), report_sha256=pointer['report_sha256'], seal_sha256=pointer['seal_sha256'],
            five_original_checker_requests_bound=True,
            original_wrong_name_source_labels_reused_unchanged=True,
            first_actor_prior_input_has_no_wrong_model_name=True,
            later_wrong_name_in_explicitly_rejected_proposal_feedback=True,
            current_auxiliary_actor_only_and12_old_readings_in_full_checker_history_proven=True,
            main_checker_already_requested_all_facts_and_grounded_navigation=True,
            original_claim_text_and_image_source_valid_but_visual_entailment_false=True,
            quote_ID_protocol_alone_will_not_repair_semantic_support=True,
            independent_completion_and_numerical_attribution_did_not_establish_model_name=True,
            no_auxiliary_causal_effect_or_repeatability_repair_claim=True),
        next_required_step='Human choice on already-submitted quote-reference wire protocol for remaining28;do not consume prospective tracks while that version/budget choice is pending;do not repeat completed controls or manufacture further audit progress',
        independent_prelaunch_diagnostics_completed=True,
        source_reference_condition_decision_received=False,
        efficacy_established=False, relative_Mirage_reduction=None, goal='active',
        new_model_GUI_capture_action_scorer_paid_calls=0,
        previous_immutable_publication=old_status.get('immutable_publication'), immutable_publication=str(out))
    invariant_keys = ['original_scope', 'original32_postexit_ledger', 'terminal_collection',
        'postexit_preservation', 'source_review_summary', 'latest_trajectory_any_definite_Mirage',
        'raw_official_reward', 'analysis_official_score', 'auxiliary', 'terminal_failure',
        'human_source_reference_question_submitted', 'human_source_reference_answer_received']
    assert all(status.get(key) == old_status.get(key) for key in invariant_keys)
    header = '''## 最新：2026-11-10 主核验错误支持与当前辅助接线已实核；来源编号不等于语义修复

权威 main-entailment-trace-20261110-43/analysis-created.json 与指向的trace.json/report.md。五份原核验0068/0079/0096/0098/0099的实际wire/payload/seal/native-call原text及既有native输入/输出证明已绑定。三个Grizzly10候选的c1都被主核验标gui_fact/supported、引用同一原图并明确称图上显示该型号；原句和图像引用存在，失败是语义支持错误。沿用原先来源标签，完整原图重新查看，未新增盲审标签；最后STOP接受但无环境动作，最低价/颜色排除的原未知保留。

首次actor完整输入文本没有Grizzly，型号首次出现在actor回复；后两次只随第26条user中明确rejected_not_executed的旧候选反馈进入输入。当前辅助没给型号，不把该词归因辅助，也不据此证明上下文强化因果。各次实际主核验消息精确等于完整actor消息只去掉本次当前辅助块，12份过去辅助读数、全部其他历史/原图/纠正逐字节保留。当前9B读数仅交actor；9B自身仍单图固定v6、逐次空上下文。此为实际接线边界，不自动等于错误原因。

真实system早已要求检查所有具体事实、区分历史报告与真值，并允许未找到目标时的有依据导航；已存在的第37候选局部误判不能靠重复旧规则称修好。最终completion0098只见任务+13原图，usable且未给型号；0099仅核数值图像来源，supported不提供型号/整体语义或任务成功证书。quote_id修复只处理来源表示，不能宣称解决这类错误；有限辅助采样的遗漏也不能强制当成反证。

首次只读取证错用了辅助raw-output.txt文件名，失败源/日志/结果封存后，在新linked02读取原native-call.json的text并与原HTTP verdict核对；原终局未改、0新推理。图像在本地导出中以SHA替换，不能称完整wirebody；完整原请求仍封存。所有原图/主历史/BF16/SDPA/原生动作/严格校验/预算保持。

下一必需步骤是此前已发出的剩余28轨quote_id输出协议条件选择；当前仍无答复，不能把自动续工作为许可，也不消耗这28轨来绕过待选版本。已有STOP原句映射许可保留不复问。独立预启动诊断已完成，不重复旧控制/审计来代替完整GUI。原32轨/16配对/8任务、4不可重跑终局及28未开始保持，相对Mirage降幅null，目标ACTIVE。本轮0新模型/GUI/截图/动作/评分/付费API。以下为保留历史。

'''
    (out / 'new-head.md').write_text(header, encoding='utf8')
    save(out / 'status.json', status)
    for name in names:
        assert (BASE / name).read_bytes() == original[name], 'Concurrent head change'
    for name in ['README.md', 'HANDOFF.md']:
        (BASE / name).write_bytes(header.encode('utf8') + original[name])
    (BASE / 'full-gui-current.json').write_bytes((out / 'status.json').read_bytes())
    for name in names:
        (out / ('after-' + name)).write_bytes((BASE / name).read_bytes())
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(out / 'receipt.json', dict(time=time.time(), trace_authority=pointer,
        current_files={name: sha(BASE / name) for name in names},
        original_scope_terminal_labels_and_pending_human_choice_unchanged=True,
        new_model_GUI_capture_action_scorer_paid_calls=0, goal='active'))
    save(out / 'seal.json', {path.name: sha(path) for path in out.iterdir() if path.is_file()})
    result = dict(root=str(out), status_sha256=sha(out / 'status.json'),
        receipt_sha256=sha(out / 'receipt.json'), seal_sha256=sha(out / 'seal.json'))
    save(HERE / 'publication-created.json', result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf8')
    main()
