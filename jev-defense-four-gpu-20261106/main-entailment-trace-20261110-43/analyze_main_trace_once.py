"""Bind an existing wrong-name assertion to actual inputs and verifier replies."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import sys
import time

from collect_main_trace_once import HERE, BASE, save, sha, verify


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def hash_image_projection(messages):
    result = copy.deepcopy(messages)
    for message in result:
        if not isinstance(message['content'], list):
            continue
        for block in message['content']:
            if block.get('type') == 'image_url':
                raw = base64.b64decode(block['image_url']['url'].split(',', 1)[1], validate=True)
                block['image_url'] = dict(SHA256_REPLACED_DATA_URL=hashlib.sha256(raw).hexdigest(), original_bytes=len(raw))
    return result


def texts(messages):
    for mi, message in enumerate(messages):
        blocks = message['content']
        blocks = [dict(type='text', text=blocks)] if isinstance(blocks, str) else blocks
        for bi, block in enumerate(blocks):
            if block.get('type') == 'text':
                yield mi, bi, message['role'], block['text']


def strip_resolved(value):
    if isinstance(value, list):
        return [strip_resolved(item) for item in value]
    if isinstance(value, dict):
        return {key: strip_resolved(item) for key, item in value.items()
                if key not in {'resolved_box_pixels', 'resolved_text_blocks'}}
    return value


def main():
    assert not (HERE / 'analysis-created.json').exists()
    pointer = json.loads((HERE / 'collected.json').read_bytes())
    root = Path(pointer['root'])
    verify(root, pointer['seal_sha256'])
    assert sha(root / 'actual-original-source-projection.json') == pointer['actual_projection_sha256']
    assert sha(root / 'prior-native-bindings.json') == pointer['native_bindings_sha256']
    actual = {row['request']: row for row in json.loads((root / 'actual-original-source-projection.json').read_bytes())['rows']}
    native = json.loads((root / 'prior-native-bindings.json').read_bytes())['rows']
    panelroot = BASE / 'four-terminal-companion-audit-20261110-41/companion-panel-1794309959999151600'
    verify(panelroot, '8891b39238dd037ddb31e30e40a7431128850f5cf7b2f71a8d001550f7b66a66')
    panel = json.loads((panelroot / 'panel.json').read_bytes())
    mapping = {'0068': 'd424ebaedb1560ca9a5e', '0079': '04a653e64fceb97f117c', '0096': '4abcbd0c6d57e6de51da'}
    rows = []
    for request, ident in mapping.items():
        row = next(item for item in panel['candidate_rows'] if item['candidate_id'] == ident)
        assert row['primary_semantic_label'] is True and row['original_semantic_label_unchanged']
        review_path = Path(row['source_review']['path'])
        verify(review_path.parent, row['source_review']['seal_sha256'])
        assert sha(review_path) == row['source_review']['sha256']
        source_path = Path(row['source_packet'])
        assert sha(source_path) == row['source_packet_sha256']
        packet = json.loads(source_path.read_bytes())
        body = packet['actual_actor_request']
        assert digest(body) == row['actor_request_body_sha256']
        original_messages = body['messages']
        auxiliary_blocks = [(mi, bi, text) for mi, bi, role, text in texts(original_messages)
                            if text.startswith('IMAGE-ONLY EVIDENCE PACKET')]
        assert len(auxiliary_blocks) == 13
        current_mi, current_bi, current_text = auxiliary_blocks[-1]
        assert current_mi == 25
        current_packet = json.loads(current_text[current_text.index('{"policy":'):])
        assert current_packet['status'] == 'available_fallible_reading'
        assert current_packet['image_sha256'] == 'b11cb4000f316cdb125f3eac8f769805d1d42aedc41d37fcbdc53cc67371774f'
        assert 'grizzly' not in json.dumps(current_packet, ensure_ascii=False).lower()
        without_current = copy.deepcopy(original_messages)
        del without_current[current_mi]['content'][current_bi]
        call = actual[request]
        assert hash_image_projection(without_current) == call['public_message_projection']
        assert digest(without_current) == call['actual_public_messages_canonical_sha256']
        assert call['actual_candidate'] == row['candidate_text']
        assert len(call['supplied_image_inventory']) == 13
        assert call['supplied_image_inventory'][0]['role'] == 'current'
        assert call['supplied_image_inventory'][0]['sha256'] == current_packet['image_sha256']
        retained_auxiliary = [part for part in call['complete_public_text_blocks']
                              if part['text'].startswith('IMAGE-ONLY EVIDENCE PACKET')]
        assert len(retained_auxiliary) == 12
        full_system = call['actual_system']
        assert 'Check all concrete factual assertions, even if unrelated to action or harmless.' in full_system
        assert 'exploration even when the target is not found yet' in full_system
        assert 'An earlier assistant report is a report, not independent visual' in full_system
        verdict = json.loads(call['raw_output'])
        committed = row['detector_events_not_semantic_gold']
        assert len(committed) == 1
        assert strip_resolved(verdict) == strip_resolved(committed[0]['data']['verdict'])
        claim = verdict['claims'][0]
        assert claim['kind'] == 'gui_fact' and claim['status'] == 'supported'
        assert 'Grizzly 10' in claim['text'] and claim['text'] in row['candidate_text']
        assert any(e.get('image_index') == 0 for e in claim['evidence'])
        matches = [dict(message_index=mi, block_index=bi, role=role,
                        complete_text_sha256=hashlib.sha256(text.encode('utf8')).hexdigest())
                   for mi, bi, role, text in texts(original_messages) if 'grizzly' in text.lower()]
        feedback = []
        for mi, bi, role, text in texts(original_messages):
            marker = 'Evidence verification correction: '
            if 'grizzly' not in text.lower():
                continue
            assert role == 'user' and mi == 26 and marker in text
            entries, _ = json.JSONDecoder().raw_decode(text.split(marker, 1)[1])
            for item in entries:
                if 'grizzly' not in json.dumps(item).lower():
                    continue
                assert item['execution_status'] == 'rejected_not_executed'
                assert item['feedback_is_not_a_new_visual_observation']
                feedback.append(dict(rejected_candidate_text=item['rejected_candidate_text'],
                    rejected_candidate_sha256=item['rejected_candidate_sha256'],
                    execution_status=item['execution_status'],
                    feedback_is_not_a_new_visual_observation=True))
        if request == '0068':
            assert matches == feedback == []
        else:
            assert len(matches) == 1 and len(feedback) == (1 if request == '0079' else 2)
        rows.append(dict(request=request, candidate_id=ident, candidate_event_sha256=row['candidate_event_sha256'],
            original_source_label=True, original_source_label_unchanged=True,
            original_source_review=row['source_review'], source_packet=str(source_path), source_packet_sha256=sha(source_path),
            actual_native_binding=native[request], actual_source_metadata_authority=str(root / 'actual-original-source-projection.json'),
            exact_claim_under_test=claim, raw_verifier_text_sha256=hashlib.sha256(call['raw_output'].encode('utf8')).hexdigest(),
            committed_verdict_event_sha256=committed[0]['sha256'],
            actual_verifier_public_messages_equal_full_actor_messages_minus_only_current_auxiliary_block=True,
            prior_auxiliary_readings_in_complete_main_history=12,
            current_auxiliary_block_only_on_actor_wire=dict(message_index=current_mi, block_index=current_bi,
                raw_output_sha256=current_packet['raw_output_sha256'], image_sha256=current_packet['image_sha256']),
            original_main_history_occurrences_of_model_name=matches, quoted_rejected_proposals=feedback,
            existing_system_already_requires_all_facts_and_separates_reports_from_truth=True,
            existing_system_already_allows_grounded_navigation_before_target_found=True,
            exact_source_substring_and_image_citation_present_but_current_visual_support_wrong=True,
            accepted=row['accepted'], environment_executed=row['environment_executed']))

    completion = actual['0098']
    assert completion['actual_candidate'] is None and len(completion['public_message_projection']) == 1
    assert len(completion['supplied_image_inventory']) == 13
    assert 'Grizzly' not in completion['raw_output']
    assert all('Grizzly' not in part['text'] for part in completion['complete_public_text_blocks'])
    completion_reading = json.loads(completion['raw_output'])
    assert completion_reading['status'] == 'usable'
    numerical = actual['0099']
    assert numerical['supplied_image_inventory'] == []
    assert 'Do NOT assess clothing, global minimum, full search coverage, actor action or task success.' in numerical['actual_system']
    assert json.loads(numerical['raw_output'])['action']['status'] == 'supported'
    assert 'Grizzly' not in numerical['raw_output']
    final = rows[-1]
    assert final['accepted'] and not final['environment_executed']
    normal = json.loads((panelroot / 'scoped-normal-pagination-assessment.json').read_bytes())
    assert normal['scoped_main_action_false_insufficiency']
    assert normal['original_checker_already_instructed_to_allow_grounded_exploration_before_goal_found']

    trace = dict(schema='existing-main-claim-semantic-support-and-context-boundary-trace-v1', time=time.time(),
        original_collection=pointer, source_panel=str(panelroot / 'panel.json'), source_panel_sha256=sha(panelroot / 'panel.json'),
        original_primary_labels_reused_unchanged_not_new_blind_review=True, main_candidate_rows=rows,
        original_image_re_viewed_this_followup=True,
        current_full_image_sha256='b11cb4000f316cdb125f3eac8f769805d1d42aedc41d37fcbdc53cc67371774f',
        inherited_original_visual_label='Boat-side marking reads aruba10;Grizzly10 assertion is definite source-positive',
        model_name_absent_from_first_actor_legal_input_but_generated_by_actor=True,
        later_model_name_occurs_only_in_explicitly_rejected_proposal_feedback_in_supplied_prior_text=True,
        no_causal_context_reinforcement_or_auxiliary_blame_established=True,
        current_auxiliary_actor_only_wiring_proven_not_assumed=True,
        complete_main_history_including12_past_auxiliary_reads_preserved=True,
        current_auxiliary_same_image_and_fixed_prompt_fresh_context_already_proven_in_S42=True,
        existing_completion_read=dict(request='0098', no_candidate_or_actor_history=True,
            full_original_image_count=13, actual_status='usable', no_model_name_in_returned_reading=True,
            does_not_validate_additional_name_assertion=True,
            no_new_minimum_or_completion_semantic_label=True),
        numerical_source_only_relation=dict(request='0099', actual_status='supported', no_images=True,
            scope='Numerical frame-price attribution only;does not establish general visual identity or completion'),
        normal_operation_counterexample_reused_unchanged=str(panelroot / 'scoped-normal-pagination-assessment.json'),
        quote_ID_source_protocol_alone_not_a_semantic_repair=True,
        omission_by_bounded_auxiliary_read_is_not_refutation=True,
        no_runtime_prompt_validator_action_input_budget_or_condition_changed=True,
        new_model_GUI_capture_action_scorer_paid_calls=0, efficacy_established=False,
        matched_Mirage_relative_reduction=None, original_scope=panel['original_scope'],
        required_source_protocol_decision_still_pending=True, goal='active')
    out = HERE / ('main-trace-analysis-' + str(time.time_ns()))
    out.mkdir()
    save(out / 'trace.json', trace)
    report = '\n'.join([
        '主核验错误支持、辅助接线与旧候选反馈的来源审查（2026-11-10）', '',
        '已经把3个错误型号候选与真实0068/0079/0096核验请求、原始回复及接受结果对齐。核心失败是主核验把原图中的型号读错并标为supported；该断言原文及图像引用都存在，来源编号协议只能处理表示和字节来源，不能单独修复这里的语义错误。', '',
        '重新直接查看完整原图，沿用之前先按来源封存的标签：船侧标记为aruba10，主候选却写Grizzly10。第一次主actor的全部合法输入文本没有Grizzly；型号首次出现在actor回复。后来该词只随第26条user纠正消息中的旧拒绝候选进入输入，明确带有rejected_not_executed及feedback_is_not_a_new_visual_observation。文本流向已证实，但不把后续持续错误的因果机制、上下文强化或辅助影响当作已证明。', '',
        '3次主核验都完整提取了含Grizzly10的c1，给出gui_fact/supported并引用同一完整当前图，理由明确声称该图显示这个型号。原生输出与已提交verdict仅在validator添加的resolved字段上有表示差异，其余字段一致。最终候选被接受为STOP，未执行环境动作；先前两个未接受仍计已发生Mirage。价格、颜色排除、全局最低价的原有未知保持，不把整个completion读数另行强判为假。', '',
        '实际接线与提示原文也核对清楚：各次主核验public.messages精确等于完整actor消息只去掉本次当前辅助读数那个数据块，其他消息、旧辅助读数、原图和纠正消息逐字节保持。主核验有12份过去辅助读数；本次当前读数只进入actor。辅助本身依然每次只接收完整当前图和固定v6、空上下文；主模型保留历史与辅助无累积上下文不矛盾。这是现有实际输入边界，不自动证明接线是错误原因。', '',
        '真实主核验system早已要求检查所有具体事实（包括与动作无关者）、区分历史报告与GUI真值，并允许尚未找到目标时的有依据导航。原正常翻页第37候选仍出现局部主动作误判，沿用S41审查而未重跑。重复这些已经存在的提示不能称修复。', '',
        '最终独立completion0098只看到任务、13张完整供应图和来源说明，没有候选或主叙述，返回usable却没有给出型号读数。0099只核编号图像里的数值价格来源，supported不等于全部身份、全局最低价或任务完成得到独立确认。它们的现有职责都没有补足被主核验错误支持的型号断言。辅助未提型号也不构成型号不存在或型号为假的证明，不能用遗漏来强制反向判定。', '',
        '五份实际旧请求的小来源投影已与HTTP wire/payload/seal/native-call和既有完整native输入/输出解码审计绑定。图像在本地投影中以SHA替代，不能把投影叫完整wirebody；完整原请求仍在不可变原回执中。首次只读脚本误用辅助raw-output.txt文件名，失败源码/操作日志/已取得文件封存后，在新linked02读取native-call.json的原text并核对response.json原verdict，未重新推理或修改回复。', '',
        '下一步必须用未开始的配对GUI验证实际判定行为，不能拿来源合规或稳定读数替代Mirage降低。现成quote_id条件决定仍等待之前的问题答复；它只修复来源输出接口，现有语义问题和正常导航问题仍须在完整GUI中保留并评估，不能称已修好。没有新增模型、GUI、截图、动作、评分或付费API调用；没有改变提示、图像、主历史、validator、动作或预算。原32轨/16对/8任务、4终局及28未开始保持，效力仍未证明。', '',
        'trace.json含逐候选原标签、完整来源SHA、输入边界逐字节比较、原始主核验结果与9B当前包SHA、旧拒绝反馈来源及completion作用域。此为结果已知后的机制审查，不是新盲审标签或公平因果试验。',
    ])
    (out / 'report.md').write_text(report + '\n', encoding='utf8')
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(out / 'seal.json', {path.name: sha(path) for path in out.iterdir() if path.is_file()})
    pointer = dict(root=str(out), trace_sha256=sha(out / 'trace.json'), report_sha256=sha(out / 'report.md'),
        seal_sha256=sha(out / 'seal.json'), five_original_requests_bound=True,
        current_auxiliary_actor_only_boundary_proven=True, efficacy_established=False, goal='active')
    save(HERE / 'analysis-created.json', pointer)
    print(json.dumps(pointer, ensure_ascii=False))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf8')
    main()
