"""Read-only request/prefill mapping for the frozen primary/auxiliary schedule.

This module never imports a model, sends a request, or modifies a runtime file.
It verifies journal order and budgets, not visual correctness or complete native
tensor provenance. Auxiliary receipt, statelessness and Controller insertion
audits remain separate requirements.
"""
import copy
import hashlib
import json
import re


CAPS = {"actor": 70, "judge": 140, "evidence": 60}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf8")


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def verified_events(raw):
    """Verify every complete event; preserve an incomplete live tail explicitly."""
    require(isinstance(raw, bytes), "Raw original journal bytes required")
    lines = raw.splitlines(keepends=True)
    partial = bool(lines and not lines[-1].endswith(b"\n"))
    if partial:
        lines.pop()
    previous, events = "0" * 64, []
    for index, line in enumerate(lines):
        value = json.loads(line)
        require(isinstance(value, dict), "Journal event object required")
        event = dict(value)
        digest = event.pop("sha256")
        require(event["seq"] == index and event["previous"] == previous,
                "Broken journal sequence/previous hash")
        require(hashlib.sha256(canonical(event)).hexdigest() == digest,
                "Journal event hash mismatch")
        previous = digest
        events.append(value)
    return events, {"events": len(events), "head": previous,
                    "incomplete_last_line": partial,
                    "original_bytes_sha256": hashlib.sha256(raw).hexdigest()}


def map_requests(events, queue, initial_counts):
    require(bool(queue) and isinstance(queue, list), "Frozen queue required")
    require(set(initial_counts) == set(CAPS), "Original carryover counts required")
    require(all(type(initial_counts[k]) is int and 0 <= initial_counts[k] <= CAPS[k]
                for k in CAPS), "Invalid carryover budget")
    require(len({item["run_id"] for item in queue}) == len(queue), "Duplicate run")
    rows, ended, control_ids = [], [], set()
    active = pending = None
    counts, index, session, global_request, failed = {}, 0, 0, 0, False
    for event in events:
        kind, data = event["kind"], event["data"]
        if kind == "GUI_run_begin":
            require(not failed and active is None and pending is None and index < len(queue),
                    "Run begin outside frozen once-only queue")
            require(set(data) == {"trajectory_id", "request_id"}, "Begin fields changed")
            require(data["trajectory_id"] == queue[index]["run_id"], "Run order mismatch")
            require(re.fullmatch(r"[0-9a-f]{32}", data["request_id"]) is not None and
                    data["request_id"] not in control_ids, "Duplicate/invalid control request")
            control_ids.add(data["request_id"])
            active = data["trajectory_id"]
            counts = copy.deepcopy(initial_counts) if index == 0 else dict.fromkeys(CAPS, 0)
        elif kind == "GUI_run_end":
            require(active is not None and pending is None, "Run ended with unfinished request")
            require(set(data) == {"trajectory_id", "request_id", "status", "terminal_receipt_sha256"},
                    "End fields changed")
            require(data["trajectory_id"] == active, "End bound to different run")
            require(re.fullmatch(r"[0-9a-f]{32}", data["request_id"]) is not None and
                    data["request_id"] not in control_ids, "Duplicate/invalid control request")
            control_ids.add(data["request_id"])
            require(data["status"] in {"completed", "technical_failure", "stopped"}, "Unknown end status")
            require(re.fullmatch(r"[0-9a-f]{64}", data["terminal_receipt_sha256"]) is not None,
                    "Invalid terminal receipt hash")
            ended.append({"trajectory_id": active, "counts": copy.deepcopy(counts),
                          "status": data["status"], "event_sha256": event["sha256"],
                          "GUI_terminal_sha256": data["terminal_receipt_sha256"]})
            failed = data["status"] != "completed"
            active, counts = None, {}
            index += 1
        elif kind == "model_request":
            require(not failed and active is not None and pending is None, "Interleaved/unbegun request")
            op = data["operation"]
            require(op in CAPS and data["trajectory_id"] == active, "Request run/operation mismatch")
            require(op != "evidence" or queue[index]["observer_enabled"] is True,
                    "Auxiliary invoked in disabled arm")
            require(type(data["decision_index"]) is int and 1 <= data["decision_index"] <= 50,
                    "Original decision cap exceeded")
            require(type(data["attempt_index"]) is int and
                    data["attempt_index"] == counts[op] + 1 <= CAPS[op], "Original call budget mismatch")
            global_request += 1
            require(data["request"] == "requests/" + str(global_request).zfill(4),
                    "Global request sequence mismatch")
            counts[op] += 1
            pending = {"request": str(global_request).zfill(4), "operation": op,
                       "trajectory_id": active, "decision": data["decision_index"],
                       "original_track_attempt_index": data["attempt_index"],
                       "payload_sha256": data["payload_sha256"],
                       "request_event_sha256": event["sha256"],
                       "primary_prefill_session": None, "prefill_completed": False,
                       "residency_transitions": [], "native_prefill_failed": False}
        elif kind == "native_prefill_idle_weights_stored_in_RAM":
            require(pending is not None and pending["operation"] in {"actor", "judge"},
                    "Primary prefill attributed to auxiliary/unbound request")
            require(pending["primary_prefill_session"] is None, "Repeated primary prefill")
            require(data["session"] == session + 1, "Primary session sequence mismatch")
            require(type(data["input_tokens"]) is int and data["input_tokens"] > 1,
                    "Fresh complete primary prefill required")
            for name in ["original_execution_devices_unchanged",
                         "native_forward_source_inputs_and_KV_not_modified", "CPU_forward_forbidden"]:
                require(data[name] is True, "Primary prefill invariant missing: " + name)
            session += 1
            pending.update(primary_prefill_session=session, actual_input_tokens=data["input_tokens"],
                           prefill_start_event_sha256=event["sha256"])
        elif kind in {"native_prefill_residency_completed", "native_prefill_residency_failed_no_retry"}:
            require(pending is not None and pending["operation"] in {"actor", "judge"} and
                    pending["primary_prefill_session"] is not None and not pending["prefill_completed"] and
                    not pending["native_prefill_failed"],
                    "Unbound/repeated primary prefill completion")
            require(data["session"] == pending["primary_prefill_session"] and
                    data["input_tokens"] == pending["actual_input_tokens"], "Prefill session/input mismatch")
            if kind == "native_prefill_residency_failed_no_retry":
                require(data["success"] is False, "Failed prefill marked successful")
                pending["native_prefill_failed"] = True
            else:
                require(data["success"] is True and data["full_GPU_resident_before_decode"] is True and
                        data["all_group_forward_parameters_BF16_on_original_GPU"] is True and
                        data["native_attention_generation_inputs_outputs_and_cache_unmodified"] is True,
                        "Native primary execution/restore invariants missing")
                pending["prefill_completed"] = True
            pending["prefill_completion_event_sha256"] = event["sha256"]
        elif kind == "GPU_weight_residency_transition":
            require(pending is not None and pending["operation"] == "evidence",
                    "Auxiliary transition attributed to primary/unbound request")
            expected = ["to_auxiliary", "to_primary"]
            position = len(pending["residency_transitions"])
            require(position < 2 and data["kind"] == expected[position], "Auxiliary transition order mismatch")
            require(data["all_actual_model_forwards_GPU_only"] is True and
                    data["precision_unchanged"] == "bfloat16" and
                    data["CPU_storage_only_no_CPU_inference"] is True,
                    "Auxiliary GPU/BF16 execution invariant missing")
            pending["residency_transitions"].append({"kind": data["kind"],
                                                      "event_sha256": event["sha256"]})
        elif kind == "model_reply_sealed":
            require(pending is not None and data["request"] == "requests/" + pending["request"] and
                    data["operation"] == pending["operation"], "Reply bound to different request")
            if pending["operation"] == "evidence":
                require(pending["primary_prefill_session"] is None and
                        len(pending["residency_transitions"]) == 2, "Auxiliary GPU cycle incomplete")
            else:
                require(pending["prefill_completed"] and not pending["native_prefill_failed"],
                        "Primary reply lacks successful original prefill/restore")
            require(re.fullmatch(r"[0-9a-f]{64}", data["seal_sha256"]) is not None, "Invalid request seal")
            pending.update(seal_sha256=data["seal_sha256"], reply_event_sha256=event["sha256"])
            rows.append(pending)
            pending = None
    return {"sealed_requests": rows, "pending_request": pending, "ended_runs": ended,
            "active_run": active, "next_run_index": index, "counts": counts,
            "primary_prefill_sessions": session, "failed_run": failed,
            "scope": "Journal order, original budgets and primary-only session mapping. Does not certify auxiliary input/cache/release, native tensors, GUI insertion, semantic labels, scores or efficacy."}
