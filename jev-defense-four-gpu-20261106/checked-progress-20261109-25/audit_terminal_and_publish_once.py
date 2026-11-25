"""Audit GUI23 preserved terminal artifacts and publish a superseding head once.

This never starts a model, browser, scorer, old queue, or completed control.
"""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
GUI = BASE / 'full-history-gui-development-20261109-23'
PRES = GUI / 'failure-preservation-1794223604796828100'
FRESH = GUI / 'actual-evidence-1794224217168490100'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def read(path):
    return json.loads(Path(path).read_bytes())


def chain(path):
    previous = '0' * 64
    kinds = {}
    rows = []
    raw = path.read_bytes()
    assert raw.endswith(b'\n')
    for index, line in enumerate(raw.splitlines()):
        row = json.loads(line)
        signature = row.pop('sha256')
        assert row['seq'] == index and row['previous'] == previous
        assert hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False,
                                        separators=(',', ':')).encode()).hexdigest() == signature
        previous = signature
        kinds[row['kind']] = kinds.get(row['kind'], 0) + 1
        rows.append(dict(row, sha256=signature))
    return {'events': len(rows), 'head': previous, 'kinds': kinds}, rows


def main():
    assert not (HERE / 'publication-created.json').exists()
    assert sha(PRES / 'receipt.json') == 'e081a48900c9ec5ea8019c2c94bd6975c8353d9bfa4caaf4ee574b24cac03838'
    preservation = read(PRES / 'receipt.json')
    for name, expected in read(FRESH / 'seal.json').items():
        assert sha(FRESH / name) == expected
    service, gui = read(FRESH / '3090.json'), read(FRESH / '4090.json')
    for name in ['worker/process.json', 'launcher-process.json']:
        assert service[name]['value']['actual']['absent']
    assert gui['control/runner-process.json']['value']['actual']['absent']
    assert len(service['held_locks']) == 9
    assert not service['authorized_GPU_actual_compute_processes']
    roots = {}
    inventories = {}
    exported = {}
    for host, info in preservation['hosts'].items():
        receipt = Path(info['receipt'])
        assert sha(receipt) == info['receipt_sha256']
        data = read(receipt)
        assert data['all_originals_retained_in_place']
        root = Path(data['local_public_originals'])
        for name, expected in data['public_exported_files'].items():
            assert sha(root / name) == expected, (host, name)
        inventories[host] = data['all_original_files']
        roots[host] = root / 'output'
        exported[host] = len(data['public_exported_files'])
        terminal = root / 'output/terminal-manifest.json'
        if terminal.exists():
            for name, expected in read(terminal).items():
                assert data['all_original_files'][name] == expected, (host, name)
    sr = roots['3090']
    gr = roots['4090']
    attempt = gr / 'batch/runs/fullhistory23-T000-clean-noaux/attempt-1794221958077864899'
    service_chain, service_events = chain(sr / 'worker/journal/events.jsonl')
    gui_chain, gui_events = chain(attempt / 'events.jsonl')
    assert service_chain['events'] == 188 and gui_chain['events'] == 497
    assert service_chain['head'] == '70fa0eede968317bbf4fd06550863b7922b26d8e0a4a8fa2d55b391b7d85ec79'
    assert gui_chain['head'] == '74598b0fcd1f615938d7d6c842e16792f2b943aaad63ea1bf4d04e799a29b797'
    wires = {row['data']['wire_sha256']: row['data']['body'] for row in gui_events
             if row['kind'] in ['actual_actor_wire_request', 'actual_judge_wire_request']
             and 'wire_sha256' in row['data']}
    assert len(wires) == 44
    totals = {'actor': 0, 'judge': 0, 'auxiliary': 0, 'natural_EOS': 0,
              'successful_input_tokens': 0, 'successful_output_tokens': 0,
              'summed_successful_native_generation_seconds': 0.0,
              'summed_successful_instrumented_seconds': 0.0, 'failed_prefill_attempts': 0}
    requests = []
    for folder in sorted((sr / 'worker/requests').iterdir()):
        bindings = read(folder / 'seal.json')
        for name, expected in bindings.items():
            assert inventories['3090'][str((folder / name).relative_to(sr)).replace('\\', '/')] == expected
        wire = read(folder / 'external-wire.json')
        assert wires[sha(folder / 'external-wire.json')] == wire
        payload = read(folder / 'payload.json')
        assert wire['payload'] == payload
        assert wire['trajectory_id'] == 'fullhistory23-T000-clean-noaux'
        op = payload['operation']
        totals[op] += 1
        prepared, first = read(folder / 'prepared.json'), read(folder / 'first-forward.json')
        assert set(prepared) == set(first)
        for key in prepared:
            assert all(prepared[key][field] == first[key][field]
                       for field in ['shape', 'dtype', 'bytes', 'sha256']), (folder.name, key)
            for records in [prepared, first]:
                assert bindings[records[key]['file']] == records[key]['sha256']
        row = {'request': folder.name, 'operation': op, 'decision': wire['decision_index'],
               'attempt_index': wire['attempt_index'], 'input_tokens': prepared['input_ids']['shape'][1],
               'image_count': prepared['image_grid_thw']['shape'][0],
               'seal_sha256': sha(folder / 'seal.json'), 'CPU_and_actual_forward_tensors_equal': True}
        if (folder / 'actual-generation.json').exists():
            generated = read(folder / 'actual-generation.json')
            response, native = read(folder / 'response.json'), read(folder / 'native-call.json')
            assert response['external_wire_sha256'] == sha(folder / 'external-wire.json')
            assert response['request_id'] == wire['request_id']
            assert response['text' if op == 'actor' else 'verdict'] == native['text']
            assert native['generated_ids'] == generated['output_ids']
            assert len(native['input_ids']) == generated['input_tokens'] == row['input_tokens']
            assert len(generated['output_ids']) == generated['output_tokens']
            assert generated['natural_EOS']
            assert not native['hit_output_cap']
            assert generated['output_ids'][-1] in read(folder / 'effective-generation.json')['eos_token_id']
            totals['natural_EOS'] += 1
            totals['successful_input_tokens'] += generated['input_tokens']
            totals['successful_output_tokens'] += generated['output_tokens']
            totals['summed_successful_native_generation_seconds'] += native['seconds']
            totals['summed_successful_instrumented_seconds'] += response['seconds_including_instrumentation']
            row.update(natural_EOS=True, output_tokens=generated['output_tokens'])
        else:
            assert folder.name == '0044'
            failure = read(folder / 'failure.json')
            assert 'OutOfMemoryError' in failure['traceback']
            assert 'torch_chunk_gated_delta_rule' in failure['traceback']
            assert (folder / 'generated-token-progress.jsonl').stat().st_size == 0
            assert read(folder / 'forward-count.json')['actual_forward_calls'] == 1
            assert row['input_tokens'] == 22596 and row['image_count'] == 11
            assert prepared['input_ids']['sha256'] == 'd7e48edfa1fe9c0ef0b184e3fe1bdea63863022d005872b59efd5d8677b8bacf'
            totals['failed_prefill_attempts'] += 1
            row.update(natural_EOS=None, generated_tokens=0, outcome='prefill_OOM')
        requests.append(row)
    assert len(requests) == 44 and totals['actor'] == 11 and totals['judge'] == 33
    assert totals['natural_EOS'] == 43 and totals['failed_prefill_attempts'] == 1
    terminal = read(attempt / 'technical-failure.json')
    assert terminal['actor_calls'] == 11 and terminal['verifier_calls'] == 33
    assert terminal['decisions'] == 11 and terminal['environment_actions'] == 10
    assert terminal['scoring_status'] == 'complete' and terminal['official_reward'] == 0
    assert terminal['semantic_mirage'] is None
    assert len([v for v in gui_events if v['kind'] == 'action_executed']) == 10
    assert read(sr / 'exit.json')['worker_exit_code'] == 1
    assert read(gr / 'control/exit.json')['child_exit'] == 1
    aggregate_pointer = read(GUI / 'source-review-current.json')
    aggregate_path = Path(aggregate_pointer['authority'])
    assert sha(aggregate_path) == aggregate_pointer['sha256']
    aggregate = read(aggregate_path)
    assert aggregate['source_reviewed_candidates'] == 11 and aggregate['unreviewed_collected_candidates'] == 0
    assert aggregate['groups']['fullhistory23-T000-clean-noaux']['trajectory_any_Mirage'] is None
    out = HERE / ('publication-' + str(time.time_ns()))
    out.mkdir()
    before = out / 'previous-heads'
    before.mkdir()
    prior = {}
    for name in ['HANDOFF.md', 'README.md', 'full-gui-current.json']:
        raw = (BASE / name).read_bytes()
        (before / name).write_bytes(raw)
        prior[name] = hashlib.sha256(raw).hexdigest()
    audit = {'schema': 'GUI23-complete-technical-terminal-audit-v1', 'time': time.time(),
             'passed': True, 'preservation_receipt_sha256': sha(PRES / 'receipt.json'),
             'fresh_identity_evidence': str(FRESH), 'fresh_identity_seal_sha256': sha(FRESH / 'seal.json'),
             'verified_public_files': exported, 'all_original_terminal_and_request_seals_bound': True,
             'all_44_native_CPU_and_actual_first_forward_tensor_bindings_verified': True,
             'requests': requests, 'totals': totals, 'service_chain': service_chain, 'GUI_chain': gui_chain,
             'original_official_score': 0, 'official_scorer_calls': 1,
             'interpretation': 'Technical terminal; score0 is not semantic model zero. Eleven action-only candidates have no definite semantic error in root-source review; the trajectory stays unknown.',
             'four_GPU_reserved_seconds_inside_launcher': read(sr / 'exit.json')['four_GPU_reserved_seconds_in_launcher'],
             'cost_exclusions': 'Outside-holder reservation, failed-call latency/work, earlier stages, currency and energy are not included in successful summed native seconds.',
             'no_completed_call_or_action_reexecution': True, 'new_model_GUI_scorer_paid_calls': 0}
    save(out / 'technical-audit.json', audit)
    status = {'schema': 'GUI23-terminal-OOM-authoritative-progress-v1', 'time': time.time(),
              'goal': 'active', 'efficacy_established': False, 'relative_Mirage_reduction': None,
              'previous_goal_turn_classification': 'no progress on experimentation: answered the prompt/output question from sealed sources; this turn resumes technical recovery',
              'current_turn_progress': 'All11source reviews aggregated; all44attempts and native tensor/output/cost bindings audited; stale running heads superseded.',
              'GUI23': {'phase': 'technical_failure_terminal', 'planned_tracks': 32,
                        'complete_tracks': 0, 'technical_failure_tracks': 1, 'unstarted_tracks': 31,
                        'actual_model_attempts': 44, 'natural_EOS': 43, 'prefill_OOM': 1,
                        'actor': 11, 'judge_attempts': 33, 'auxiliary': 0,
                        'decisions': 11, 'executed_actions': 10, 'source_reviewed_candidates': 11,
                        'definite_candidate_Mirage': 0, 'trajectory_Mirage': None,
                        'official_score': 0, 'official_score_is_technical_failure_not_model_zero': True,
                        'worker_launcher_GUI_runner_actually_absent': True,
                        'all_old_prepare_orchestrate_service_GUI_actions_must_not_resubmit': True},
              'failed_request': requests[-1], 'technical_audit': str(out / 'technical-audit.json'),
              'technical_audit_sha256': sha(out / 'technical-audit.json'),
              'source_review_aggregate': aggregate_pointer,
              'preservation_receipt': str(PRES / 'receipt.json'),
              'preservation_receipt_sha256': sha(PRES / 'receipt.json'),
              'resources': {'authorized_physical_GPUs': [4, 5, 6, 7], 'holder': service['holder'],
                            'held_locks': service['held_locks'], 'actual_compute': [],
                            'GPUs0_to3_authorized': False},
              'next_action': 'Prepare a new linked original-budget technical attempt. Successful request0041 already approaches all-card peaks: GPU6 free at failed prefill is not proven usable headroom. Evaluate weight-residency scheduling without CPU inference, truncation, precision or native algorithm changes.',
              'new_model_GUI_scorer_paid_calls': 0, 'previous_head_SHA': prior}
    save(out / 'status.json', status)
    header = f'''## 最新：2026-11-09 新23完整主历史GUI因预填充OOM技术终局，原件已全部保全

权威 `{out.relative_to(BASE).as_posix()}/status.json`、同目录technical-audit.json与新fresh实际证据。原23只有首轨fullhistory23-T000-clean-noaux开始：11actor EOS＋32judge EOS＋1judge预填充OOM，共44实际尝试43EOS；11决策10实际动作，0辅助。32轨中0完成、1技术终局、31未开始。原官方score0已保留，是技术失败，不是modelzero/防御成功。worker/launcher/GUI runner实际均已消失；原holder UID1033完整cmd/start/九锁仍持有4–7，0–3未授权。严禁重跑23 prepare/orchestrate stage/preflight/service/gui或任何旧终局queue。

失败0044是完整22596tokens/11原图/4096核验输出预算，原native gated-delta prefill在逻辑1即物理5显存不足、0生成token。原CPU与真实first-forward IDs/pixels/grid一致；全部44请求/43自然回复、1007＋163远端原文件、两链188/497与884公共文件绑定已审计。preservation receipt e081a48900c9ec5ea8019c2c94bd6975c8353d9bfa4caaf4ee574b24cac03838；原/end连接拒绝是后续症状，不能当根因。

11候选原图/完整合法历史来源审查全覆盖，先seal后join：0确定语义正例、0未决子断言、0native目标/方向错；前10接受执行，第11正确探索滚动提议未执行。均为动作-only，不能称整轨无Mirage/成功或辅助收益。累计成功输入{totals['successful_input_tokens']}、输出{totals['successful_output_tokens']}tokens，{totals['summed_successful_native_generation_seconds']:.3f}成功native生成秒；不含失败工作/加载/holder外占用，不是walltime/货币/能耗。目标ACTIVE，尚无可复核降幅。

下一步仅新linked技术恢复，携带原33judge/11actor/10actions计数和原预算，绝不重刷43完成调用/已执行动作。成功0041在21014tokens/10图时四卡峰值均近上限，失败时物理6空7.8GB尚未跑其层，不足证明重新分层可fit。准备按调用调度权重驻留、全部forward仍在GPU，保留完整原图历史/BF16/SDPA/native算法/严格validator/全部原预算；真实容量和GUI恢复尚未完成。实际辅助仍Qwen3.5-9B共享基座，decision_adapter_loaded=false，单完整当前供应图＋固定v6独立调用。

'''
    (out / '完整主历史GUI显存失败与恢复边界-20261109.md').write_text(header, encoding='utf8')
    save(out / 'receipt.json', {'time': time.time(), 'technical_audit_sha256': sha(out / 'technical-audit.json'),
                              'status_sha256': sha(out / 'status.json'), 'previous_heads': prior,
                              'no_new_experiment_calls': True, 'goal': 'active'})
    save(out / 'seal.json', {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()})
    for name in ['HANDOFF.md', 'README.md']:
        assert sha(BASE / name) == prior[name]
        (BASE / name).write_bytes(header.encode('utf8') + (before / name).read_bytes())
    assert sha(BASE / 'full-gui-current.json') == prior['full-gui-current.json']
    (BASE / 'full-gui-current.json').write_bytes((out / 'status.json').read_bytes())
    save(HERE / 'publication-created.json', {'publication': str(out), 'receipt_sha256': sha(out / 'receipt.json'),
                                            'seal_sha256': sha(out / 'seal.json')})
    print(json.dumps({'publication': str(out), 'totals': totals, '11_candidates_reviewed': True,
                      'trajectory_reduction': None, 'goal': 'active'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
