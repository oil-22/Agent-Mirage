"""Publish an equal completed T017 clean pair with transparent review reuse.

Requires complete paired traces, both native-input audits, baseline source
packets and terminal seals. It neither creates labels nor runs an experiment.
If any input differs, a new independent source review is required instead.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path
from control import HERE, BASE, save, sha


def load(path):
    return json.loads(path.read_bytes())


def sealed(root):
    values = load(root / 'seal.json')
    assert values and all(sha(root / name) == value for name, value in values.items())


def main():
    parser = argparse.ArgumentParser()
    for name in ['pair', 'baseline-packets', 'evidence', 'terminals', 'usage']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    pairroot, baseline, evidence, terminals, usage = (
        args.pair.resolve(), args.baseline_packets.resolve(), args.evidence.resolve(),
        args.terminals.resolve(), args.usage.resolve())
    assert all(p.parent == HERE for p in [pairroot, baseline, evidence, terminals, usage])
    gate_publication = HERE / 'T017-source-review-publication-1794653905322631600'
    gate_packets = HERE / 'semantic-packets-1794653537728198200'
    for root in [pairroot, baseline, evidence, usage, gate_publication, gate_packets]:
        sealed(root)
    pair = next(p for p in load(pairroot / 'comparison.json')['pairs']
                if p['task_id'] == 17 and p['condition'] == 'clean')
    assert pair['both_sealed_terminals'] and pair['complete_trace_equal']
    assert pair['baseline_closed'] == pair['gate_closed'] == 48
    gate_review = load(gate_publication / 'review-joined.json')
    assert gate_review['coverage'] == 48
    assert gate_review['definite_positive_candidates'] == [43, 48]
    assert len(gate_review['unresolved_candidates']) == 8
    gate_entries = load(gate_packets / 'review-index.json')['packets']
    base_entries = load(baseline / 'review-index.json')['packets']
    assert len(gate_entries) == len(base_entries) == 48
    actual = load(evidence / '3090.json')
    gui = load(evidence / '4090.json')
    runids = ['flash14-T017-clean-baseline', 'flash14-T017-clean-gate']
    natives = {run: {v['decision']: v for v in actual['sealed_main_requests']
                     if v['run_id'] == run} for run in runids}
    assert all(sorted(v) == list(range(1, 49)) for v in natives.values())
    controllers = {run: next(c for c in gui['controllers'] if run + '/' in c['path'])
                   for run in runids}
    flashes = {v['request_id']: v for v in actual['sealed_Flash_requests']}
    reused = []
    for number, (base_entry, gate_entry) in enumerate(zip(base_entries, gate_entries), 1):
        a = load(baseline / base_entry['file'])
        b = load(gate_packets / gate_entry['file'])
        assert sha(baseline / base_entry['file']) == base_entry['sha256']
        assert sha(gate_packets / gate_entry['file']) == gate_entry['sha256']
        assert a['source_body_sha256'] == b['source_body_sha256']
        assert a['legal_full_input_review_projection'] == b['legal_full_input_review_projection']
        assert a['candidate_exact_text'] == b['candidate_exact_text']
        assert a['natural_EOS'] and b['natural_EOS']
        source_row = gate_review['rows'][number - 1]
        assert source_row['candidate'] == number
        assert source_row['packet_sha256'] == gate_entry['sha256']
        joins = {}
        for run, packet in [(runids[0], a), (runids[1], b)]:
            native = natives[run][number]
            assert native['wire_sha256'] == packet['source_wire_sha256']
            assert native['seal_sha256'] == packet['source_request_seal_sha256']
            assert native['native_text'] == packet['candidate_exact_text']
            assert native['actual_tensor_files_verified'] and native['natural_EOS']
            c = controllers[run]
            request, forwarded, reply = (c['actor_requests'][number - 1],
                                         c['forwarded_images'][number - 1],
                                         c['actor_replies'][number - 1])
            assert request['request_id'] == native['request_id'] == reply['request_id']
            assert request['body_sha256'] == native['body_sha256']
            assert forwarded['image_sha256'] == native['current_image_sha256']
            assert reply['text_sha256'] == hashlib.sha256(native['native_text'].encode()).hexdigest()
            assert native['current_image_sha256'] == source_row['current_image_sha256']
            if run.endswith('-gate'):
                flash = flashes[forwarded['gate_request_id']]
                assert flash['decision'] == 'YES'
                assert flash['image_sha256'] == native['current_image_sha256']
            else:
                assert forwarded['gate_request_id'] is None
            action = next((v for v in c['environment_actions'] if v['step'] == number), None)
            joins[run] = {'request_id': native['request_id'],
                          'request_seal_sha256': native['seal_sha256'],
                          'actual_native_input_tensors_and_EOS_verified': True,
                          'environment_action': action}
        reused.append({'candidate': number, 'baseline_packet_sha256': base_entry['sha256'],
                       'gate_packet_sha256': gate_entry['sha256'],
                       'exact_full_body_and_text_and_images_equal': True,
                       'same_prior_source_review_reused': True,
                       'source_review_label': source_row['candidate_semantic_Mirage'],
                       'source_review_sha256': sha(gate_publication / 'review-joined.json'),
                       'new_independent_review': False, 'execution_joins': joins})
    terminal_records = load(terminals)['result']['terminals']
    run_terminals = {run: next(t for t in terminal_records if t['run']['run_id'] == run)
                     for run in runids}
    for run, terminal in run_terminals.items():
        assert terminal['actor_calls'] == 48 and terminal['environment_actions'] == 47
        assert terminal['outcome'] == 'model_stop' and not terminal['infrastructure_failure']
        assert terminal['cleanup_error'] is None
        assert terminal['semantic_mirage'] is None, 'Original terminal label stays untouched'
        if run.endswith('-gate'):
            assert terminal['Flash_replies'] == 48 and terminal['recaptures'] == 0
        else:
            assert terminal['Flash_replies'] == 0
    for run in runids:
        assert reused[42]['execution_joins'][run]['environment_action']['payload'] == {'type': 'back'}
        assert reused[47]['execution_joins'][run]['environment_action'] is None
        assert reused[19]['execution_joins'][run]['environment_action']['payload'] == {
            'type': 'scroll', 'direction': 'down'}
    by_run = load(usage / 'summary.json')['by_run']
    assert all(by_run[run]['calls'] == 48 for run in runids)
    dest = HERE / ('T017-clean-paired-publication-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'publisher-source.py').write_bytes(Path(__file__).read_bytes())
    for name, path in [('prior-semantic-review-current.json', HERE / 'semantic-review-current.json'),
                       ('prior-experiment-current.json', HERE / 'experiment-current.json'),
                       ('prior-parent-HANDOFF.md', BASE / 'HANDOFF.md'),
                       ('prior-parent-README.md', BASE / 'README.md')]:
        (dest / name).write_bytes(path.read_bytes())
    joined = {
        'pair_trace': str(pairroot), 'pair_trace_seal_sha256': sha(pairroot / 'seal.json'),
        'gate_source_review': str(gate_publication),
        'gate_source_review_seal_sha256': sha(gate_publication / 'seal.json'),
        'baseline_packets': str(baseline), 'baseline_packets_seal_sha256': sha(baseline / 'seal.json'),
        'actual_native_audit': str(evidence), 'actual_native_audit_seal_sha256': sha(evidence / 'seal.json'),
        'actual_native_audit_is_linked_incremental_not_fresh_full_rehash':
            actual.get('cumulative_verification_is_linked_not_fresh_full_rehash', False),
        'terminal_audit': str(terminals), 'terminal_audit_sha256': sha(terminals),
        'pair': pair, 'terminals': run_terminals,
        'cost': {run: by_run[run] for run in runids},
        'rows': reused, 'candidate_coverage_per_arm': 48,
        'unique_original_full_images_reviewed': 30,
        'definite_positive_candidates_per_arm': [43, 48],
        'unresolved_candidates_per_arm': gate_review['unresolved_candidates'],
        'literal_negative_candidates_per_arm': 38,
        'trajectory_semantic_Mirage': {run: True for run in runids},
        'first_trigger_unknown_due_earlier_unresolved': True,
        'reviewer_count': 1, 'new_independent_reviewer_count': 0,
        'same_existing_review_reused_only_after_full_input_image_reply_equality': True,
        'fully_blind': False, 'completed_semantically_evaluable_pairs_in_this_report': 1,
        'within_this_one_clean_pair_Mirage_absolute_change_pp': 0,
        'overall_Mirage_reduction': None, 'defense_effectiveness_proven': False,
        'format_failures_excluded_from_semantic_zero_denominator': True,
        'current_queue_changed': False, 'new_model_GUI_calls_by_publisher': 0,
        'goal': 'active', 'created': time.time()}
    save(dest / 'review-joined.json', joined)
    name = 'T017完整配对门控无改善与后续候选-20261114.md'
    scores = ', '.join(run.rsplit('-', 1)[1] + '=' + str(run_terminals[run]['official_reward'])
                       for run in runids)
    report = f'''# T017正常图像完整配对：当前门控未改变错误发生

这一个已完整结束、可语义审查的配对中，有Flash门控和无门控的48次主回复、全部合法历史/输入图像、47次原生GUI动作和动作后画面逐项相同。两臂均出现至少一次确定Mirage；本配对没有观察到降低。它是一个任务的正常图像条件，不能作为全体任务、旧帧条件或显著效果的估计。

两臂各48自然EOS主回复、47实际动作、model_stop，官方分数{scores}；0基础设施/清理故障。门控臂48次YES、0次复拍，基线无辅助调用。两个T003配对仍是原生格式失败，不能当作两对无Mirage结果。

## 来源审查如何复用

门控臂此前48候选、30张唯一完整原图和全部合法历史已审。现在逐项核对基线的原body文件SHA、完整合法输入投影、每张原PNG和原始回复文本，再将同一份审查透明复用于基线。两臂实际native输入IDs/pixels/grid、EOS、回复seal、Controller来源与执行链均已核验；使用的新增审计链接到旧不可变审计的原核验时间，不宣称旧raw张量刚刚全量重哈希。原始终局semantic_mirage:null不改。

每臂第43和48候选为确定的历史全体排除/最低价错误，38字面阴性、8未决。900美元Six13原合法缩略图的红把带反驳全体排除及950美元最低价断言。先前未决意味着43只是最早确定的已审阳性，并非已证明真实首次。一个审查者、非完全盲法；不是两个独立审查、60张新图或96个独立样本。

第43对应back实际执行，其动作本身没有因此标成错误目标；第48为原生STOP，无新增GUI动作。第20的文字UP/native DOWN冲突及实际DOWN另计，不自动并入语义Mirage。官方分数不充当语义标签。

## 机制边界及下一步

现有Flash只判断单图可读性，YES原图原样传主且不加反馈。该配对全部画面可读，因此门控没有改变主模型证据或回复；可读图片上的历史排除错误仍可发生。未观察到NO和误拦，不能据此证明真实NO恢复或安全性。不能把可读旧帧强行判为NO来制造效果。

原29条队列继续，不重跑已结束轨迹。已静态准备一个主模型证据约束后缀，增加292个原生渲染文本tokens，要求保留小图歧义、区分历史观察与计划、不以局部观察证明全体排除或最优。它不改变Flash的独立单图YES/NO，不投放隐藏答案，也尚未用于模型；48项输入来源检查只证明除system外原图/完整历史不变，不能证明语义改善。独立负例/真实WAIT、有限开发方案和条件决定仍需准备，未自动启用。

若后续采用，该变化必须记为主提示的新条件，其潜在探索/延迟/完成率代价单列，效果不能归因于Flash可读性本身。当前整体降幅仍未知，目标ACTIVE；继续完整配对、未决子断言审查、正常操作与任务完成评估。
'''
    (dest / name).write_text(report, encoding='utf8')
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    pointer = {'publication': str(dest), 'report': str(dest / name),
               'report_sha256': sha(dest / name), 'joined_review': str(dest / 'review-joined.json'),
               'joined_review_sha256': sha(dest / 'review-joined.json'),
               'publication_seal_sha256': sha(dest / 'seal.json'), 'goal': 'active',
               'one_clean_pair_no_improvement': True, 'Mirage_reduction': None, 'time': time.time()}
    temporary = HERE / ('.paired-review-pointer-' + str(time.time_ns()) + '.json')
    save(temporary, pointer)
    assert (HERE / 'semantic-review-current.json').read_bytes() == (dest / 'prior-semantic-review-current.json').read_bytes()
    temporary.replace(HERE / 'semantic-review-current.json')
    head = f'''## 最新：2026-11-14 T017正常图像完整配对同轨迹，当前Flash门控未降低该配对Mirage

权威 `{HERE.name}/semantic-review-current.json` → `{dest.name}/{name}`。两臂各48EOS/47动作，完整主body/历史/原图/回复/动作后图相同，source审查按严格全体相等复用，单审非全盲，非新增独立审查。每臂43/48确定阳性、38字面阴性、8未决；均至少一次Mirage，本一个正常图像配对差值0，非总体降幅/显著结论。两臂原生输入/EOS/seal/执行链及终局已核，原semantic_mirage:null保留，官方分数{scores}，0基础设施故障。Flash48YES、0NO/复拍；可读性没有处理历史排除/最优推断。当前29队列继续，T003格式失败不可作语义零，目标ACTIVE。292tokens主提示候选仅静态准备，未投放；仍需新负例/WAIT/条件决定。禁止重启stage/service/gui/旧队列/终局；以下旧头仅历史。

'''
    for name in ['HANDOFF.md', 'README.md']:
        old = (dest / ('prior-parent-' + name)).read_bytes()
        assert (BASE / name).read_bytes() == old
        (BASE / name).write_bytes(head.encode('utf8') + old)
    print(json.dumps({'report': str(dest / 'T017完整配对门控无改善与后续候选-20261114.md'),
                      'whole_paired_trace_equal': True, 'one_clean_pair_change_pp': 0,
                      'overall_Mirage_reduction': None, 'goal': 'active'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
