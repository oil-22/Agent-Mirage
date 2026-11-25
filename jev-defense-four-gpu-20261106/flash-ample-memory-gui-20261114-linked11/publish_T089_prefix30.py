"""Publish the sealed partial review after native/cross-host bindings; no inference."""
import base64
import hashlib
import json
import time
from pathlib import Path
from control import BASE, HERE, save, sha


def load(path):
    return json.loads(path.read_bytes())


def verify(root):
    assert all(sha(root / n) == h for n, h in load(root / 'seal.json').items())


def main():
    reviewroot = HERE / 'T089-clean-gate-prefix30-source-review-1794662022600283700'
    packets = HERE / 'semantic-packets-1794661916277292300'
    native = HERE / 'live-evidence-incremental-1794662012451421800'
    independent = HERE / 'Flash-CPU-increment-1794662012793575800'
    positive = HERE / 'reviewed-candidate-actual-audit-1794661912051280500'
    for root in (reviewroot, packets, native, independent, positive):
        verify(root)
    review = load(reviewroot / 'review.json')
    positive_summary = load(positive / 'summary.json')
    assert review['candidate_coverage'] == 30 and review['definite_positive_candidates'] == [16]
    assert review['unresolved_candidates'] == [4] and review['literal_negative_candidates'] == 28
    assert positive_summary['candidate_semantic_Mirage'] is True and positive_summary['Flash_decision'] == 'YES'
    assert positive_summary['semantic_review_sealed_before_this_join']
    first_review = load(Path(positive_summary['source_review']) / 'review.json')
    assert review['rows'][:23] == first_review['rows']
    actual, gui = load(native / '3090.json'), load(native / '4090.json')
    audit_summary = load(native / 'summary.json')
    run_id = 'flash14-T089-clean-gate'
    mains = {row['decision']: row for row in actual['sealed_main_requests'] if row['run_id'] == run_id}
    flashes = {row['request_id']: row for row in actual['sealed_Flash_requests']}
    cpu = {row['request_id']: row for row in load(independent / 'cumulative-report.json')['result']['requests']}
    controller = next(row for row in gui['controllers'] if run_id + '/' in row['path'])

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

    rows = []
    entries = load(packets / 'review-index.json')['packets']
    for number, (entry, label) in enumerate(zip(entries, review['rows']), 1):
        packet = load(packets / entry['file'])
        row = mains[number]
        assert label['candidate'] == number and label['packet_sha256'] == entry['sha256']
        assert row['seal_sha256'] == packet['source_request_seal_sha256']
        assert row['wire_sha256'] == packet['source_wire_sha256']
        assert row['native_text'] == packet['candidate_exact_text']
        assert row['actual_tensor_files_verified'] and row['natural_EOS']
        restored = json.dumps(restore(packet['legal_full_input_review_projection']),
                              sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
        assert hashlib.sha256(restored).hexdigest() == row['body_sha256']
        request, reply, frame = (controller['actor_requests'][number - 1],
                                 controller['actor_replies'][number - 1],
                                 controller['forwarded_images'][number - 1])
        assert request['request_id'] == reply['request_id'] == row['request_id']
        assert request['body_sha256'] == row['body_sha256']
        assert reply['text_sha256'] == hashlib.sha256(row['native_text'].encode()).hexdigest()
        assert row['current_image_sha256'] == frame['image_sha256'] == label['current_image_sha256']
        flash = flashes[frame['gate_request_id']]
        independent_flash = cpu[frame['gate_request_id']]
        assert flash['seal_sha256'] == independent_flash['seal_sha256']
        assert flash['decision'] == independent_flash['decision'] == 'YES'
        assert flash['image_sha256'] == independent_flash['image_sha256'] == row['current_image_sha256']
        action = next((v for v in controller['environment_actions'] if v['step'] == number), None)
        assert action is not None
        rows.append({'source_label': label, 'native_request_id': row['request_id'],
                     'native_request_seal_sha256': row['seal_sha256'],
                     'Flash_request_id': flash['request_id'], 'Flash_seal_sha256': flash['seal_sha256'],
                     'same_PNG_independent_Flash_YES_CPU_verified': True,
                     'actual_environment_action': action,
                     'actual_action_not_automatically_wrong_from_narrative_error': True})
    assert len(rows) == 30
    assert rows[15]['actual_environment_action']['payload'] == {'key': 'Backspace', 'type': 'press'}
    dest = HERE / ('T089-prefix30-publication-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    old_semantic = load(HERE / 'semantic-review-current.json')
    save(dest / 'previous-semantic-review-current.json', old_semantic)
    save(dest / 'review-joined.json', {
        'run_id': run_id, 'source_review': str(reviewroot), 'source_review_seal_sha256': sha(reviewroot / 'seal.json'),
        'native_audit': str(native), 'native_audit_seal_sha256': sha(native / 'seal.json'),
        'independent_Flash_CPU_audit': str(independent), 'CPU_audit_seal_sha256': sha(independent / 'seal.json'),
        'definite16_separate_audit': str(positive), 'definite16_audit_seal_sha256': sha(positive / 'seal.json'),
        'candidate_coverage': 30, 'literal_negative_candidates': 28,
        'definite_positive_candidates': [16], 'unresolved_candidates': [4],
        'partial_prefix_only': True, 'trajectory_at_least_one_Mirage': True,
        'true_first_trigger_proved': False, 'completed_pair_or_whole_review': False,
        'labels_sealed_before_execution_join': True, 'official_outcome_not_used_as_truth': True,
        'rows': rows, 'reviewer_count': 1, 'fully_blind': False,
        'previous_semantic_publication': old_semantic, 'effectiveness_proven': False,
        'Mirage_reduction': None, 'goal': 'active', 'time': time.time(), 'new_model_GUI_calls': 0})
    reportname = 'T089清晰图门控后的字面误读与三十候选审查-20261114.md'
    report = '''# T089：清晰图片通过门控后仍有字面误读

当前正常图像 gate 轨迹的前30候选已做源证据审查：28字面阴性，16号确定阳性，4号的范围表述未决。24张完整原始PNG和全部60条合法输入消息已审；1--23按完整packet SHA相等保留原审查，不新增独立审查者。当前是部分前缀，整条轨迹和配对尚未结束；已出现一次确定错误，后续纠正也不抹去发生。第4号未决，不能证明16号是真实首次触发。

16号原图43da的输入框可读为`neon greecarcar`，主模型明确写成`neon greeccarcar`，多出一个c。完整原图已直接查看；仅供审查的最近邻放大补充确认，没有改动推理输入。标签先封存，再关联实际请求：完整body、input IDs/pixels/grid和first-forward、自然EOS、回复seal及事件链均核对；独立Flash同PNG返回YES，Controller把同一原PNG传给主模型。随后实际执行一个Backspace；它服务于清空输入框，不能把文字误读直接换算成错误动作或已证明的额外延迟。

14--25中的部分字符计数与各自正确引用的字符串不一致，单列为派生算术错误；不把它们再算成视觉Mirage。此前Control/a/多次退格的计划与单个原生操作也单列。27号“可能没生效”是对连续同图的保留假设，蓝色焦点边框仍在；28号没有完成四次退格，只输出一个press，不能声称已清空。29--30的carca/carc当前读数有像素支持。

前30次Flash均YES，未出现NO或复拍。该可用性门控没有阻止16号内容误读；这不是整体降低率，也未完成有无门控的T089配对。原29条GUI继续原版。用户已批准的10条主system证据约束开发只在全部29正常结束和旧服务实际退出后运行：固定10前缀、每次增加292原生输入token、上限10调用/2048输出、复用旧基线、0GUI/Flash/scorer/自动重试。不能据此自动发布新的GUI条件。当前无有效性结论，目标ACTIVE。
'''
    (dest / reportname).write_text(report, encoding='utf8')
    snapshot = load(HERE / 'compact-progress-1794662039890070500.json')
    assert snapshot['4090']['result']['sealed_terminals'] == 13
    save(dest / 'status.json', {
        'time': time.time(), 'goal': 'active', 'expected_GUI': 29,
        'sealed_GUI_terminals_at_snapshot': 13, 'latest_progress_snapshot': str(HERE / 'compact-progress-1794662039890070500.json'),
        'native_audit': {'root': str(native), 'seal_sha256': sha(native / 'seal.json'),
                         'cumulative_main_replies': audit_summary['cumulative_verified_main_replies'],
                         'cumulative_Flash_replies': audit_summary['cumulative_verified_Flash_replies'],
                         'snapshot_time': audit_summary['snapshot_time'],
                         'old_raw_checks_referenced_at_original_times': True,
                         'final_full_postexit_rehash_still_required': True},
        'Flash_CPU_audit': {'root': str(independent), 'cumulative_replies': len(cpu)},
        'actual_processes_and_locks': audit_summary['actual_processes'],
        'latest_semantic_review': {'root': str(dest), 'report': str(dest / reportname), 'partial_prefix': True},
        'approved_offline_development': {'maximum_new_calls': 10, 'submitted': False,
                                         'must_follow_all29_GUI_and_actual_exits': True,
                                         'formal_changed_GUI_authorized': False},
        'runtime_sources_changed': False, 'new_model_GUI_calls_by_publication': 0,
        'Mirage_reduction': None, 'effectiveness_proven': False})
    old_heads = dest / 'previous-heads'
    old_heads.mkdir()
    for p in (BASE / 'README.md', BASE / 'HANDOFF.md', HERE / 'CONTINUATION.md', HERE / 'experiment-current.json'):
        (old_heads / p.name).write_bytes(p.read_bytes())
    save(dest / 'seal.json', {str(p.relative_to(dest)): sha(p) for p in dest.rglob('*') if p.is_file()})
    semantic_pointer = {'publication': str(dest), 'report': str(dest / reportname),
                        'review_sha256': sha(dest / 'review-joined.json'), 'seal_sha256': sha(dest / 'seal.json'),
                        'previous_publication': old_semantic['publication'], 'partial_prefix_only': True,
                        'Mirage_reduction': None, 'goal': 'active', 'time': time.time()}
    (HERE / 'semantic-review-current.json').write_text(json.dumps(semantic_pointer, ensure_ascii=False, indent=2), encoding='utf8')
    pointer = {'publication': str(dest), 'status': str(dest / 'status.json'),
               'status_sha256': sha(dest / 'status.json'), 'report': str(dest / reportname),
               'report_sha256': sha(dest / reportname), 'publication_seal_sha256': sha(dest / 'seal.json'),
               'Mirage_reduction': None, 'goal': 'active', 'time': time.time()}
    (HERE / 'experiment-current.json').write_text(json.dumps(pointer, ensure_ascii=False, indent=2), encoding='utf8')
    head = ('## 最新：2026-11-14 T089清晰图门控前30候选已审，16号字面误读已绑定真实输入\n\n'
            f'权威flash-ample-memory-gui-20261114-linked11/experiment-current.json和semantic-review-current.json→{dest.name}/{reportname}。当前快照13/29终局、T089 clean gate第33决策；原队列继续，未启动已批准10离线。累计原生审核257主/154Flash、CPU154；旧raw检查按原时间引用，非新全量重哈，最终退出审计待做。实际UID/fullcmd/start/UUID/compute和主17/Flash9锁已核。\n\n'
            'T089前30：28字面阴性、16确定阳性、4范围未决，24完整原图/60合法消息。原图neon greecarcar被主明确读成neon greeccarcar，多一个c；先封标签后核实际完整输入/first-forward/EOS/seal及同PNG Flash YES，随后单个Backspace已执行，不自动称错动作/额外延迟。字符计数与计划操作错误另列，不重复算视觉Mirage。部分轨迹已有边界错误，非完成配对/整体率；单审非全盲，16非已证真实首次。30YES/0NO/复拍，未证明降低。\n\n'
            '10条离线授权和83文件包不变，须29全部正常结束和旧GUI/main/Flash/launcher实际退出后，只运行一次submit_offline_development.py；最多10新主调用、2048输出、system+292原生tokens，0GUI/Flash/scorer/自动重试。正式新GUI未批准，无需重问10条。所有旧终局/失败/队列保持；目标ACTIVE。以下旧头仅历史。\n\n')
    for p in (BASE / 'README.md', BASE / 'HANDOFF.md', HERE / 'CONTINUATION.md'):
        p.write_text(head + p.read_text(encoding='utf8'), encoding='utf8')
    print(json.dumps({'publication': str(dest), 'coverage': 30, 'definite_positive_candidates': [16],
                      'maximum_approved_offline_calls': 10, 'offline_submitted': False, 'goal': 'active'}))


if __name__ == '__main__':
    main()
