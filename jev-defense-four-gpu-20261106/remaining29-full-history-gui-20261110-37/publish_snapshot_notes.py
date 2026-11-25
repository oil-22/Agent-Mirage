"""Publish current verified evidence with explicit phase notes, without experiment calls.

The notes are supplied source-review prose, not automatically inferred semantic
labels. Every referenced evidence pointer is checked before mutable heads change.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time

from orchestrate import HERE, save, sha
from join_source_reviews import verify_seal


def read(path):
    return json.loads(path.read_bytes())


def authority(pointer, folder_key, filename, digest_key):
    value = read(pointer)
    folder = Path(value[folder_key])
    assert folder.parent == HERE
    assert verify_seal(folder) == value['seal_sha256']
    assert sha(folder / filename) == value[digest_key]
    return folder, read(folder / filename), value


def main(evidence, notes_path):
    assert evidence.parent == HERE and notes_path.parent == HERE
    evidence_seal = verify_seal(evidence)
    service, gui = read(evidence / '3090.json'), read(evidence / '4090.json')
    worker, runner = service['worker/process.json']['actual'], gui['control/runner-process.json']['actual']
    assert (worker['pid'], worker['uid'], worker['start_ticks']) == (252807, 1033, '1191243649')
    assert (runner['pid'], runner['uid'], runner['start_ticks']) == (3333015, 1015, '127695701')
    assert worker['state'] not in ['Z', 'X'] and runner['state'] not in ['Z', 'X']
    assert HERE.name in worker['command'] and HERE.name in runner['command']
    assert len(service['held_locks']) == 9 and service.get('worker/terminal.json') is None
    assert gui.get('control/exit.json') is None
    manifest_sha = sha(HERE / 'runtime-package/manifest.json')
    assert manifest_sha == '368b0a594822f5e294fcd21927aa924a18a80f23249f160857b5de7090c1c02d'
    manifest = read(HERE / 'runtime-package/manifest.json')
    for name, expected in manifest['files'].items():
        assert sha(HERE / 'runtime-package' / name) == expected
    inspected = {row['request']: row for row in service['sealed_requests']}
    reports, audit_authorities = {}, []
    for pointer in sorted(HERE.glob('mixed-receipt-audit-created-*.json')):
        folder, receipt, value = authority(pointer, 'root', 'receipt.json', 'receipt_sha256')
        assert receipt['passed']
        for row in read(folder / '3090-native-bindings.json')['reports']:
            if row['request'] not in inspected:
                continue
            assert row['request_seal_sha256'] == inspected[row['request']]['seal_sha256']
            if row['request'] in reports:
                assert row == reports[row['request']]
            reports[row['request']] = row
        audit_authorities.append(value)
    continuous = 0
    while '%04d' % (continuous + 1) in reports:
        continuous += 1
    assert continuous == len(reports) and reports
    assert all(row['native_proof']['natural_EOS'] for row in reports.values())
    counts = dict(Counter(row['operation'] for row in reports.values()))
    totals = dict(input_tokens=sum(row['native_proof']['actual_input_tokens'] for row in reports.values()),
        output_tokens=sum(row['native_proof']['output_tokens'] for row in reports.values()),
        summed_native_call_timer_seconds=sum(row['native_proof']['native_call_timer_seconds'] for row in reports.values()))
    labels, source_authorities = {}, []
    for pointer in sorted(HERE.glob('source-review-*-created.json')):
        if not re.fullmatch(r'source-review-\d+-created\.json', pointer.name):
            continue
        folder, review, value = authority(pointer, 'review', 'review.json', 'review_sha256')
        assert review['independent_current_checker_execution_score_join_not_performed']
        for row in review['rows']:
            assert row['id'] not in labels
            packet = Path(row['public_source_packet'])
            assert sha(packet) == row['packet_sha256']
            verify_seal(packet.parent.parent)
            labels[row['id']] = row
        source_authorities.append(value)
    joined_rows, joins = {}, []
    for pointer in sorted(HERE.glob('post-review-join-created-*.json')):
        value = read(pointer)
        folder = Path(value['join'])
        assert folder.parent == HERE and verify_seal(folder) == value['seal_sha256']
        assert sha(folder / 'join.json') == value['join_sha256']
        joined = read(folder / 'join.json')
        assert joined['all_source_labels_sealed_before_this_join']
        for row in joined['rows']:
            assert row['sealed_source_label'] == labels[row['id']]
            joined_rows[row['id']] = row
        joins.append(value)
    summary = dict(reviewed_candidates=len(labels),
        definite_positive=sum(row['candidate_semantic_mirage'] is True for row in labels.values()),
        source_negative=sum(row['candidate_semantic_mirage'] is False for row in labels.values()),
        semantic_unknown=sum(row['candidate_semantic_mirage'] is None for row in labels.values()),
        native_action_unknown=sum(row['native_action_error'] is None for row in labels.values()),
        pure_native_WAIT_excluded=sum(row['pure_native_WAIT_excluded'] for row in labels.values()),
        accepted=sum(row['accepted'] for row in joined_rows.values()),
        executed=sum(row['executed'] for row in joined_rows.values()),
        candidate_rate_or_whole_trajectory_negative_not_inferred=True)
    pointers = sorted(HERE.glob('original32-live-ledger-created-*.json'))
    assert pointers
    ledger_root, ledger, ledger_authority = authority(pointers[-1], 'root', 'ledger.json', 'ledger_sha256')
    assert ledger['actual_live_evidence'] == str(evidence), 'Rebuild the ledger for this exact inspected snapshot first'
    assert ledger['original_scope'] == dict(tracks=32, matched_pairs=16, selected_tasks=8)
    assert sha(ledger_root / 'descriptive-analysis.json') == ledger_authority['analysis_sha256']
    analysis = read(ledger_root / 'descriptive-analysis.json')
    notes = read(notes_path)
    assert isinstance(notes['title'], str) and notes['title'].strip()
    assert isinstance(notes['paragraphs'], list) and notes['paragraphs']
    assert all(isinstance(row, str) and row.strip() for row in notes['paragraphs'])
    extra = {}
    for name in notes['authority_pointers']:
        pointer = HERE / name
        assert pointer.parent == HERE and pointer.suffix == '.json'
        value = read(pointer)
        folder = Path(value.get('root', value.get('review', value.get('collection', ''))))
        assert folder.parent == HERE and verify_seal(folder) == value['seal_sha256']
        checked = 0
        for key, filename in [('review_sha256', 'review.json'), ('receipt_sha256', 'receipt.json'),
                              ('ledger_sha256', 'ledger.json'), ('status_sha256', 'status.json')]:
            if key in value:
                assert sha(folder / filename) == value[key]
                checked += 1
        assert checked
        extra[name] = value
    paths = [HERE.parent / name for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']]
    before = {path: path.read_bytes() for path in paths}
    previous = json.loads(before[paths[2]])
    assert previous['original_scope']['tracks'] == 32 and previous['original_scope']['matched_pairs'] == 16
    folder = HERE / ('reviewed-progress-publication-' + str(time.time_ns()))
    folder.mkdir()
    for path, content in before.items():
        (folder / ('before-' + path.name)).write_bytes(content)
    (folder / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (folder / 'explicit-phase-notes.json').write_bytes(notes_path.read_bytes())
    state, guistate = service['worker/status.json']['value'], gui['batch/status.json']['value']
    status = dict(schema='original32-reviewed-live-progress-v2', time=time.time(), goal='active',
        previous_goal_turn_classification=notes['previous_goal_turn_classification'],
        current_goal_turn_classification=notes['current_goal_turn_classification'],
        original_scope=previous['original_scope'],
        original_three_terminal_authority=previous['original_three_terminal_authority'],
        monitor_should_remain_active=True, source_condition_blocker_resolved=True,
        experimental_state='same_verified_live_runtime_continues',
        remaining29=dict(runtime_root=str(HERE), manifest_sha256=manifest_sha,
            actual_service_state=state, actual_GUI_state=guistate, actual_worker=worker,
            actual_GUI_runner=runner, actual_held_locks=9, inspected_sealed_request_count=len(inspected),
            native_audited_requests=sorted(reports, key=int), native_audited_contiguous_through=continuous,
            native_audited_operations=counts, native_audited_totals=totals, source_review_summary=summary,
            current_trajectory_any_Mirage=next(row['trajectory_any_definite_Mirage'] for row in ledger['rows'] if row['run_id'] == state['active']),
            auxiliary_enabled_branch_not_yet_observed=counts.get('evidence', 0) == 0,
            service_event_chain=service['journal'], GUI_event_chains=gui['GUI_event_chains']),
        auxiliary=previous['auxiliary'], frozen_auxiliary_config=read(HERE / 'runtime-package/auxiliary-config.json'),
        source_rule_version='evidence-v4.0.12-STAGED-native-answer-source-20261110',
        native_audit_authorities=audit_authorities, source_review_authorities=source_authorities,
        source_sealed_join_authorities=joins, original32_live_matched_ledger=ledger_authority,
        current_phase_notes=notes, current_phase_note_source=str(notes_path), current_phase_note_sha256=sha(notes_path),
        current_phase_authorities=extra,
        prior_reviewed_progress=dict(root=previous['immutable_publication'],
            status_sha256=sha(Path(previous['immutable_publication']) / 'status.json')),
        actual_evidence=str(evidence), actual_evidence_seal_sha256=evidence_seal,
        immutable_publication=str(folder), full_images_main_history_native_actions_precision_and_budgets_unchanged=True,
        no_relaunch_no_terminal_retry_no_new_condition=True,
        cost_scope='Summed actual audited native-call timers and tokens; not walltime, currency, energy or savings.',
        efficacy_established=False, relative_Mirage_reduction=analysis['primary']['relative_reduction_point'],
        final_completion_audit_not_performed_or_passed=True,
        publication_adds_no_model_GUI_capture_action_or_scorer_calls=True)
    save(folder / 'status.json', status)
    body = '\n\n'.join(notes['paragraphs'])
    head = f'''## 最新：{notes['title']}

权威 `{HERE.name}/{folder.name}/status.json`；实际证据 `{HERE.name}/{evidence.name}`。同一worker252807 UID1033/start1191243649与GUI3333015 UID1015/start127695701完整命令、九锁、4–7独占范围和双机SHA链已核。当前{state.get('request')}/{state.get('operation')}/{state.get('phase')}；已封{len(inspected)}份，连续原生审计0001–{continuous:04d}，操作{json.dumps(counts, ensure_ascii=False)}，均自然EOS。剩余29完成{guistate.get('completed')}/{guistate.get('expected')}；不重启stage/service/gui，不重刷终局或扩预算。

{len(labels)}个主候选按完整供应图和完整合法历史先审封存，再关联自身当前checker/执行：{summary['source_negative']}个来源阴性、{summary['semantic_unknown']}个语义未知、{summary['definite_positive']}个确定阳性；{summary['accepted']}个放行、{summary['executed']}个实执。此为已审前缀，不是整轨阴性或候选触发率；后来恢复不抹去错误，也不重写最初未知。

{body}

完整原32轨/16对/8选任务及全部旧终局保持；最新账本 `{HERE.name}/{ledger_root.name}/ledger.json`，状态{json.dumps(ledger['exposure_states'], ensure_ascii=False)}。原16对仍为主范围，14全新对仅版本分层；未知保留原分母，技术终局原始score与模型结果分开。相对降幅当前为{analysis['primary']['relative_reduction_point']}；正常操作、误拦、任务完成、暴露和成本的完整匹配结论尚未就绪，未证明30%或减半。

辅助仍为单个Qwen3.5-9B基座、decision_adapter_loaded=false、完整供应单图+固定v6，每次空上下文。当前无辅助对照的新辅助调用数为{state['counts'].get('evidence', 0)}。原图、完整主历史、BF16/SDPA、原生动作/评分、严格来源和全部恢复调用预算保持；本发布仅读取既有结果，0新模型/GUI/截图/动作/scorer调用。PRIVATE映射只作标签封存后的评估来源，不进checker。计时仅原调用之和，不是walltime/货币/能耗。目标ACTIVE；以下为保留历史。

'''
    (folder / 'report.md').write_text(head, encoding='utf8', newline='\n')
    save(folder / 'seal.json', {path.name: sha(path) for path in folder.iterdir() if path.is_file()})
    for path, content in before.items():
        assert path.read_bytes() == content, 'Concurrent mutable-head change; immutable publication preserved'
    for path in paths[:2]:
        content = head.encode('utf8') + before[path]
        path.write_bytes(content)
        assert path.read_bytes() == content
    paths[2].write_bytes((folder / 'status.json').read_bytes())
    assert sha(paths[2]) == sha(folder / 'status.json')
    result = dict(root=str(folder), status_sha256=sha(folder / 'status.json'), seal_sha256=sha(folder / 'seal.json'),
        native_audited_through=continuous, source_reviewed_candidates=len(labels), goal='active',
        efficacy_established=False, new_model_GUI_scorer_calls=0)
    save(HERE / ('reviewed-progress-publication-created-' + folder.name.rsplit('-', 1)[1] + '.json'), result)
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--notes', type=Path, required=True)
    arguments = parser.parse_args()
    main(arguments.evidence.resolve(), arguments.notes.resolve())
