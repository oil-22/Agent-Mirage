"""Read-only native primary receipts, independent of mixed global request index.

Complete original binary SHA authorities and full journal mapping must be
verified by the caller. No weights, inference, output repair or semantic labels.
"""
import base64
import copy
import io
import json
import math
from PIL import Image
from auxiliary_receipt_checks import canonical, digest, id_bytes, require
from mixed_exchange_checks import checked_event


def primary_messages(payload):
    """Independently rebuild the original actor or public verifier message body."""
    if payload["operation"] == "actor":
        require(set(payload) == {"operation", "body"}, "Actor payload fields changed")
        return payload["body"]["messages"]
    require(payload["operation"] == "judge" and
            set(payload) == {"operation", "system", "view", "candidate"}, "Judge payload changed")
    source_view = payload["view"]
    require(set(source_view) == {"observation_id", "messages", "images", "recent_action",
                          "execution_feedback", "observed_at"}, "Original public view fields changed")
    # The native verifier serializes PublicView.data into a text block without
    # sorting. Rebuild that source-defined order after canonical HTTP parsing.
    view = {key: copy.deepcopy(source_view[key]) for key in
            ["observation_id", "messages", "images", "recent_action", "execution_feedback", "observed_at"]}
    raw_images = []
    for entry in view["images"]:
        require(set(entry) == {"raw_base64", "role"} and entry["role"] in {"current", "reference"},
                "Original verifier image transport changed")
        raw_images.append(base64.b64decode(entry["raw_base64"], validate=True))
    infos = []
    for raw, entry in zip(raw_images, view["images"]):
        with Image.open(io.BytesIO(raw)) as image:
            image.load()
            size = list(image.size)
        infos.append({"sha256": digest(raw), "size": size, "role": entry["role"], "decoded": True})
    view["images"] = infos
    for message in view["messages"]:
        if not isinstance(message["content"], list):
            continue
        blocks = []
        for block in message["content"]:
            if block["type"] == "image_url":
                url = block["image_url"]
                url = url["url"] if isinstance(url, dict) else url
                raw = base64.b64decode(url.split(",", 1)[1], validate=True)
                matches = [i for i, info in enumerate(infos) if info["sha256"] == digest(raw)]
                require(bool(matches), "Historical message image absent from supplied verifier images")
                blocks.append({"type": "image_reference", "image_index": matches[0]})
            else:
                blocks.append(block)
        message["content"] = blocks
    blocks = [{"type": "text", "text": json.dumps({"public": view, "candidate": payload["candidate"]}, ensure_ascii=False)}]
    for index, (raw, info) in enumerate(zip(raw_images, infos)):
        blocks.extend([{"type": "text", "text": "Image index " + str(index) + ", role " + info["role"] + ", original pixels:"},
                       {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(raw).decode()}}])
    return [{"role": "system", "content": payload["system"]}, {"role": "user", "content": blocks}]


def check_primary_receipts(*, external_request, response, mapped_request, prepared,
                           first_forward, effective_generation, expected_generation,
                           native_call, actual_generation, sequence_ids, forward_count,
                           independently_decoded_native_output, verified_file_SHA256,
                           prefill, prefill_completion_event, expected_device_map,
                           expected_group_order, expected_actor_parameters,
                           expected_verifier_schema):
    payload = external_request["payload"]
    op = payload["operation"]
    require(op in {"actor", "judge"} and mapped_request["operation"] == op,
            "Primary auditor cannot certify an auxiliary request")
    require(external_request["trajectory_id"] == mapped_request["trajectory_id"] and
            external_request["decision_index"] == mapped_request["decision"] and
            external_request["attempt_index"] == mapped_request["original_track_attempt_index"],
            "Native input belongs to another run, decision or original call budget")
    require(digest(canonical(payload)) == mapped_request["payload_sha256"] == response["payload_sha256"] and
            response["operation"] == op and response["request_id"] == external_request["request_id"] and
            response["external_wire_sha256"] == digest(canonical(external_request)) and
            response["receipt"].endswith("/requests/" + mapped_request["request"]),
            "Native payload/returned request binding changed")
    require(1 <= mapped_request["decision"] <= 50 and
            1 <= mapped_request["original_track_attempt_index"] <= (70 if op == "actor" else 140),
            "Original primary decision or call budget exceeded")
    messages = primary_messages(payload)
    require(native_call["request_messages_sha256"] == digest(canonical(messages)),
            "Native generated messages omit or alter original lawful context/images")
    image_count = sum(block["type"] == "image_url" for message in messages
                      if isinstance(message.get("content"), list) for block in message["content"])
    require(set(prepared) == set(first_forward) and "input_ids" in prepared,
            "Prepared and actual first forward input keys differ")
    for name in prepared:
        before, actual = prepared[name], first_forward[name]
        require(all(before[field] == actual[field] for field in ["shape", "dtype", "bytes", "sha256"]),
                "Actual first forward changed native processor tensor: " + name)
        for item in [before, actual]:
            require(verified_file_SHA256[item["file"]] == item["sha256"],
                    "Native input tensor full SHA authority differs: " + name)
    if image_count:
        require({"pixel_values", "image_grid_thw"} <= set(prepared) and
                prepared["image_grid_thw"]["shape"] == [image_count, 3] and
                prepared["image_grid_thw"]["dtype"] == "torch.int64",
                "Complete original supplied image grids missing")
    else:
        require(not ({"pixel_values", "image_grid_thw"} & set(prepared)),
                "Text-only request incorrectly attributed image input")
    require(prepared["input_ids"]["dtype"] == "torch.int64" and
            prepared["input_ids"]["shape"] == [1, actual_generation["input_tokens"]] and
            len(native_call["input_ids"]) == actual_generation["input_tokens"] and
            digest(id_bytes(native_call["input_ids"])) == prepared["input_ids"]["sha256"],
            "Actual native input token IDs differ from full original processor input")
    require(canonical(effective_generation) == canonical(expected_generation) == canonical(native_call["generation_config"]) and
            effective_generation["max_new_tokens"] == (2048 if op == "actor" else 4096) and
            effective_generation["do_sample"] is False,
            "Source-rebuilt original effective generation changed")
    for field in ["force_words_ids", "forced_decoder_ids", "forced_bos_token_id", "forced_eos_token_id",
                  "constraints", "bad_words_ids", "suppress_tokens", "begin_suppress_tokens"]:
        require(effective_generation.get(field) in [None, []], "Forced semantic/token rewriting: " + field)
    if op == "actor":
        require(canonical({key: value for key, value in payload["body"].items() if key != "messages"}) == canonical(expected_actor_parameters) and
                native_call["verifier_grammar"] is None and expected_verifier_schema is None,
                "Actor original parameters or unconstrained narration changed")
    else:
        grammar = native_call["verifier_grammar"]
        require(grammar["engine"] == "lm-format-enforcer" and grammar["version"] == "0.11.3" and
                grammar["schema"] == expected_verifier_schema and
                grammar["schema_sha256"] == digest(canonical(expected_verifier_schema)),
                "Original strict native verifier grammar changed")
    outputs = actual_generation["output_ids"]
    require(outputs == native_call["generated_ids"] and len(outputs) == actual_generation["output_tokens"] and
            0 < len(outputs) < effective_generation["max_new_tokens"] and
            native_call["hit_output_cap"] is False and actual_generation["natural_EOS"] is True and
            outputs[-1] in effective_generation["eos_token_id"], "Original native EOS/output cap accounting differs")
    require(isinstance(sequence_ids, list) and len(sequence_ids) == 1 and
            sequence_ids[0] == native_call["input_ids"] + outputs and
            verified_file_SHA256["sequence_ids.tensor"] == digest(id_bytes(sequence_ids[0])),
            "Native generate return differs from actual original input/output IDs")
    require(native_call["text"] == response["text" if op == "actor" else "verdict"] ==
            independently_decoded_native_output.strip(), "Independent native ID decode differs from unmodified reply")
    require(native_call["environment_actions_executed"] is False and
            actual_generation["actual_forward_calls"] == forward_count["actual_forward_calls"] > 0 and
            forward_count["first_forward_recorded"] is True, "Actual native forward measurement differs")
    require(mapped_request["primary_prefill_session"] == prefill["session"] and
            mapped_request["prefill_completed"] is True and mapped_request["native_prefill_failed"] is False and
            prefill["input_tokens"] == actual_generation["input_tokens"] == mapped_request["actual_input_tokens"],
            "Native prefill selected by wrong mixed index/session or input")
    event_data = checked_event(prefill_completion_event, "native_prefill_residency_completed")
    require(event_data == prefill and
            prefill_completion_event["sha256"] == mapped_request["prefill_completion_event_sha256"],
            "Native prefill artifact differs from original completed journal event")
    require(prefill["success"] is True and prefill["full_GPU_resident_before_decode"] is True and
            prefill["all_group_forward_parameters_BF16_on_original_GPU"] is True and
            prefill["native_attention_generation_inputs_outputs_and_cache_unmodified"] is True and
            prefill["same_native_execution_device_map"] == expected_device_map,
            "Original native GPU/BF16 placement or restore invariant changed")
    require(len(expected_group_order) == len(expected_device_map) == 69 and
            set(expected_group_order) == set(expected_device_map), "Original69native groups required")
    expected_visited = set(expected_device_map)
    if not image_count:
        expected_visited.remove("model.visual")
    visited = prefill["visited_groups"]
    require(len(visited) == len(expected_visited) and set(visited) == expected_visited,
            "Native prefill groups skipped or duplicated")
    moves = [(row["group"], row["device"]) for row in prefill["moves"]]
    expected_moves = [(name, "cpu") for name in expected_group_order]
    for name in visited:
        expected_moves.extend([(name, "cuda:" + str(expected_device_map[name])), (name, "cpu")])
    expected_moves.extend((name, "cuda:" + str(expected_device_map[name])) for name in expected_group_order)
    require(moves == expected_moves, "Native GPU prefill/restore move sequence differs")
    require(type(native_call["seconds"]) in {int, float} and math.isfinite(native_call["seconds"]) and
            native_call["seconds"] >= 0, "Missing original native timer")
    return {"request": mapped_request["request"], "operation": op, "decision": mapped_request["decision"],
            "original_track_attempt_index": mapped_request["original_track_attempt_index"],
            "primary_prefill_session": mapped_request["primary_prefill_session"],
            "complete_supplied_images": image_count, "actual_input_tokens": actual_generation["input_tokens"],
            "output_tokens": len(outputs), "natural_EOS": True,
            "all_prepared_first_forward_and_returned_sequence_IDs_bound": True,
            "source_rebuilt_original_effective_generation_exact": True,
            "independent_native_tokenizer_decode_matches_unmodified_reply": True,
            "complete_original_actor_or_verifier_messages_bound": True,
            "original_GPU_prefill_group_moves_and_restore_bound": True,
            "native_call_timer_seconds": native_call["seconds"],
            "scope": "Native source/input/output/grammar/session provenance only. No independent semantic label, official score, current tensor-value hash, walltime/currency/energy or efficacy claim."}
