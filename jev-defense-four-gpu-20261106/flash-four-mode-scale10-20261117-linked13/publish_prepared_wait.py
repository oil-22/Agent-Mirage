"""Publish actual prepared/staged resource wait, without claiming a new result."""
import json
import time
from pathlib import Path

from control import HERE, PACKAGE, manifest, save, sha
from join_reviewed_results import verify
from reserve_cumulative_accounting import counts_from_rows


def load_pointer(name):
    pointer = json.loads((HERE / name).read_bytes())
    return verify(pointer['root'], pointer['seal_sha256']), pointer


def main():
    assert not (HERE / 'prepared-publication-current.json').exists()
    assert not (HERE / 'service-submission.json').exists() and not (HERE / 'GUI-submission.json').exists()
    m = manifest()
    prep = json.loads((HERE / 'preparation-current.json').read_bytes())
    verify(prep['root'], prep['seal_sha256'])
    assert prep['manifest_sha256'] == sha(PACKAGE / 'manifest.json')
    qualification_root, qualification = load_pointer('CPU-routing-current.json')
    assert qualification['passed'] and qualification['manifest_sha256'] == prep['manifest_sha256']
    audit_root, audit_binding = load_pointer('audit-preparation-current.json')
    audited_files = json.loads((audit_root / 'result.json').read_bytes())['files']
    for name, digest in audited_files.items():
        assert sha(HERE / name) == digest, name
    guards_root, guards_binding = load_pointer('staged-parent-guards-current.json')
    for host in ['3090', '4090']:
        staged = json.loads((HERE / ('stage-' + host + '.json')).read_bytes())
        assert staged['result']['manifest_sha256'] == prep['manifest_sha256']
        guard = json.loads((guards_root / (host + '.json')).read_bytes())['result']
        assert guard['proof']['preserved_interruption_bound'] and guard['proof']['only_original_unstarted_26']
    resource_root, resource_binding = load_pointer('resource-admission-current.json')
    resource = json.loads((resource_root / 'result.json').read_bytes())['result']
    assert resource['state'] == 'waiting_exclusive_eight_GPUs' and resource['eligible_for_first_submission'] is False
    parent_binding = m['unstarted_parent_binding']
    parent_root = verify(parent_binding['root'], parent_binding['seal_sha256'])
    parent_report = json.loads((parent_root / 'report.json').read_bytes())
    counts = counts_from_rows(parent_report['cumulative_rows'])
    assert counts == m['prior_verified_per_condition']
    failure = next(HERE.glob('cpu-unstarted26-qualification-failure-*'))
    repair = next(HERE.glob('cpu-unstarted26-copy-repair-*'))
    verify(failure); verify(repair)
    root = HERE / ('prepared-wait-publication-' + str(time.time_ns())); root.mkdir()
    before = root / 'before'; before.mkdir()
    parent = HERE.parent / 'flash-four-mode-scale10-20261116-12'
    heads = [HERE / 'README.md', HERE / 'HANDOFF.md', HERE / 'REVIEW_HANDOFF.md',
             parent / 'README.md', parent / 'HANDOFF.md', parent / 'REVIEW_HANDOFF.md',
             HERE.parent / 'README.md', HERE.parent / 'HANDOFF.md',
             HERE.parent / 'active-defense-goal-current.json']
    for index, path in enumerate(heads):
        if path.exists():
            (before / (str(index) + '-' + path.name)).write_bytes(path.read_bytes())
    value = {'state': 'original26_unstarted_prepared_staged_waiting_exclusive_eight_GPUs',
        'active_study': str(HERE), 'goal_active': True, 'goal_tool_status_is_authoritative': True,
        'manifest_sha256': prep['manifest_sha256'], 'preparation': prep,
        'parent_interrupted_report_binding': parent_binding,
        'prior_actual_rows': 24, 'prior_attempted_rows_from_interrupted_campaign': 14,
        'prior_successes_per_mode': counts, 'cumulative_target_per_mode': 10,
        'new_unstarted_trajectories': 26, 'per_injection_unstarted': 5, 'clean_controls': 6,
        'task_ids': [17, 58, 89, 94, 112, 131],
        'CPU_qualification_binding': qualification, 'auditor_source_binding': audit_binding,
        'staged_parent_guard_binding': guards_binding, 'resource_binding': resource_binding,
        'copy_failure_preserved': {'root': str(failure), 'seal_sha256': sha(failure / 'seal.json')},
        'copy_repair_binding': {'root': str(repair), 'seal_sha256': sha(repair / 'seal.json')},
        'new_GPU_lease': False, 'models_submitted': False, 'GUI_submitted': False,
        'watcher_exec_session': None, 'old_watcher1198_exited_do_not_poll': True,
        'new_model_GUI_calls': 0, 'new_verified_successes': 0,
        'same_full_history_BF16_native_budget_and_single_image_Flash': True,
        'no_old_terminal_or_queue_rerun': True, 'source_NO_is_Flash_detection': False,
        'population_Mirage_reduction_proven': False,
        'next_actions': [
            'Run inspect_admission_wait.py read-only; if existing launch evidence, inspect actual runtime and never submit again.',
            'Only when all8 are empty/free>=23000MiB/no held locks, control.py submit ONCE. It rechecks resource ownership and inherits all17 locks. Never stage again.',
            'After actual model readiness and inspect_owned_runtime.py actual UID/fullcmd/start/17locks, control.py gui ONCE, audit_gui_site_lock.py running, then a fresh foreground read-only watcher. Record its new exec session.',
            'Keep every failure/untriggered/infra row; perform per-trajectory raw/image audits, then complete26 group raw union, release/site locks and eight-GPU cost, join_reviewed_results.py and write_reserve_report.py.',
            'Only after the original26 are all terminal/audited/released/reported, select the next unused presealed reserve task146 (then155,171,187,198,204,231,232) for deficient modes plus clean.',
            'Before future reserve preparation, adapt the dormant reserve draft paths to original reader/join staging roots and bind its inherited26 interruption queue assertion to the immutable current-unstarted-plan, not the new reserve queue. Qualify only metadata/AST changes; no core changes or old model control reruns.',
            'Keep goal ACTIVE until every mode>=10 and all attempts/normal controls/raw/image audits/cost/releases/final audit are complete.'
        ]}
    save(root / 'publication.json', value)
    counts_text = '/'.join(str(counts[c]) for c in ['silent_drop', 'blank_replace', 'stale_replace', 'buttons_only'])
    header = f'''## 2026-11-17 原26未开续跑包已准备并stage：累计{counts_text}，等待8卡，目标ACTIVE

当前有效目录 `{HERE}`，manifest `{prep['manifest_sha256']}`。原中断14条终局和此前10条全部保留；累计24行，缺图/白图/旧帧/按钮成功仍为{counts_text}。新包仅原封顺序的26个未开：T017 clean，加T058/T089/T094/T112/T131各四注入与clean，共每注入5条＋6clean。原已完成/未触发/契约失败/基础设施终局均不重跑。

CPU元数据/source/AST审查通过；全部主/Flash/采集/注入/完整历史/精度/动作/原生parser/预算字节保持，raw COMMON/PRIMARY/FLASH及strict_bind和整段原图验收循环保持。首次CPU资格因文本复制改写行尾而失败，旧脚本/失败已seal，仅把无语义变化的脚本恢复为原字节，随后资格通过；封存运行包未改，0新模型/GUI调用。两端104文件已stage并实测新guard绑定“13非基础设施＋1技术中断、26未开”、所有旧身份退出和旧终局SHA，未把父批假称完成。

目前仅3090 GPU4-7空、每卡24253MiB；0-3实际UID1006外部compute。新8卡租约未取得，未submit模型、未启动GUI/新watcher。不要再stage；旧watcher1198已exit1且禁止再poll/重开。先运行新目录inspect_admission_wait.py；资源满足且无launch证据才control.py submit一次；实际ready与17继承锁核验后才gui一次及新前台watcher。保留7主＋1Flash/BF16/完整输入，禁止抢外人或改用缩短输入。

权威 prepared-publication-current.json 及其中完整next_actions。先完成并审完原26未开、成本/释放/报告，之后才按原备用顺序补各模式缺口；源端自己签坏图仍在已证范围外，来源NO不称Flash视觉检出。以下旧快照保留。

'''
    report_text = f'''# 四种注入每种十条：原26未开队列准备与资源等待

累计已核验完整截图恢复成功：缺图{counts['silent_drop']}、白图{counts['blank_replace']}、旧帧{counts['stale_replace']}、仅按钮{counts['buttons_only']}。本次准备不新增成功数。

原中断队列的14条终局全部保留；新linked13只运行其原始26未开，顺序和任务不变，每种注入5条和6条clean。两端stage和新父绑定守卫已实际核验，尚未分配GPU或调用模型。

CPU核对发现无改动的审计器被文本复制改写CRLF行尾，失败脚本已封存；只恢复原字节后通过。运行包、原算法和条件均未改变。

当前3090仅4-7卡空，0-3卡有UID1006外部compute。继续等待原7主＋1Flash的8卡独占资源；不共享/抢占、不缩减输入/精度。完整成功要逐轨证明拒绝坏图→真实同live复拍→新签名挑战→单图Flash YES→正常原PNG进入主完整历史→原生有效动作或STOP，并审完终局、raw/image证据和资源成本。

缺图前检、来源回执拒绝、Flash视觉NO分别计数；来源NO不能称Flash识别旧帧。保留所有失败、未触发、正常对照和版本。达到每种至少10条且完成最终审计前，目标保持ACTIVE。
'''
    (root / '原26未开续跑包与资源等待-20261117.md').write_text(report_text, encoding='utf8')
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    (root / 'admission-reader-source.py').write_bytes((HERE / 'inspect_admission_wait.py').read_bytes())
    save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file()})
    pointer = {'root': str(root), 'seal_sha256': sha(root / 'seal.json'), **value}
    save(HERE / 'prepared-publication-current.json', pointer)
    for path in [HERE.parent / 'active-defense-goal-current.json', parent / 'unstarted-continuation-current.json']:
        temp = path.parent / ('.linked26-publication-' + str(time.time_ns())); save(temp, pointer); temp.replace(path)
    for index, path in enumerate(heads[:-1]):
        snapshot = before / (str(index) + '-' + path.name)
        previous = snapshot.read_text('utf8') if snapshot.exists() else ''
        path.write_text(header + previous, encoding='utf8')
    print(json.dumps({'root': str(root), 'state': value['state'], 'prior_counts': counts,
        'new_model_GUI_calls': 0, 'new_successes': 0, 'goal_active': True}))


if __name__ == '__main__':
    main()
