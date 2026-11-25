"""Read-only cross-host HTTP, GPU-cycle and actor-insertion binding checks.

Callers must verify complete journal prefixes and original request file seals.
These checks do not generate, relabel semantic truth, repair output, or change
runtime conditions. Native input/ID/cache checks remain a separate requirement.
"""
import base64
import copy
import hashlib
import io
import json
import math
import re


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def checked_event(event, kind):
    require(event["kind"] == kind, "Different journal event kind")
    original = dict(event)
    signature = original.pop("sha256")
    require(digest(canonical(original)) == signature, "Selected event hash differs")
    require(type(event["seq"]) is int and event["seq"] >= 0,
            "Actual journal sequence required")
    return event["data"]


def check_http_exchange(*, request_event, raw_response_event, response_event,
                        server_binding, mapped_request):
    """Bind an actual GUI exchange to the separately sealed server receipt."""
    op = mapped_request["operation"]
    require(op in {"actor", "judge", "evidence"}, "Unknown model operation")
    prefix = "actual_" + op + "_wire"
    request = checked_event(request_event, prefix + "_request")
    raw_reply = checked_event(raw_response_event, prefix + "_raw_response")
    reply = checked_event(response_event, prefix + "_response")
    require(request_event["seq"] < raw_response_event["seq"] < response_event["seq"],
            "Actual HTTP event order changed")
    body = request["body"]
    require(set(body) == {"trajectory_id", "decision_index", "attempt_index",
                          "request_id", "payload"}, "External request fields changed")
    require(re.fullmatch(r"[0-9a-f]{32}", body["request_id"]) is not None,
            "Invalid original request ID")
    require(body["trajectory_id"] == mapped_request["trajectory_id"] and
            body["decision_index"] == mapped_request["decision"] and
            body["attempt_index"] == mapped_request["original_track_attempt_index"],
            "GUI/server run, decision or original budget differs")
    require(request["path"] == ("/evidence" if op == "evidence" else "/"),
            "Different model endpoint")
    wire_sha = digest(canonical(body))
    payload_sha = digest(canonical(body["payload"]))
    require(request["wire_sha256"] == wire_sha == server_binding["wire_sha256"] and
            payload_sha == server_binding["payload_sha256"] == mapped_request["payload_sha256"],
            "GUI wire/payload differs from actual server input")
    require(server_binding["request_id"] == body["request_id"] and
            server_binding["request_seal_sha256"] == mapped_request["seal_sha256"],
            "Actual sealed server request differs")
    raw = base64.b64decode(raw_reply["raw_base64"], validate=True)
    require(raw_reply["http_status"] == 200 and digest(raw) == raw_reply["raw_sha256"] ==
            server_binding["response_raw_sha256"], "Actual response bytes/status differ")
    response = reply["body"]
    require(json.loads(raw) == response == server_binding["response"],
            "Parsed response differs from raw bytes or sealed server response")
    require(response["request_id"] == body["request_id"] and
            response["external_wire_sha256"] == wire_sha and
            response["payload_sha256"] == payload_sha and response["operation"] == op,
            "Returned request, payload or operation differs")
    require(response["receipt"] == server_binding["receipt"] and
            response["receipt"].endswith("/requests/" + mapped_request["request"]),
            "Reply refers to different native receipt")
    require(type(response["seconds_including_instrumentation"]) in {int, float} and
            math.isfinite(response["seconds_including_instrumentation"]) and
            response["seconds_including_instrumentation"] >= 0, "Missing original HTTP timer")
    return {"request": mapped_request["request"], "operation": op,
            "wire_sha256": wire_sha, "payload_sha256": payload_sha,
            "request_event_sha256": request_event["sha256"],
            "raw_reply_event_sha256": raw_response_event["sha256"],
            "reply_event_sha256": response_event["sha256"],
            "cross_host_raw_HTTP_request_response_bound": True,
            "server_timer_seconds_including_instrumentation":
                response["seconds_including_instrumentation"],
            "same_timer_scope_as_primary_native_call": False,
            "timer_scope": "Server model-operation path, including preprocessing and instrumentation; auxiliary also includes the GPU residency cycle. Separate from native-call.seconds; not walltime, currency or energy."}


def check_gpu_cycle(*, mapped_request, transition_events, transition_files,
                    expected_primary_groups, expected_tensor_proofs,
                    auxiliary_native_forwards):
    require(mapped_request["operation"] == "evidence" and
            mapped_request["primary_prefill_session"] is None,
            "Auxiliary must not consume primary prefill session")
    require(len(transition_events) == len(transition_files) == 2,
            "Exactly one complete auxiliary GPU cycle required")
    require(len(expected_primary_groups) == 15 and len(set(expected_primary_groups)) == 15,
            "Original primary device-three group set required")
    require(type(auxiliary_native_forwards) is int and auxiliary_native_forwards > 0,
            "Actual native auxiliary forward count required")
    require(len(expected_tensor_proofs) == 2, "Source-bound native tensor metadata required")
    for index, (event, artifact) in enumerate(zip(transition_events, transition_files)):
        row = checked_event(event, "GPU_weight_residency_transition")
        kind = ["to_auxiliary", "to_primary"][index]
        require(row == artifact and row["kind"] == kind and
                mapped_request["residency_transitions"][index] ==
                {"kind": kind, "event_sha256": event["sha256"]},
                "GPU transition file/journal/request differs")
        require(row["all_actual_model_forwards_GPU_only"] is True and
                row["precision_unchanged"] == "bfloat16" and
                row["CPU_storage_only_no_CPU_inference"] is True and
                row["transferred_primary_groups"] == expected_primary_groups,
                "GPU cycle changed native precision, devices or groups")
        proof = row["actual_CUDA_tensors"]
        expected_devices = ["cuda:3"] if index == 0 else ["cuda:0", "cuda:1", "cuda:2", "cuda:3"]
        require(proof["devices"] == expected_devices and
                set(proof["tensor_bytes_by_device"]) == set(expected_devices),
                "Actual complete tensor devices differ")
        require(type(proof["tensor_count"]) is int and proof["tensor_count"] > 0 and
                all(type(n) is int and n > 0 for n in proof["tensor_bytes_by_device"].values()) and
                proof["dtype_elements"].get("torch.bfloat16", 0) > 0 and
                proof == expected_tensor_proofs[index],
                "Missing tensor accounting or unexpected floating-point precision")
    before, after = transition_files
    require(transition_events[0]["seq"] < transition_events[1]["seq"] and
            after["primary_forward_calls"] == before["primary_forward_calls"] and
            after["auxiliary_forward_calls"] - before["auxiliary_forward_calls"] == auxiliary_native_forwards,
            "Actual forward counters do not bind this auxiliary cycle")
    return {"one_actual_auxiliary_GPU_cycle_bound": True,
            "auxiliary_native_forward_calls": auxiliary_native_forwards,
            "primary_weights_restored_to_original_four_GPUs_before_reply": True,
            "GPU_transition_event_SHA256": [event["sha256"] for event in transition_events],
            "parameter_placement_receipts_are_not_current_GPU_tensor_value_hashes": True}


def check_actor_insertion(*, context_event, packet_event, insertion_event,
                          actor_request_event, actor_template, actor_boundary,
                          expected_packet, observer_enabled,
                          evidence_exchange=None, observer_request_event=None,
                          observer_raw_reply_event=None):
    """Check a single extra data block against the full actual lawful view."""
    context = checked_event(context_event, "actor_request")
    packet = checked_event(packet_event, "neutral_evidence_packet")
    insertion = checked_event(insertion_event, "neutral_evidence_actor_insertion")
    actual = checked_event(actor_request_event, "actual_actor_wire_request")
    require(context_event["seq"] < packet_event["seq"] < insertion_event["seq"] < actor_request_event["seq"],
            "Evidence was inserted outside the original actor invocation")
    require(packet == expected_packet and packet["automatic_allow_or_block"] is False and
            packet["semantic_correctness_established"] is False and
            packet["inventory_is_exhaustive"] is False,
            "Inserted packet differs from frozen contract or claims semantic authority")
    view = context["public"]
    require(set(view) == {"observation_id", "messages", "images", "recent_action",
                          "execution_feedback", "observed_at"}, "Actual lawful public view changed")
    body = actual["body"]["payload"]["body"]
    require(actual["body"]["payload"]["operation"] == "actor", "Insertion not sent to actor")
    original = copy.deepcopy(actor_template)
    original["messages"] = copy.deepcopy(view["messages"])
    require(digest(canonical(original)) == insertion["original_actor_body_sha256"] and
            digest(canonical(body)) == insertion["augmented_actor_body_sha256"] and
            digest(canonical(view)) == insertion["original_view_sha256"] and
            digest(canonical(packet)) == insertion["packet_sha256"] and
            insertion["full_original_history_and_trailing_corrections_retained"] is True,
            "Original body/view, augmented body or packet SHA differs")
    index = next((i for i in range(len(original["messages"]) - 1, -1, -1)
                  if original["messages"][i].get("role") == "user" and
                  isinstance(original["messages"][i].get("content"), list)), None)
    require(index is not None and insertion["current_message_index"] == index,
            "Packet appended to wrong current user message")
    original["messages"][index]["content"].append({"type": "text", "text": actor_boundary +
        json.dumps(packet, ensure_ascii=False, separators=(",", ":"))})
    require(original == body, "Actor history, images, corrections or generation body edited")
    from PIL import Image
    image_bytes = {}
    for message in view["messages"]:
        if not isinstance(message.get("content"), list):
            continue
        for block in message["content"]:
            if block.get("type") != "image_url":
                continue
            uri = block["image_url"]["url"]
            require(uri.startswith("data:image/png;base64,"), "Unexpected main image transport")
            raw = base64.b64decode(uri.split(",", 1)[1], validate=True)
            image_bytes[digest(raw)] = raw
    for image in view["images"]:
        raw = image_bytes[image["sha256"]]
        with Image.open(io.BytesIO(raw)) as decoded:
            require(image["size"] == list(decoded.size) and image["decoded"] is True,
                    "Original lawful image dimensions/decoding differ")
    current = [image for image in view["images"] if image["role"] == "current"]
    blocks = [block for block in view["messages"][index]["content"] if block.get("type") == "image_url"]
    require(len(current) <= 1 and len(blocks) == len(current), "Current image count differs")
    if current:
        raw = base64.b64decode(blocks[0]["image_url"]["url"].split(",", 1)[1], validate=True)
        require(digest(raw) == current[0]["sha256"], "Actual actor current pixels differ")
    if observer_enabled and observer_request_event is not None:
        request = checked_event(observer_request_event, "neutral_evidence_request")
        raw_reply = checked_event(observer_raw_reply_event, "neutral_evidence_raw_reply")
        require(evidence_exchange is not None and len(current) == 1,
                "Auxiliary reply lacks actual HTTP exchange/current image")
        wire = checked_event(evidence_exchange["request"], "actual_evidence_wire_request")
        reply = checked_event(evidence_exchange["response"], "actual_evidence_wire_response")["body"]
        require(context_event["seq"] < observer_request_event["seq"] < evidence_exchange["request"]["seq"] <
                evidence_exchange["raw_response"]["seq"] < evidence_exchange["response"]["seq"] <
                observer_raw_reply_event["seq"] < packet_event["seq"], "Observer/HTTP event order differs")
        require(request["request"] == wire["body"]["payload"] and
                request["request_sha256"] == digest(canonical(request["request"])) == raw_reply["request_sha256"] and
                raw_reply["response"] == reply["evidence_response"] and
                raw_reply["preserved_before_contract_validation"] is True and
                request["call_number"] == wire["body"]["attempt_index"] and
                request["request"]["image_sha256"] == current[0]["sha256"] and
                base64.b64decode(request["request"]["image_base64"], validate=True) == raw,
                "Original observer request, response or complete current image differs")
        require(wire["body"]["trajectory_id"] == actual["body"]["trajectory_id"] and
                wire["body"]["decision_index"] == actual["body"]["decision_index"],
                "Auxiliary evidence belongs to different trajectory/decision")
    else:
        require(observer_request_event is None and observer_raw_reply_event is None and evidence_exchange is None,
                "Unavailable/disabled observer unexpectedly invoked")
        require(packet["status"] in {"observer_not_run", "unavailable_no_current_image", "unavailable_budget_exhausted"},
                "Available evidence lacks original inference/provenance events")
        require(observer_enabled or packet["status"] == "observer_not_run",
                "Disabled arm contains evidence")
    return {"current_observation_id": view["observation_id"],
            "complete_original_message_count": len(view["messages"]),
            "original_image_blocks": sum(len([b for b in m["content"] if b.get("type") == "image_url"])
                for m in view["messages"] if isinstance(m.get("content"), list)),
            "packet_status": packet["status"], "only_one_final_current_message_data_block_appended": True,
            "all_original_messages_images_trailing_corrections_and_body_parameters_retained": True,
            "auxiliary_actual_HTTP_linked": evidence_exchange is not None,
            "semantic_correctness_or_defense_efficacy_established": False}
