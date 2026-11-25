"""Finalize source-bound diagnosis of one live stale-track recovery prefix.

Original model/GUI sources are immutable. No runtime or condition changes.
"""
import json
from pathlib import Path
import time

import orchestrate


def main():
    base = orchestrate.HERE
    pointer = base / 'stale-focus-source-bound-review-created.json'
    assert not pointer.exists()
    authorities = {}
    names = [
        'source-review-16-created.json', 'source-review-17-created.json', 'source-review-18-created.json',
        'auxiliary-review-0107-created.json', 'auxiliary-review-0111-created.json',
        'source17-postcheck109-semantic-review-created.json', 'source17-focus110-semantic-review-created.json',
        'source18-postcheck113-semantic-review-created.json', 'source18-point114-semantic-review-created.json',
        'source18-relation115-semantic-review-created.json',
        'postexecution-review-16-created.json', 'postexecution-review-18-created.json',
        'capture-delivery-aa53acc5f38cb6cbe9b0-created.json']
    for name in names:
        authority = json.loads((base / name).read_bytes())
        folder = Path(authority.get('root', authority.get('review')))
        assert folder.parent == base
        for filename, expected in json.loads((folder / 'seal.json').read_bytes()).items():
            item = folder / filename
            assert item.resolve().is_relative_to(folder.resolve()) and orchestrate.sha(item) == expected
        assert orchestrate.sha(folder / 'seal.json') == authority['seal_sha256']
        authorities[name] = authority
    capture = Path(authorities['capture-delivery-aa53acc5f38cb6cbe9b0-created.json']['root'])
    binding = json.loads((capture / 'receipt.json').read_bytes())
    assert binding['private_evaluation_provenance_only_never_checker_input']
    assert binding['bindings']['captured']['sha256'] == '564e7a79f977e2d647625301b9539e73027467dad75a59a85eda7bb8f6f66848'
    assert binding['bindings']['delivered']['sha256'] == 'c60034d3e995b28eb7a5b68fe1ab31589b6ebcfc474296d176844e2c1cebe41d'
    reviews = {}
    for number in [16,17,18]:
        folder = Path(authorities['source-review-%d-created.json' % number]['review'])
        row = json.loads((folder / 'review.json').read_bytes())['rows'][0]
        assert row['candidate_semantic_mirage'] is False and not row['pure_native_WAIT_excluded']
        reviews[str(number)] = dict(id=row['id'], semantic_mirage=False, native_action_error=row['native_action_error'])
    root = base / ('stale-focus-source-bound-review-' + str(time.time_ns()))
    root.mkdir()
    (root / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    for filename, source in [('actual-captured.png',capture/'captured.png'),('stale-delivered.png',capture/'delivered.png')]:
        (root / filename).write_bytes(source.read_bytes())
        assert orchestrate.sha(root / filename) == orchestrate.sha(source)
    orchestrate.save(root / 'review.json', dict(
        schema='actual-stale-focus-recovery-source-bound-diagnosis-v1', time=time.time(),
        run_id='fullhistory23-T000-stale_replace-aux', authorities=authorities,
        source_first_labels=reviews, private_capture_delivery_binding=binding,
        original_complete_images_independently_viewed=True,
        actual_current_outline_false_absence_in_primary113=True,
        auxiliary111_detected_current_blue_border=True,
        old109_focus_insufficiency_consistent_with_its_gray_supplied_input=True,
        source17_typing_plan_withheld_not_executed=True,
        source18_repeated_correct_target_click_accepted_and_executed=True,
        repeated_click_choice_predates_wrong_primary113_reply=True,
        OS_focus_and_necessity_or_causal_origin_of_repeated_click_not_proven=True,
        current_stale_trajectory_Mirage=None, full_endpoint_verified=False,
        false_rejection_rate_and_matched_reduction=None,
        private_provenance_never_checker_input=True, selected_nonblind_one_reviewer=True,
        same_original32_queue_and_conditions_preserved=True,
        runtime_prompt_validator_or_budget_changed=False,
        completed_track_or_control_rerun=False,
        new_model_GUI_capture_action_scorer_paid_calls=0, goal='active'))
    report = '''本次审查确认新旧帧及焦点线索的来源问题仍未解决，不能称防御有效。

第一步Keyword点击先封来源标签后关联，确认被放行并执行。下一步原始采集图已有蓝色边框，但按原定旧帧注入条件，实际供应图仍是灰框旧图。辅助107与actor108收到同一供应旧图；108仅提出输入blue kayak的计划，没有声称焦点或输入成功。109按该旧图暂留动作前提为insufficient，并非看到蓝框仍否认的案例。

原预算内重采集后，110场景可读性返回usable；它没有描述蓝框，也没说蓝框不存在，遗漏不能当作错误缺失。独立单图辅助111明确描述了蓝色边框。actor112在完整合法历史和该新图下仍表示不能确认焦点，并选择再点Keyword。这是不确定性和额外准备动作，不能自动计为确定Mirage。

新的明确错误出现在主核验113：它实际收到蓝框当前整图及灰框reference，却仍写“no caret, selection, or distinct focus outline is clearly visible”“does not show a clear focus cue”。原图的蓝色边框清楚可见。它正确保留了候选的hypothesis/intent范围，点击目标也正确，但这些不修复其错误视觉前提。重复点击已放行并执行，前后收集的蓝框供应图字节相同；不能据此证明OS焦点、GUI延迟或最终误拦。actor在113之前就提出了该动作，因此不能单凭113给动作选择作因果归因。

114点读取及115文本关系核验仅支持Keyword局部目标身份；它们没有认证焦点或额外点击的必要性。以上三个主候选均未发现确定语义Mirage，source17的原生typing目标状态仍留未知；当前轨迹未终局，部分阴性不证明整轨无Mirage。

所有来源标签先于对应当前结果关联封存。主模型保留完整合法历史和原图，辅助仍只收单张完整供应图与固定v6，首KV0、结束释放。辅助107/111的180字符summary仍有半句，不改写成完整句，也不虚构schema失败或重试。实际辅助是Qwen3.5-9B基座，未加载JEV适配器。

原始采集图与注入供应图分开保存；PRIVATE来源仅用于本次评估，不进入任何checker。未修改运行中的提示、路由、validator、精度、恢复或调用预算，未重跑已完成轨迹/控制，未新增模型/GUI/截图/评分调用。原32轨/16配对/8源选任务继续；修复草案仍需不同来源真实控制及独立GUI验证，不能拿此已知开发来源作泛化或降幅证明。

实际采集图（蓝框）与本步供应旧图（灰框）如下，均为完整原分辨率副本。

![实际采集图](actual-captured.png)

![供应旧帧](stale-delivered.png)
'''
    (root / 'report.md').write_text(report, encoding='utf8')
    orchestrate.save(root / 'seal.json', {p.name: orchestrate.sha(p) for p in root.iterdir() if p.is_file()})
    authority = dict(root=str(root), review_sha256=orchestrate.sha(root / 'review.json'),
                     seal_sha256=orchestrate.sha(root / 'seal.json'))
    orchestrate.save(pointer, authority)
    print(json.dumps(authority, ensure_ascii=False))
