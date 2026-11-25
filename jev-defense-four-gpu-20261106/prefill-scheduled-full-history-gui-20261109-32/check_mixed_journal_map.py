"""Adversarial CPU checks for provenance accounting; no model/GUI calls."""
import copy
import hashlib
import json
from mixed_journal_map import canonical, map_requests, verified_events


def fixture():
    queue = [{"run_id": "first-noaux", "observer_enabled": False},
             {"run_id": "second-aux", "observer_enabled": True}]
    entries = []

    def emit(event_kind, **data):
        entries.append({"kind": event_kind, "data": data})

    def begin(run, request):
        emit("GUI_run_begin", trajectory_id=run, request_id=request * 32)

    def primary(number, run, op, attempt, session):
        emit("model_request", request="requests/" + str(number).zfill(4), operation=op,
             trajectory_id=run, decision_index=17 if run == "first-noaux" else 1,
             attempt_index=attempt, payload_sha256="a" * 64)
        emit("native_prefill_idle_weights_stored_in_RAM", session=session, input_tokens=100,
             original_execution_devices_unchanged=True,
             native_forward_source_inputs_and_KV_not_modified=True, CPU_forward_forbidden=True)
        emit("native_prefill_residency_completed", session=session, input_tokens=100,
             success=True, full_GPU_resident_before_decode=True,
             all_group_forward_parameters_BF16_on_original_GPU=True,
             native_attention_generation_inputs_outputs_and_cache_unmodified=True)
        emit("model_reply_sealed", request="requests/" + str(number).zfill(4),
             operation=op, seal_sha256="b" * 64)

    def end(run, request):
        emit("GUI_run_end", trajectory_id=run, request_id=request * 32,
             status="completed", terminal_receipt_sha256="c" * 64)

    begin("first-noaux", "1")
    primary(1, "first-noaux", "judge", 51, 1)
    end("first-noaux", "2")
    begin("second-aux", "3")
    emit("model_request", request="requests/0002", operation="evidence",
         trajectory_id="second-aux", decision_index=1, attempt_index=1, payload_sha256="d" * 64)
    for kind in ["to_auxiliary", "to_primary"]:
        emit("GPU_weight_residency_transition", kind=kind,
             all_actual_model_forwards_GPU_only=True, precision_unchanged="bfloat16",
             CPU_storage_only_no_CPU_inference=True)
    emit("model_reply_sealed", request="requests/0002", operation="evidence", seal_sha256="e" * 64)
    primary(3, "second-aux", "actor", 1, 2)
    end("second-aux", "4")
    return entries, queue, {"actor": 17, "judge": 50, "evidence": 0}


def chain(entries):
    rows, previous = [], "0" * 64
    for index, entry in enumerate(entries):
        value = dict(entry, seq=index, previous=previous, time=float(index))
        value["sha256"] = hashlib.sha256(canonical(value)).hexdigest()
        previous = value["sha256"]
        rows.append(value)
    return b"".join(canonical(value) + b"\n" for value in rows)


def run_checks():
    entries, queue, counts = fixture()
    results = []

    def accepted(name, records=entries, plan=queue, budget=counts):
        events, proof = verified_events(chain(records))
        value = map_requests(events, plan, budget)
        results.append({"case": name, "passed": True})
        return value, proof

    def rejected(name, mutation, target="entries"):
        records, plan, budget = copy.deepcopy(entries), copy.deepcopy(queue), copy.deepcopy(counts)
        mutation({"entries": records, "queue": plan, "counts": budget}[target])
        try:
            events, _ = verified_events(chain(records))
            map_requests(events, plan, budget)
        except (ValueError, KeyError):
            results.append({"case": name, "passed": True})
        else:
            raise AssertionError("Invalid accounting accepted: " + name)

    value, _ = accepted("primary_auxiliary_primary_with_track_reset")
    assert [r["primary_prefill_session"] for r in value["sealed_requests"]] == [1, None, 2]
    assert value["ended_runs"][0]["counts"] == {"actor": 17, "judge": 51, "evidence": 0}
    assert value["ended_runs"][1]["counts"] == {"actor": 1, "judge": 0, "evidence": 1}
    assert value["active_run"] is None and value["next_run_index"] == 2
    live, _ = accepted("live_same_request_not_terminal", entries[:3])
    assert live["pending_request"]["request"] == "0001" and not live["sealed_requests"]
    failed = copy.deepcopy(entries[:3])
    failed.append({"kind": "native_prefill_residency_failed_no_retry",
                   "data": {"session": 1, "input_tokens": 100, "success": False}})
    value, _ = accepted("failed_prefill_preserved_as_pending_not_reply", failed)
    assert value["pending_request"]["native_prefill_failed"] and not value["sealed_requests"]
    rejected("wrong_global_request_number", lambda e: e[11]["data"].update(request="requests/0004"))
    rejected("global_index_used_as_primary_session_after_aux", lambda e: e[12]["data"].update(session=3))
    rejected("auxiliary_consumed_primary_prefill_session", lambda e: e.insert(8, copy.deepcopy(e[2])))
    rejected("primary_prefill_start_missing", lambda e: e.pop(2))
    rejected("duplicate_primary_prefill_completion", lambda e: e.insert(4, copy.deepcopy(e[3])))
    rejected("failed_prefill_counted_as_successful_reply", lambda e: (
        e[3].update(kind="native_prefill_residency_failed_no_retry"), e[3]["data"].update(success=False)))
    rejected("second_track_counts_not_reset", lambda e: e[11]["data"].update(attempt_index=18))
    rejected("auxiliary_disabled_arm", lambda q: q[1].update(observer_enabled=False), "queue")
    rejected("missing_gpu_return_transition", lambda e: e.pop(9))
    rejected("reversed_gpu_transition", lambda e: e[8]["data"].update(kind="to_primary"))
    rejected("cpu_auxiliary_forward", lambda e: e[8]["data"].update(all_actual_model_forwards_GPU_only=False))
    rejected("changed_auxiliary_precision", lambda e: e[8]["data"].update(precision_unchanged="float16"))
    rejected("primary_restore_missing", lambda e: e[3]["data"].update(full_GPU_resident_before_decode=False))
    rejected("wrong_primary_token_binding", lambda e: e[3]["data"].update(input_tokens=99))
    rejected("wrong_first_carryover_attempt", lambda e: e[1]["data"].update(attempt_index=1))
    rejected("original_actor_budget_exceeded", lambda e: e[11]["data"].update(attempt_index=71))
    rejected("original_decision_cap_exceeded", lambda e: e[11]["data"].update(decision_index=51))
    rejected("wrong_request_run", lambda e: e[7]["data"].update(trajectory_id="first-noaux"))
    rejected("wrong_frozen_run_order", lambda e: e[6]["data"].update(trajectory_id="first-noaux"))
    rejected("duplicated_control_request_id", lambda e: e[6]["data"].update(request_id="1" * 32))
    rejected("duplicate_model_reply", lambda e: e.insert(5, copy.deepcopy(e[4])))
    rejected("end_with_unfinished_request", lambda e: e.pop(4))
    rejected("reply_from_different_request", lambda e: e[4]["data"].update(request="requests/0002"))
    rejected("continued_after_technical_terminal", lambda e: e[5]["data"].update(status="technical_failure"))
    try:
        verified_events(chain(entries).replace(b'"input_tokens":100', b'"input_tokens":101', 1))
    except ValueError:
        results.append({"case": "actual_hash_chain_tamper_rejected", "passed": True})
    else:
        raise AssertionError("Hash tamper accepted")
    partial = chain(entries[:3]) + b'{"seq":3'
    events, proof = verified_events(partial)
    assert len(events) == 3 and proof["incomplete_last_line"] is True
    assert map_requests(events, queue, counts)["pending_request"]["request"] == "0001"
    results.append({"case": "partial_live_tail_not_treated_as_terminal", "passed": True})
    return results


if __name__ == "__main__":
    checks = run_checks()
    print(json.dumps({"passed": True, "CPU_accounting_checks": len(checks), "checks": checks,
                      "model_GUI_scorer_calls": 0, "semantic_controls": 0}))
