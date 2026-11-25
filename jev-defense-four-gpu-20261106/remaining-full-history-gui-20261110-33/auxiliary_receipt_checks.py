"""Read-only native single-image/cache-release receipt checks.

The caller must first verify the request seal and every binary file SHA. This
module checks their bindings, independent native tokenizer decode and measured
stateless boundary. It never generates, repairs text, or labels visual truth.
Outer HTTP/GUI journal linkage, GPU transitions and actual actor insertion are
separate required audits; this module alone cannot certify the full pipeline.
"""
import base64
import hashlib
import io
import json
import re
import struct


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def id_bytes(ids):
    require(isinstance(ids, list) and all(type(token) is int for token in ids),
            "Actual native integer token IDs required")
    return struct.pack("<" + "q" * len(ids), *ids)


def selected_token_bytes(tokenizer, output_ids, eos_ids):
    """Independently reconstruct only selected native ByteLevel token bytes."""
    decoder = json.loads(tokenizer.backend_tokenizer.to_str())["decoder"]
    require(decoder["type"] == "ByteLevel", "Unreviewed native decoder")
    direct = set(range(33, 127)) | set(range(161, 173)) | set(range(174, 256))
    remaining = [value for value in range(256) if value not in direct]
    inverse = {chr(value): value for value in direct}
    inverse.update({chr(256 + index): value for index, value in enumerate(remaining)})
    specials = set(tokenizer.all_special_ids)
    pieces = []
    for token in output_ids:
        if token in eos_ids:
            continue
        require(token not in specials, "Unexpected native special token in evidence text")
        piece = tokenizer.convert_ids_to_tokens(token)
        require(isinstance(piece, str), "Missing native token piece")
        pieces.append(bytes(inverse[character] for character in piece))
    return b"".join(pieces)


def check_auxiliary_receipts(*, request, original_image, fixed_prompt, expected_model,
                             expected_revision, prepared, first_forward,
                             effective_generation, expected_generation, actual_generation,
                             sequence_ids, raw_output, raw_native_token_bytes,
                             independently_decoded_native_output,
                             independently_reconstructed_native_token_bytes, input_boundary,
                             discarded_context, mask_steps, unicode_guard,
                             utf8_validation, expected_schema_sha256,
                             expected_unicode_guard_sha256, verified_file_SHA256):
    require(set(request) == {"policy", "model", "revision", "image_base64", "image_sha256",
                             "original_size", "prompt", "prompt_sha256"},
            "Auxiliary request contains missing/extra input fields")
    require(request["policy"] == "single-image-balanced-visual-evidence-v6-development",
            "Different auxiliary policy")
    require(request["model"] == expected_model and request["revision"] == expected_revision,
            "Different auxiliary model/revision")
    require(request["prompt"] == fixed_prompt and request["prompt_sha256"] == digest(fixed_prompt.encode("utf8")),
            "Nonfixed prompt or prompt hash mismatch")
    require(base64.b64decode(request["image_base64"], validate=True) == original_image and
            request["image_sha256"] == digest(original_image), "Complete original image bytes mismatch")
    from PIL import Image
    with Image.open(io.BytesIO(original_image)) as image:
        size, rgb_sha = list(image.size), digest(image.convert("RGB").tobytes())
    require(request["original_size"] == size, "Original image dimensions changed")
    require(input_boundary["message_count"] == 1 and input_boundary["role"] == "user" and
            input_boundary["content_types"] == ["image", "text"], "Auxiliary input accumulated messages")
    require(input_boundary["complete_image_sha256"] == request["image_sha256"] and
            input_boundary["complete_RGB_sha256"] == rgb_sha and input_boundary["size"] == size and
            input_boundary["fixed_prompt_sha256"] == request["prompt_sha256"],
            "Actual processor image/prompt boundary differs from request")
    require(input_boundary["task_history_candidate_previous_auxiliary_content_supplied"] is False and
            input_boundary["actual_first_forward_cache_recorded_separately"] is True,
            "Unverified isolation from main context")
    require(re.fullmatch(r"[0-9a-f]{32}", input_boundary["call_id"]) is not None and
            input_boundary["call_id"] == discarded_context["call_id"], "Per-invocation boundary ID mismatch")
    require(discarded_context["template_calls"] == 1 and
            discarded_context["actual_first_forward_cache_length"] == 0,
            "Actual first forward not a fresh invocation")
    require(discarded_context["actual_forward_calls"] == actual_generation["actual_forward_calls"] and
            discarded_context["actual_forward_calls"] > 0, "Measured native forward counts disagree")
    require(discarded_context["error_type"] is None and
            discarded_context["observed_cache_objects"] > 0 and
            discarded_context["observed_cache_objects_still_alive"] == 0 and
            discarded_context["untrackable_cache_types"] == [] and
            discarded_context["all_observed_cache_objects_released"] is True,
            "Cache release not actually measured/proven")
    require(discarded_context["main_model_or_main_context_referenced"] is False and
            discarded_context["raw_experiment_receipts_deleted"] is False and
            discarded_context["weights_unloaded"] is False and
            discarded_context["not_a_claim_of_physical_GPU_memory_zeroization"] is True,
            "Unexpected context/receipt/weight boundary")
    require("auxiliary.model.rope_deltas" in
            discarded_context["known_auxiliary_per_generation_fields_reset_to_none"],
            "Native auxiliary positional state reset missing")
    require(set(prepared) == set(first_forward) and
            {"input_ids", "pixel_values", "image_grid_thw"} <= set(prepared),
            "Actual first forward omitted native processor inputs")
    for key in prepared:
        before, actual = prepared[key], first_forward[key]
        require(all(before[field] == actual[field] for field in ["shape", "dtype", "bytes", "sha256"]),
                "Prepared/actual first-forward tensor differs: " + key)
        for item in [before, actual]:
            require(verified_file_SHA256[item["file"]] == item["sha256"],
                    "Full binary SHA authority mismatch: " + key)
    require(prepared["input_ids"]["dtype"] == "torch.int64" and
            prepared["input_ids"]["shape"] == [1, actual_generation["input_tokens"]],
            "Native input token shape/dtype mismatch")
    require(prepared["image_grid_thw"]["shape"] == [1, 3] and
            prepared["image_grid_thw"]["dtype"] == "torch.int64",
            "Auxiliary did not receive exactly one original image grid")
    require(effective_generation == expected_generation, "Original effective auxiliary generation changed")
    require(effective_generation["max_new_tokens"] == 2048 and effective_generation["do_sample"] is False and
            effective_generation["eos_token_id"] == [248044, 248046] and
            effective_generation["num_beams"] == 1 and effective_generation["num_return_sequences"] == 1,
            "Frozen auxiliary generation boundaries changed")
    for name in ["forced_eos_token_id", "force_words_ids", "forced_decoder_ids", "forced_bos_token_id",
                 "constraints", "bad_words_ids", "suppress_tokens", "begin_suppress_tokens"]:
        require(effective_generation.get(name) in [None, []], "Forced native semantic/token rewriting: " + name)
    require(isinstance(sequence_ids, list) and len(sequence_ids) == 1, "One native returned sequence required")
    sequence = sequence_ids[0]
    n_input = actual_generation["input_tokens"]
    native_inputs, native_outputs = sequence[:n_input], sequence[n_input:]
    require(digest(id_bytes(native_inputs)) == prepared["input_ids"]["sha256"],
            "Native returned prefix differs from actual input IDs")
    require(native_outputs == actual_generation["output_ids"] and
            len(native_outputs) == actual_generation["output_tokens"] and
            0 < len(native_outputs) <= effective_generation["max_new_tokens"],
            "Native returned output IDs/cap mismatch")
    require(verified_file_SHA256["sequence_ids.tensor"] == digest(id_bytes(sequence)),
            "Native returned sequence binary SHA mismatch")
    natural_eos = native_outputs[-1] in effective_generation["eos_token_id"]
    require(actual_generation["natural_EOS"] is natural_eos, "EOS accounting mismatch")
    require(isinstance(raw_output, bytes), "Original raw output file bytes required")
    text = raw_output.decode("utf8", errors="strict")
    require(independently_decoded_native_output == text,
            "Original raw text differs from independent native tokenizer decode")
    require(independently_reconstructed_native_token_bytes == raw_native_token_bytes,
            "Saved native UTF8 bytes differ from independent selected-ID byte reconstruction")
    require(mask_steps["native_stops"] == effective_generation["eos_token_id"] and
            mask_steps["schema_sha256"] == expected_schema_sha256 and
            mask_steps["all_actual_selected_tokens_allowed"] is True and
            mask_steps["no_unmasked_probability_claim"] is True,
            "Original structural mask provenance changed")
    require(len(mask_steps["steps"]) == len(native_outputs), "Selected-token mask step count mismatch")
    for index, (token, step) in enumerate(zip(native_outputs, mask_steps["steps"])):
        require(step["selected_id"] == token and step["selected_allowed"] is True and
                step["prefix_length"] == len(native_inputs) + index and
                step["prefix_sha256"] == digest(canonical(native_inputs + native_outputs[:index])),
                "Actual selected-token/prefix provenance mismatch")
        require(type(step["allowed_count"]) is int and step["allowed_count"] > 0 and
                re.fullmatch(r"[0-9a-f]{64}", step["allowed_sha256"]) is not None,
                "Missing actual structural-choice audit record")
    require(unicode_guard["source_sha256"] == expected_unicode_guard_sha256 and
            unicode_guard["subset_only"] is True and
            unicode_guard["strict_final_validator_unchanged"] is True and
            unicode_guard["native_selected_tokens_not_rewritten"] is True,
            "Unicode guard source/boundaries changed")
    require(not natural_eos or unicode_guard["final_decoded_length_state_complete_before_EOS"] is True,
            "Natural EOS without complete original structural state")
    try:
        roundtrip = raw_native_token_bytes.decode("utf8", errors="strict") == text
    except UnicodeDecodeError:
        roundtrip = False
    require(utf8_validation["strict_native_UTF8_roundtrip"] is roundtrip and
            utf8_validation["native_output_unchanged"] is True, "Native UTF8 transport audit mismatch")
    require(verified_file_SHA256["raw-output.txt"] == digest(raw_output) and
            verified_file_SHA256["generated-raw-utf8.bin"] == digest(raw_native_token_bytes),
            "Original output/raw-token bytes SHA mismatch")
    return {"request_sha256": digest(canonical(request)), "image_sha256": digest(original_image),
            "prompt_sha256": request["prompt_sha256"], "call_id": input_boundary["call_id"],
            "actual_input_tokens": len(native_inputs), "output_tokens": len(native_outputs),
            "natural_EOS": natural_eos, "native_UTF8_roundtrip": roundtrip,
            "single_complete_image_and_fixed_prompt_bound": True,
            "all_prepared_first_forward_tensors_and_actual_native_IDs_bound": True,
            "independent_native_tokenizer_decode_matches_original_raw_text": True,
            "independent_selected_native_ID_bytes_match_saved_token_bytes": True,
            "actual_first_cache_length": 0, "all_observed_cache_objects_released": True,
            "structural_mask_selected_token_provenance_bound": True,
            "mask_choices_independently_recomputed": False,
            "unmasked_probability_or_semantic_correctness_established": False,
            "full_HTTP_GPU_cycle_Controller_insertion_or_defense_efficacy_certified": False}
