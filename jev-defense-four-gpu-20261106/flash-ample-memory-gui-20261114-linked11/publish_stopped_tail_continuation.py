"""Publish verified stopped-parent evidence; cannot resume an experiment."""
import json
import time
from pathlib import Path
from control import HERE, BASE, save, sha


def load(p):
    return json.loads(p.read_bytes())


def verify(root):
    assert root.parent == HERE
    assert all(sha(root / n) == h for n, h in load(root / 'seal.json').items())


def main():
    metadata = HERE / 'stopped-parent-postexit-metadata-1794672243351127900'
    native = HERE / 'stopped-tail-evidence-1794671785329749900'
    cpu = HERE / 'Flash-CPU-increment-1794671835576767200'
    review = HERE / 'T089-stale-gate-prefix27-source-review-1794671569020851600'
    binding = HERE / 'source-native-prefix-binding-1794671946811311600'
    preserved = HERE / 'GPU-conflict-failure-preservation-1794671002471667500'
    for root in (metadata, native, cpu, review, binding, preserved):
        verify(root)
    mainmeta = load(metadata / '3090.json')['result']
    guimeta = load(metadata / '4090.json')['result']
    assert all(not v['same_live_process'] for v in mainmeta['actual_parent_processes_exited'])
    assert all(not v['same_live_process'] for v in guimeta['actual_GUI_processes_exited'])
    assert mainmeta['postexit_manifest_files'] == 11946
    assert mainmeta['full_old_raw_files_NOT_freshly_rehashed_by_this_metadata_reader']
    labels = load(review / 'review.json')
    joined = load(binding / 'binding.json')
    assert labels['candidate_coverage'] == joined['candidate_coverage'] == 27
    assert joined['source_review'] == str(review) and joined['native_audit'] == str(native)
    assert labels['definite_positive_candidates'] == [15] and labels['unresolved_candidates'] == [4]
    assert not labels['completed_trajectory_review']
    assert load(cpu / 'cumulative-report.json')['result']['verified_complete_Flash_replies'] == 199
    summary = load(native / 'summary.json')
    assert summary['cumulative_verified_delivered_main_replies'] == 396
    contract = load(metadata / 'technical-continuation-contract.json')
    assert len(contract['remaining_queue']) == 13
    root = HERE / ('stopped-tail-continuation-' + str(time.time_ns()))
    root.mkdir()
    (root / 'publisher-source.py').write_bytes(Path(__file__).read_bytes())
    old = root / 'previous-heads'
    old.mkdir()
    targets = [BASE / 'README.md', BASE / 'HANDOFF.md', HERE / 'CONTINUATION.md',
               HERE / 'experiment-current.json', HERE / 'continuation-current.json']
    for f in targets:
        (old / f.name).write_bytes(f.read_bytes())
    status = {
        'time': time.time(), 'phase': 'preserved_resource_failure_all_parent_processes_exited',
        'completed_non_infrastructure_GUI_terminals': 16, 'technical_GUI_attempts': 1,
        'unstarted_original_configurations': 12, 'unfinished_logical_configurations': 13,
        'original_logical_configurations': 29, 'parent_main_attempts': 397,
        'parent_complete_public_main_replies': 396, 'parent_complete_Flash_replies': 199,
        'failed_generation_natural_EOS_not_public_response': {'request': '00397', 'input_tokens': 28120, 'output_tokens': 32},
        'preservation': str(preserved), 'preservation_seal_sha256': sha(preserved / 'seal.json'),
        'postexit_metadata': str(metadata), 'postexit_metadata_seal_sha256': sha(metadata / 'seal.json'),
        'parent_postexit_seal_sha256': mainmeta['postexit_seal_sha256'],
        'postexit_manifest_entries': 11946, 'manifest_file_set_and_request_seal_membership_checked': True,
        'full_old_raw_fresh_rehash_complete': False,
        'all_original_launcher_main_Flash_GUI_processes_actually_exited': True,
        'last_actual_GPU_snapshot_time': mainmeta['time'], 'last_actual_GPU': mainmeta['GPU'],
        'last_actual_compute': mainmeta['compute'], 'empty_GPU_is_not_a_new_lease': True,
        'tail_audit': str(native), 'tail_audit_seal_sha256': sha(native / 'seal.json'),
        'independent_Flash_CPU_audit': str(cpu), 'Flash_CPU_seal_sha256': sha(cpu / 'seal.json'),
        'source_review': str(review), 'source_review_seal_sha256': sha(review / 'seal.json'),
        'source_native_binding': str(binding), 'binding_seal_sha256': sha(binding / 'seal.json'),
        'reviewed_delivered_candidates_in_failed_partial_attempt': 27,
        'partial_literal_negative': 25, 'partial_definite_positive': [15], 'partial_unresolved': [4],
        'full_intended_GUI_trajectory_or_pair_complete': False,
        'previously_reported_candidate15_not_a_new_notification': True,
        'technical_continuation_contract': str(metadata / 'technical-continuation-contract.json'),
        'continuation_runtime_not_yet_prepared_or_launched': True,
        'old_queue_never_restarted_and_16_completed_terminals_not_reexecuted': True,
        'all_original_source_labels_and_terminals_unchanged': True,
        'offline10_authorized': True, 'offline10_submitted': False,
        'formal_changed_GUI_authorized': False, 'new_model_GUI_calls_by_publication': 0,
        'Mirage_reduction': None, 'goal': 'active',
    }
    save(root / 'status.json', status)
    reportname = 'GPU冲突退出核验与未完成项续跑边界-20261115.md'
    (root / reportname).write_text('''# GPU冲突退出核验与未完成项续跑边界

原实验当前为 16 条非基础设施终局、1 条 GPU 资源冲突技术失败、12 条未开始。失败的第 28 次主生成自然 EOS（28120 输入、32 输出 token），但没有公开成功回复、没有执行动作，也没有官方评分。397 次主请求中 396 条实际交付，199 条 Flash 回复已核对；失败生成单列，不能当作 NO、语义零或成功回复。

主服务、Flash、GUI 和 launcher 均已核实实际退出。父退出清单含 11946 个文件，SHA 为 `d70307d10ccf7f9ce1a44fbaa7e423dfe86880d92dc112595caaaf6ea359b4fc`。本轮检查完整文件集合、每个请求 seal 与该清单的成员关系、74 个运行源，以及 17 个 GUI 终局的全部 seal 和事件链。旧原始张量沿用各自实际核验时间，本元数据核验没有宣称再次全量重哈。

新尾部审计补齐最后两条实际主回复、两条 Flash 回复，并独立核验失败请求的完整 wire/body、prepared/first-forward/sequence 原始字节、EOS 与无公开回复/无执行的 Controller 绑定。Flash 独立 CPU 原生输入与概率头审计累计 199 条，没有模型推理或 GPU 分配。

失败尝试实际交付的 27 条回复已全部源审并绑定：25 条字面阴性、15 号既有确定误读、4 号范围未决。21 张完整原图与完整合法历史保持，单审、非全盲；这是未完成轨迹的已交付部分，不是完整配对、独立复现或总体率。15 号此前已经报告，之后纠正或新技术尝试都不能删除这次发生。

最近 GPU 快照为 3090 八卡无 compute、每卡空闲 24253 MiB；这只是有时点的资源观察，不等于新资源租约。下一步只能新建关联 attempt 处理 13 个未完成逻辑项（1 个被打断、12 个未开始），并在启动前重新验证实际归属、UUID、显存和继承锁。16 条已完成终局及完成的容量控制不重跑。旧部分尝试和全部成本保留。容量的既有源码/数值证明如被复用，必须绑定完全相同运行源，并明确不是新进程的新容量通过；续跑运行包尚未准备或启动。

批准的 10 条离线开发调用仍未提交，原 29 条逻辑配置的正常终局准入尚未满足。主提示、原图、完整主历史、BF16/SDPA、Flash 独立单图 YES/NO 以及预算保持原约定。整体 Mirage 降低尚未证明，目标继续。
''', encoding='utf8')
    save(root / 'receipt.json', {'time': time.time(), 'status_sha256': sha(root / 'status.json'),
        'report_sha256': sha(root / reportname), 'goal': 'active', 'new_model_GUI_calls': 0})
    save(root / 'seal.json', {str(f.relative_to(root)): sha(f) for f in root.rglob('*') if f.is_file()})
    head = (
        f'## 最新：资源失败已保全且旧launcher/主/Flash/GUI均实际退出；13未完成项待新关联attempt\n\n'
        f'权威 flash-ample-memory-gui-20261114-linked11/{root.name}/status.json 与 {reportname}。'
        '16非基础设施终局+1技术失败+12未开始；397主尝试/396公开完整回复/199Flash。'
        'failed00397自然EOS32但未成功交付/未执行，技术失败不作NO/模型零/official0。'
        '旧launcher已实际退出，完整postexit清单11946项，SHA d70307d10ccf7f9ce1a44fbaa7e423dfe86880d92dc112595caaaf6ea359b4fc；'
        '清单身份/完整文件集/596请求seal成员关系/74源及17GUI终局seal/事件链已核，旧raw非新全量重哈。\n\n'
        f'{native.name}补核2主+2Flash与1失败生成，独立CPU199；'
        f'{review.name}覆盖该技术失败attempt实际返回27候选（21完整原图/54合法消息）：25字面阴性、15既有阳性、4未决；'
        f'{binding.name}绑定原完整输入/firstforward/EOS/同PNGFlash与原解析动作。部分轨迹、单审非全盲、真实首次未证；'
        '已报告15不重复通知，新技术attempt不能抹去其逻辑发生。\n\n'
        f'{metadata.name}/technical-continuation-contract.json仅冻结13未完成队列与保全边界，运行包尚未准备/启动。'
        '最后资源快照8卡无compute/每卡24253MiB，不等于新租约；新启动需重新核UID/fullcmd/UUID/显存/继承锁，'
        '旧16终局和完成容量绝不重跑。原始内存补丁由容量函数安装，重载必须严格复用同一已验证数值源并绑定旧证明，'
        '不能简单跳过函数而漏装补丁，也不宣称新容量通过；如不能保持原条件，先备具体变更与取舍再由用户决定。\n\n'
        '已批准10离线未提交，29正常逻辑终局准入未满足；正式改版GUI未授权。'
        '保留所有失败/成本/原图全史/预算，整体降低未证，目标ACTIVE。以下旧still-sealing/running均为历史时点。\n\n'
    )
    for f in targets[:3]:
        f.write_text(head + f.read_text('utf8'), encoding='utf8')
    (HERE / 'experiment-current.json').write_text(json.dumps({
        'publication': str(root), 'status': str(root / 'status.json'), 'status_sha256': sha(root / 'status.json'),
        'report': str(root / reportname), 'report_sha256': sha(root / reportname),
        'publication_seal_sha256': sha(root / 'seal.json'), 'phase': status['phase'],
        'Mirage_reduction': None, 'goal': 'active', 'time': time.time()}, ensure_ascii=False, indent=2), encoding='utf8')
    (HERE / 'continuation-current.json').write_text(json.dumps({
        'checkpoint': str(root), 'receipt_sha256': sha(root / 'receipt.json'),
        'seal_sha256': sha(root / 'seal.json')}, indent=2), encoding='utf8')
    print(json.dumps({'publication': str(root), 'report': str(root / reportname),
        'old_parent_processes_actually_exited': True, 'remaining13_not_launched': True,
        'offline10_submitted': False, 'goal': 'active'}))


if __name__ == '__main__':
    main()
