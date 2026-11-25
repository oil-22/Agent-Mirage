"""Publish the fully equal23-reply pair, preserving uncertain absence claims."""
import base64
import hashlib
import json
import time
from pathlib import Path

from control import HERE, save, sha


def load(p):
    return json.loads(p.read_bytes())


def main():
    evidence = HERE / 'live-evidence-incremental-1794659250426232400'
    pairs = HERE / 'pair-trace-equivalence-1794659206339554400'
    flashroot = HERE / 'Flash-CPU-increment-1794659207445110300'
    terminals = HERE / 'terminal-audit-1794659327783558600.json'
    usage = HERE / 'usage-snapshot-1794659334650254900'
    roots = {
        'baseline': (HERE / 'semantic-packets-1794659249116490800',
                     HERE / 'T058-stale-baseline-source-review-reuse-1794659325492176600'),
        'gate': (HERE / 'semantic-packets-1794658995377566300',
                 HERE / 'T058-stale-gate23-source-review-1794659186595498100')}
    for root in [evidence, pairs, flashroot, usage] + [p for v in roots.values() for p in v]:
        assert all(sha(root / n) == h for n, h in load(root / 'seal.json').items())
    pair = next(v for v in load(pairs / 'comparison.json')['pairs']
                if v['task_id'] == 58 and v['condition'] == 'stale_replace')
    assert pair['both_sealed_terminals'] and pair['complete_trace_equal']
    assert pair['baseline_closed'] == pair['gate_closed'] == 23
    actual, gui = load(evidence / '3090.json'), load(evidence / '4090.json')
    flashes = {v['request_id']: v for v in actual['sealed_Flash_requests']}
    independent = {v['request_id']: v for v in load(flashroot / 'cumulative-report.json')['result']['requests']}
    joined = {}
    for arm, (packets, reviewroot) in roots.items():
        run = 'flash14-T058-stale_replace-' + arm
        review = load(reviewroot / 'review.json')
        assert review['candidate_coverage'] == 23 and review['unresolved_candidates'] == [23]
        assert review['trajectory_semantic_Mirage'] is None
        native = {v['decision']: v for v in actual['sealed_main_requests'] if v['run_id'] == run}
        assert sorted(native) == list(range(1, 24))
        controller = next(v for v in gui['controllers'] if run + '/' in v['path'])
        terminal = next(v for v in load(terminals)['result']['terminals'] if v['run']['run_id'] == run)
        assert terminal['actor_calls'] == 23 and terminal['environment_actions'] == 22
        assert terminal['outcome'] == 'model_stop' and terminal['injection_fired']
        assert not terminal['infrastructure_failure'] and terminal['cleanup_error'] is None
        assert terminal['semantic_mirage'] is None
        rows = []
        for number, (entry, label) in enumerate(zip(load(packets / 'review-index.json')['packets'], review['rows']), 1):
            packet = load(packets / entry['file'])
            a = native[number]
            assert label['candidate'] == number and label['packet_sha256'] == entry['sha256']
            assert packet['source_request_seal_sha256'] == a['seal_sha256']
            assert packet['source_wire_sha256'] == a['wire_sha256']
            assert packet['source_body_sha256'] == label['source_full_legal_body_sha256']
            assert packet['candidate_exact_text'] == a['native_text']
            assert a['actual_tensor_files_verified'] and a['natural_EOS']

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

            canonical = json.dumps(restore(packet['legal_full_input_review_projection']),
                                   sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
            assert hashlib.sha256(canonical).hexdigest() == a['body_sha256']
            request, forward, reply = (controller['actor_requests'][number - 1],
                                      controller['forwarded_images'][number - 1], controller['actor_replies'][number - 1])
            assert request['request_id'] == reply['request_id'] == a['request_id']
            assert request['body_sha256'] == a['body_sha256']
            assert reply['text_sha256'] == hashlib.sha256(a['native_text'].encode()).hexdigest()
            assert forward['image_sha256'] == label['current_image_sha256'] == a['current_image_sha256']
            f = None
            if arm == 'gate':
                rid = forward['gate_request_id']
                f = flashes[rid]
                assert f['seal_sha256'] == independent[rid]['seal_sha256']
                assert f['decision'] == independent[rid]['decision'] == 'YES'
                assert f['image_sha256'] == independent[rid]['image_sha256'] == a['current_image_sha256']
            else:
                assert forward['gate_request_id'] is None
            action = next((v for v in controller['environment_actions'] if v['step'] == number), None)
            assert (action is None) == (number == 23)
            rows.append({'source_review': label, 'actual_native_request_id': a['request_id'],
                         'actual_input_tensor_bytes_and_first_forward_EOS_verified': True,
                         'request_seal_sha256': a['seal_sha256'], 'actual_environment_action': action,
                         'Flash': f})
        assert terminal['Flash_replies'] == (23 if arm == 'gate' else 0) and terminal['recaptures'] == 0
        cost = load(usage / 'summary.json')['by_run'][run]
        assert cost['calls'] == 23
        joined[arm] = {'run_id': run, 'source_review': str(reviewroot),
                       'source_review_seal_sha256': sha(reviewroot / 'seal.json'),
                       'trajectory_semantic_Mirage': None, 'unresolved_candidates': [23],
                       'terminal': terminal, 'cost': cost, 'rows': rows}
    dest = HERE / ('T058-stale-paired-publication-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    (dest / 'previous-semantic-review-current.json').write_bytes((HERE / 'semantic-review-current.json').read_bytes())
    save(dest / 'review-joined.json', {
        'arms': joined, 'pair_trace': str(pairs), 'pair_trace_seal_sha256': sha(pairs / 'seal.json'),
        'actual_native_audit': str(evidence), 'actual_native_audit_seal_sha256': sha(evidence / 'seal.json'),
        'independent_Flash_CPU_audit': str(flashroot), 'independent_Flash_audit_seal_sha256': sha(flashroot / 'seal.json'),
        'terminal_audit': str(terminals), 'terminal_audit_sha256': sha(terminals),
        'complete_input_image_reply_action_trace_equal': True,
        'source_review_reused_transparently': True, 'reviewer_count': 1,
        'new_independent_reviewer_count': 0, 'fully_blind': False,
        'source_labels_sealed_before_official_execution_join': True,
        'unknown_not_converted_to_no_Mirage': True,
        'Mirage_reduction': None, 'effectiveness_proven': False,
        'new_model_GUI_calls_by_publication': 0, 'goal': 'active', 'time': time.time()})
    report = 'T058旧帧配对无结果推断边界-20261114.md'
    (dest / report).write_text('''# T058旧帧配对：门控同轨迹，未证明Mirage下降

两臂各23个自然EOS回复、22个实际动作、原生STOP、官方评分0，0基础设施/清理故障；原终局semantic_mirage:null保留。全体完整输入、历史、原图、回复、动作及动作后图逐项相同后，透明复用同一份21原图/23候选审查，不算第二位独立审查者。两臂每个实际请求的输入IDs/pixels/grid、first-forward、EOS和controller动作链已绑定；Flash23次YES同PNG转主、0NO/复拍，原始head概率和独立单图调用已核。两终局分别74文件、183/206事件链通过。

每臂22个候选字面阴性，最后23号保留未决。blue chair/chair/sofa几个查询的无结果回复在原图中明确可读；但最后把它们推广为“任何家具搜索都无结果／华盛顿没有家具和蓝椅子”，证据范围不足。尝试空关键词时原图30e5同时写着只接受至少4字符搜索，不能据此宣称成功穷尽本地区全部家具。合法输入也没有可核验的华盛顿蓝椅子反例或全量库存，因此不硬判该事实必假，也不把它作无Mirage；确定的推断范围问题单列，整轨语义标签仍null。原生STOP没有新增环境动作；不依据官方0倒推语义错误。

这组未观察到门控轨迹或任务得分改善；因关键断言仍未决，不能给出Mirage率或下降百分点。可读原生无结果页面本身正常，Flash放行不构成误拦，但YES也不为主模型的全局不存在结论背书。单审、非全盲、一个任务内配对，46个候选不是46个独立任务。成本明细、原始证据和版本边界见review-joined.json；增量原始输入审核保留各自时间，最终全队列退出全量终结审计仍待完成。
''', encoding='utf8')
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    (HERE / 'semantic-review-current.json').write_text(json.dumps({
        'publication': str(dest), 'report': str(dest / report),
        'review_sha256': sha(dest / 'review-joined.json'), 'seal_sha256': sha(dest / 'seal.json'),
        'previous_T017_stale_pair': str(HERE / 'T017-stale-paired-publication-1794658396227176000'),
        'previous_T017_clean_pair': str(HERE / 'T017-clean-paired-publication-1794656865993420400'),
        'Mirage_reduction': None, 'goal': 'active', 'time': time.time()}, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'publication': str(dest), 'per_arm_coverage': 23,
                      'trajectory_Mirage_labels': [None, None], 'Mirage_reduction': None, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
