"""Publish immutable source/execution and generation-fidelity evidence for GUI32."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def verified_pointer(name):
    pointer = read(HERE / name)
    path = Path(pointer['audit'])
    assert sha(path) == pointer['audit_sha256']
    assert read(path)['passed']
    return pointer


def main():
    assert not (HERE / 'source-progress19-publication-created.json').exists()
    evidence = sorted(HERE.glob('actual-evidence-*'))[-1]
    for name, expected in read(evidence / 'seal.json').items():
        assert sha(evidence / name) == expected
    service, gui = read(evidence / '3090.json'), read(evidence / '4090.json')
    assert time.time() - service['time'] < 180
    for record in [service['worker/process.json']['value'], service['launcher-process.json']['value'],
                   gui['control/runner-process.json']['value']]:
        assert not record['actual'].get('absent')
        assert record['actual']['state'] not in ['Z', 'X']
        assert all(str(record['actual'][key]) == str(record['record'][key])
                   for key in ['pid', 'uid', 'command', 'start_ticks'])
    assert len(service['held_locks']) == 9
    reviews = [read(HERE / name) for name in ['source-review-01-created.json', 'source-review-02-created.json']]
    joins = [HERE / 'post-review-join-1794231345652204800', HERE / 'post-review-join-1794231445391121300']
    joined = []
    for review, folder in zip(reviews, joins):
        assert sha(Path(review['review']) / 'review.json') == review['review_sha256']
        assert sha(folder / 'join.json') == read(folder / 'seal.json')['join.json']
        data = read(folder / 'join.json')
        assert len(data['rows']) == 1
        row = data['rows'][0]
        assert row['accepted'] and row['executed']
        assert row['sealed_source_label']['definite_semantic_Mirage'] is False
        joined.append({'path': str(folder / 'join.json'), 'sha256': sha(folder / 'join.json'),
                       'candidate_id': row['id'], 'accepted': True, 'executed': True})
    audits = {name: verified_pointer(name) for name in [
        'prefix-audit-created.json', 'new-replies-02-audit-created.json',
        'new-replies-03-audit-created.json', 'new-replies-04-audit-created.json',
        'actor-output-fidelity-audit-created.json']}
    fidelity = read(audits['actor-output-fidelity-audit-created.json']['audit'])
    assert len(fidelity['rows']) == 19
    assert all(row['raw_ID_decode_equals_native_and_unmodified_candidate']
               and row['actor_grammar_or_forced_words'] is False for row in fidelity['rows'])
    out = HERE / ('source-progress19-publication-' + str(time.time_ns()))
    out.mkdir()
    previous = out / 'previous-heads'
    previous.mkdir()
    previous_hashes = {}
    for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']:
        (previous / name).write_bytes((BASE / name).read_bytes())
        previous_hashes[name] = sha(BASE / name)
    status = read(BASE / 'full-gui-current.json')
    status.update(schema='GUI32-source-sealed-candidates18to19-execution-and-native-actor-fidelity19-v1',
        time=time.time(), previous_heads_SHA256=previous_hashes,
        previous_goal_turn_classification='no progress in the running experiment: answered user prompt/output question using sealed historical evidence; no experiment advancement was claimed',
        current_goal_turn_classification='progress: new source-only candidate19 review sealed, existing18 and new19 labels joined to actual acceptance/execution, actual new requests5..9 tensor/EOS/native budget audited, all19raw actor token decodes bound to unmodified candidate text')
    status['authorities']['latest_actual_UID_locks_requests_chains'] = {
        'path': str(evidence), 'seal_sha256': sha(evidence / 'seal.json')}
    status['authorities']['new32_source_reviews18and19'] = reviews
    status['authorities']['new32_source_review_execution_joins18and19'] = joined
    status['authorities']['new32_incremental_native_request_audits'] = audits
    status['actual_service_state_at_snapshot'] = service['worker/status.json']['value']
    status['actual_worker_identity_at_snapshot'] = service['worker/process.json']['value']
    status['actual_launcher_identity_at_snapshot'] = service['launcher-process.json']['value']
    status['actual_GUI_state_at_snapshot'] = gui['batch/status.json']['value']
    status['actual_GUI_runner_identity_at_snapshot'] = gui['control/runner-process.json']['value']
    status['service_event_chains'], status['GUI_event_chains'] = service['chains'], gui['chains']
    status['new32_sealed_requests_at_snapshot'] = service['sealed_requests']
    status['new32_terminals_at_snapshot'] = gui['terminals']
    status['confirmed_original_actions_total'] = 19
    status['new_source_review_progress'] = {
        'original_unique_actor_candidates_reviewed_through': 19,
        'new_candidates_this_goal_turn': [18, 19],
        'both_new_candidates_native_scroll_down_without_factual_history_or_completion_assertions': True,
        'both_accepted_and_executed_once_with_original_controller': True,
        'earlier_pending17_not_relabelled_or_reexecuted': True,
        'single_source_author_review_not_fully_blind_or_independent_human_gold': True,
        'whole_trajectory_Mirage': None, 'official_task_score': None,
        'efficacy_or_full_falseblock_rate_established': False,
    }
    status['raw_actor_measurement_fidelity'] = {
        'source_bound_raw_native_replies': 19,
        'all_actual_output_ID_decodes_equal_native_text_and_GUI_candidate': True,
        'all_actor_generation_unconstrained_without_forced_words': True,
        'original_system_requests_brief_evidence_and_uncertainty': True,
        'only_native_special_tokens_and_outer_whitespace_removed': True,
        'action_only_response_style_is_observed_not_an_added_decode_constraint': True,
        'all19currently_action_only_limits_positive_semantic_evidence': True,
        'no_prompt_change_to_add_or_suppress_narration': True,
        'audit': audits['actor-output-fidelity-audit-created.json'],
    }
    status['native_request_tensor_EOS_and_prefill_audit_completed_through_new32_request'] = '0009'
    status['largest_newly_audited_completed_judge'] = read(audits['new-replies-04-audit-created.json']['audit'])['requests'][0]
    status['local_reporter_repair'] = {
        'failure': 'New audit03 local source-transform guard expected one occurrence of a pointer used twice.',
        'preserved_roots': [str(p) for p in HERE.glob('reply-audit03-local-failure-preservation-*')],
        'linked_repair_passed': True,
        'model_runtime_original_inputs_outputs_and_strict_validator_changed': False,
        'extra_model_GUI_scorer_calls': 0,
    }
    status['next_action'] = ('Continue the same actual verified GUI32 worker/launcher/runner and original32track plan. '
        'Review new20+raw candidates from original images/legal history before outcome joins; '
        'audit only newly sealed requests10+. Do not restart old terminals or reexecute/relabel1..19. '
        'New schedule auxiliary inference/emptyKV/release/actor insertion remains to be verified when an enabled track naturally starts.')
    save(out / 'status.json', status)
    note = (
        '## 最新：2026-11-09 新32第18–19正常滚动已执行；19份原始actor输出未删叙述\n\n'
        '权威 `' + str((out / 'status.json').relative_to(BASE)).replace('\\', '/') + '`。'
        '第18与19候选均先看完整原图/合法文字历史封存，再关联原Controller接受与实际执行；两次均为正常down探索，无事实/历史/完成断言。'
        '原17已封存标签不重复计数；累计已确认19原生动作，整轨Mirage和官方评分仍unknown。32轨仍首轨noaux，完成0、其余31尚未开始；不称防御有效。\n\n'
        '新32请求0005–0009原wire/全部prepared-first-forward tensor/实际input-output IDs/EOS/原effective generation与原计数已审；'
        '包含完整18/19图长核验，具体tokens与原计时见回执；没有裁图历史或追加模型控制。另独立只读重建19份actor原始token解码，'
        '全部等于native返回与GUI候选；原system要求简述证据和不确定性，actor无grammar/forced words。当前action-only是实际输出风格，'
        '没有后处理删掉解释；仍不能从少断言推出整轨0Mirage或收益。\n\n'
        'fresh证据核同一worker4108313 UID1033/start1184962121、launcher4108082/start1184958788、GUI18635 UID1015/start121404726及九锁/双链。'
        '请求0005–0009和19输出审计均0新推理；本地audit03的重复字符串计数断言失败已原件封存，linked仅修报告器并通过。'
        '当前精确调用/阶段以fresh实际证据为准。仅4–7授权，主完整历史/原图/BF16/SDPA/native/strict validator/全部原cap保持。'
        '辅助实际仍Qwen3.5-9B基座、decision_adapter_loaded=false，单图固定v6/空首KV/释放；新调度真实aux调用和插入仍待enabled轨。目标ACTIVE。\n\n')
    (out / 'new-head.md').write_text(note, encoding='utf8')
    save(out / 'seal.json', {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()})
    for name, expected in previous_hashes.items():
        assert sha(BASE / name) == expected
    for name in ['README.md', 'HANDOFF.md']:
        (BASE / name).write_bytes(note.encode('utf8') + (previous / name).read_bytes())
    (BASE / 'full-gui-current.json').write_bytes((out / 'status.json').read_bytes())
    save(HERE / 'source-progress19-publication-created.json', {
        'publication': str(out), 'status_sha256': sha(out / 'status.json'),
        'seal_sha256': sha(out / 'seal.json'), 'goal': 'active'})
    print(json.dumps({'publication': str(out), 'status_sha256': sha(out / 'status.json'),
                      'confirmed_original_actions': 19, 'goal': 'active'}))


if __name__ == '__main__':
    main()
