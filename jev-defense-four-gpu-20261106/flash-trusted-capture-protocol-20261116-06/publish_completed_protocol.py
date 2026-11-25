"""Publish a verified terminal report while preserving prior handoff heads."""
import json
import time
from pathlib import Path

from remote_util import HERE, save, sha


def main():
    assert not (HERE / 'completed-publication-current.json').exists()
    pointer = json.loads((HERE / 'completed-protocol-report-current.json').read_bytes())
    report_root = Path(pointer['root'])
    assert sha(report_root / 'seal.json') == pointer['seal_sha256']
    for name, expected in json.loads((report_root / 'seal.json').read_bytes()).items():
        assert sha(report_root / name) == expected
    report = json.loads((report_root / 'report.json').read_bytes())
    assert report['completed_new_GUI_trajectories'] == 2
    base = HERE.parent
    success = report['new_protocol_successes']
    totals = report['per_mode']
    rows = report['new_protocol_rows']
    per_run = '; '.join(f"{v['run_id']} {v['primary_replies']}主/{v['Flash_replies']}Flash/{v['environment_actions']}动作/{v['recaptures']}复拍/{v['outcome']}/official{v['official_reward']}" for v in rows)
    counts = '/'.join(str(totals[k]['successful_examples_across_explicit_versions']) for k in ['silent_drop', 'blank_replace', 'stale_replace', 'buttons_only'])
    proposal_study = base / 'flash-buttons-policy-proposal-20261116-07'
    proposal_note = ''
    if (proposal_study / 'proposal-current.json').exists():
        development = json.loads((proposal_study / 'proposal-current.json').read_bytes())
        development_root = Path(development['root'])
        assert sha(development_root / 'seal.json') == development['seal_sha256']
        proposal_note = f"\n另有按钮新判据开发方案 `{development_root / '按钮残留单图判据与正常误拦开发方案-20261116.md'}`，固定20图、最多20新Flash/每图一次/0自动重试/0主GUI评分付费，尚未部署。真实用户决定优先读 `{proposal_study / 'decision-request-current.json'}` 及后续用户授权回执；已通过request_user_input_async询问，不重复发问，不把预选或时间当批准。它可能误拒合法单按钮页，不能用坏图NO掩盖正常误拦。开发批准不等于新GUI发布批准。\n"
    head = f'''## 2026-11-16 最新终局：可信采集回执两条新旧帧GUI完成并审计，闭环成功{success}/2

权威报告 `{report_root / '可信采集回执旧帧防御完整GUI结果-20261116.md'}`；report seal {pointer['seal_sha256']}。用户已直接回复“增加可信采集回执，另设新协议验证”，旧来源回执待批准项已解决，不再询问。两条新协议T058/T089均完整终局；{per_run}。逐轨与整组原始wire/input IDs/pixels/grid/完整主历史/自然EOS/Flash原始head概率/原生动作/官方评分及独立采集签名/一次性挑战/持久化账本/原图和SHA事件链均已核验。整组 `completed-group-audit-current.json`、图像验收 `acceptance-checkpoint-current.json`，以不可变回执为准。

本轮{report['primary_replies']}完整主回复、{report['Flash_replies']}Flash（YES{report['Flash_YES']}/NO{report['Flash_NO']}），来源NO={report['source_NO']}、缺图前置NO={report['missing_precheck_NO']}。来源NO跳过Flash和主当前图输入，真实同live新挑战复拍后来源YES、原固定单图Flash YES、正常原PNG实际入主并完成原生dispatch。正常图后文字误读按用户口径不计门控失败，官方分数另列。它是可信采集后的字节替换防御，不是Flash识别出旧帧；原合法历史不删除。可信OS/Controller/采集程序和浏览器是边界，采集端本身签下的旧/坏/DOM遮罩图不保证识别。

原10终局及全部漏放/未触发不变：按明确版本的缺图/白图/旧帧/按钮成功例覆盖为{counts}，四种各2目标达成={report['all_four_conditions_two_successes_across_explicit_versions_reached']}。不合并不同协议为同一效果率，不称总体Mirage显著降低。按钮主体缺失/合法稀疏界面的边界仍未解决，未部署新prompt或阈值，不能重跑相同漏放筛NO。20协议边界/16真实采集接口/7假模型路由仅工程控制，旧失败与关联修复保留。
{proposal_note}

实际原launcher/主/Flash/GUI/采集身份均核实退出，17个内核锁已释放，新租约无broker残留；资源权威 `resource-release-audit-current.json`。8张3090=7主+1Flash，本轮保留含加载/就绪空闲{report['GPU_seconds_lower']/3600:.3f}–{report['GPU_seconds_upper']/3600:.3f} GPU·小时；主输入{report['primary_input_tokens']}/输出{report['primary_output_tokens']}tokens，生成求和{report['primary_native_seconds_sum']:.3f}秒，不是walltime/货币/能耗/所有历史成本。严禁重开本2终局或任意旧stage/submit/gui/queue/resource_control --worker；未来需独立新协议、未用预算和重新核验资源归属。整体授权目标仍未完成，不因本子组完成暂停monitor。以下旧快照保留。

'''
    root = HERE / ('completed-publication-' + str(time.time_ns()))
    root.mkdir()
    before = root / 'before'
    after = root / 'after'
    before.mkdir(); after.mkdir()
    targets = [('new-HANDOFF.md', HERE / 'HANDOFF.md'), ('new-README.md', HERE / 'README.md'),
               ('main-HANDOFF.md', base / 'HANDOFF.md'), ('main-README.md', base / 'README.md'),
               ('parent-HANDOFF.md', base / 'flash-four-injection-defense-20261115-04/HANDOFF.md'),
               ('legacy-HANDOFF.md', base.parent / 'jev-defense-local-20261102/HANDOFF.md'),
               ('legacy-README.md', base.parent / 'jev-defense-local-20261102/README.md')]
    transitions = []
    for label, path in targets:
        original = path.read_bytes()
        (before / label).write_bytes(original)
        (after / label).write_bytes(head.encode('utf8') + original)
        transitions.append({'path': str(path), 'before_sha256': sha(before / label),
                            'after_sha256': sha(after / label), 'snapshot': label})
    prior_pointers = [('new-publication.json', HERE / 'publication-current.json'),
                      ('main-protocol.json', base / 'trusted-capture-protocol-current.json')]
    for label, path in prior_pointers:
        if path.exists():
            (before / label).write_bytes(path.read_bytes())
    for transition in transitions:
        path = Path(transition['path'])
        assert sha(path) == transition['before_sha256'], 'Handoff changed concurrently'
        temporary = path.with_name('.protocol-publication-' + str(time.time_ns()))
        temporary.write_bytes((after / transition['snapshot']).read_bytes())
        temporary.replace(path)
        assert sha(path) == transition['after_sha256']
    save(root / 'state.json', {'created': time.time(), 'report': pointer,
                              'new_protocol_successes': success, 'per_mode': totals,
                              'processes_and_resource_release_verified': True,
                              'all_four_targets_reached': report['all_four_conditions_two_successes_across_explicit_versions_reached'],
                              'monitor_pause_not_requested': True, 'new_model_GUI_calls': 0,
                              'transitions': transitions})
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file()})
    published = {'root': str(root), 'seal_sha256': sha(root / 'seal.json'), 'terminal': True,
                 'report': pointer}
    for path in [HERE / 'publication-current.json', base / 'trusted-capture-protocol-current.json']:
        temporary = path.with_name('.' + path.name + '.' + str(time.time_ns()))
        save(temporary, published)
        temporary.replace(path)
    save(HERE / 'completed-publication-current.json', published)
    print(json.dumps({'root': str(root), 'report': str(report_root), 'new_protocol_successes': success,
                      'all_four_targets_reached': report['all_four_conditions_two_successes_across_explicit_versions_reached']}))


if __name__ == '__main__':
    main()
