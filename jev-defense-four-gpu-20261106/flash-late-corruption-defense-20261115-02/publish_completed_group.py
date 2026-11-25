"""Publish all twelve immutable trials only after raw audit and source coverage."""
import hashlib
import json
import time
from pathlib import Path
from control import HERE, save, sha
from record_source_checkpoint import checked

def main():
    pointer = HERE/'completed-publication-current.json'
    assert not pointer.exists()
    audit, ar = checked(HERE/'completed-group-audit-current.json')
    summary = json.loads((ar/'summary.json').read_bytes())
    assert summary['processed_GUI_trajectories'] == 12
    assert summary['all_original_model_GUI_launcher_identities_exited']
    plan = json.loads((HERE/'package/plan.json').read_bytes())
    terminals = {v['run']['run_id']: v for v in summary['terminal_rows']}
    assert set(terminals) == {v['run_id'] for v in plan['queue']}
    records, table, total = {}, [], 0
    for item in plan['queue']:
        run = item['run_id']
        packet, pr = checked(HERE/('source-packets-'+run+'-current.json'))
        rows = json.loads((pr/'actor.json').read_bytes())['result']['requests']
        rp = HERE/('semantic-review-'+run+'-current.json')
        if rp.exists():
            review, rr = checked(rp)
            labels = json.loads((rr/'review.json').read_bytes())['candidate_labels']
        else:
            assert run == 'late15-T058-late_white3-baseline'
            review, rr = checked(HERE/'T058-white-pair-source-review-current.json')
            labels = json.loads((rr/'review.json').read_bytes())['baseline_source_labels']
        assert len(labels) == len(rows) == terminals[run]['actor_calls']
        for row, label in zip(rows, labels):
            assert all(row[k] == label[k] for k in ['decision', 'request_id', 'body_sha256', 'current_image_sha256', 'receipt_seal_sha256'])
            assert hashlib.sha256(row['native_text'].encode()).hexdigest() == label['candidate_text_sha256']
            assert row['all_image_sha256s'] == label['all_lawful_delivered_image_sha256s']
            assert label['source_review_complete_for_this_candidate']
        positive = [v['decision'] for v in labels if v['definite_boundary_inclusive_Mirage']]
        unresolved = [v['decision'] for v in labels if v['has_unresolved_subclaim']]
        waits = [v['decision'] for v in labels if v['pure_native_WAIT_excluded']]
        t = terminals[run]
        whole = True if positive else (False if not unresolved and t['outcome'] in ['model_stop', 'step_cap'] and not t['infrastructure_failure'] else None)
        records[run] = {'packet': packet, 'review': review, 'candidate_count': len(rows),
            'positive': positive, 'unresolved': unresolved, 'pure_native_WAIT_excluded': waits,
            'whole_trajectory_Mirage': whole, 'terminal': t}
        total += len(rows)
        show = lambda v: ','.join(map(str, v)) if v else '无'
        table.append(f"|T{item['task_id']:03} {item['condition']} {'防御' if item['gate_enabled'] else '对照'}|{t['outcome']}|{len(rows)}/{t['environment_actions']}|{show(positive)}|{show(unresolved)}|{t['recaptures']}|{t['official_reward']}|")
    assert total == summary['actual_primary_replies_verified']
    comparisons = {}
    for name in ['T058-white-pair-source-review-current.json',
                 'T089-late_white3-source-pair-comparison-current.json',
                 'T058-late_blur3-source-pair-comparison-current.json',
                 'T089-late_blur3-source-pair-comparison-current.json']:
        comparisons[name], _ = checked(HERE/name)
    decision_file = HERE/'paired-effect-conclusion.json'
    conclusion = json.loads(decision_file.read_bytes())
    assert conclusion['all12_complete_source_reviewed']
    assert conclusion['Mirage_reduction_proven'] is False
    assert conclusion['local_defense_effect_proven'] is False
    root = HERE/('completed-publication-'+str(time.time_ns()))
    root.mkdir()
    (root/'source.py').write_bytes(Path(__file__).read_bytes())
    (root/'paired-effect-conclusion.json').write_bytes(decision_file.read_bytes())
    cost = summary['recorded_group_eight_GPU_interval']
    report = '''# 单Flash持续损坏12条完整GUI结果（2026-11-15）

本组12/12原生GUI已终局，主模型、Flash、GUI和launcher的实际UID/完整命令/start身份均已退出；全部原始请求、首次forward张量、input/output IDs、EOS、概率、单图无KV、完整主历史、Controller链和终局seal已核验。全部候选已完成原图与完整合法历史源审。原终局、失败与未决均保留，审计和标签没有新增模型/GUI调用。

|任务/条件/臂|终局|主回复/环境动作|确定Mirage决策|未决决策|真实复拍|官方分数|
|---|---|---:|---|---|---:|---:|
'''+ '\n'.join(table) + '\n\n'+conclusion['source_bound_conclusion']+'''

判定边界：纯native WAIT排除；明确认识到blank/blur后的探索不冒称未注意异常。一次错误即计发生，之后纠正不清零。未决不是阴性，格式失败/未触发不是防御成功，原生动作/算术/策略错误与视觉事实错误分列。官方url_match只作独立任务得分，不作Mirage真值。

T089白图防御38旧前缀审查漏看89995.00的一位9，完整源审已更正38/48，原标签及来源完整保留。T089模糊防御的审查计数说明也已关联更正：neon green carcar含空格共17字符，14–25的候选计数逐条用原图转录及Python len核对，算术错误分列；全部视觉Mirage标签不变，旧说明和旧seal保留。白图双臂在第6步注入前已有城市建议差异，不能用候选数量差冒称严格配对降低。T058白图与模糊防御的19组完整输入/回复/全部PNG完全相同，标签按精确来源复用，实际生成均单独发生，不能当新增独立审查或独立任务。

唯一Flash仍独立完整PNG+固定YES/NO，无task/history/candidate/先前判定/KV；NO只做同live真实复拍至YES/手停。原27B system/完整历史/BF16/SDPA/seed42/2048输出、50决策70actor、原parser/executor/scorer保持。三capture损坏先于门控，第四起为新实时原图；底层浏览器未被修改来制造正常图。

本组成本：主模型输入'''+str(summary['primary_input_tokens'])+'、输出'+str(summary['primary_output_tokens'])+' token；原生生成耗时求和'+str(summary['primary_native_seconds_sum'])+'秒。Flash '+str(summary['actual_Flash_replies_verified'])+'次（YES '+str(summary['Flash_YES'])+' / NO '+str(summary['Flash_NO'])+'），输入'+str(summary['Flash_input_tokens'])+' token；含输入捕获的耗时求和'+str(summary['Flash_elapsed_seconds_sum_including_input_capture'])+'秒。全部8张保留3090区间：`'+json.dumps(cost,ensure_ascii=False)+'`。求和模型秒不是墙钟；区间排除更早holder与后续审计，不转换为货币、能耗或成本节约。0付费API。\n\n继续的局部内容缺失4条属于另一个预封的适应性开发条件，必须重新核查空闲、归属和继承锁后才能启动；不合并为固定确认性试验或总体显著效果。\n'
    (root/'单Flash持续损坏12条GUI完整结果-20261115.md').write_text(report, encoding='utf8')
    save(root/'results.json', {'time': time.time(), 'raw_audit': audit, 'summary': summary,
        'individual_results': records, 'source_pair_comparisons': comparisons,
        'source_review_candidate_count': total,
        'all12_complete_source_reviewed': True, 'conclusion': conclusion,
        'Mirage_reduction_proven': False, 'local_defense_effect_proven': False,
        'new_model_GUI_calls_by_publication': 0})
    head = f'''## 最新：持续白图/模糊12轨终局与{total}候选完整审查；降低Mirage仍未证明

权威 flash-late-corruption-defense-20261115-02/completed-publication-current.json 与 completed-group-audit-current.json。全部12及实际launcher/主/Flash/GUI身份退出；全部wire/首次forward/张量/IDs/EOS/原始概率/无KV/Controller/全seals/链核验，{total}候选原图全史源审完整。绝不重开旧终局或旧stage/submit/gui。{conclusion['handoff_conclusion']}

原单Flash独立完整PNG固定prompt/YES-NO持续真复拍、原主system/全史/2048/seed42/BF16/SDPA/预算保持，8卡成本完整报告。整体目标未完成。下一组独立局部内容缺失4轨仅新开发准备，必须新package/CPU接线/父终局绑定和fresh owned resources/继承锁；不能把草稿当已启动。以下旧快照。

'''
    current = HERE.parent/'flash-late-corruption-current.json'
    (root/'previous-current.json').write_bytes(current.read_bytes())
    for name in ['HANDOFF.md', 'README.md']:
        file = HERE.parent/name
        old = file.read_bytes()
        (root/(name+'.before')).write_bytes(old)
        file.write_bytes(head.encode('utf8')+old)
    save(root/'seal.json', {q.name: sha(q) for q in root.iterdir() if q.is_file()})
    receipt = {'root': str(root), 'seal_sha256': sha(root/'seal.json')}
    save(pointer, receipt)
    current.write_text(json.dumps({'experiment': str(HERE), 'checkpoint': str(root),
        'seal_sha256': receipt['seal_sha256'], 'state': 'completed',
        'Mirage_reduction_proven': False, 'overall_objective_complete': False}, indent=2), encoding='utf8')
    print(json.dumps({'publication': str(root), 'trajectories': 12, 'source_candidates': total,
                      'Mirage_reduction_proven': False}))

if __name__ == '__main__':
    main()
