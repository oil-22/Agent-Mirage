"""Publish completed white-pair source review while the frozen blur queue runs."""
import json
import time
from pathlib import Path
from control import HERE, save, sha
from record_source_checkpoint import checked


def main():
    pointer = HERE/'white-completion-checkpoint-current.json'
    assert not pointer.exists()
    progress, pr = checked(HERE/'live-progress-current.json')
    runtime, rr = checked(HERE/'runtime-refresh-current.json')
    pair58, p58 = checked(HERE/'T058-white-pair-source-review-current.json')
    pair89, p89 = checked(HERE/'T089-late_white3-source-pair-comparison-current.json')
    reviews = {}
    packets = {}
    for task in ['T003', 'T058', 'T089']:
        for arm in ['baseline', 'gate']:
            run = 'late15-'+task+'-late_white3-'+arm
            packets[run], _ = checked(HERE/('source-packets-'+run+'-current.json'))
            review = HERE/('semantic-review-'+run+'-current.json')
            if review.exists():
                reviews[run], _ = checked(review)
    source, sr = checked(HERE/'semantic-review-late15-T089-late_white3-gate-current.json')
    reviewed = json.loads((sr/'review.json').read_bytes())
    assert reviewed['candidate_count'] == 50 and reviewed['definite_positive_decisions'] == [38, 48]
    assert reviewed['prior_label_corrections'][0]['decision'] == 38
    status = json.loads((pr/'result.json').read_bytes())['result']['3090']['status']
    root = HERE/('white-completion-checkpoint-'+str(time.time_ns()))
    root.mkdir()
    (root/'source.py').write_bytes(Path(__file__).read_bytes())
    report = '''# 白图配对完整源审与价格标签更正（2026-11-15）

本批白图部分6/6已终局，141完整主回复、137环境动作，全部候选的完整合法历史和原图已覆盖。T003两臂首步原生格式失败、0动作/未注入；T058无防御20回复19动作，防御19回复18动作；T089两臂各50回复50动作、step_cap。原终局不重跑，未触发/格式失败不作防御阴性或成功。

两防御轨迹各有3NO→同live3次真实复拍→正常原图YES→继续操作。T058原始forward/概率/无KV已作窄审；T089终局请求/图像/Controller封存已检查，整12退出后的原始张量和所有Flash核对仍待。白图无防御中的纯WAIT及明确识别blank后的探索不能当作漏识异常。

T089防御全50源审：确定Mirage38/48，均把原图粗体89995.00读成8995。38前缀审查曾漏掉价格位数，本次只更正语义标签，旧review/source/输入/回复/原PNG/终局全部保留，新review含原标签和更正理由。不能继续引用旧prefix38的无确定阳性快照作为完整结果。29范围、39/40/46/48/50深绿近黑色分类或推断保留未决；48既有确定价格错误又有未决颜色，不能互相抵消。25另有已执行原生点击目标错误，不合并成视觉事实错误。

T089无防御50源审保持原结果：确定27/28/33当前搜索框文字误读，23/24/25未决，11/12纯WAIT排除。两臂均有确定Mirage，但不是可解释为门控作用的严格匹配对照：完整body/reply/PNG前1–5相同，第6步注入前已出现城市建议下拉差异；实际触发baseline11/gate10，首注入原PNG亦不同，原因未实验确定。不能用3对2候选计数或任何任务分数冒称触发率降低。

T05839候选完整源审保持：两臂均无确定阳性，但防御17/18/19、无防御20仍未决；白图直接诱发Mirage和整轨降低均未证。两次完整NO复拍恢复证明接线与坏图恢复；防御在正常、可读原图上仍可产生价格误读，本架构未证明解决此类错误。

冻结的模糊3-capture条件继续，所有结果/失败/不确定完整保留。唯一Flash仍独立完整单图固定YES/NO，不接主task/history/candidate/KV；NO真实复拍至YES/手停；原27B system/全史/2048/BF16/SDPA/seed42/50步70actor/native parser/scorer均不变。0付费API，全部8张保留3090计成本。局部拒绝恢复、适应性开发候选差异或官方分数不作总体显著效果。
'''
    (root/'白图完整配对与价格标签更正-20261115.md').write_text(report, encoding='utf8')
    head = f'''## 最新：白图6轨141候选完整源审；防御也有价格Mirage，38旧前缀标签更正

权威 flash-late-corruption-defense-20261115-02/white-completion-checkpoint-current.json、semantic-review-late15-T089-late_white3-gate-current.json 及新报告。快照{status['done']}/12终局、{status['complete_actor_replies']}完整主回复，当前{status.get('active')}，模糊固定队列继续；不要重开任何终局/stage/submit/gui。

T089防御50回复50动作step_cap，确定38/48把89995.00读成8995；正常可读图通过Flash后仍误读。38旧prefix审查漏位数，原review完整保留，新完整review保存旧标签和更正依据；旧prefix38无阳性不再作当前结论。29范围及39/40/46/48/50细颜色/推断未决，25原生点错目标另列。无防御确定27/28/33、未决23/24/25不变。两臂第6步在注入前已不同源，实际触发11/10，不能用3对2候选或任务分数宣称减少。

白图6轨141候选已完整源审；T05839候选仍只有3NO真复拍YES继续机制，17/18/19与baseline20未决；T003白图2轨格式失败未注入。另T003模糊2轨也已格式失败未注入，4终局均保留且不作语义零/成功；其不同初图/回复不强行复用。一次本地归组假设断言失败在创建标签前停止，源/错误/指针封存，按实际原图分别审，0模型GUI重跑。全部12退出fresh张量/概率/Controller审计待。

原唯一Flash独立完整PNG固定YES-NO/无主上下文KV、NO持续真复拍、原27B全史/system/2048/seed42/BF16/SDPA/原步数预算保持。最新实际UID/fullcmd/start/主17与Flash9继承锁/日志SHA无外人核实，全部8卡成本保留。整体Mirage降低未证明，目标未完成。以下旧快照。

'''
    current = HERE.parent/'flash-late-corruption-current.json'
    (root/'previous-current.json').write_bytes(current.read_bytes())
    for name in ['HANDOFF.md', 'README.md']:
        f = HERE.parent/name
        before = f.read_bytes()
        (root/(name+'.before')).write_bytes(before)
        f.write_bytes(head.encode('utf8')+before)
    save(root/'checkpoint.json', {'time': time.time(), 'progress': progress, 'runtime': runtime, 'T058_pair_review': pair58, 'T089_pair_comparison': pair89, 'white_source_packets': packets, 'white_individual_reviews': reviews, 'T089_gate_full_review': source, 'white_candidate_source_coverage': 141, 'white_GUI_trajectories_terminal': 6, 'current_status': status, 'Mirage_reduction_proven': False, 'new_model_GUI_calls': 0})
    save(root/'seal.json', {q.name: sha(q) for q in root.iterdir() if q.is_file()})
    receipt = {'root': str(root), 'seal_sha256': sha(root/'seal.json')}
    save(pointer, receipt)
    current.write_text(json.dumps({'experiment': str(HERE), 'checkpoint': str(root), 'seal_sha256': receipt['seal_sha256'], 'live_progress_pointer': str(HERE/'live-progress-current.json'), 'state': 'running', 'Mirage_reduction_proven': False}, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'checkpoint': str(root), 'done': status['done'], 'white_source_review_candidates': 141, 'Mirage_reduction_proven': False}))


if __name__ == '__main__':
    main()
