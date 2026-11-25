"""Archive mutable heads, then publish the sealed downstream audit only."""
import json
from pathlib import Path
import sys
import time

from collect_four_terminal_once import HERE, BASE, save, sha
from build_companion_panel_once import seal


def main():
    assert not (HERE / 'publication-created.json').exists()
    pointer = json.loads((HERE / 'companion-panel-created.json').read_bytes())
    panelroot = Path(pointer['root'])
    seal(panelroot, pointer['seal_sha256'])
    assert sha(panelroot / 'panel.json') == pointer['panel_sha256']
    panel = json.loads((panelroot / 'panel.json').read_bytes())
    assert panel['goal'] == 'active' and not panel['efficacy_established']
    assert panel['matched_Mirage_relative_reduction'] is None
    source39 = BASE / 'source-quote-reference-staging-20261110-39'
    assert not (source39 / 'human-source-reference-condition-decision.json').exists()
    assert not (BASE / 'remaining28-source-reference-gui-20261110-40').exists()
    out = HERE / ('companion-publication-' + str(time.time_ns()))
    out.mkdir()
    heads = ['README.md', 'HANDOFF.md', 'full-gui-current.json']
    old = {}
    for name in heads:
        path = BASE / name
        assert path.resolve().is_relative_to(BASE.resolve())
        old[name] = path.read_bytes()
        (out / ('before-' + name)).write_bytes(old[name])
    status = json.loads(old['full-gui-current.json'])
    status.update(time=time.time(),
        previous_goal_turn_classification='no progress: configuration-only answer; no experimental advancement',
        current_goal_turn_classification='progress: six actual terminal event chains/all84 original candidates uniquely joined to75 acceptances and74 executions; pending11/pending17 cross-attempt first executions bound; scoped normal-pagination main-checker false insufficiency reviewed; no new model or GUI calls',
        downstream_companion_audit=dict(report=str(panelroot / 'report.md'), report_sha256=pointer['report_sha256'],
            panel=str(panelroot / 'panel.json'), panel_sha256=pointer['panel_sha256'],
            seal_sha256=pointer['seal_sha256'], totals=panel['totals'],
            source_labels_reused_unchanged_not_new_blind_review=True,
            all84_candidates_and74_environment_executions_unique=True,
            scoped_main_action_false_insufficiency_candidate='9334046de6a30e7d0ad3',
            full_pipeline_false_block_accuracy_still_unproven=True,
            track_outcomes=[{k: row[k] for k in ['run_id', 'source_negative', 'source_unknown',
                'source_positive', 'accepted', 'environment_executed', 'positive_accepted',
                'positive_environment_executed', 'trajectory_any_Mirage', 'analysis_official_score']}
                for row in panel['tracks']]),
        new_quote_ID_condition_decision='pending; prior approved decoded STOP-answer mapping is retained and is not permission for a new wire protocol',
        broad_Mirage_effect_or_false_block_improvement_established=False,
        relative_Mirage_reduction=None, goal='active',
        no_new_model_GUI_capture_action_scorer_paid_calls_in_companion_audit=True)
    header = '''## 最新：2026-11-10 四条终局执行关联已补齐；正常翻页存在主核验局部误拒，尚无防御降幅证明

权威 `four-terminal-companion-audit-20261110-41/companion-panel-1794309959999151600/panel.json` 及同目录 `report.md`。本轮重新只读核对6段实际终局/技术续跑事件链，4521事件、1668321588日志字节；84个原候选与75接受/74环境实执全部唯一对齐。原第11/17候选在新命名空间首次执行的完整请求、文本和事件SHA已衔接，修正仅看旧快照会漏记2动作的问题。未重跑任何原轨/完成控制，未重hash权重。

原来源标签保持61阴性/18未知/5阳性，不是新盲审或候选触发率。3阳性候选被接受：2执行环境动作、1为STOP；另2阳性未放行仍计已发生的Mirage。clean无辅助38候选/36实执、整轨未知；clean辅助15/12且阳性；旧帧辅助16/13和无辅助15/13均阳性。一个已接受STOP有官方1仍不抹去错误；两技术终局原始0与分析null分开。全部四轨仅同一T000任务，版本/技术中断/暴露不同，不能得公平降幅或成本结论。

新限定正常操作审查：clean无辅助第37候选仅点击可见9号页，实际点在按钮内；真实主核验也认出9号按钮，却以目标未找到/结果不相关输出insufficient，触发重新生成。该次实际system早已允许有依据的导航探索，不能靠重复规则称修复。此为主动作核验局部误判；后续点读/对齐未在此候选运行，不能断言全流水线必然成功。第38价格范围仍未知、预算终局不能仅归因本次拒绝。两打字候选的真实焦点仍未证实，不自动计误拦。评估坐标未进入任何actor/checker/executor，原标签与运行条件未改。

首次合并只读审查55秒超时，源/回执已封存，实查旧读取句柄不存在后改为6个独立有界只读分片，全部完成；没有模型/GUI失败或额外调用。单个Qwen3.5-9B基座/decision_adapter_loaded=false、完整供应单图+固定v6/每次空上下文及完整合法主历史、原图、BF16/SDPA、动作/校验/预算保持。

新的quote_id来源协议仍待之前已发出的独立条件决定，未部署/无新GUI；既有STOP原句映射许可保留、不复问、不挪用为新wire许可。原32轨/16配对/8任务及4不可重跑终局/28未开始保持，14全新对只是版本分层。相对降低仍null，未证明30%或减半，目标ACTIVE。以下为保留历史。

'''
    (out / 'new-head.md').write_text(header, encoding='utf8')
    save(out / 'status.json', status)
    for name in heads:
        assert (BASE / name).read_bytes() == old[name], 'Concurrent head edit; preserve instead of overwriting'
    for name in ['README.md', 'HANDOFF.md']:
        (BASE / name).write_bytes(header.encode('utf8') + old[name])
    (BASE / 'full-gui-current.json').write_bytes((out / 'status.json').read_bytes())
    for name in heads:
        (out / ('after-' + name)).write_bytes((BASE / name).read_bytes())
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(out / 'receipt.json', dict(time=time.time(), panel_authority=pointer,
        pending_source_reference_condition_decision_unchanged=True,
        current_files={name: sha(BASE / name) for name in heads}, original_scope_unchanged=True,
        new_model_GUI_capture_action_scorer_paid_calls=0, goal='active'))
    save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    result = dict(root=str(out), status_sha256=sha(out / 'status.json'),
        receipt_sha256=sha(out / 'receipt.json'), seal_sha256=sha(out / 'seal.json'))
    save(HERE / 'publication-created.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf8')
    main()
