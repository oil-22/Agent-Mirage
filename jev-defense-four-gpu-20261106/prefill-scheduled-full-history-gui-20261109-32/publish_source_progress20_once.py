"""Publish candidate20's sealed execution join and nonoverlapping11call audit."""
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


def main():
    assert not (HERE / 'source-progress20-publication-created.json').exists()
    evidence = sorted(HERE.glob('actual-evidence-*'))[-1]
    for name, expected in read(evidence / 'seal.json').items():
        assert sha(evidence / name) == expected
    service, gui = read(evidence / '3090.json'), read(evidence / '4090.json')
    assert time.time() - service['time'] < 180
    for record in [service['worker/process.json']['value'], service['launcher-process.json']['value'],
                   gui['control/runner-process.json']['value']]:
        assert not record['actual'].get('absent') and record['actual']['state'] not in ['Z', 'X']
        assert all(str(record['actual'][key]) == str(record['record'][key])
                   for key in ['pid', 'uid', 'command', 'start_ticks'])
    assert len(service['held_locks']) == 9
    review = read(HERE / 'source-review-03-created.json')
    assert sha(Path(review['review']) / 'review.json') == review['review_sha256']
    joinpath = HERE / 'post-review-join-1794232016065618400/join.json'
    assert sha(joinpath) == read(joinpath.parent / 'seal.json')['join.json']
    joined = read(joinpath)
    assert len(joined['rows']) == 1 and joined['rows'][0]['accepted'] and joined['rows'][0]['executed']
    pointers = [HERE / 'prefix-audit-created.json'] + [HERE / ('new-replies-' + x + '-audit-created.json') for x in ['02','03','04','05']]
    rows, authorities = [], []
    for pointer in pointers:
        record = read(pointer)
        path = Path(record['audit'])
        assert sha(path) == record['audit_sha256']
        data = read(path)
        assert data['passed']
        rows.extend(data['requests'])
        authorities.append(record)
    assert [r['request'] for r in rows] == [str(i).zfill(4) for i in range(1,12)]
    totals = {'input_tokens': sum(r['actual_input_tokens'] for r in rows),
              'output_tokens': sum(r['output_tokens'] for r in rows),
              'summed_native_call_timer_seconds': sum(r['native_call_timer_seconds'] for r in rows)}
    out = HERE / ('source-progress20-publication-' + str(time.time_ns()))
    out.mkdir()
    previous = out / 'previous-heads'
    previous.mkdir()
    previous_hashes = {}
    for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']:
        (previous / name).write_bytes((BASE / name).read_bytes())
        previous_hashes[name] = sha(BASE / name)
    status = read(BASE / 'full-gui-current.json')
    status.update(schema='GUI32-source-review20-first-execution-and-eleven-native-calls-v1', time=time.time(),
                  previous_heads_SHA256=previous_hashes,
                  current_goal_turn_classification='progress: source-first reviews18..20 sealed then joined to actual normal execution; requests1..11 exact wire/tensors/IDs/native budgets/EOS/prefill audited without rerunning inference, native actor output fidelity1..19 additionally verified')
    status['authorities']['latest_actual_UID_locks_requests_chains'] = {'path': str(evidence), 'seal_sha256': sha(evidence / 'seal.json')}
    status['authorities']['new32_source_review20'] = review
    status['authorities']['new32_source_review20_execution_join'] = {'path': str(joinpath), 'sha256': sha(joinpath)}
    status['authorities']['new32_nonoverlapping_requests1to11_audits'] = authorities
    for target, source in [('actual_service_state_at_snapshot','worker/status.json'), ('actual_worker_identity_at_snapshot','worker/process.json'), ('actual_launcher_identity_at_snapshot','launcher-process.json')]:
        status[target] = service[source]['value']
    status['actual_GUI_state_at_snapshot'] = gui['batch/status.json']['value']
    status['actual_GUI_runner_identity_at_snapshot'] = gui['control/runner-process.json']['value']
    status['service_event_chains'], status['GUI_event_chains'] = service['chains'], gui['chains']
    status['new32_sealed_requests_at_snapshot'], status['new32_terminals_at_snapshot'] = service['sealed_requests'], gui['terminals']
    status['confirmed_original_actions_total'] = 20
    status['new_source_review_progress'].update(original_unique_actor_candidates_reviewed_through=20,
        new_candidates_this_goal_turn=[18,19,20], all_three_new_candidates_normal_scroll_down=True,
        all_three_source_labels_sealed_before_outcome_join=True,
        all_three_accepted_and_executed_once=True, whole_trajectory_Mirage=None,
        official_task_score=None, efficacy_or_full_falseblock_rate_established=False)
    status['native_request_tensor_EOS_and_prefill_audit_completed_through_new32_request'] = '0011'
    status['largest_newly_audited_completed_judge'] = max((r for r in rows if r['operation']=='judge'), key=lambda r:r['actual_input_tokens'])
    status['new32_audited_completed_prefix_totals'] = dict(totals,
        requests=11, actor_replies=3, judge_replies=8, auxiliary_replies=0,
        natural_EOS_replies=11, format_retries=0,
        scope='Only new32requests0001..0011; excludes original23/29/31calls, all failed/in-progress work, loading/preprocessing and outside-holder reservation. Native timing includes instrumentation/transfers; not walltime/currency/energy or savings.')
    status['next_action'] = ('Continue the same actual worker4108313/launcher4108082/GUI18635 after revalidating identity/locks. '
        'Original1..20candidates are source-reviewed and actually executed once; do not relabel/reexecute. '
        'Review newly generated21+from original pixels/full lawful history before joins; audit newly sealed12+only. '
        'Keep original32tracks/16pairs, all caps and stateless single-image auxiliary; enabled-track actual auxiliary/KV/insertion remains unverified in new schedule until it naturally occurs.')
    save(out / 'status.json', status)
    note = ('## 最新：2026-11-09 新32累计20动作；新增三次正常滚动均先审后关联执行\n\n'
        '权威 `' + str((out / 'status.json').relative_to(BASE)).replace('\\','/') + '`。'
        '第18–20三候选均为原生down探索，无事实/历史/完成断言；各自原图和完整合法历史先独立来源审查封存，再关联未经修改的Controller接受与实际执行。'
        '累计20原生动作，原17不重复计数。首轨noaux仍未完成，其余31轨未开始，整轨Mirage/官方分数与匹配降幅未知，不称防御有效。\n\n'
        '新32请求0001–0011共11自然EOS=3actor+8judge，0辅助/格式retry；各不重叠增量审计已绑定完整wire/prepared-first-forward全部tensor/native IDs/原有效生成/原预算/设备驻留。'
        '最新长核验完整20图36950tokens正常EOS238tokens，actor20完整20图23886tokens自然EOS15tokens。'
        '11回复累计' + str(totals['input_tokens']) + 'input/' + str(totals['output_tokens']) + 'output，'
        + str(round(totals['summed_native_call_timer_seconds'],3)) + 'summed native计时秒；含传输/记录，排除旧根/失败/进行中/加载/外部holder预留，不是walltime/货币/能耗或收益。'
        '完整更长历史fit不保证。\n\n'
        '另19份actor原始token解码已只读核对，无grammar/forced words/删解释；第20源绑定也保持原输出，但不把19份decode审计冒称20份。'
        '所有失败与旧终局保持不可变，本地audit03报告器守卫失败已保全并linked修复，0额外模型调用。'
        'fresh实际身份/九锁/双链见回执；仅4–7获授权，0–3不动。主完整历史/原图/BF16/SDPA/native/strict validator/原cap保持。'
        '辅助仍9B基座decision_adapter_loaded=false、单完整当前供应图+固定v6/空首KV/结束释放；新调度aux实际推理与插入仍待enabled轨验证。目标ACTIVE。\n\n')
    (out / 'new-head.md').write_text(note, encoding='utf8')
    save(out / 'seal.json', {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()})
    for name, expected in previous_hashes.items():
        assert sha(BASE / name) == expected
    for name in ['README.md','HANDOFF.md']:
        (BASE / name).write_bytes(note.encode('utf8') + (previous / name).read_bytes())
    (BASE / 'full-gui-current.json').write_bytes((out / 'status.json').read_bytes())
    save(HERE / 'source-progress20-publication-created.json', {'publication': str(out),
        'status_sha256': sha(out / 'status.json'), 'seal_sha256': sha(out / 'seal.json'), 'goal': 'active'})
    print(json.dumps({'publication': str(out), 'confirmed_original_actions': 20,
                      'new32_audited_prefix_totals': totals, 'goal': 'active'}))


if __name__ == '__main__':
    main()
