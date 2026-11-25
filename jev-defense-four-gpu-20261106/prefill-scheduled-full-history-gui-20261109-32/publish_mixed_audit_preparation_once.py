"""Publish mixed-audit implementation and its bounded actual compatibility."""
import argparse
import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import time

from publish_source_progress22_once import BASE, HERE, read, save, sha, verify_folder


def main(evidence):
    pointer = HERE / 'mixed-audit-preparation-publication-created.json'
    assert not pointer.exists()
    verify_folder(evidence)
    service, gui = read(evidence / '3090.json'), read(evidence / '4090.json')
    authorities = {}
    for name in ['mixed-audit-selection-controls-created.json', 'mixed-tensor-source-preparation-created.json']:
        record = read(HERE / name)
        verify_folder(record['root'], record['seal_sha256'])
        assert sha(Path(record['root']) / 'receipt.json') == record['receipt_sha256']
        authorities[name] = record
    compatibility = []
    for folder_name in ['mixed-receipt-audit-1794246218838928100', 'mixed-receipt-audit-1794246577165072700']:
        root = HERE / folder_name
        verify_folder(root)
        receipt = read(root / 'receipt.json')
        assert receipt['passed'] and not receipt['actual_enabled_mixed_branch_observed']
        assert not receipt['runtime_modified'] and receipt['new_model_GUI_scorer_paid_calls'] == 0
        compatibility.append(dict(root=str(root), receipt_sha256=sha(root / 'receipt.json'), seal_sha256=sha(root / 'seal.json')))
    actors = read(Path(compatibility[1]['root']) / '4090-GUI-bindings.json')['actor_insertions']
    assert len(actors) == 1 and actors[0]['request'] == '0072'
    assert actors[0]['complete_original_message_count'] == 75 and actors[0]['original_image_blocks'] == 37
    rows, audits = [], []
    for p in [HERE / 'prefix-audit-created.json'] + sorted(p for p in HERE.glob('new-replies-*-audit-created.json')
            if re.fullmatch(r'new-replies-\d+-audit-created\.json', p.name)):
        record = read(p)
        path = Path(record['audit'])
        verify_folder(path.parent)
        assert sha(path) == record['audit_sha256']
        audit = read(path)
        assert audit['passed']
        if int(audit['requests'][0]['request']) > 87:
            continue
        assert int(audit['requests'][-1]['request']) <= 87
        rows.extend(audit['requests'])
        audits.append(record)
    rows.sort(key=lambda row: row['request'])
    assert [row['request'] for row in rows] == [str(i).zfill(4) for i in range(1, 88)]
    assert all(row['natural_EOS'] for row in rows)
    totals = dict(requests=87, actor_replies=21, judge_replies=66, auxiliary_replies=0, natural_EOS_replies=87,
        input_tokens=sum(row['actual_input_tokens'] for row in rows), output_tokens=sum(row['output_tokens'] for row in rows),
        summed_native_call_timer_seconds=sum(row['native_call_timer_seconds'] for row in rows),
        scope='Only sealed new32native1..87, including original instrumentation/transfers. Excludes failures/ongoing work, other roots, load and outside-holder reservation. Not walltime/currency/energy/savings.')
    assert sum(row['operation'] == 'actor' for row in rows) == 21
    assert sum(row['operation'] == 'judge' for row in rows) == 66
    old = read(BASE / 'full-gui-current.json')
    assert old['native_request_tensor_EOS_and_prefill_audit_completed_through_new32_request'] == '0081'
    out = HERE / ('mixed-audit-preparation-publication-' + str(time.time_ns()))
    out.mkdir()
    previous = out / 'previous-heads'
    previous.mkdir()
    before = {}
    for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']:
        (previous / name).write_bytes((BASE / name).read_bytes())
        before[name] = sha(BASE / name)
    status = copy.deepcopy(old)
    status.update(schema='GUI32-composed-mixed-provenance-audit-prepared-v1', time=time.time(), goal='active',
        previous_goal_turn_classification='Progress: new77..81 audited without overlap; published sealed original-budget lower bound and isolated Controller recovery preparation. Prompt disclosure itself did not establish efficacy.',
        current_goal_turn_classification='Progress: implemented complete mixed audit composition, passed15new selection/journal CPU controls, source-derived native metadata including82float32 buffer elements per model, verified actual noaux72actor and82judge native/HTTP and full75message37image actor insertion. Audited only new82..87. No inference reruns or runtime condition changes.',
        previous_heads_SHA256=before, monitor_should_remain_active=True, efficacy_established=False,
        relative_Mirage_reduction=None, native_request_tensor_EOS_and_prefill_audit_completed_through_new32_request='0087',
        new32_audited_completed_prefix_totals=totals)
    status['composed_mixed_audit'] = dict(implementation_prepared=True, actual_enabled_branch_audited=False,
        new_CPU_selection_controls=15, source_reconstruction_only_not_new_visual_controls=True,
        actual_noaux_compatibility=compatibility, newly_independently_tokenizer_decoded_original_requests=['0072', '0082'],
        all87independently_redecoded=False, actual_noaux_actor_messages=75, actual_noaux_actor_original_images=37,
        original_lawful_history_trailing_corrections_and_single_data_block_bound=True,
        original_stage_copies_preserved=True, buffer_aware_source_preparation=authorities['mixed-tensor-source-preparation-created.json'],
        primary_and_auxiliary_native_float32_buffer_elements_each=82,
        native_meta_not_weight_load_or_GPU_inference=True, native_mask_choices_independently_recomputed=False,
        current_GPU_tensor_values_independently_hashed=False, new_model_GUI_scorer_paid_calls=0,
        semantic_truth_or_efficacy_established=False)
    status['authorities'].update(mixed_audit_preparation=authorities, mixed_audit_actual_noaux_compatibility=compatibility,
        latest_nonoverlapping_native_request_audits=audits,
        latest_actual_UID_locks_requests_chains=dict(path=str(evidence), seal_sha256=sha(evidence / 'seal.json')))
    for key, name in [('actual_service_state_at_snapshot', 'worker/status.json'),
                      ('actual_worker_identity_at_snapshot', 'worker/process.json'),
                      ('actual_launcher_identity_at_snapshot', 'launcher-process.json')]:
        status[key] = service[name]['value']
    status['actual_GUI_state_at_snapshot'] = gui['batch/status.json']['value']
    status['actual_GUI_runner_identity_at_snapshot'] = gui['control/runner-process.json']['value']
    status['service_event_chains'], status['GUI_event_chains'] = service['chains'], gui['chains']
    status['new32_sealed_requests_at_snapshot'], status['new32_terminals_at_snapshot'] = service['sealed_requests'], gui['terminals']
    status['storage_at_snapshot'] = dict(service=service['filesystem'], GUI=gui['filesystem'],
        whole32storage_fit_not_guaranteed=True, no_original_files_deleted_moved_compressed=True)
    status['next_action'] = ('Keep same frozen32 worker; source-review new actor candidates before current checker/execution joins. '
        'Audit only88+ next. The first actual enabled actor must be audited with audit_mixed_receipts_once.py and automatically '
        'include its immediately preceding original auxiliary, mapped primary-only prefill session and full original GUI context. '
        'Do not count stage compatibility as actual enabled success. Preserve all originals; inspect additional persistent storage '
        'availability without evicting any task or deleting/moving old evidence. Full32/16matched efficacy remains unverified; goal active.')
    save(out / 'status.json', status)
    date = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    note = ('## 最新：' + date + ' 混合来源审计包装已准备；实际无辅助75消息/37图插入及双机HTTP通过；enabled仍待真实调用\n\n'
        '权威 `' + (out / 'status.json').relative_to(BASE).as_posix() + '`。新包装组合原生IDs/tensors/generation、HTTP原始字节、'
        '辅助单图固定prompt/首KV0/释放、GPU切换和完整主历史插入；按primary-only session选prefill，不使用混合global编号。'
        '15项新选择/串联CPU控制通过；实际原72actor与82judge已只读验证原生输入输出及双机传输，原72的75消息/37完整图与末尾纠错、'
        '单一数据块插入通过。原控制没有重推/新增计数。actual enabled整链仍UNOBSERVED，不计辅助收益。\n\n'
        '已补足来源元数据中的原生非持久buffer：单靠state_dict不覆盖3个buffer。原生meta实例分别保留82个float32元素，'
        '27B匹配当前封存loaded CUDA布局、9B匹配旧实际CUDA布局；其余原BF16保持。这只证明原生元数据，未加载权重/启动CUDA/新推理，'
        '不是当前GPU tensor值全量哈希。之前stage副本仍封存。独立tokenizer仅具体回执所列请求，不是87全覆盖。\n\n'
        '新32已不重叠审计87自然EOS=21actor+66judge，0aux，累计' + str(totals['input_tokens']) + 'input/'
        + str(totals['output_tokens']) + 'output，' + str(round(totals['summed_native_call_timer_seconds'], 3))
        + 'summed native计时秒，不是walltime/货币/能耗或收益。snapshot实际UID/fullcmd/start、4–7独占compute/九锁和双链已核；'
        '执行仍36、候选审查至38，完整轨' + str(gui['batch/status.json']['value']['completed']) + '/32。'
        '当前历史价格分支继续原预算，不热改冻结32；隔离预算恢复副本未部署。辅助仍9B基座/decision_adapter_loaded=false。'
        '全32存储尚未保证；不删/移/压缩原件、不占外人资源。轨级Mirage/误拦/任务成功和配对效果均未建立，目标ACTIVE。\n\n')
    (out / 'new-head.md').write_text(note, encoding='utf8')
    report = ('# 混合来源审计接线与使用\n\n' + note[note.index('权威 '):]
        + '\n首次开启辅助后，先巡检同一活进程并取得不可变actual-evidence回执，再调用：\n\n'
        + '```powershell\n& "D:\\MultiModel\\MultiModelenv\\Scripts\\python.exe" "' + str(HERE / 'audit_mixed_receipts_once.py')
        + '" --evidence "<actual-evidence绝对路径>" --request "<已封存actor编号>"\n```\n\n'
        + '选actor会自动纳入紧邻的原辅助请求；选辅助则要求后续actor也已封存。未结束调用保持pending，不重启。'
        + '完整原请求所有文件重新核SHA，GUI完整事件前缀核链，按原生配置重建generation/schema并独立解码；'
        + '证据包由冻结observer用录得原envelope重建，属于CPU来源重建，不是新模型调用。\n\n'
        + '新CPU选择控制：`' + str(Path(authorities['mixed-audit-selection-controls-created.json']['root']) / 'receipt.json') + '`。\n\n'
        + '原生buffer来源：`' + str(Path(authorities['mixed-tensor-source-preparation-created.json']['root']) / 'receipt.json') + '`。\n\n'
        + '读图正确性、模型置信度校准、Mirage标签、官方任务结果及配对降幅均须各自证据，不由此审计推导。\n')
    report_name = '混合来源审计接线与使用-20261110.md'
    assert not (BASE / report_name).exists()
    (out / report_name).write_text(report, encoding='utf8')
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(out / 'seal.json', {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()})
    for name, value in before.items():
        assert sha(BASE / name) == value
    raw_note = (out / 'new-head.md').read_bytes()
    for name in ['README.md', 'HANDOFF.md']:
        (BASE / name).write_bytes(raw_note + (previous / name).read_bytes())
        assert (BASE / name).read_bytes() == raw_note + (previous / name).read_bytes()
    (BASE / 'full-gui-current.json').write_bytes((out / 'status.json').read_bytes())
    (BASE / report_name).write_bytes((out / report_name).read_bytes())
    assert sha(BASE / 'full-gui-current.json') == sha(out / 'status.json')
    assert sha(BASE / report_name) == sha(out / report_name)
    result = dict(publication=str(out), status_sha256=sha(out / 'status.json'), seal_sha256=sha(out / 'seal.json'),
                  report=str(BASE / report_name), three_heads_original_byte_readback_passed=True, goal='active')
    save(pointer, result)
    print(__import__('json').dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--evidence', type=Path, required=True)
    main(p.parse_args().evidence.resolve())
