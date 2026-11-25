"""Audit already delivered auxiliary reads; never execute a model or GUI."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import struct
import sys
import time


HERE = Path(__file__).resolve().parent
BASE = HERE.parent
PROMPT_SHA = '2a6a2d210bac4cd552e477df15dab86aacd4ff479cd85a3e070f01dcc97e558c'
REVISION = 'c202236235762e1c871ad0ccb60c8ee5ba337b9a'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def verify_seal(folder, expected):
    assert sha(folder / 'seal.json') == expected
    for name, expected_sha in json.loads((folder / 'seal.json').read_bytes()).items():
        path = folder / name
        assert path.resolve().is_relative_to(folder.resolve())
        assert sha(path) == expected_sha, str(path)


def tensor_signature(value):
    return {key: {field: entry[field] for field in ['shape', 'dtype', 'bytes', 'sha256']}
            for key, entry in value.items()}


def main():
    assert not (HERE / 'analysis-created.json').exists(), 'Immutable completed audit must not be rerun'
    pointer = json.loads((HERE / 'collected.json').read_bytes())
    root = Path(pointer['root'])
    verify_seal(root, pointer['seal_sha256'])
    assert sha(root / 'sealed-source-and-native-index.json') == pointer['source_index_sha256']
    assert sha(root / 'actual-original-metadata.json') == pointer['actual_metadata_sha256']
    source_data = json.loads((root / 'sealed-source-and-native-index.json').read_bytes())
    actual_data = json.loads((root / 'actual-original-metadata.json').read_bytes())
    sources = {row['auxiliary_request']: row for row in source_data['rows']}
    actual = {row['request']: row for row in actual_data['rows']}
    assert len(sources) == len(actual) == len(source_data['rows']) == len(actual_data['rows']) == 31
    assert set(sources) == set(actual)
    assert source_data['original_primary_labels_unchanged']
    assert source_data['full_tensor_hash_and_native_decode_proofs_reused_not_rerun']
    assert actual_data['remote_read_only'] and actual_data['new_model_GUI_capture_action_scorer_paid_calls'] == 0

    groups, rows, call_ids = defaultdict(list), [], set()
    effective_signatures, guard_sources = set(), set()
    for request, entry in actual.items():
        source = sources[request]
        assert source['original_label_unchanged']
        assert entry['request_seal_sha256'] == source['expected_auxiliary_seal_sha256']
        assert entry['model'] == 'Qwen/Qwen3.5-9B' and entry['revision'] == REVISION
        assert entry['prompt_sha256'] == PROMPT_SHA
        assert entry['raw_output_sha256'] == hashlib.sha256(entry['raw_output'].encode('utf8')).hexdigest()
        assert entry['raw_output_sha256'] == source['observer_packet']['raw_output_sha256']
        assert entry['image_sha256'] == source['observer_packet']['image_sha256']
        meta = entry['metadata']
        before = tensor_signature(meta['prepared.json'])
        forward = tensor_signature(meta['first-forward.json'])
        assert before == forward
        assert {'input_ids', 'pixel_values', 'image_grid_thw', 'attention_mask'} <= set(forward)
        assert forward['input_ids']['sha256'] == entry['native_input_IDs_SHA_from_actual_returned_sequence']
        generation = meta['effective-generation.json']
        assert generation['do_sample'] is False and generation['max_new_tokens'] == 2048
        assert generation['num_beams'] == 1 and generation['eos_token_id'] == [248044, 248046]
        generated = meta['actual-generation.json']
        ids = generated['output_ids']
        assert generated['natural_EOS'] and ids[-1] in generation['eos_token_id']
        assert len(ids) == generated['output_tokens'] < generation['max_new_tokens']
        assert hashlib.sha256(struct.pack('<' + 'q' * len(ids), *ids)).hexdigest() == entry['native_output_IDs_SHA']
        boundary = meta['stateless-input-boundary.json']
        discarded = meta['stateless-context-discarded.json']
        assert boundary['call_id'] == discarded['call_id']
        assert boundary['call_id'] not in call_ids
        call_ids.add(boundary['call_id'])
        assert boundary['message_count'] == 1 and boundary['role'] == 'user'
        assert boundary['content_types'] == ['image', 'text']
        assert boundary['task_history_candidate_previous_auxiliary_content_supplied'] is False
        assert boundary['complete_image_sha256'] == entry['image_sha256']
        assert boundary['fixed_prompt_sha256'] == PROMPT_SHA
        assert discarded['actual_first_forward_cache_length'] == 0
        assert discarded['all_observed_cache_objects_released']
        assert discarded['observed_cache_objects_still_alive'] == 0
        assert not discarded['main_model_or_main_context_referenced']
        assert discarded['error_type'] is None
        guard = meta['unicode-length-guard.json']
        assert guard['final_decoded_length_state_complete_before_EOS']
        assert guard['native_selected_tokens_not_rewritten'] and guard['strict_final_validator_unchanged']
        utf8 = meta['raw-UTF8-validation.json']
        assert utf8['native_output_unchanged'] and utf8['strict_native_UTF8_roundtrip']
        proof = source['actual_native_proof_reused']
        assert proof['single_complete_image_and_fixed_prompt_bound']
        assert proof['all_prepared_first_forward_tensors_and_actual_native_IDs_bound']
        assert proof['independent_native_tokenizer_decode_matches_original_raw_text']
        assert proof['independent_selected_native_ID_bytes_match_saved_token_bytes']
        insertion = source['actual_Controller_actor_insertion_reused']
        assert insertion['auxiliary_actual_HTTP_linked']
        assert insertion['all_original_messages_images_trailing_corrections_and_body_parameters_retained']

        # Full recorded native tensor bytes/signatures, not image identity alone.
        signature = dict(model=entry['model'], revision=entry['revision'],
            image_sha256=entry['image_sha256'], complete_RGB_sha256=boundary['complete_RGB_sha256'],
            prompt_sha256=PROMPT_SHA, first_forward_tensors=forward,
            effective_generation=generation, unicode_length_guard_source_sha256=guard['source_sha256'])
        signature_sha = digest(signature)
        effective_signatures.add(digest(generation))
        guard_sources.add(guard['source_sha256'])
        content = json.loads(entry['raw_output'])
        assert content['schema_version'] == 'image-evidence-v2-compact'
        assert content['coordinate_space'] == 'normalized_1000'
        assert len(content['frame']['summary']) <= 180
        assert len(content['text_spans']) <= 6 and len(content['elements']) <= 6
        assert len(content['uncertain_regions']) <= 2
        row = dict(request=request, independent_call_id=boundary['call_id'],
            actor_request=source['actor_request'], run_id=source['run_id'],
            candidate_id=source['candidate_id'], candidate_event_sha256=source['candidate_event_sha256'],
            original_primary_semantic_label=source['original_primary_semantic_label'],
            original_label_unchanged=True, accepted=source['accepted'], environment_executed=source['environment_executed'],
            source_packet=source['source_packet'], source_packet_sha256=source['source_packet_sha256'],
            image_sha256=entry['image_sha256'], complete_input_signature_sha256=signature_sha,
            input_tokens=generated['input_tokens'], output_tokens=generated['output_tokens'],
            raw_output_sha256=entry['raw_output_sha256'], native_output_IDs_sha256=entry['native_output_IDs_SHA'],
            frame_kind=content['frame']['kind'], summary_characters=len(content['frame']['summary']),
            text_spans=len(content['text_spans']), elements=len(content['elements']),
            uncertain_regions=len(content['uncertain_regions']), natural_EOS=True,
            actual_first_cache_length=0, all_observed_cache_objects_released=True,
            one_complete_image_and_fixed_prompt_no_task_or_history=True,
            complete_input_signature=signature,
            original_request_metadata_file_SHA=entry['metadata_original_file_SHA_bound'])
        groups[signature_sha].append(row)
        rows.append(row)

    assert len(call_ids) == 31 and len(groups) == 26
    assert len(effective_signatures) == len(guard_sources) == 1
    repeats = []
    for signature_sha, group in groups.items():
        if len(group) == 1:
            continue
        assert len({row['image_sha256'] for row in group}) == 1
        text_sha = {row['raw_output_sha256'] for row in group}
        id_sha = {row['native_output_IDs_sha256'] for row in group}
        assert len(text_sha) == len(id_sha) == 1
        repeats.append(dict(complete_input_signature_sha256=signature_sha,
            image_sha256=group[0]['image_sha256'], independent_actual_calls=len(group),
            request_ids=[row['request'] for row in group],
            candidate_ids=[row['candidate_id'] for row in group],
            unique_raw_output_SHA=len(text_sha), unique_native_output_ID_SHA=len(id_sha),
            identical_recorded_input_and_output=True, raw_output_sha256=next(iter(text_sha)),
            native_output_IDs_sha256=next(iter(id_sha)),
            original_primary_labels=[row['original_primary_semantic_label'] for row in group],
            accepted=[row['accepted'] for row in group],
            environment_executed=[row['environment_executed'] for row in group]))
    assert sorted(group['independent_actual_calls'] for group in repeats) == [2, 2, 2, 3]
    detail = next(group for group in repeats if group['independent_actual_calls'] == 3)
    assert detail['candidate_ids'] == ['d424ebaedb1560ca9a5e', '04a653e64fceb97f117c', '4abcbd0c6d57e6de51da']
    assert detail['original_primary_labels'] == [True, True, True]
    assert detail['accepted'] == [False, False, True] and detail['environment_executed'] == [False] * 3
    first = actual[detail['request_ids'][0]]
    raw_detail = json.loads(first['raw_output'])
    assert 'Grizzly' not in first['raw_output'] and 'aruba' not in first['raw_output'].lower()
    for request in detail['request_ids']:
        assert 'Grizzly 10' in sources[request]['candidate_text']

    counts = dict(actual_auxiliary_calls=31, independent_call_ids=31, unique_complete_images=26,
        unique_recorded_complete_native_inputs=26, repeated_input_groups=4,
        calls_in_repeated_groups=9, unique_groups_with_single_call=22,
        repeated_groups_with_identical_output_text_and_native_IDs=4,
        natural_EOS=31, output_cap_failures=0,
        input_cache_empty_and_observed_cache_released=31,
        Controller_insertions_bound=31,
        summaries_at_180_character_limit=sum(row['summary_characters'] == 180 for row in rows),
        output_token_minimum=min(row['output_tokens'] for row in rows),
        output_token_maximum=max(row['output_tokens'] for row in rows),
        sum_original_auxiliary_output_tokens=sum(row['output_tokens'] for row in rows))
    assert counts['summaries_at_180_character_limit'] == 22
    assert counts['sum_original_auxiliary_output_tokens'] == 17918
    detail_followup = dict(original_labels_reused_no_new_blind_semantic_label=True,
        three_same_complete_input_reads=detail,
        exact_auxiliary_reading=raw_detail,
        auxiliary_never_stated_model_name_Grizzly_or_aruba=True,
        all_three_main_candidates_stated_Grizzly_10_and_retained_original_positive_labels=True,
        final_candidate_was_accepted_STOP_without_environment_action=True,
        causal_attribution_of_model_name_error_to_auxiliary=None,
        repeated_auxiliary_invocations_are_not_new_independent_experimental_replicates=True,
        no_global_minimum_or_full_image_semantic_accuracy_inferred=True)
    audit = dict(schema='delivered-auxiliary-native-input-and-output-stability-v1', time=time.time(),
        collection_authority=pointer, counts=counts, repeated_complete_input_groups=repeats,
        per_original_call=rows, detail_followup='same-image-detail-main-claims.json',
        all_original_primary_Mirage_labels_reused_unchanged=True,
        no_new_Mirage_labels_or_recognition_accuracy_claim=True,
        observed_repeat_stability_not_universal_determinism=True,
        field_length_saturation_is_not_proven_truncation_or_semantic_error=True,
        full_original_tensor_binary_and_native_decode_proofs_reused_not_rehashed_or_regenerated=True,
        freshly_bound_small_original_metadata_and_actual_returned_ID_prefixes=True,
        no_current_GPU_tensor_value_or_unmasked_probability_verification=True,
        cache_release_not_physical_GPU_memory_zeroization=True,
        all_auxiliary_reads_from_two_arms_of_same_selected_T000_task=True,
        efficacy_established=False, matched_Mirage_relative_reduction=None,
        source_reference_protocol_human_decision_still_pending=True,
        no_runtime_protocol_conditions_or_budgets_changed=True,
        no_new_model_GUI_capture_action_scorer_paid_calls=True, goal='active')

    out = HERE / ('stability-analysis-' + str(time.time_ns()))
    out.mkdir()
    save(out / 'audit.json', audit)
    save(out / 'same-image-detail-main-claims.json', detail_followup)
    text = '\n'.join([
        '辅助证据的完整输入、输出稳定性与主模型错误审查（2026-11-10）', '',
        '本次完成31次既有辅助调用的实际输入和输出关联。4组重复的完整原生输入共9次独立调用，原始文本及原生输出IDs分别完全一致。现有错误不能自动归因辅助输出随机漂移，也没有证据支持通过重复调用同一图片来解决。此为既有轨迹的稳定性诊断，尚未证明Mirage触发率降低。', '',
        '31次调用有31个独立call_id；26个不同完整供应图也对应26组完整实际原生输入。分组使用模型固定revision、完整图SHA与RGB SHA、固定v6提示、全部first-forward tensor的shape/dtype/bytes/SHA、实际effective generation和Unicode长度约束源码SHA，不只比较图片名或截图hash。4个重复组大小为3、2、2、2。全部31次自然EOS，输出534–625tokens，原输出总计17918tokens；没有本次新模型调用、重试或输出上限失败。', '',
        '每次实际请求仅单个user消息内的完整图与固定提示，不包含任务、主历史、候选或前次辅助内容。prepared与first-forward输入及实际返回sequence前缀IDs逐一绑定；每次首forward cache长度0、全部观察到的cache对象已释放。原完整tensor二进制和原生tokenizer解码证明沿用已封存审计，本次只重核小metadata、原request seal及实际返回IDs，没有重复权重加载/推理或二进制全hash。释放cache不等于物理显存清零；模型权重没有因此卸载。31份辅助结果均按真实HTTP请求和Controller插入记录关联到对应actor。', '',
        '最有用的限定观察：同一详情图的3次辅助回复都描述蓝色皮划艇、185美元、姓名及可见控件，没有写商品型号。随后3个主候选均写Grizzly 10，沿用原先按完整原图和合法历史封存的确定错误标签；前两个未接受、最后一个作为STOP接受，没有对应环境动作。重复读数一致仍未阻止主模型持续作出该身份断言。不能将这个型号错误归因辅助模型提供了错误型号，也不能从单图未提及型号推断主模型必然应否定型号；这不是辅助因果效应或完整识别准确率实验。', '',
        '31份读数中22份摘要恰好达到180字符上限。所有输出均完成JSON并自然EOS；这是字段长度饱和，不能自动当模型截断、语义错误或Mirage。没有暗中扩长度/调用预算、编辑模型输出或修改图像和提示。所有样本来自同一选定T000任务的两条有辅助轨，重复组不是独立任务重复试验；不能推出普遍确定性、画面识别准确率或总体防御效力。', '',
        '下一步的实质问题仍是断言来源与证据蕴含如何进入判定，以及已有正常导航的主核验误判；给同图增加辅助重试没有当前证据依据。新的quote_id协议只准备、未部署，仍等待此前已发出的独立条件决定。原32轨/16配对/8任务、4条不可重跑终局和28未开始保留，原生STOP原句映射的既有许可不重复询问。', '',
        '单个辅助实际为Qwen3.5-9B基座，未加载原生JEV决策适配器。完整供应单图+固定v6、逐次空上下文、主完整合法历史、原图、BF16/SDPA、原生动作/评分和严格来源校验及每轨原预算均保留。稳定输出与字段合规都不是防御成功；相对Mirage降低仍null，目标ACTIVE。', '',
        '证据：audit.json保留31逐请求输入签名和原metadata SHA、4组原生输入/输出比较；same-image-detail-main-claims.json保留3次相同详情读数与原主标签/接受/执行关系；collected.json指向此次只读采集的完整原始小metadata及既有审计来源。',
    ])
    (out / 'report.md').write_text(text + '\n', encoding='utf8')
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    result = dict(root=str(out), audit_sha256=sha(out / 'audit.json'), report_sha256=sha(out / 'report.md'),
        detail_sha256=sha(out / 'same-image-detail-main-claims.json'), seal_sha256=sha(out / 'seal.json'),
        counts=counts, efficacy_established=False, relative_Mirage_reduction=None, goal='active')
    save(HERE / 'analysis-created.json', result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf8')
    main()
