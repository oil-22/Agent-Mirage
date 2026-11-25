"""Publish completed audit pointers, preserving byte-exact previous document heads."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, data):
    assert not path.exists(), path
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    receipt = json.loads((ROOT / 'completion-receipt.json').read_text(encoding='utf-8'))
    assert receipt['status'] == 'complete_review_not_demonstrated_Mirage_reduction'
    completion_seal = json.loads((ROOT / 'completion-seal.json').read_text(encoding='utf-8'))
    for rel, expected in completion_seal.items():
        assert sha(ROOT / rel) == expected
    target = ROOT / 'publication-01'
    current = BASE / 'complete-review-three-current.json'
    assert not target.exists() and not current.exists()
    target.mkdir()
    completion_sha = sha(ROOT / 'completion-receipt.json')
    seal_sha = sha(ROOT / 'completion-seal.json')
    report = 'complete-review-three-01/' + receipt['report']
    summary = (
        '24候选、73主核验、20辅助forward及20原图的完整审查已完成，结构/请求/执行链通过；'
        '**当前单Flash三题版本尚未证明可观Mirage降幅**。1确定候选Mirage（c23）已发生但未接受/未执行，'
        '3未决候选（c5/7/11，其中c5执行）；c23/24重复同一错点，均未执行。'
        'c13正常局部陈述被补充absence检查误拦，1重采+1重生后c14保留同一有效点击继续。'
        '最后主核验误认“1按钮”，原containment正确阻止错点；技术终局/原官方0.0/未注入分列。'
        '两条旧帧配对未开始、0调用，不能估计降幅或相对30%目标。'
    )
    handoff_head = (
        '## 最新：完整审查完成，未证明Mirage降低；模型服务已封存退出\n\n'
        + summary + '\n\n'
        + f'报告：`{report}`。不可变回执`complete-review-three-01/completion-receipt.json` SHA`{completion_sha}`；'
        + f'最终seal SHA`{seal_sha}`。独立actor标签先封存后join，原标签/summary未改；'
        + 'root主核验审查非盲法，三未决不可改阴性。全部50结果行确已在交付图出现，'
        + '不等于所有细小服装排除或全局最低价证明。辅助仅原图+固定通用三题，实际actor24包含4同源复用；'
        + '全20原生BF16概率已按原softmax/温度独立复算；pixels只核实际shape/hash绑定，未全量processor重新编码。\n\n'
        + '119请求/1103Controller链/238服务链/19执行/原预算均核；本地192公共seal条目复核，'
        + 'Controller249依赖条目仅在原远端audit完整验证，不伪称全量本地镜像。'
        + '3090/4090原source/请求回复/图像历史/log已保全；仅root写stop marker后primary/Flash真实exit0/0、launcher消失，'
        + '原848项服务terminal manifest核验。退出审查快照GPU4–7compute空，holder2568295仍持9锁，**预留未释放**。'
        + '两模型均加载至退出14.8824小时/四卡等价59.5297GPUh，其中终局后等待审查13.5919小时/54.3674GPUh；'
        + '不是完整预留总成本、货币或能耗。\n\n'
        + '本轮0新模型/GUI/health/scorer，不改原validator/点框/动作/条件/预算，不重启原终局或旧队列。'
        + '下一修复建议仅为建议：单辅助中立细证据能力、主历史源一致性、候选抽取与点框来源匹配；'
        + '新条件及有限控制须重新冻结后才可试验，不能自动补跑这条失败轨迹。全局其他授权工作尚未完成，不因本审查暂停全局monitor。\n\n'
    )
    readme_head = (
        '最新完整审查已交付：' + summary + '\n\n'
        + f'详见[{receipt["report"]}]({report})及`complete-review-three-current.json`。'
        + '原请求/回复/输入/执行链、独立标签与后置join均已封存；单Flash只给粗分类，不覆盖具体服装/坐标/历史反例。'
        + '两模型已正常退出并保全，退出审查时holder仍持9锁；未释放四卡预留。没有新实验、没有证明降幅，严禁重启已终局轨迹。\n\n'
    )
    before, after = {}, {}
    for filename, head in [('HANDOFF.md', handoff_head), ('README.md', readme_head)]:
        path = BASE / filename
        old = path.read_bytes()
        (target / (filename + '.before')).write_bytes(old)
        before[filename] = hashlib.sha256(old).hexdigest()
        content = old.decode('utf-8-sig')
        first, separator, rest = content.partition('\n')
        assert first.startswith('# '), filename
        path.write_text(first.rstrip('\r') + '\n\n' + head + rest.lstrip('\r\n'), encoding='utf-8')
        after[filename] = sha(path)
    write_new(current, {
        'status': receipt['status'], 'report': report,
        'completion_receipt': 'complete-review-three-01/completion-receipt.json',
        'completion_receipt_sha256': completion_sha, 'completion_seal_sha256': seal_sha,
        'single_clean_technical_terminal_only': True, 'two_stale_paired_runs_unstarted': True,
        'substantial_trigger_reduction_demonstrated': False,
        'definite_candidate_Mirage': 1, 'additional_unknown_candidates': 3,
        'definite_accepted_executed_Mirage_identified': 0, 'unknown_accepted_executed_candidates': 1,
        'native_wrong_point_candidates_unexecuted': 2, 'source_bound_false_blocks': 1,
        'worker_exit_codes': {'primary': 0, 'pplx_flash': 0},
        'holder9locks_remain_at_postexit_snapshot': True,
        'new_model_GUI_health_scorer_calls_during_review': 0,
        'no_automatic_relaunch_or_budget_extension': True
    })
    write_new(target / 'receipt.json', {
        'status': 'completed_audit_heads_published_with_original_head_backups',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'completion_receipt_sha256': completion_sha, 'completion_seal_sha256': seal_sha,
        'before_document_SHA256': before, 'after_document_SHA256': after,
        'current_pointer_sha256': sha(current),
        'only_mutations': ['prepend completed audit heads to HANDOFF.md/README.md with exact old bytes backed up', 'new complete-review-three-current.json'],
        'original_experimental_sources_terminals_labels_changed': False,
        'new_model_GUI_health_scorer_calls': 0
    })
    seal = {'receipt.json': sha(target / 'receipt.json'), '../publish_review_heads.py': sha(Path(__file__)),
            '../../complete-review-three-current.json': sha(current)}
    seal.update({filename + '.before': sha(target / (filename + '.before')) for filename in before})
    write_new(target / 'seal.json', seal)
    print(json.dumps({'status': 'published', 'publication_receipt_sha256': sha(target / 'receipt.json'),
        'publication_seal_sha256': sha(target / 'seal.json'), 'current_pointer': str(current)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
