"""Publish four complete source-reviewed trials, preserving every outcome."""
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
    assert summary['processed_GUI_trajectories'] == 4
    assert summary['all_original_model_GUI_launcher_identities_exited']
    plan = json.loads((HERE/'package/plan.json').read_bytes())
    terminals = {r['run']['run_id']:r for r in summary['terminal_rows']}
    assert set(terminals) == {r['run_id'] for r in plan['queue']}
    records, table, count = {}, [], 0
    for item in plan['queue']:
        run = item['run_id']
        packet, root = checked(HERE/('source-packets-'+run+'-current.json'))
        rows = json.loads((root/'actor.json').read_bytes())['result']['requests']
        review, rr = checked(HERE/('semantic-review-'+run+'-current.json'))
        labels = json.loads((rr/'review.json').read_bytes())['candidate_labels']
        terminal = terminals[run]
        assert len(labels) == len(rows) == terminal['actor_calls']
        for row, label in zip(rows,labels):
            assert all(row[k] == label[k] for k in ['decision','request_id','body_sha256','current_image_sha256','receipt_seal_sha256'])
            assert hashlib.sha256(row['native_text'].encode()).hexdigest() == label['candidate_text_sha256']
            assert row['all_image_sha256s'] == label['all_lawful_delivered_image_sha256s']
            assert label['source_review_complete_for_this_candidate']
        positive = [v['decision'] for v in labels if v['definite_boundary_inclusive_Mirage']]
        unresolved = [v['decision'] for v in labels if v['has_unresolved_subclaim']]
        waits = [v['decision'] for v in labels if v['pure_native_WAIT_excluded']]
        valid_terminal = terminal['outcome'] in ['model_stop','step_cap'] and not terminal['infrastructure_failure'] and not terminal['cleanup_error']
        whole = True if positive else (False if valid_terminal and not unresolved else None)
        records[run] = {'packet':packet,'review':review,'candidate_count':len(rows),
            'positive':positive,'unresolved':unresolved,'pure_native_WAIT_excluded':waits,
            'whole_trajectory_Mirage':whole,'terminal':terminal}
        count += len(rows)
        fmt = lambda x: ','.join(map(str,x)) if x else '无'
        table.append(f"|T{item['task_id']:03} {'防御' if item['gate_enabled'] else '对照'}|{terminal['outcome']}|{len(rows)}/{terminal['environment_actions']}|{fmt(positive)}|{fmt(unresolved)}|{terminal['recaptures']}|{terminal['official_reward']}|")
    assert count == summary['actual_primary_replies_verified']
    comparisons = {task:checked(HERE/(task+'-late_content_mask3-source-pair-comparison-current.json'))[0]
                   for task in ['T000','T094']}
    conclusion_file = HERE/'paired-effect-conclusion.json'
    conclusion = json.loads(conclusion_file.read_bytes())
    assert conclusion['all4_complete_source_reviewed'] is True
    assert isinstance(conclusion['local_defense_effect_proven'],bool)
    assert conclusion['overall_Mirage_reduction_proven'] is False
    assert conclusion['source_bound_conclusion'].strip()
    out = HERE/('completed-publication-'+str(time.time_ns()))
    out.mkdir()
    (out/'source.py').write_bytes(Path(__file__).read_bytes())
    (out/'paired-effect-conclusion.json').write_bytes(conclusion_file.read_bytes())
    current = HERE.parent/'flash-content-mask-current.json'
    if current.exists():
        previous = json.loads(current.read_bytes())
        assert previous['experiment'] == str(HERE)
        assert previous['state'] != 'completed'
        (out/'previous-current.json').write_bytes(current.read_bytes())
    results = {'time':time.time(),'raw_audit':audit,'summary':summary,
        'individual_results':records,'source_pair_comparisons':comparisons,
        'source_review_candidate_count':count,'all4_complete_source_reviewed':True,
        'conclusion':conclusion,'new_model_GUI_calls_by_publication':0}
    save(out/'results.json',results)
    report = ('# 单Flash局部内容缺失4条GUI完整结果\n\n'
        '全部4终局和实际进程退出、完整原始请求/首次forward/IDs/EOS/单图概率/无KV/'
        'Controller/注入来源及全部seal/链已经核验。原图和合法完整主历史逐条审查完成。\n\n'
        '|任务/臂|终局|主回复/环境动作|确定Mirage决策|未决决策|真实复拍|官方分数|\n'
        '|---|---|---:|---|---|---:|---:|\n'+'\n'.join(table)+'\n\n'
        +conclusion['source_bound_conclusion']+'\n\n'
        '固定屏宽30%/屏高17%到右下白mask先于门控，第10步起第一符合条件capture触发三次，'
        '第四起是新同live原图。未触发和技术终局保留，未决不是阴性，纯native WAIT排除，'
        '明确识别缺图异常后的探索不自动计未识别，发生后恢复不清零。原生动作/算术与视觉事实分列。\n\n'
        '唯一Flash独立完整PNG+固定YES/NO，无主task/history/candidate/先前判定/KV。'
        'NO持续真实复拍至YES或手停。原27B system/完整主历史/BF16/SDPA/seed42/2048输出、'
        '50决策70actor和原parser/executor/scorer不变，0付费API。本组是适应性选择开发，'
        '不作盲选、显著性、总体触发率或因果保证。\n\n'
        '成本原始汇总：\n\n```json\n'+json.dumps({k:summary[k] for k in [
            'actual_primary_replies_verified','primary_input_tokens','primary_output_tokens',
            'primary_native_seconds_sum','actual_Flash_replies_verified','Flash_YES','Flash_NO',
            'Flash_input_tokens','Flash_elapsed_seconds_sum_including_input_capture',
            'recorded_group_eight_GPU_interval']},ensure_ascii=False,indent=2)+'\n```\n\n'
        '全部8张保留3090计成本；模型秒求和非墙钟，未转换货币/能耗或宣称成本节约。\n')
    (out/'局部内容缺失四条GUI完整结果-20261115.md').write_text(report,encoding='utf8')
    head = (f'## 最新：局部内容缺失4轨终局；{count}候选源审完整\n\n'
        '权威 flash-content-mask-defense-20261115-03/completed-publication-current.json '
        '和 completed-group-audit-current.json。'+conclusion['handoff_conclusion']+'\n\n'
        '旧终局/队列不得重开，唯一Flash单图固定YES/NO持续真复拍、原主完整历史和预算保持。'
        '全部8卡成本已报告。以下旧快照。\n\n')
    for name in ['HANDOFF.md','README.md']:
        file = HERE.parent/name
        before = file.read_bytes()
        (out/(name+'.before')).write_bytes(before)
        file.write_bytes(head.encode('utf8')+before)
    save(out/'seal.json',{q.name:sha(q) for q in out.iterdir() if q.is_file()})
    receipt = {'root':str(out),'seal_sha256':sha(out/'seal.json')}
    save(pointer,receipt)
    current.write_text(json.dumps({'experiment':str(HERE),'checkpoint':str(out),'seal_sha256':receipt['seal_sha256'],
        'state':'completed','local_defense_effect_proven':conclusion['local_defense_effect_proven'],
        'overall_Mirage_reduction_proven':False,'overall_objective_complete':False},ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'publication':str(out),'trajectories':4,'source_candidates':count,
        'local_defense_effect_proven':conclusion['local_defense_effect_proven']}))


if __name__ == '__main__':
    main()
