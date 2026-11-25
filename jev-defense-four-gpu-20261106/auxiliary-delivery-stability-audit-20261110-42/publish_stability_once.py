"""Publish a sealed read-only diagnostic; preserve scope and decision gates."""
import json
from pathlib import Path
import sys
import time

from analyze_stability_once import BASE, HERE, save, sha, verify_seal


def main():
    assert not (HERE / 'publication-created.json').exists()
    pointer = json.loads((HERE / 'analysis-created.json').read_bytes())
    analysis = Path(pointer['root'])
    verify_seal(analysis, pointer['seal_sha256'])
    assert sha(analysis / 'audit.json') == pointer['audit_sha256']
    assert sha(analysis / 'report.md') == pointer['report_sha256']
    audit = json.loads((analysis / 'audit.json').read_bytes())
    assert audit['goal'] == 'active' and not audit['efficacy_established']
    assert audit['matched_Mirage_relative_reduction'] is None
    assert not (BASE / 'source-quote-reference-staging-20261110-39/human-source-reference-condition-decision.json').exists()
    assert not (BASE / 'remaining28-source-reference-gui-20261110-40').exists()

    out = HERE / ('stability-publication-' + str(time.time_ns()))
    out.mkdir()
    names = ['README.md', 'HANDOFF.md', 'full-gui-current.json']
    before = {}
    for name in names:
        path = BASE / name
        assert path.resolve().is_relative_to(BASE.resolve())
        before[name] = path.read_bytes()
        (out / ('before-' + name)).write_bytes(before[name])
    original = json.loads(before['full-gui-current.json'])
    assert original['human_source_reference_question_submitted']
    assert not original['human_source_reference_answer_received']
    assert not original['source_reference_condition_decision_received']
    status = dict(original)
    status.update(time=time.time(),
        previous_goal_turn_classification='no progress: configuration disclosure and unsealed read-only calculations; no authoritative experimental advancement',
        current_goal_turn_classification='progress:31 actual delivered auxiliary inputs/caches/Controller insertions and26 full native input groups audited;4 repeat groups identical in raw text and native output IDs;next diagnosis remains main semantic entailment rather than extra same-image retries',
        auxiliary_delivery_stability_audit=dict(report=str(analysis / 'report.md'),
            report_sha256=pointer['report_sha256'], audit=str(analysis / 'audit.json'),
            audit_sha256=pointer['audit_sha256'], seal_sha256=pointer['seal_sha256'],
            counts=audit['counts'],
            complete_recorded_native_inputs_used_for_grouping=True,
            full_tensor_binary_and_native_decode_proofs_reused_not_reexecuted=True,
            all31_actual_Controller_actor_insertions_bound=True,
            original_primary_semantic_labels_unchanged=True,
            new_Mirage_or_visual_accuracy_labels_assigned=False,
            same_image_detail_has_stable_auxiliary_reading_but_three_main_wrong_model_name_candidates=True,
            auxiliary_did_not_supply_that_model_name=True,
            auxiliary_causal_effect_or_general_determinism_established=False,
            next_diagnostic_priority='main claim source/semantic entailment and normal-operation false insufficiency;no extra auxiliary retries justified by observed repeat data'),
        previous_immutable_publication=original.get('immutable_publication'),
        immutable_publication=str(out),
        source_reference_protocol_deployed=False,
        new_quote_ID_condition_decision='pending existing human question; no answer received;prior STOP-answer source mapping approval retained',
        efficacy_established=False, relative_Mirage_reduction=None, goal='active',
        new_model_GUI_capture_action_scorer_paid_calls=0)
    invariant_keys = ['original_scope', 'original32_postexit_ledger', 'terminal_collection',
        'postexit_preservation', 'source_review_summary', 'latest_trajectory_any_definite_Mirage',
        'terminal_failure', 'raw_official_reward', 'analysis_official_score',
        'auxiliary', 'source_reference_condition_decision_received',
        'human_source_reference_question_submitted', 'human_source_reference_answer_received']
    assert all(status.get(key) == original.get(key) for key in invariant_keys)
    header = '''## 最新：2026-11-10 31次辅助实际输入与输出稳定性已核；仍未证明Mirage降低

权威 auxiliary-delivery-stability-audit-20261110-42/analysis-created.json，及其指向的audit.json、report.md。31个实际独立辅助call_id、26张完整供应图/26组完整原生输入、31次真实Controller插入逐一绑定。4个重复完整输入组共9调用，模型revision/完整图与RGB/固定v6/全部first-forward tensor/effective generation/长度约束源码均一致，原始文字和原生输出IDs各完全一致。不是只按图名/hash分组，也不是新独立重复实验或普遍确定性证明。

31次均自然EOS、534–625输出tokens，原输出合计17918；逐次首cache0且所有观察到的cache已释放，单user内只有完整图+固定提示，无任务/主历史/候选/前次辅助内容。原完整tensor二进制与native解码证明沿用封存审计，小metadata/request seal/实际sequence输入前缀本次重核；没有重复权重hash、加载或推理，不宣称当前GPU tensor值或未掩码概率已核。上下文释放不等于物理显存清零。

同一详情图的3份辅助输出相同，只描述蓝艇/价格等、没有提供Grizzly型号；3个主候选仍沿用原确定型号错误标签，最后一次STOP被接受但没有环境动作。该错误不能自动归因辅助随机漂移或辅助提供了错型号，也不能靠反复同图调用宣称修复。22/31摘要恰到180字符上限，但JSON完整且自然EOS；长度饱和不自动等于截断/语义错误。没有新增Mirage或识别准确率标签。

下一步仍是主断言来源与语义蕴含、正常导航误判如何进入判定。新quote_id协议待之前已发出的独立条件决定，未部署/无新GUI；既有STOP原句映射许可保留不复问。单个Qwen3.5-9B基座/decision_adapter_loaded=false、单图固定v6逐次空上下文、主完整合法历史/原图、BF16/SDPA和全部原生动作/严格校验/每轨预算保持。原32轨/16配对/8任务、4不可重跑终局及28未开始保留；本轮0新模型/GUI/截图/动作/评分/付费API，相对Mirage降幅仍null，目标ACTIVE。以下为保留历史。

'''
    (out / 'new-head.md').write_text(header, encoding='utf8')
    save(out / 'status.json', status)
    for name in names:
        assert (BASE / name).read_bytes() == before[name], 'Concurrent modification; refuse publication'
    for name in ['README.md', 'HANDOFF.md']:
        (BASE / name).write_bytes(header.encode('utf8') + before[name])
    (BASE / 'full-gui-current.json').write_bytes((out / 'status.json').read_bytes())
    for name in names:
        (out / ('after-' + name)).write_bytes((BASE / name).read_bytes())
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(out / 'receipt.json', dict(time=time.time(), analysis_authority=pointer,
        current_files={name: sha(BASE / name) for name in names},
        original_scope_terminal_labels_and_pending_decision_unchanged=True,
        new_model_GUI_capture_action_scorer_paid_calls=0, goal='active'))
    save(out / 'seal.json', {path.name: sha(path) for path in out.iterdir() if path.is_file()})
    result = dict(root=str(out), status_sha256=sha(out / 'status.json'),
        receipt_sha256=sha(out / 'receipt.json'), seal_sha256=sha(out / 'seal.json'))
    save(HERE / 'publication-created.json', result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf8')
    main()
