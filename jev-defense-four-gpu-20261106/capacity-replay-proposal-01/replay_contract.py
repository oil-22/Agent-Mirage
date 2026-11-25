"""CPU-only exact finite repair proposal. No model, process launch or HTTP code."""
import hashlib
import json

COUNTS = [14, 22, 22, 6]
ALLOCATOR = 'expandable_segments:True'
EXTERNAL_WIRE = '170e61a801551d69aa4b6aeb6b2f5f3dbfa03e9e3352f00034f35b9df635ef7d'
CANONICAL_PAYLOAD = '688585e446fcf5994ec2c711061d033f72ddff80c78aa8057a9dd222d95a29a7'
CPU_PROOF = 'acb9b2fb465bb2763a696c83599d5b50f1aa61f5de78393b244084d5db02a6e9'
PRESERVATION = 'd78feb1d58d452c5218663bd41afe155e35825efddff0300ef0f5ff2c9c7e976'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def candidate_device_map():
    result = {'model.visual': 0, 'model.language_model.embed_tokens': 0,
        'model.language_model.norm': 3, 'model.language_model.rotary_emb': 3, 'lm_head': 3}
    for layer in range(64):
        result['model.language_model.layers.' + str(layer)] = 0 if layer < 14 else 1 if layer < 36 else 2 if layer < 58 else 3
    return result


def validate_plan(plan, original_failed_envelope):
    assert plan['stage'] == 'one_failed_judge_capacity_technical_replay'
    assert plan['budgets'] == {'judge': 1, 'actor': 0, 'helper': 0, 'GUI': 0, 'scorer': 0,
                              'format_retries': 0, 'output_tokens': 4096}
    assert plan['original_failed_external_wire_sha256'] == EXTERNAL_WIRE
    assert plan['original_failed_canonical_payload_sha256'] == CANONICAL_PAYLOAD
    assert hashlib.sha256(canonical(original_failed_envelope['payload'])).hexdigest() == CANONICAL_PAYLOAD
    assert original_failed_envelope['payload']['operation'] == 'judge'
    assert plan['CPU_input_binding_proof_sha256'] == CPU_PROOF
    assert plan['preservation_proof_sha256'] == PRESERVATION
    assert plan['input_tokens'] == 21470 and plan['original_images'] == 12
    assert plan['physical_gpus'] == [4, 5, 6, 7] and plan['helper_physical_gpu'] == 7
    assert plan['candidate_decoder_layer_counts'] == COUNTS
    assert plan['model_conditions'] == {'primary_dtype': 'bfloat16', 'primary_attention': 'sdpa',
        'seed': 42, 'original_images': True, 'complete_history': True,
        'native_processor_generation_grammar': True, 'helper_fast': False}
    assert plan['primary_process_environment'] == {'PYTORCH_CUDA_ALLOC_CONF': ALLOCATOR}
    assert plan['helper_mode'] == 'resident_only' and plan['automatic_retry'] is False
    assert plan['launch_ready'] is False and plan['GUI_release_after_capacity'] is False
    assert plan['old_GUI_budget_reset_or_resume_allowed'] is False
    return candidate_device_map()


def validate_future_launch_evidence(evidence):
    # A future launcher must bind real old postexit seals and actual process/lock
    # observations; these are deliberately absent from the preparation proposal.
    fields = ('root_reviewed_exact_new_sources', 'old_online_terminal_manifest_verified',
        'old_exact_workers_absent', 'original_73_request_seals_unchanged',
        'actual_holder_identity_and9locks_held', 'all_four_target_GPUs_empty_no_foreign',
        'new_once_only_claim_absent', 'new_attempt_and_token_independent',
        'candidate_native_meta_layout_bound', 'frozen_original_failed_payload_wire_bound')
    assert all(evidence.get(field) is True for field in fields)
    assert isinstance(evidence.get('old_online_terminal_manifest_sha256'), str)
    assert len(evidence['old_online_terminal_manifest_sha256']) == 64
    assert evidence.get('primary_calls') == 1 and evidence.get('helper_calls') == 0
    assert evidence.get('actor_GUI_scorer_calls') == 0
    return True
