"""Source-derived CPU adversarial checks, never new model/GUI trials."""
import copy
from primary_receipt_checks import check_primary_receipts
from auxiliary_receipt_checks import canonical, digest


def run_checks(original):
    require_operations = {"actor", "judge"}
    assert set(original) == require_operations
    compatibility = {op: check_primary_receipts(**arguments) for op, arguments in original.items()}
    checks = [{"case": "original_" + op + "_native_receipts_read_not_regenerated", "passed": True}
              for op in original]

    # Deliberately derived fixture: a global mixed index may differ from the
    # primary-only session. This does not stand in for a real auxiliary request.
    synthetic = copy.deepcopy(original["actor"])
    synthetic["mapped_request"]["request"] = "9001"
    synthetic["response"]["receipt"] = synthetic["response"]["receipt"].rsplit("/", 1)[0] + "/9001"
    assert check_primary_receipts(**synthetic)["primary_prefill_session"] != 9001
    checks.append({"case": "synthetic_mixed_index_does_not_select_primary_session", "passed": True,
                   "not_actual_auxiliary_or_new_model_control": True})

    def reject(name, operation, mutation):
        data = copy.deepcopy(original[operation])
        mutation(data)
        try:
            check_primary_receipts(**data)
        except (ValueError, KeyError, TypeError, IndexError):
            checks.append({"case": name, "passed": True, "not_new_model_or_GUI_control": True})
        else:
            raise AssertionError("Invalid native receipt accepted: " + name)

    reject("different_run", "actor", lambda d: d["mapped_request"].update(trajectory_id="other"))
    reject("different_original_call_budget", "actor", lambda d: d["mapped_request"].update(original_track_attempt_index=1))
    reject("different_decision", "actor", lambda d: d["mapped_request"].update(decision=1))
    reject("auxiliary_routed_to_primary_audit", "actor", lambda d: d["mapped_request"].update(operation="evidence"))
    reject("different_request_sealed_response", "actor", lambda d: d["response"].update(request_id="f" * 32))
    reject("different_native_message_SHA", "actor", lambda d: d["native_call"].update(request_messages_sha256="a" * 64))
    reject("different_actual_input_ID", "actor", lambda d: d["native_call"]["input_ids"].__setitem__(0, 0))
    reject("different_first_forward_pixel_SHA", "actor", lambda d: d["first_forward"]["pixel_values"].update(sha256="b" * 64))
    reject("omitted_native_input_tensor", "actor", lambda d: d["first_forward"].pop("attention_mask"))
    reject("different_full_binary_SHA_authority", "actor", lambda d:
        d["verified_file_SHA256"].update({d["prepared"]["pixel_values"]["file"]: "c" * 64}))
    reject("incorrect_complete_image_grid_count", "actor", lambda d: d["prepared"]["image_grid_thw"].update(shape=[1, 3]))
    reject("changed_original_generation_default", "actor", lambda d: d["effective_generation"].update(top_p=0.5))
    reject("changed_generation_numeric_type", "actor", lambda d: d["effective_generation"].update(temperature=0))
    reject("changed_original_output_budget", "actor", lambda d: d["effective_generation"].update(max_new_tokens=4096))
    reject("actor_grammar_constrained", "actor", lambda d: d["native_call"].update(verifier_grammar={"schema": {}}))
    reject("different_output_IDs", "actor", lambda d: d["actual_generation"]["output_ids"].__setitem__(0, 0))
    reject("different_returned_sequence", "actor", lambda d: d["sequence_ids"][0].__setitem__(0, 0))
    reject("different_returned_sequence_binary_SHA", "actor", lambda d:
        d["verified_file_SHA256"].update({"sequence_ids.tensor": "d" * 64}))
    reject("EOS_not_natural", "actor", lambda d: d["actual_generation"].update(natural_EOS=False))
    reject("native_cap_not_a_success", "actor", lambda d: d["native_call"].update(hit_output_cap=True))
    reject("different_independent_decode", "actor", lambda d: d.update(independently_decoded_native_output="altered native text"))
    reject("wrong_prefill_session", "actor", lambda d: d["mapped_request"].update(primary_prefill_session=9001))
    reject("different_prefill_input_length", "actor", lambda d: d["prefill"].update(input_tokens=10))
    reject("different_prefill_completed_event", "actor", lambda d:
        d["mapped_request"].update(prefill_completion_event_sha256="e" * 64))
    reject("different_original_device_map", "actor", lambda d:
        d["expected_device_map"].update({"model.language_model.layers.0": 3}))
    reject("different_source_group_order", "actor", lambda d: d["expected_group_order"].reverse())
    reject("missing_actual_forward_record", "actor", lambda d: d["forward_count"].update(first_forward_recorded=False))
    reject("different_actual_forward_count", "actor", lambda d: d["forward_count"].update(actual_forward_calls=9999))
    reject("nonfinite_native_timer", "actor", lambda d: d["native_call"].update(seconds=float("inf")))

    def changed_prefill(data, mutate):
        mutate(data["prefill"])
        data["prefill_completion_event"]["data"] = copy.deepcopy(data["prefill"])
        event = dict(data["prefill_completion_event"])
        event.pop("sha256")
        data["prefill_completion_event"]["sha256"] = digest(canonical(event))
        data["mapped_request"]["prefill_completion_event_sha256"] = data["prefill_completion_event"]["sha256"]

    reject("source_resigned_missing_GPU_restore", "actor", lambda d: changed_prefill(d,
        lambda p: p.update(full_GPU_resident_before_decode=False)))
    reject("source_resigned_missing_move", "actor", lambda d: changed_prefill(d, lambda p: p["moves"].pop()))
    reject("source_resigned_wrong_execution_device", "actor", lambda d: changed_prefill(d,
        lambda p: p["moves"][69].update(device="cpu")))
    reject("source_resigned_duplicate_prefill_group", "actor", lambda d: changed_prefill(d,
        lambda p: p["visited_groups"].append(p["visited_groups"][0])))
    reject("different_verifier_native_schema", "judge", lambda d: d.update(expected_verifier_schema={}))
    reject("different_verifier_grammar_engine", "judge", lambda d: d["native_call"]["verifier_grammar"].update(engine="other"))
    reject("different_verifier_schema_SHA", "judge", lambda d:
        d["native_call"]["verifier_grammar"].update(schema_sha256="f" * 64))
    reject("different_verifier_decode", "judge", lambda d: d.update(independently_decoded_native_output="{}"))
    return {"passed": True, "actual_compatibility": compatibility, "checks": checks, "count": len(checks),
            "actual_auxiliary_or_multitrack_execution_proven": False,
            "new_model_GUI_scorer_calls": 0}
