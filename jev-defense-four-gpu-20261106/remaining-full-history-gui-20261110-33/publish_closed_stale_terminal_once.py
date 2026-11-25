"""Publish the preserved terminal, separate semantic occurrence and format failure."""
import collections
import copy
import importlib.util
import json
from pathlib import Path
import re
import time

import orchestrate as o
from join_source_reviews import verify_seal


RUN = 'fullhistory23-T000-stale_replace-aux'


def read(path):
    return json.loads(Path(path).read_bytes())


def authority(name, folder_key, filename, hash_key):
    a = read(o.HERE / name)
    root = Path(a[folder_key])
    assert root.parent == o.HERE and verify_seal(root) == a['seal_sha256']
    assert o.sha(root / filename) == a[hash_key]
    return a, root, read(root / filename)


def main():
    pointer = o.HERE / 'stale-aux-closed-terminal-publication-created.json'
    assert not pointer.exists()
    collection, folder, receipt = authority('logical-terminal-' + RUN + '-collected.json',
        'collection', 'receipt.json', 'receipt_sha256')
    logs, _, log_receipt = authority('closed-batch-postexit-preservation-created.json',
        'root', 'receipt.json', 'receipt_sha256')
    assert log_receipt['passed']
    gui, service = read(folder / 'GUI-preservation.json'), read(folder / 'service-preservation.json')
    t = gui['terminal']
    assert t['run']['run_id'] == RUN and t['technical_status'] == 'verifier_failure'
    assert t['blocked_reason'].startswith('candidate_verifier_error:Exact candidate extraction provenance invalid:')
    assert t['official_reward'] == 0 and t['scoring_status'] == 'complete'
    assert (t['actor_calls'], t['verifier_calls'], t['auxiliary_calls']) == (16, 51, 16)
    assert (t['decisions'], t['environment_actions']) == (14, 13)
    assert receipt['GUI_original_files_full_SHA_verified'] == 57
    assert receipt['service_original_requests_full_SHA_verified'] == 83
    assert o.sha(folder / 'selected-originals/technical-failure.json') == gui['terminal_sha256']
    final = folder / 'selected-originals/final-actually-captured.png'
    assert o.sha(final) == '2c7e38311097cbb00f28ae622d6550f2e64ccb05b3cd5c9780bd577aa8536cee'
    labels = {}
    for p in o.HERE.glob('source-review-*-created.json'):
        if not re.fullmatch(r'source-review-\d+-created\.json', p.name):
            continue
        _, _, reviewed = authority(p.name, 'review', 'review.json', 'review_sha256')
        assert reviewed['independent_current_checker_execution_score_join_not_performed']
        for row in reviewed['rows']:
            assert row['candidate_event_sha256'] not in labels
            labels[row['candidate_event_sha256']] = row
    relevant = [labels[h] for h in gui['original_candidate_event_hashes']]
    assert len(relevant) == 16
    positives = [r['id'] for r in relevant if r['candidate_semantic_mirage'] is True and not r['pure_native_WAIT_excluded']]
    assert positives == ['54f8ef71fd4bf82dc62b']
    joined = read(o.HERE / 'post-review-join-1794278896430073300/join.json')['rows'][0]
    assert joined['run'] == RUN and joined['accepted'] and joined['executed']
    latest_join = read(o.HERE / 'post-review-join-1794280687462020400/join.json')['rows'][0]
    assert latest_join['id'] == '4335535706704d79f7c6' and not latest_join['accepted'] and not latest_join['executed']
    audited, audits = {}, []
    for p in sorted(o.HERE.glob('mixed-receipt-audit-created-*.json')):
        a, root, ar = authority(p.name, 'root', 'receipt.json', 'receipt_sha256')
        assert ar['passed']
        audits.append(a)
        for row in read(root / '3090-native-bindings.json')['reports']:
            assert row['native_proof']['natural_EOS']
            if row['request'] in audited:
                assert audited[row['request']] == row
            audited[row['request']] = row
    assert sorted(audited) == ['%04d' % i for i in range(1, 183)]
    counts = dict(collections.Counter(r['operation'] for r in audited.values()))
    assert counts == dict(actor=31, judge=120, evidence=31)
    original = o.PACKAGE / 'release/claim_origin.py'
    spec = importlib.util.spec_from_file_location('sealed_original_claim_quote_checker', original)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    packet = read(relevant[-1]['public_source_packet'])
    assert packet['id'] == latest_join['id']
    answer = packet['native_parser_result']['payload']['answer']
    representation_diagnosis = []
    for ident, name in [('0181', 'source31-postcheck181-reply-created.json'), ('0182', 'source31-format182-reply-created.json')]:
        a, root, _ = authority(name, 'root', 'receipt.json', 'receipt_sha256')
        v = json.loads((root / (ident + '-raw.txt')).read_bytes())
        result = checker.check_claim_origins(v, packet['candidate'])
        assert len(result['errors']) == 1 and result['errors'][0]['claim_index'] == 3
        text = v['claims'][3]['text']
        assert packet['candidate'].find(text) == -1 and answer.find(text) == 0
        representation_diagnosis.append(dict(request=ident, actual_reply_authority=a,
            original_rejection=result['errors'], exact_decoded_native_answer_span=[0, len(text)],
            raw_candidate_unchanged=True, verdict_or_status_modified=False))
    evidence = o.HERE / 'actual-evidence-1794279955566222400'
    verify_seal(evidence)
    actual, actual_gui = read(evidence / '3090.json'), read(evidence / '4090.json')
    assert actual['worker/process.json']['actual'].get('absent')
    assert actual_gui['control/runner-process.json']['actual'].get('absent')
    before = {name: (o.BASE / name).read_bytes() for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']}
    status = copy.deepcopy(json.loads(before['full-gui-current.json']))
    c = status['linked_remaining31']
    planned = read(o.PACKAGE / 'plan.json')['queue']
    finished = [status['original_first_track']['run_id'], *[r['run_id'] for r in actual['worker/status.json']['value']['done']]]
    remaining = [row['run_id'] for row in planned if row['run_id'] not in finished]
    assert len(remaining) == 29 and len(set(finished)) == 3
    c.update(state=actual['worker/status.json']['value'], new31_GUI_state=actual_gui['batch/status.json']['value'],
        actual_worker=actual['worker/process.json']['actual'], actual_GUI=actual_gui['control/runner-process.json']['actual'],
        actual_evidence_reports_closed_worker=True, audited_requests=sorted(audited), audited_request_counts=counts,
        actual_launcher_and_GUI_postexit_logs=logs, current_run_full_endpoint_verified=True,
        current_run_observed_prefix_any_Mirage=True, trajectory_semantic_mirage=True,
        current_run_terminal=RUN, verified_new31_terminal_track_count=2,
        remaining_original_unstarted_tracks=remaining, remaining_original_unstarted_track_count=29,
        existing_batch_has_exited=True, existing_stage_service_GUI_must_never_restart=True)
    c['verified_terminal_source_outcome_reviews'][RUN] = dict(
        authority=collection, original_terminal_sha256=gui['terminal_sha256'],
        terminal_outcome='blocked', technical_status='verifier_failure', official_reward=0.0,
        scoring_status='complete', original_model_calls=dict(actor=16, judge=51, evidence=16),
        original_environment_actions=13, original_decisions=14, trajectory_semantic_mirage=True,
        positive_candidate_ids=positives, accepted_and_executed_positive_candidate=positives[0],
        all16_source_candidates_reviewed=True, all83_native_natural_EOS_audited=True,
        quote_representation_failure_is_separate_from_semantic_error=True)
    primary = [r['native_proof'] for r in audited.values() if r['operation'] != 'evidence']
    aux = [r['native_proof'] for r in audited.values() if r['operation'] == 'evidence']
    c['primary_only_audited_totals'] = dict(calls=len(primary), input_tokens=sum(r['actual_input_tokens'] for r in primary),
        output_tokens=sum(r['output_tokens'] for r in primary), summed_native_call_timer_seconds=sum(r['native_call_timer_seconds'] for r in primary))
    c['auxiliary_only_audited_totals'] = dict(calls=len(aux), input_tokens=sum(r['actual_input_tokens'] for r in aux),
        output_tokens=sum(r['output_tokens'] for r in aux), timing_scope='Auxiliary timers include GPU switches/instrumentation; not added to primary timers.')
    status.update(time=time.time(), goal='active', monitor_should_remain_active=True,
        execution_state='original_batch_exited_after_technical_terminal', previous_goal_turn_classification='progress',
        current_goal_turn_classification='progress: preserved and source-reviewed the terminal; isolated exact JSON-answer representation failure',
        efficacy_established=False, relative_Mirage_reduction=None, matched_efficacy_analysis_ready=False,
        verified_complete_original32_track_count_lower_bound=3, original32_all_verified_complete=False)
    root = o.HERE / ('stale-aux-closed-terminal-publication-' + str(time.time_ns()))
    root.mkdir()
    report = ('## 最新：2026-11-10 旧帧有辅助轨终局；原队列已退出，29轨尚未开始\n\n'
        '权威 `' + root.relative_to(o.BASE).as_posix() + '/status.json`。目标ACTIVE；不能使用旧stage/service/gui重新启动。\n\n'
        'fullhistory23-T000-stale_replace-aux终局verifier_failure/blocked/official0：14决策、13环境动作、16actor+51judge+16aux=83次本地调用，全部自然EOS。原57个GUI终局文件、83组完整请求SHA、824条GUI链及结束确认封存；worker和GUI实际退出，双机日志另有postexit seal。原有unused预算不是重刷本条的授权。\n\n'
        '16个主候选均先审完整原图/合法历史再关联。来源29把65美元支架归为kayak，已有放行并实执，故本轨Mirage=true；最后来源31已改称rack，不抹除发生。最后STOP未放行，原后图仍为185/199列表及正常页脚。最低价/唯一蓝艇及50/70小图颜色仍未知，不能称挡住确定Mirage或整条正常STOP误拦。\n\n'
        '直接技术终局来自两次真实核验181/182的c4来源检查：所引句子逐字等于原生STOP answer解码后的前缀，却因JSON字符串里的转义引号不在原始候选正文中形成相同字节片段而被拒。原始回复、字节规则、失败和官方0全部保留；这里只定位表示层问题，尚未修改validator、状态或动作。181/182同时要求单帧12条、承认升序后仍要求后续页，逻辑问题另存，不能靠修复转义来认证最低价。\n\n'
        '累计182次真实调用已原生审计，31主候选、4阳性来自两个有辅助轨，任意未知15个。识别仅诊断，主要终点仍为完整匹配GUI轨迹中的主模型Mirage及完成/误拦。原32中3个端点包括技术失败，29轨从未开始。后续仅准备新的、明确排除所有终局的来源绑定技术方案；不重跑已结束轨，不静默更改正式条件，不扩大原预算。尚无可核实30%或减半降幅。\n\n')
    status['latest_findings'] = report.split('\n\n')[2:]
    status['authorities'].update(actual_evidence=str(evidence), actual_evidence_seal_sha256=o.sha(evidence / 'seal.json'),
        all_nonoverlapping_native_audits=audits, latest_closed_terminal_collection=collection,
        closed_batch_postexit_log_preservation=logs, decoded_answer_representation_diagnosis=representation_diagnosis,
        closed_terminal_publication=str(root))
    for name, raw in before.items():
        (root / ('before-' + name)).write_bytes(raw)
    (root / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (root / 'report.md').write_text(report, encoding='utf8')
    o.save(root / 'status.json', status)
    o.save(root / 'review.json', dict(run_id=RUN, collection=collection, postexit_logs=logs,
        source_labels=relevant, positive_candidate_ids=positives, trajectory_semantic_mirage=True,
        representation_diagnosis=representation_diagnosis, source_labels_or_originals_modified=False,
        new_model_GUI_scorer_calls=0, condition_change_deployed=False, goal='active'))
    for name in ['README.md', 'HANDOFF.md']:
        assert (o.BASE / name).read_bytes() == before[name]
        (o.BASE / name).write_bytes(report.encode('utf8') + before[name])
    assert (o.BASE / 'full-gui-current.json').read_bytes() == before['full-gui-current.json']
    o.save(o.BASE / 'full-gui-current.json', status)
    for name in ['README.md', 'HANDOFF.md']:
        assert (o.BASE / name).read_bytes().startswith(report.encode('utf8'))
    assert read(o.BASE / 'full-gui-current.json') == status
    o.save(root / 'receipt.json', dict(passed=True, heads_verified=True, closed_batch_not_restarted=True,
        remaining_tracks_never_started=29, new_model_GUI_scorer_calls=0, efficacy_established=False))
    o.save(root / 'seal.json', {p.name: o.sha(p) for p in root.iterdir() if p.is_file()})
    a = dict(root=str(root), status_sha256=o.sha(root / 'status.json'), review_sha256=o.sha(root / 'review.json'),
        seal_sha256=o.sha(root / 'seal.json'))
    o.save(pointer, a)
    print(json.dumps(a))


if __name__ == '__main__':
    main()
