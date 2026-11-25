"""Publish qualified future operational preparation, with no experiment claims."""
import json
import time
from pathlib import Path

from control import HERE, PACKAGE, save, sha
from join_reviewed_results import verify


def main():
    assert not (HERE / 'service-submission.json').exists() and not (HERE / 'GUI-submission.json').exists()
    assert not (HERE / 'reserve-readiness-publication-current.json').exists()
    previous = json.loads((HERE / 'prepared-publication-current.json').read_bytes())
    verify(previous['root'], previous['seal_sha256'])
    draft = json.loads((HERE / 'future-reserve-preparer-current.json').read_bytes())
    draft_root = verify(draft['root'], draft['seal_sha256'])
    result = json.loads((draft_root / 'result.json').read_bytes())
    assert result['current_runtime_package_and_auditors_unchanged']
    assert result['actual_reserve_plan_or_campaign_created'] is False
    assert result['reserve_task_claimed'] is False and result['new_model_GUI_calls'] == 0
    assert sha(draft['preparer_path']) == draft['preparer_sha256']
    assert sha(PACKAGE / 'manifest.json') == previous['manifest_sha256'] == result['current_staged_manifest_sha256']
    resource = json.loads((HERE / 'resource-admission-current.json').read_bytes())
    resource_root = verify(resource['root'], resource['seal_sha256'])
    admission = json.loads((resource_root / 'result.json').read_bytes())['result']
    assert admission['state'] == 'waiting_exclusive_eight_GPUs' and admission['eligible_for_first_submission'] is False
    root = HERE / ('reserve-readiness-publication-' + str(time.time_ns())); root.mkdir()
    before = root / 'before'; before.mkdir()
    parent = HERE.parent / 'flash-four-mode-scale10-20261116-12'
    heads = [HERE / 'README.md', HERE / 'HANDOFF.md', HERE / 'REVIEW_HANDOFF.md',
        HERE.parent / 'README.md', HERE.parent / 'HANDOFF.md',
        parent / 'README.md', parent / 'HANDOFF.md', parent / 'REVIEW_HANDOFF.md']
    active = HERE.parent / 'active-defense-goal-current.json'
    for index, path in enumerate([*heads, active]):
        if path.exists():
            (before / (str(index) + '-' + path.name)).write_bytes(path.read_bytes())
    value = {key: val for key, val in previous.items() if key not in ['root', 'seal_sha256']}
    value.update(previous_prepared_publication={'root':previous['root'],'seal_sha256':previous['seal_sha256']},
        resource_binding=resource, future_reserve_preparer_binding=draft,
        previous_goal_turn_classification='progress: exact26 prepared/qualified/staged, resource wait verified',
        current_goal_turn_classification='progress: required future reserve path/ancestor compatibility qualified',
        current_model_GUI_success_counts_unchanged=True,
        pending_resource_blocker='same eight-GPU exclusivity gate; foreign UID1006 onGPU0-3; only4-7 empty',
        useful_operational_preparation_remaining=False)
    value['next_actions'] = [
        'Run inspect_admission_wait.py; inspect existing launch evidence without submitting again. Never stage again.',
        'If and only if eight empty/free>=23000MiB and no held locks, control.py submit once. Recheck and inherit fresh owned17 locks; keep7main+1Flash/BF16/full history.',
        'After actual ready and inspect_owned_runtime.py verifies UID/fullcmd/start/17locks, control.py gui once; audit_gui_site_lock.py running; launch one fresh foreground watcher and record its new exec handle.',
        'Complete original26 with every failure/untriggered terminal preserved; full raw/image audits, normal controls, terminal group/release/site lock/eightGPU cost, join_reviewed_results.py and write_reserve_report.py.',
        'Only then run plan_reserve_after_terminal.py. Use qualified prepare_reserve_after_current.py <sealed-plan-root> <fresh-reserve-study-name> from this linked13 directory for every future reserve, including later reserve parents; do not use the old draft with relative staging roots.',
        'Next unused presealed reserve order146,155,171,187,198,204,231,232; only deficient modes plus clean. New reserve package still needs qualify_reserve_campaign.py and actual free owned8GPU admission.',
        'No new model result here. Success remains4/4/3/3; all>=10 plus full final audit still required. Goal is active; if the same resource blocker persists with no safe progress, apply the goal blocked audit after its threshold.'
    ]
    save(root / 'publication.json', value)
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file()})
    pointer = {'root':str(root),'seal_sha256':sha(root/'seal.json'),**value}
    save(HERE / 'reserve-readiness-publication-current.json', pointer)
    for path in [active, HERE / 'continuation-current.json', parent / 'unstarted-continuation-current.json']:
        temporary=path.parent/('.reserve-readiness-'+str(time.time_ns()));save(temporary,pointer);temporary.replace(path)
    header = f'''## 2026-11-17 备用队列兼容预备器已核验；原26仍等8卡，0新调用

当前有效目录仍 `{HERE}`，原stage manifest `{previous['manifest_sha256']}` 未改，累计缺图/白图/旧帧/按钮4/4/3/3。当前仅3090 GPU4-7空、0-3实际UID1006外部compute；无新GPU租约/主/Flash/GUI/watcher，旧exec1198不可poll/restart。先运行inspect_admission_wait.py；满足原8卡独占条件才submit一次，真实ready与17锁后gui一次。原26未开队列和顺序不变，不再stage。

为达各10必需的后续备用预备器现已完成纯元数据兼容检查：`prepare_reserve_after_current.py` 修正静态reader/join根目录，并把继承的中断26队列绑定到原封current-unstarted-plan而非未来备用队列；保留所有原祖先文件/身份检查和运行时算法。CPU实测2/3/4/5条备用形状保留原26绑定、损坏祖先仍拒绝、当前未完成队列在claim/SSH前拒绝。未创建/预占任何真实备用任务或包，0模型/GUI调用；这不是新防御效果。

权威 continuation-current.json / reserve-readiness-publication-current.json，future-reserve-preparer-current.json 指向完整资格与固定脚本SHA。原26全终局/全审/成本/释放/报告之后，才运行plan_reserve_after_terminal.py，再从本linked13目录调用已资格的prepare_reserve_after_current.py来准备下一个原预封备用任务（146起）；每个新包仍需单独CPU资格与8卡实际租约。原未适配prepare_reserve_campaign.py草稿不直接使用。目标ACTIVE，等待外部资源变化；若连续阻塞审计阈值满足且已无安全推进动作，按goal规则标blocked。

以下旧快照保留。

'''
    for index, path in enumerate(heads):
        snapshot=before/(str(index)+'-'+path.name)
        path.write_text(header+(snapshot.read_text('utf8') if snapshot.exists() else ''),encoding='utf8')
    print(json.dumps({'root':str(root),'resource_state':admission['state'],
        'future_reserve_compatibility_qualified':True,'new_model_GUI_calls':0,
        'new_successes':0,'goal_active':True}))


if __name__ == '__main__':
    main()
