"""Join separately sealed source reviews to the new stale pair; no experiment calls."""
import hashlib
import base64
import json
import time
from pathlib import Path

from control import HERE, BASE, save, sha


def load(path):
    return json.loads(path.read_bytes())


def sealed(root):
    assert all(sha(root / n) == h for n, h in load(root / 'seal.json').items())


def main():
    evidence = HERE / 'live-evidence-incremental-1794657927079853400'
    pairs = HERE / 'pair-trace-equivalence-1794657585337221400'
    usage = HERE / 'usage-snapshot-1794658177685481800'
    flash = HERE / 'Flash-CPU-increment-1794658094422652800'
    terminals = HERE / 'terminal-audit-1794658095535372800.json'
    roots = {
        'baseline': (HERE / 'semantic-packets-1794657027458544900',
                     HERE / 'T017-stale-baseline12-source-review-1794657453338855200'),
        'gate': (HERE / 'semantic-packets-1794657911428332100',
                 HERE / 'T017-stale-gate14-source-review-1794658093401223200')}
    for root in [evidence, pairs, usage, flash] + [v for pair in roots.values() for v in pair]:
        sealed(root)
    actual = load(evidence / '3090.json')
    gui = load(evidence / '4090.json')
    independent_flash = {v['request_id']: v for v in load(flash / 'cumulative-report.json')['result']['requests']}
    forwards = {v['request_id']: v for v in actual['sealed_Flash_requests']}
    records = load(terminals)['result']['terminals']
    pair = next(v for v in load(pairs / 'comparison.json')['pairs']
                if v['task_id'] == 17 and v['condition'] == 'stale_replace')
    assert pair['both_sealed_terminals'] and not pair['complete_trace_equal']
    assert pair['first_difference']['step'] == 1
    joined = {}
    for arm, (packets, reviewroot) in roots.items():
        run = 'flash14-T017-stale_replace-' + arm
        review = load(reviewroot / 'review.json')
        count = 12 if arm == 'baseline' else 14
        assert review['candidate_coverage'] == count and review['unreviewed_candidates'] == 0
        assert review['source_judgments_before_this_run_official_or_execution_join']
        entries = load(packets / 'review-index.json')['packets']
        private = load(packets / 'PRIVATE-source-index.json')
        assert len(entries) == len(private) == len(review['rows']) == count
        controller = next(c for c in gui['controllers'] if run + '/' in c['path'])
        natives = {v['decision']: v for v in actual['sealed_main_requests'] if v['run_id'] == run}
        assert sorted(natives) == list(range(1, count + 1))
        terminal = next(v for v in records if v['run']['run_id'] == run)
        assert terminal['outcome'] == 'model_stop' and terminal['actor_calls'] == count
        assert terminal['environment_actions'] == count - 1
        assert terminal['injection_fired'] and not terminal['infrastructure_failure']
        assert terminal['semantic_mirage'] is None and terminal['cleanup_error'] is None
        rows = []
        for number, (entry, mapping, source) in enumerate(zip(entries, private, review['rows']), 1):
            packet = load(packets / entry['file'])
            native = natives[number]
            assert source['candidate'] == number and source['packet_sha256'] == entry['sha256']
            assert mapping['run_id'] == run and mapping['decision_index'] == number
            assert mapping['request_id'] == native['request_id']
            assert packet['source_wire_sha256'] == native['wire_sha256']
            def restore(value):
                if isinstance(value, list):
                    return [restore(v) for v in value]
                if isinstance(value, dict):
                    if value.get('type') == 'image_url':
                        data = (packets / value['image_url']['url']).read_bytes()
                        assert hashlib.sha256(data).hexdigest() == value['original_PNG_sha256']
                        return {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(data).decode()}}
                    return {k: restore(v) for k, v in value.items()}
                return value
            full_body = restore(packet['legal_full_input_review_projection'])
            raw_body = json.dumps(full_body, ensure_ascii=False, indent=2).encode()
            canonical_body = json.dumps(full_body, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
            assert hashlib.sha256(raw_body).hexdigest() == packet['source_body_sha256']
            assert hashlib.sha256(canonical_body).hexdigest() == native['body_sha256']
            assert packet['source_request_seal_sha256'] == native['seal_sha256']
            assert packet['candidate_exact_text'] == native['native_text']
            assert native['actual_tensor_files_verified'] and native['natural_EOS']
            request, forwarded, reply = (controller['actor_requests'][number - 1],
                                          controller['forwarded_images'][number - 1],
                                          controller['actor_replies'][number - 1])
            assert request['request_id'] == reply['request_id'] == native['request_id']
            assert request['body_sha256'] == native['body_sha256']
            assert reply['text_sha256'] == hashlib.sha256(native['native_text'].encode()).hexdigest()
            assert forwarded['image_sha256'] == source['current_image_sha256'] == native['current_image_sha256']
            flash_binding = None
            if arm == 'gate':
                rid = forwarded['gate_request_id']
                f, independent = forwards[rid], independent_flash[rid]
                assert f['decision'] == independent['decision'] == 'YES'
                assert f['image_sha256'] == independent['image_sha256'] == native['current_image_sha256']
                assert f['seal_sha256'] == independent['seal_sha256']
                flash_binding = {'request_id': rid, 'seal_sha256': f['seal_sha256'],
                                 'same_PNG_actual_forward_and_raw_head_verified': True}
            else:
                assert forwarded['gate_request_id'] is None
            action = next((a for a in controller['environment_actions'] if a['step'] == number), None)
            if number == count:
                assert action is None
            else:
                assert action is not None
            rows.append({'source_review': source, 'actual_request_id': native['request_id'],
                         'actual_request_seal_sha256': native['seal_sha256'],
                         'native_input_ID_pixels_grid_first_forward_and_EOS_verified': True,
                         'Flash': flash_binding, 'actual_environment_action': action})
        assert terminal['Flash_replies'] == (count if arm == 'gate' else 0)
        assert terminal['recaptures'] == 0
        cost = load(usage / 'summary.json')['by_run'][run]
        assert cost['calls'] == count
        joined[arm] = {'run_id': run, 'source_review': str(reviewroot),
                       'source_review_sha256': sha(reviewroot / 'review.json'),
                       'source_packets_seal_sha256': sha(packets / 'seal.json'),
                       'trajectory_semantic_Mirage': review['trajectory_semantic_Mirage'],
                       'definite_positive_candidates': review['definite_positive_candidates'],
                       'unresolved_candidates': review['unresolved_candidates'],
                       'literal_negative_candidates': review['literal_negative_candidates'],
                       'terminal': terminal, 'cost': cost, 'rows': rows}
    assert joined['baseline']['trajectory_semantic_Mirage'] is None
    assert joined['gate']['trajectory_semantic_Mirage'] is False
    dest = HERE / ('T017-stale-paired-publication-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    for name, path in [('previous-semantic-review-current.json', HERE / 'semantic-review-current.json'),
                       ('previous-experiment-current.json', HERE / 'experiment-current.json'),
                       ('previous-HANDOFF.md', BASE / 'HANDOFF.md'),
                       ('previous-README.md', BASE / 'README.md')]:
        (dest / name).write_bytes(path.read_bytes())
    save(dest / 'review-joined.json', {
        'pair_trace': str(pairs), 'pair_trace_seal_sha256': sha(pairs / 'seal.json'),
        'first_difference': pair['first_difference'], 'arms': joined,
        'actual_native_audit': str(evidence), 'actual_native_audit_seal_sha256': sha(evidence / 'seal.json'),
        'terminal_audit': str(terminals), 'terminal_audit_sha256': sha(terminals),
        'independent_Flash_CPU_audit': str(flash), 'independent_Flash_seal_sha256': sha(flash / 'seal.json'),
        'source_reviews_sealed_before_outcome_join': True,
        'reporter_hash_domain_repair_preservation': 'D:\\MultiModel\\jev-defense-four-gpu-20261106\\flash-ample-memory-gui-20261114-linked11\\stale-pair-publication-binding-failure-1794658345132527300',
        'both_raw_file_and_canonical_wire_body_hashes_verified': True,
        'one_reviewer_not_fully_blind': True,
        'whole_trace_equivalence_or_blanket_label_reuse': False,
        'initial_PNG_already_differs_before_first_gate': True,
        'all_gate_yes_and_zero_recaptures': True,
        'baseline_unknown_not_converted_to_zero': True,
        'within_pair_Mirage_reduction': None, 'overall_Mirage_reduction': None,
        'defense_effectiveness_proven': False, 'current_queue_changed': False,
        'new_model_GUI_calls_by_publication': 0, 'goal': 'active', 'time': time.time()})
    report = 'T017旧帧配对完整审查与授权开发预检-20261114.md'
    text = '''# T017旧帧配对：两臂均完成，尚不能证明防御降低Mirage

无门控12个自然EOS回复、11个实际动作；Flash门控14个自然EOS回复、13个实际动作。两臂均原生STOP、官方评分1，无基础设施或清理故障；两份原终局semantic_mirage:null保持不改。评分只说明任务得分，语义标签在读取本组评分和执行关联前单独封存。

无门控12/12候选审完：11个字面阴性，候选2关于Keyword焦点的断言未决。图上没有蓝色焦点框，但历史点击与执行返回也不能单独证明当前视觉焦点；缺边框不足以确证实际未聚焦，不能硬记阳性或阴性。因此整轨标签保留null。

门控14/14候选与12张完整原图新审：14个字面阴性、无未决、无纯原生WAIT；在这条完整轨迹和本次单审范围内未发现Mirage。候选2只计划输入，没有把焦点当作已见事实。模型先查看F700大图，区分红车架和黑车把，再打开Six13，实际大图显示红把带、900美元和Fairfax Station/Virginia。在任务900–950区间内，合格的900美元商品已达下限，最低价结论不需要声称其余所有商品均不匹配，也未声称唯一。

这不是可归因的门控降幅：两臂第一步的原始截图和完整输入已经不同；不能把差异误报成同输入数值失稳或套用另一臂标签。门控14次全部YES、0NO、0复拍，清晰旧帧也被放行。两臂都任务成功，而基线语义仍未决，所以配对与总体Mirage降幅均为null。单图可读性问题不能保证旧帧新鲜，也不核验主模型的历史总结。正常图清晰度没有误拦，但没有真实NO后恢复的验证。

实际请求、完整输入IDs/pixels/grid、第一forward、自然EOS、原图原字节转交、Flash原始概率、95/125事件链与42/47终局文件分别绑定。原始张量审核按已封存时间增量引用，并非重新全量散列；最终全队列退出后的全量终结审核仍必需。单审、已知任务、非全盲；不将26个候选当26个独立任务。具体tokens、原生秒数与来源见review-joined.json，两阶段显存预检、加载和旧工程失败成本不混入本组原生推理秒数。

用户已明确批准当前29条GUI结束后的10条离线主27B证据约束开发预检：每条保留完整原图和历史，仅原system追加已封存约束，每次增加292个原生输入tokens，最多10次新调用、2048输出、无格式重试/自动重试、无GUI/评分/Flash/付费API。旧基线回复复用。当前GUI不变；本批准不等于新正式GUI发布授权。新回复即使纠正先前错误，也不能抹去历史中已经发生的Mirage。
'''
    (dest / report).write_text(text, encoding='utf8')
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    (HERE / 'semantic-review-current.json').write_text(json.dumps({
        'publication': str(dest), 'report': str(dest / report),
        'review_sha256': sha(dest / 'review-joined.json'), 'seal_sha256': sha(dest / 'seal.json'),
        'previous_clean_pair': str(HERE / 'T017-clean-paired-publication-1794656865993420400'),
        'Mirage_reduction': None, 'goal': 'active', 'time': time.time()}, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'publication': str(dest), 'baseline_label': None, 'gate_label': False,
                      'pair_Mirage_reduction': None, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
