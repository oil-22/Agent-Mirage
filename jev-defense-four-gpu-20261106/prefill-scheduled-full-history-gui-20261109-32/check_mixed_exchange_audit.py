"""Adversarial CPU transport fixtures; never new model/GUI controls."""
import base64
import copy
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "runtime-package/release"))
from image_evidence import ACTOR_BOUNDARY, canonical, digest
from evidence_observer import NeutralEvidenceObserver
from mixed_exchange_checks import check_actor_insertion, check_gpu_cycle, check_http_exchange


def fixture(*, enabled=True, invalid_raw=False):
    old = HERE.parent / "unicode-guard-real-preflight-20261109-18/terminal-collection-1794218465768999100/original/worker/auxiliary/T03-filled-filter"
    req = json.loads((old / "request.json").read_bytes())
    image = (old / "original.png").read_bytes()
    native_text = "not JSON" if invalid_raw else (old / "raw-output.txt").read_text(encoding="utf8")
    envelope = {"request_sha256": digest(canonical(req)), "image_sha256": req["image_sha256"],
                "model": req["model"], "revision": req["revision"], "raw_output": native_text, "natural_eos": True}
    observer = NeutralEvidenceObserver(lambda request: copy.deepcopy(envelope), model=req["model"],
        revision=req["revision"], enabled=enabled, max_calls=60)
    expected_packet = observer.packet(image)
    image_block = {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(image).decode()}}
    messages = [{"role": "system", "content": "Synthetic native system"},
                {"role": "user", "content": [copy.deepcopy(image_block), {"type": "text", "text": "Earlier legal observation"}]},
                {"role": "assistant", "content": "A past plan is not executed inspection."},
                {"role": "user", "content": [{"type": "text", "text": "Synthetic current task"}, copy.deepcopy(image_block)]},
                {"role": "user", "content": "A trailing source correction must remain unchanged."}]
    public = {"observation_id": "fixture-obs1", "messages": messages,
              "images": [{"sha256": req["image_sha256"], "size": req["original_size"], "role": "current", "decoded": True}],
              "recent_action": "fixture native scroll", "execution_feedback": "execution alone is not confirmation", "observed_at": 100.0}
    template = {"model": "/opt/whz/llms/Qwen3.8-27B", "temperature": 0, "max_tokens": 2048,
                "chat_template_kwargs": {"enable_thinking": False}}
    original = dict(template, messages=copy.deepcopy(messages))
    augmented = copy.deepcopy(original)
    augmented["messages"][3]["content"].append({"type": "text", "text": ACTOR_BOUNDARY +
        json.dumps(expected_packet, ensure_ascii=False, separators=(",", ":"))})
    events = []

    def emit(kind, data):
        e = {"kind": kind, "data": copy.deepcopy(data), "time": float(len(events)),
             "seq": len(events), "previous": "0" * 64 if not events else events[-1]["sha256"]}
        e["sha256"] = digest(canonical(e))
        events.append(e)
        return e

    context = emit("actor_request", {"public": public, "corrections": [{"status": "pending"}]})
    observer_request = observer_raw = exchange = None
    if enabled:
        observer_request = emit("neutral_evidence_request", {"call_number": 1, "request": req,
            "request_sha256": digest(canonical(req))})
        body = {"trajectory_id": "synthetic-aux-trajectory", "decision_index": 1, "attempt_index": 1,
                "request_id": "1" * 32, "payload": req}
        wire_event = emit("actual_evidence_wire_request", {"path": "/evidence", "body": body,
            "wire_sha256": digest(canonical(body))})
        response = {"request_id": body["request_id"], "external_wire_sha256": digest(canonical(body)),
                    "payload_sha256": digest(canonical(req)), "operation": "evidence",
                    "receipt": "/synthetic/worker/requests/0001", "seconds_including_instrumentation": 10.0,
                    "evidence_response": envelope}
        raw = canonical(response)
        raw_event = emit("actual_evidence_wire_raw_response", {"http_status": 200,
            "raw_base64": base64.b64encode(raw).decode(), "raw_sha256": digest(raw)})
        response_event = emit("actual_evidence_wire_response", {"body": response})
        exchange = {"request": wire_event, "raw_response": raw_event, "response": response_event}
        observer_raw = emit("neutral_evidence_raw_reply", {"response": envelope,
            "request_sha256": digest(canonical(req)), "preserved_before_contract_validation": True})
    packet_event = emit("neutral_evidence_packet", expected_packet)
    insertion = emit("neutral_evidence_actor_insertion", {"current_message_index": 3,
        "original_actor_body_sha256": digest(canonical(original)), "augmented_actor_body_sha256": digest(canonical(augmented)),
        "original_view_sha256": digest(canonical(public)), "packet_sha256": digest(canonical(expected_packet)),
        "full_original_history_and_trailing_corrections_retained": True})
    actor_wire = {"trajectory_id": "synthetic-aux-trajectory", "decision_index": 1,
                  "attempt_index": 1, "request_id": "2" * 32, "payload": {"operation": "actor", "body": augmented}}
    actor_event = emit("actual_actor_wire_request", {"path": "/", "body": actor_wire,
        "wire_sha256": digest(canonical(actor_wire))})
    actor_args = dict(context_event=context, packet_event=packet_event, insertion_event=insertion,
        actor_request_event=actor_event, actor_template=template, actor_boundary=ACTOR_BOUNDARY,
        expected_packet=expected_packet, observer_enabled=enabled, evidence_exchange=exchange,
        observer_request_event=observer_request, observer_raw_reply_event=observer_raw)
    if not enabled:
        return {"actor": actor_args}
    mapped = {"operation": "evidence", "request": "0001", "trajectory_id": body["trajectory_id"],
              "decision": 1, "original_track_attempt_index": 1, "payload_sha256": digest(canonical(req)),
              "seal_sha256": "a" * 64, "primary_prefill_session": None}
    binding = {"wire_sha256": digest(canonical(body)), "payload_sha256": digest(canonical(req)),
               "request_id": body["request_id"], "request_seal_sha256": "a" * 64,
               "response_raw_sha256": digest(raw), "response": response, "receipt": response["receipt"]}
    http_args = dict(request_event=wire_event, raw_response_event=raw_event, response_event=response_event,
                     server_binding=binding, mapped_request=mapped)
    groups = ["synthetic-group-" + str(i) for i in range(15)]
    forwards = json.loads((old / "actual-generation.json").read_bytes())["actual_forward_calls"]
    transitions = []
    for index, kind in enumerate(["to_auxiliary", "to_primary"]):
        devices = ["cuda:3"] if index == 0 else ["cuda:0", "cuda:1", "cuda:2", "cuda:3"]
        row = {"kind": kind, "seconds": 1.0, "transferred_primary_groups": groups,
               "all_actual_model_forwards_GPU_only": True, "precision_unchanged": "bfloat16",
               "CPU_storage_only_no_CPU_inference": True, "primary_forward_calls": 7,
               "auxiliary_forward_calls": 0 if index == 0 else forwards,
               "actual_CUDA_tensors": {"devices": devices, "tensor_count": 100,
                  "tensor_bytes_by_device": {dev: 1000 for dev in devices}, "dtype_elements": {"torch.bfloat16": 2000}}}
        transitions.append(emit("GPU_weight_residency_transition", row))
    mapped["residency_transitions"] = [{"kind": e["data"]["kind"], "event_sha256": e["sha256"]} for e in transitions]
    gpu_args = dict(mapped_request=mapped, transition_events=transitions,
                    transition_files=[e["data"] for e in transitions], expected_primary_groups=groups,
                    expected_tensor_proofs=[copy.deepcopy(e["data"]["actual_CUDA_tensors"]) for e in transitions],
                    auxiliary_native_forwards=forwards)
    return {"actor": actor_args, "http": http_args, "gpu": gpu_args}


def resign(event):
    value = dict(event)
    value.pop("sha256")
    event["sha256"] = digest(canonical(value))


def run_checks():
    rows = []
    functions = {"actor": check_actor_insertion, "http": check_http_exchange, "gpu": check_gpu_cycle}
    for name, data in [("synthetic_available_auxiliary", fixture()),
                       ("synthetic_invalid_reply_preserved_unavailable", fixture(invalid_raw=True)),
                       ("synthetic_noaux_control", fixture(enabled=False))]:
        for kind, arguments in data.items():
            value = functions[kind](**arguments)
            if kind == "http":
                assert value["same_timer_scope_as_primary_native_call"] is False
        rows.append({"case": name, "passed": True, "not_actual_new_GUI_or_model_control": True})

    def reject(name, kind, mutate):
        data = copy.deepcopy(fixture()[kind])
        mutate(data)
        try:
            functions[kind](**data)
        except (ValueError, KeyError, TypeError, StopIteration):
            rows.append({"case": name, "passed": True, "not_actual_new_GUI_or_model_control": True})
        else:
            raise AssertionError("Invalid provenance accepted: " + name)

    def event_change(data, event, mutation):
        mutation(data[event]["data"])
        resign(data[event])

    for field, value in [("trajectory_id", "other-run"), ("decision_index", 2), ("attempt_index", 2),
                         ("request_id", "invalid-id")]:
        reject("different_external_" + field, "http", lambda d, f=field, v=value:
            event_change(d, "request_event", lambda x: x["body"].update({f: v})))
    reject("changed_wire_hash", "http", lambda d: event_change(d, "request_event", lambda x: x.update(wire_sha256="f" * 64)))
    reject("different_endpoint", "http", lambda d: event_change(d, "request_event", lambda x: x.update(path="/")))
    reject("HTTP_failure_not_reply", "http", lambda d: event_change(d, "raw_response_event", lambda x: x.update(http_status=500)))
    reject("changed_raw_response_bytes", "http", lambda d: event_change(d, "raw_response_event", lambda x: x.update(raw_base64=base64.b64encode(b"{}").decode())))
    reject("different_sealed_response", "http", lambda d: d["server_binding"]["response"].update(operation="judge"))
    reject("different_server_seal", "http", lambda d: d["server_binding"].update(request_seal_sha256="b" * 64))
    reject("reordered_HTTP_events", "http", lambda d: d["raw_response_event"].update(seq=999))
    reject("auxiliary_consumes_primary_session", "gpu", lambda d: d["mapped_request"].update(primary_prefill_session=2))
    reject("incomplete_GPU_cycle", "gpu", lambda d: d["transition_files"].pop())
    reject("changed_GPU_transition_artifact", "gpu", lambda d: d.update(transition_files=[dict(d["transition_files"][0], kind="to_primary"),d["transition_files"][1]]))
    reject("wrong_expected_primary_groups", "gpu", lambda d: d["expected_primary_groups"].reverse())
    reject("wrong_native_auxiliary_forward_count", "gpu", lambda d: d.update(auxiliary_native_forwards=1))
    reject("different_source_tensor_dtype_metadata", "gpu", lambda d:
        d["expected_tensor_proofs"][0]["dtype_elements"].update({"torch.float32": 1}))
    for field in ["all_actual_model_forwards_GPU_only", "CPU_storage_only_no_CPU_inference"]:
        reject("missing_GPU_invariant_" + field, "gpu", lambda d, f=field: d["transition_files"][0].update({f: False}))
    reject("missing_current_data_block", "actor", lambda d: event_change(d, "actor_request_event", lambda x:
        x["body"]["payload"]["body"]["messages"][3]["content"].pop()))
    reject("changed_main_generation_parameters", "actor", lambda d: event_change(d, "actor_request_event", lambda x:
        x["body"]["payload"]["body"].update(max_tokens=512)))
    reject("removed_legal_history", "actor", lambda d: event_change(d, "actor_request_event", lambda x:
        x["body"]["payload"]["body"]["messages"].pop(1)))
    reject("removed_trailing_correction", "actor", lambda d: event_change(d, "actor_request_event", lambda x:
        x["body"]["payload"]["body"]["messages"].pop()))
    reject("wrong_insertion_message", "actor", lambda d: event_change(d, "insertion_event", lambda x: x.update(current_message_index=4)))
    reject("changed_original_view_SHA", "actor", lambda d: event_change(d, "insertion_event", lambda x: x.update(original_view_sha256="e" * 64)))
    reject("different_expected_packet", "actor", lambda d: d.update(expected_packet={**d["expected_packet"], "image_freshness_known": True}))
    reject("original_reply_not_preserved", "actor", lambda d: event_change(d, "observer_raw_reply_event", lambda x: x.update(preserved_before_contract_validation=False)))
    reject("wrong_observer_request_budget", "actor", lambda d: event_change(d, "observer_request_event", lambda x: x.update(call_number=2)))
    reject("missing_real_auxiliary_exchange", "actor", lambda d: d.update(evidence_exchange=None))
    reject("auxiliary_in_disabled_arm", "actor", lambda d: d.update(observer_enabled=False))
    reject("missing_observer_raw_reply", "actor", lambda d: d.update(observer_raw_reply_event=None))
    return rows


if __name__ == "__main__":
    checks = run_checks()
    print(json.dumps({"passed": True, "count": len(checks), "checks": checks,
        "new_model_GUI_scorer_calls": 0, "actual_enabled_GUI_pipeline_proven": False}, ensure_ascii=False))
