"""Publish the completed GUI corpus after full raw and Controller verification."""
import json
import time
from pathlib import Path
from control import HERE, save, sha


def load(path):
    return json.loads(Path(path).read_bytes())


def verify(root):
    assert root.parent == HERE
    assert all(sha(root / n) == h for n, h in load(root / 'seal.json').items())


def main():
    pointer = HERE / 'GUI29-completed-current.json'
    assert not pointer.exists(), 'Inspect the already published immutable completion'
    roots = {
        'parent_raw': HERE / 'fresh-exited-parent-raw-1794674765901374600',
        'parent_controller': HERE / 'fresh-exited-parent-controller-1794677452899273700',
        'continuation_raw': HERE / 'fresh-exited-continuation-raw-1794681237647187300',
        'continuation_controller': HERE / 'fresh-exited-continuation-controller-1794681951664470100',
        'registry': HERE / 'semantic-coverage-registry-1794681968796492900',
        'admission': HERE / 'aggregate-GUI-completion-1794681237579110600',
        'trace': HERE / 'aggregate-pair-trace-equivalence-1794681237873203400',
        'zero_call_failure': HERE / 'offline10-postexit-audit-1794681468201898100'}
    for root in roots.values():
        verify(root)
    registry = load(roots['registry'] / 'registry.json')
    assert registry['completed_trajectories'] == 29
    assert registry['completed_native_replies'] == 520 and registry['source_labels_indexed'] == 516
    assert registry['native_format_failures_without_semantic_labels'] == 4
    assert registry['completed_replies_waiting_for_source_review'] == 0
    assert registry['all_completed_reply_IDs_accounted_for'] and registry['existing_labels_replaced'] == 0
    admission = load(roots['admission'] / 'admission.json')
    assert len(admission['terminals']) == 29 and len(admission['preserved_technical_attempts']) == 1
    controllers, mains, flashes, failures, summaries = [], [], [], [], {}
    for group in ['parent', 'continuation']:
        raw, ctrl = roots[group + '_raw'], roots[group + '_controller']
        summary, binding = load(raw / 'summary.json'), load(ctrl / 'bindings.json')
        assert summary['actual_original_group_process_exits_verified']
        assert binding['source_full_raw_audit'] == str(raw)
        assert binding['source_full_raw_seal_sha256'] == sha(raw / 'seal.json')
        assert binding['all_actual_requests_replies_PNGs_Flash_and_native_actions_bound']
        actual = load(raw / '3090.json')
        assert {v['request_id']: v['seal_sha256'] for v in actual['sealed_Flash_requests']} == {
            v['request_id']: v['seal_sha256'] for v in load(raw / 'Flash-CPU.json')['result']['requests']}
        mains.extend(actual['sealed_main_requests'])
        flashes.extend(actual['sealed_Flash_requests'])
        failures.extend(actual['failed_requests'])
        controllers.extend(load(ctrl / 'GUI-collection.json')['result']['controllers'])
        summaries[group] = summary
    normal = [v for v in controllers if not v['terminal']['infrastructure_failure']]
    technical = [v for v in controllers if v['terminal']['infrastructure_failure']]
    assert len(normal) == 29 and len(technical) == len(failures) == 1
    normal_run_ids = {v['terminal']['run']['run_id'] for v in normal}
    assert normal_run_ids == {v['run_id'] for v in admission['terminals']}
    normal_ids = {v['request_id'] for v in registry['rows'] + registry['excluded_format_replies']}
    controller_normal = [v for c in normal for v in c['terminal']['actor_receipts']]
    controller_technical = [v for c in technical for v in c['terminal']['actor_receipts']]
    assert len(controller_normal) == len(normal_ids) == 520
    assert {v['request_id'] for v in controller_normal} == normal_ids
    technical_ids = {v['request_id'] for v in controller_technical}
    assert len(controller_technical) == len(technical_ids) == 27
    assert not normal_ids & technical_ids
    assert {v['request_id'] for v in mains} == normal_ids | technical_ids
    main_by_id = {v['request_id']: v for v in mains}
    for receipt in controller_normal + controller_technical:
        actual = main_by_id[receipt['request_id']]
        assert actual['folder'] == receipt['receipt']
        assert actual['wire_sha256'] == receipt['wire_sha256']
    for receipt in registry['rows'] + registry['excluded_format_replies']:
        assert main_by_id[receipt['request_id']]['seal_sha256'] == receipt['request_seal_sha256']
    normal_mains = [v for v in mains if v['request_id'] in normal_ids]
    assert len(normal_mains) == 520 and len(mains) == 547 and len(flashes) == 294
    assert len({v['request_id'] for v in mains}) == len(mains)
    trace = load(roots['trace'] / 'comparison.json')
    assert len(trace['pairs']) == 14 and all(v['both_noninfrastructure_sealed_terminals'] for v in trace['pairs'])
    run_labels = {v['run_id']: v for v in registry['runs']}
    pairs = []
    for pair in trace['pairs']:
        prefix = 'flash14-T%03d-%s-' % (pair['task_id'], pair['condition'])
        arms = {arm: run_labels[prefix + arm] for arm in ['baseline', 'gate']}
        a, b = (arms[k]['trajectory_semantic_Mirage'] for k in ['baseline', 'gate'])
        pairs.append({'task_id': pair['task_id'], 'condition': pair['condition'],
            'baseline': arms['baseline'], 'gate': arms['gate'],
            'complete_trace_equal': pair['complete_trace_equal'],
            'first_trace_difference': pair['first_difference'],
            'within_pair_reduction': None if a is None or b is None else a is True and b is False,
            'causal_reduction_inferred_from_different_initial_PNGs': False})
    zero = load(roots['zero_call_failure'] / 'summary.json')
    assert zero['attempted_calls'] == 0 and zero['preserved_failure']
    repair = HERE / 'approved-offline-receipt-repair-01'
    assert load(repair / 'CPU-binding-controls.json')['result']['passed'] == 12
    assert (repair / 'submission.json').exists()
    publication = HERE / ('GUI29-completed-publication-' + str(time.time_ns()))
    publication.mkdir()
    (publication / 'source.py').write_bytes(Path(__file__).read_bytes())
    status = {'time': time.time(), 'evidence': {k: {'root': str(v), 'seal_sha256': sha(v / 'seal.json')} for k, v in roots.items()},
        'logical_GUI_configurations_completed': 29, 'preserved_technical_attempts': 1,
        'paired_tasks': 7, 'conditions_per_task': ['clean', 'stale_replace'], 'paired_configurations': 28,
        'additional_unpaired_diagnostic': 1, 'normal_complete_replies': 520,
        'source_labels': 516, 'native_format_failures_not_semantic_zero': 4, 'pending_source_reviews': 0,
        'source_label_counts_are_coverage_not_rate': registry['source_label_counts'],
        'all_GUI_and_native_full_raw_Controller_audits_complete': True,
        'actual_original_GUI_model_launcher_exits_verified': True,
        'all_original_main_public_replies_including_technical_partial': 547,
        'technical_partial_public_replies_separate': len(mains) - len(normal_mains),
        'undelivered_natural_EOS_failure_generations_separate': len(failures),
        'all_Flash_replies_including_preserved_technical_attempt': len(flashes),
        'all_Flash_YES': sum(v['decision'] == 'YES' for v in flashes),
        'all_Flash_NO': sum(v['decision'] == 'NO' for v in flashes),
        'NO_recapture_path_not_naturally_exercised_in_this_corpus': all(v['decision'] == 'YES' for v in flashes),
        'complete_pairs': 14, 'identical_complete_trace_pairs': sum(v['complete_trace_equal'] for v in pairs),
        'source_reviewed_pairs': pairs, 'source_review_single_reviewer_not_fully_blind': True,
        'unresolved_not_no_Mirage': True, 'official_reward_not_semantic_truth': True,
        'different_initial_inputs_not_attributed_to_Flash': True,
        'first_offline_failure_attempts': 0, 'first_offline_failure_recorded_eight_GPU_seconds': zero['eight_GPU_reserved_seconds'],
        'first_offline_failure_cost_excludes_unmeasured_later_sealing_and_original_holder_intervals': True,
        'linked_offline_repair_submission': str(repair / 'submission.json'),
        'linked_offline_repair_manifest_sha256': sha(repair / 'package/offline-manifest.json'),
        'shared_approved_offline_maximum_calls': 10, 'formal_changed_GUI_authorized': False,
        'reserved_GPU_architecture_for_cost': 8, 'effectiveness_proven': False,
        'Mirage_reduction': None, 'goal': 'active', 'new_model_GPU_GUI_calls_by_publication': 0}
    save(publication / 'status.json', status)
    report = publication / 'Flash门控29条GUI完整审查-20261115.md'
    lines = ['# Flash门控29条GUI完整审查', '',
        '当前证据未证明降低Mirage。29个逻辑配置全部结束，原生输入、首次forward、原始概率、EOS、请求回复、Controller、终局文件和事件链已完成退出后全量核验。发生后的恢复与官方得分不删除错误，未决不当作阴性。', '',
        '范围为7个任务×clean/旧帧×baseline/gate共28配置，加1个非配对诊断；不是29个独立任务。520条正常终局回复均已入账：516条源审标签、4条原生格式失败，0条待源审。原技术attempt另保留27条公开主回复、1条未交付自然EOS生成及全部成本。', '',
        '| 任务 | 条件 | 基线整轨Mirage | 门控整轨Mirage | 完整trace相同 |',
        '|---|---|---|---|---|']
    for p in pairs:
        lines.append('| %03d | %s | %s | %s | %s |' % (p['task_id'], p['condition'],
            p['baseline']['trajectory_semantic_Mirage'], p['gate']['trajectory_semantic_Mirage'], p['complete_trace_equal']))
    lines += ['', 'None表示仍有未决判断或原生格式失败，不是没有Mirage。14个配对中11个完整body/历史/原PNG/回复/动作/后图均相同。其余配对的来源差异必须保留，不能把差异直接归因于Flash。', '',
        '最新源审：T114旧帧门控20号将历史末页概括为全是手机和船，与已提供的Asus ROG Ally、Video gaming冲突；全局最老仍未决。T125 clean门控2号把嵌入截图的$349.00读成$349.90；手机网页截图与任务中desktop一词的范围另保留未决。二者是有界叙述错误，不自动等于错误点击或任务官方失败。', '',
        '本次两运行根共294条Flash回复全部为YES，其中包含保留的技术attempt。图片可解释不保证时效、逐字读数、历史概括或完成判断正确；本批没有自然进入NO持续复拍，因此不证明该恢复路径有效，也不证明真实误拦率。辅助仍每次独立单图＋固定prompt，无主任务、主历史、候选、前帧或累计KV。', '',
        '部署成本按8张3090保留资源说明，不能把主模型调用秒当完整部署成本。10条离线首次attempt在加载后、第一条调用前因包装/内层回执误比较失败，实际0调用，记录区间795.26 GPU秒；封存和原holder区间未包含，不称完整成本或节省。原失败20文件和实际退出已封存。', '',
        '新关联技术attempt仅修正精确包装回执→原始CPU结果的绑定，12项来源/篡改控制通过。授权方案、原system增量292token、10个完整输入、每次2048输出、原种子/BF16/SDPA与0GUI/Flash/scorer/自动重试保持；旧调用0，授权总量仍最多10。正式新提示GUI未获授权。', '',
        '权威详细来源与SHA见同目录status.json；语义审查为同一审查者、非全盲，透明精确来源复用不增加独立样本。目标保持ACTIVE。', '']
    report.write_text('\n'.join(lines), encoding='utf8')
    archive = publication / 'previous-heads'
    archive.mkdir()
    head_paths = [HERE.parent / 'HANDOFF.md', HERE.parent / 'README.md', HERE / 'CONTINUATION.md', HERE / 'README.md']
    original_heads = {path: path.read_bytes() for path in head_paths}
    for i, path in enumerate(head_paths):
        (archive / ('%02d-%s' % (i, path.name))).write_bytes(original_heads[path])
    current_paths = [HERE / name for name in ['experiment-current.json', 'continuation-current.json', 'semantic-review-current.json']]
    for path in current_paths:
        if path.exists():
            (archive / path.name).write_bytes(path.read_bytes())
    save(publication / 'seal.json', {p.relative_to(publication).as_posix(): sha(p)
        for p in publication.rglob('*') if p.is_file()})
    state = {'publication': str(publication), 'report': str(report), 'seal_sha256': sha(publication / 'seal.json'),
        'time': time.time(), 'goal': 'active', 'effectiveness_proven': False}
    save(pointer, state)
    header = ('## 最新：29/29 GUI终局、520回复入账及全量退出审计完成；10条离线关联修复已提交\n\n'
        f'权威 {HERE.name}/{publication.name}/status.json 与 {report.name}。7任务×2条件×2臂+1诊断，516源标签+4格式失败，0待源审；父396公开主/199Flash/1未交付生成及新151主/95Flash完整raw和30GUI Controller均fresh核验。旧技术27公开回复/未交付生成/成本单列，绝不重跑终局、容量、父新完整审计。14配对11完整trace相同；其余初图不同不归因Flash。降低未证，未知非阴性、official非真值。\n\n'
        '批准10离线首attempt因本地包装SHA误比远端内层JSON，实际0调用失败，20文件/实际退出保全；权威offline10-postexit-audit-1794681468201898100。旧795.26记录GPU秒不含封存/holder区间。新approved-offline-receipt-repair-01 manifest223f9ac8565b39eade41116d881b26a36b14ced78020fc448946591c3077dd82，12新CPU来源/篡改控制通过，97文件已stage并once提交新关联command；原plan98d788.../全部10输入/+292/2048/种子/BF16/预算不变，原0调用+新最多10，不重问、不自动重复命令。实际运行以新inspect_offline_receipt_repair.py检查UID/fullcmd/start/18继承锁/UUID/compute/日志/journal/回执为准；不要用旧inspect或旧submit/launch。\n\n'
        '新离线退出后用audit_offline_receipt_repair_postexit.py再export_offline_receipt_repair_packets.py，先新源审后旧标签比较，失败先保全，不扩预算。正式改版GUI未授权。目标ACTIVE。以下为历史。\n\n')
    for path in head_paths:
        assert path.read_bytes() == original_heads[path]
        path.write_bytes(header.encode('utf8') + original_heads[path])
    for path in current_paths:
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'publication': str(publication), 'report': str(report), 'normal_replies': 520,
        'complete_pairs': 14, 'equal_complete_pairs': 11, 'effectiveness_proven': False}))


if __name__ == '__main__':
    main()
