"""Adversarial accounting checks using one already completed frozen reply.

No images are sent to a model and no control is regenerated. Mutated in-memory
records test rejection of corrupted provenance, not visual semantic accuracy.
"""
import copy
from auxiliary_receipt_checks import check_auxiliary_receipts


def run_checks(arguments):
    baseline = check_auxiliary_receipts(**arguments)
    results = [{"case": "frozen_native_reply_compatibility_without_new_inference", "passed": True}]

    def reject(name, mutate):
        changed = copy.deepcopy(arguments)
        mutate(changed)
        try:
            check_auxiliary_receipts(**changed)
        except (ValueError, KeyError):
            results.append({"case": name, "passed": True})
        else:
            raise AssertionError("Invalid auxiliary provenance accepted: " + name)

    reject("extra_task_input_field", lambda a: a["request"].update(task="hidden target"))
    reject("task_appended_to_prompt", lambda a: a["request"].update(prompt=a["fixed_prompt"] + " Find target"))
    reject("old_prompt_hash", lambda a: a["request"].update(prompt_sha256="0" * 64))
    reject("different_model_revision", lambda a: a["request"].update(revision="wrong"))
    reject("different_original_image_bytes", lambda a: a.update(original_image=a["original_image"] + b"x"))
    reject("different_original_dimensions", lambda a: a["request"].update(original_size=[640, 360]))
    reject("different_actual_processor_pixels", lambda a: a["input_boundary"].update(complete_RGB_sha256="0" * 64))
    reject("accumulated_auxiliary_history", lambda a: a["input_boundary"].update(message_count=2))
    reject("multiple_auxiliary_images", lambda a: a["input_boundary"].update(content_types=["image", "image", "text"]))
    reject("prior_main_context_supplied", lambda a: a["input_boundary"].update(task_history_candidate_previous_auxiliary_content_supplied=True))
    reject("reused_call_boundary", lambda a: a["discarded_context"].update(call_id="0" * 32))
    reject("reused_auxiliary_template", lambda a: a["discarded_context"].update(template_calls=2))
    reject("nonempty_actual_first_KV", lambda a: a["discarded_context"].update(actual_first_forward_cache_length=1))
    reject("unbound_actual_forward_count", lambda a: a["discarded_context"].update(actual_forward_calls=1))
    reject("claimed_release_with_live_cache", lambda a: a["discarded_context"].update(observed_cache_objects_still_alive=1))
    reject("no_observed_cache_object", lambda a: a["discarded_context"].update(observed_cache_objects=0))
    reject("untrackable_cache_type", lambda a: a["discarded_context"].update(untrackable_cache_types=["unknown.Cache"]))
    reject("release_not_measured", lambda a: a["discarded_context"].update(all_observed_cache_objects_released=False))
    reject("positional_state_not_reset", lambda a: a["discarded_context"].update(known_auxiliary_per_generation_fields_reset_to_none=[]))
    reject("main_context_referenced", lambda a: a["discarded_context"].update(main_model_or_main_context_referenced=True))
    reject("raw_receipt_deleted", lambda a: a["discarded_context"].update(raw_experiment_receipts_deleted=True))
    reject("first_forward_pixels_changed", lambda a: a["first_forward"]["pixel_values"].update(sha256="0" * 64))
    reject("processor_tensor_omitted_at_forward", lambda a: a["first_forward"].pop("image_grid_thw"))
    reject("input_tensor_binary_SHA_not_bound", lambda a: a["verified_file_SHA256"].update({a["prepared"]["input_ids"]["file"]: "0" * 64}))
    reject("two_actual_native_grids", lambda a: (
        a["prepared"]["image_grid_thw"].update(shape=[2, 3]),
        a["first_forward"]["image_grid_thw"].update(shape=[2, 3])))
    reject("expanded_original_output_budget", lambda a: a["effective_generation"].update(max_new_tokens=4096))
    reject("changed_original_sampling", lambda a: a["effective_generation"].update(do_sample=True))
    reject("returned_native_prefix_changed", lambda a: a["sequence_ids"][0].__setitem__(0, 1))
    reject("native_output_ID_changed", lambda a: a["actual_generation"]["output_ids"].__setitem__(0, 1))
    reject("native_return_binary_SHA_changed", lambda a: a["verified_file_SHA256"].update({"sequence_ids.tensor": "0" * 64}))
    reject("EOS_relabelled", lambda a: a["actual_generation"].update(natural_EOS=False))
    reject("raw_text_not_independent_native_decode", lambda a: a.update(independently_decoded_native_output="invented"))
    reject("saved_bytes_not_actual_selected_ID_bytes", lambda a: a.update(independently_reconstructed_native_token_bytes=b"invented"))
    reject("selected_mask_token_changed", lambda a: a["mask_steps"]["steps"][0].update(selected_id=1))
    reject("selected_mask_token_disallowed", lambda a: a["mask_steps"]["steps"][0].update(selected_allowed=False))
    reject("wrong_native_prefix_hash", lambda a: a["mask_steps"]["steps"][0].update(prefix_sha256="0" * 64))
    reject("mask_step_omitted", lambda a: a["mask_steps"]["steps"].pop())
    reject("different_grammar_schema", lambda a: a["mask_steps"].update(schema_sha256="0" * 64))
    reject("Unicode_guard_source_changed", lambda a: a["unicode_guard"].update(source_sha256="0" * 64))
    reject("semantic_token_rewrite", lambda a: a["unicode_guard"].update(native_selected_tokens_not_rewritten=False))
    reject("incomplete_JSON_relabelled_natural_EOS", lambda a: a["unicode_guard"].update(final_decoded_length_state_complete_before_EOS=False))
    reject("raw_UTF8_status_relabelled", lambda a: a["utf8_validation"].update(strict_native_UTF8_roundtrip=False))
    reject("raw_output_file_SHA_changed", lambda a: a["verified_file_SHA256"].update({"raw-output.txt": "0" * 64}))
    return baseline, results
