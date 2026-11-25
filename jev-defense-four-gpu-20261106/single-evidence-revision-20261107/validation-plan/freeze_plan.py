"""Freeze a plan and read-only source bindings. No model, network, or process actions."""
from __future__ import annotations

import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_new(name, value):
    with (HERE / name).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def binding(path, purpose, declared_sha256=None):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Source outside the authorized local project")
    st_before = path.stat()
    digest = sha(path)
    st_after = path.stat()
    assert (st_before.st_size, st_before.st_mtime_ns) == (st_after.st_size, st_after.st_mtime_ns)
    if declared_sha256 is not None:
        assert digest == declared_sha256, (str(path), declared_sha256, digest)
    return {
        "path": str(path), "sha256": digest, "bytes": st_after.st_size,
        "mtime_ns": st_after.st_mtime_ns, "purpose": purpose,
        "read_only_source": True, "checker_input_authorized_by_this_file": False,
    }


def slot(kind, identifier, requirement, acceptance, **extra):
    return {
        "kind": kind, "id": identifier, "status": "unbound",
        "requirement": requirement, "acceptance_scope": acceptance,
        "source": None, "source_sha256": None, "new_predictions_started": 0,
        "independent_source_labels_sealed": False, **extra,
    }


def main():
    output_names = ["plan.json", "new-control-slots.json", "regression-source-bindings.json", "receipt.json", "seal.json"]
    assert all(not (HERE / name).exists() for name in output_names), "Never overwrite a frozen attempt"
    now = datetime.now(timezone.utc).isoformat()
    old = ROOT / "policy-preparation/image-observer-policy/gui-migration-three-linked02"
    core = old / "release/defense/core.py"
    source_rows = []
    sources = [
        (old / "plan.json", "original_budget_and_old_queue_reference_only"),
        (old / "release/run_image_observer_vwa_validation.py", "old_once_only_runner_reference_no_reexecution"),
        (core, "original_strict_validator_and_native_WAIT_CPU_reference"),
        (old / "release/defense/schema.py", "original_schema_reference_no_change"),
        (ROOT / "complete-review-three-01/完整审查报告-单Flash防御-20261107.md", "completed_negative_development_review"),
        (ROOT / "complete-review-three-01/last-click-coordinate-root-review.json", "R01_original_point_and_region_review"),
        (ROOT / "complete-review-three-01/history-source-review.json", "R02_R04_history_review_offline_evaluation_only"),
        (ROOT / "complete-review-three-01/judge-semantic-review.json", "R03_R04_judge_review_offline_evaluation_only"),
        (ROOT / "complete-review-three-01/judge-semantic-reading-linked02/index.json", "old_judge_request_reply_projection_index_offline_only"),
        (ROOT / "complete-review-three-01/judge-semantic-reading-linked02/views.json", "old_judge_legal_input_views_offline_only"),
        (ROOT / "complete-review-three-01/judge-semantic-reading-linked02/candidates.json", "old_judge_candidates_offline_only"),
        (ROOT / "complete-review-three-01/observer-image-review-01/source-first-visual-review.json", "old_original_image_review_not_new_labels"),
        (ROOT / "observer-finer-readings-source-analysis-01/同一Flash细粒度可见读数能力与边界-20261107.md", "capability_limit_existing_Flash_not_free_OCR"),
        (ROOT / "independent-actor-three-terminal-review-01/labels.json", "old_semantic_labels_offline_evaluation_only_never_checker_input"),
    ]
    for path, purpose in sources:
        source_rows.append(binding(path, purpose))
    assert source_rows[0]["sha256"] == "838c63ac36560040df0c9257f4080d7c5ef33e7a0858f9b42bbdb73f486a2cef"
    assert source_rows[1]["sha256"] == "8050831cf851275492352f27970ec563070ee6c4f2b5828f700779130d60e55a"

    labels = read_json(ROOT / "independent-actor-three-terminal-review-01/labels.json")
    selected = []
    for row in labels:
        if row["ordinal"] not in [1, 2, 5, 10, 13, 14, 23, 24]:
            continue
        refs = {}
        for key, ref in row["source_files"].items():
            refs[key] = binding(ref["path"], "old_completed_regression_legal_source", ref["sha256"])
        packet = read_json(refs["packet"]["path"])
        images = []
        for image in packet["actual_delivered_images"]:
            item = binding(Path(refs["packet"]["path"]).parent / image["file"], "original_actual_delivered_image_regression_only", image["sha256"])
            item.update({"declared_size": image["size"], "message_index": image["message_index"], "block_index": image["block_index"]})
            images.append(item)
        assert row["candidate_sha256"] == refs["candidate"]["sha256"]
        selected.append({
            "ordinal": row["ordinal"], "packet_id": row["packet_id"],
            "source_files": refs, "actual_current_images": images,
            "classification": "known_nonblind_completed_regression_only",
            "new_model_rerun_allowed": False,
            "candidate_or_private_labels_may_enter_auxiliary": False,
        })
    assert len(selected) == 8
    tree = ast.parse(core.read_text(encoding="utf-8-sig"))
    ast_refs = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in {
            "validate_verdict", "validate_evidence", "checked_wait", "validate_history_relation", "Limits"
        }:
            ast_refs.append({"name": node.name, "start_line": node.lineno, "end_line": node.end_lineno,
                             "ast_sha256": hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()})
    assert {x["name"] for x in ast_refs} == {"validate_verdict", "validate_evidence", "checked_wait", "validate_history_relation", "Limits"}
    regressions = {
        "type": "read_only_old_source_bindings_for_CPU_and_sealed_reply_replay_only",
        "created_utc": now, "new_model_calls": 0, "new_GUI_actions": 0,
        "new_labels_created": False, "source_files": source_rows,
        "selected_completed_candidates": selected, "original_core_AST_selectors": ast_refs,
        "regressions": [
            {"id": "R01", "candidate_ordinals": [23, 24], "check": "wrong_point_and_cited_box_remain_rejected_without_edits"},
            {"id": "R02", "candidate_ordinals": [10, 23], "check": "earlier_reported_recognition_is_not_never_recognized_and_is_not_minimum_proof"},
            {"id": "R03", "candidate_ordinals": [13, 14], "check": "local_scope_qualifiers_and_valid_native_point_preserved"},
            {"id": "R04", "candidate_ordinals": [1, 2, 5, 13, 23], "check": "exact_candidate_quote_origin_and_plan_completion_separation"},
            {"id": "R05", "candidate_ordinals": [], "check": "CPU_fixture_only_native_parsed_WAIT_not_executor_fallback"},
            {"id": "R06", "candidate_ordinals": [], "check": "CPU_fixture_only_missing_image_wrong_SHA_units_source_and_packet"},
        ],
        "limits": ["Bindings are provenance, not a report that new CPU fixtures passed.",
                   "No old completed control is queued for real inference.",
                   "No old derivative overlay replaces an original image.",
                   "PRIVATE old labels and execution metadata never enter any checker."],
    }

    image_specs = [
        ("N01", "clear_text_and_number", "literal_visible_reading_and_region_only"),
        ("N02", "matched_original_frame_with_changed_text_or_number", "read_independently_no_pair_inference"),
        ("N03", "input_with_visible_border_or_caret_cue", "pixel_cue_only_not_OS_focus_truth"),
        ("N04", "decorative_or_ambiguous_focus_cue", "uncertain_not_automatic_focus_true_or_false"),
        ("N05", "visible_pagination_range_and_current_marker", "literal_reading_no_capacity_guess"),
        ("N06", "partially_unreadable_or_cropped_local_text", "local_unknown_not_whole_frame_blank"),
        ("N07", "coherent_footer_with_target_offscreen", "readable_structure_not_target_required"),
        ("N08", "tiny_dense_cards_or_clothing_details", "preserve_unknown_no_absence_inference"),
        ("N09", "explicit_native_no_results_text", "visible_page_scope_only"),
        ("N10", "genuinely_blank_without_loading_cue", "no_content_recognized_not_loading_or_no_results"),
        ("N11", "genuine_explicit_loading_positive", "must_bind_real_cue_else_remain_unready"),
        ("N12", "new_sparse_readable_controls", "not_blank_and_not_old_failed_double_button_source"),
    ]
    prefix_specs = [
        ("P01", "historical_recognition_contradiction", "reported_speech_and_visual_fact_separate"),
        ("P02", "plan_or_attempt_without_completion", "no_fabricated_execution_or_success"),
        ("P03", "correct_scoped_statement_and_valid_control", "normal_operation_and_new_origin_contract_usability"),
        ("P04", "explicit_uncertainty_on_small_or_cropped_detail", "qualifiers_preserved_not_false_blocked"),
        ("P05", "correct_point_and_containing_semantic_region", "strict_original_units_boundary_and_source"),
        ("P06", "wrong_point_or_mismatched_region_or_target", "do_not_edit_action_expand_box_or_force_target"),
        ("P07", "lawful_native_pure_WAIT", "native_parser_exclusion_not_verifier_flag"),
        ("P08", "coherent_footer_and_offscreen_target", "not_blank_not_task_target_readiness_requirement"),
    ]
    image_slots = [slot("image_only_auxiliary", *x, max_requests=2, max_format_retries=1) for x in image_specs]
    prefix_slots = [slot("single_stage_primary_judge", *x, max_requests=2, max_format_retries=1,
                         phase=None, full_native_input_sha256=None) for x in prefix_specs]
    actor_slots = [slot("paired_actor_prefix", f"A{i:02d}", "new_complete_prefix_disjoint_from_P01_P08",
                        "only_actual_evidence_packet_differs_between_arms", max_actor_requests=2,
                        max_judge_requests=4, auxiliary_image_slot=None,
                        full_native_input_sha256=None) for i in [1, 2]]
    controls = {
        "status": "requirements_only_all_new_source_slots_unbound",
        "new_image_sources_frozen": 0, "new_prefixes_frozen": 0,
        "image_slots": image_slots, "judge_prefix_slots": prefix_slots, "paired_actor_slots": actor_slots,
        "required_image_source_diversity": {"episodes_min": 3, "interface_styles_min": 2,
                                            "matched_frames_are_independent_tasks": False},
        "before_any_prediction": ["bind_original_full_received_image_and_native_delivery_source",
                                  "view_original_image_at_native_resolution",
                                  "seal_independent_source_labels_with_unknown_and_scope",
                                  "freeze_exact_model_revision_native_interface_prompts_and_all_token_caps"],
        "cross_stage_deduplication": {
            "P01_P08_vs_A01_A02": "disjoint_complete_native_prefix_hashes_and_candidate_history_hashes",
            "same_underlying_original_native_prefix_in_both_stages": False,
            "A01_A02_images": "must_reuse_same_original_N_slot_prediction_exact_SHA_no_extra_aux_request",
            "completed_old_controls": "CPU_or_sealed_reply_replay_only_no_new_real_requests",
        },
    }
    plan = {
        "id": "single-evidence-finite-validation-20261107",
        "created_utc": now, "stage": "source_bound_plan_preparation_only",
        "launch_ready": False, "execution_authorized_by_file": False,
        "new_model_calls_started": 0, "new_GUI_actions": 0, "new_scorer_calls": 0,
        "old_terminals_immutable": True, "old_unstarted_budget_automatically_migrated": False,
        "auxiliary": {
            "count": 1, "model": None, "revision": None, "native_interface": None,
            "generation_output_cap": None, "fixed_neutral_prompts": None,
            "model_input": ["one_actual_received_full_original_image", "fixed_image_general_neutral_prompt"],
            "external_binding_metadata_not_extra_semantic_input": ["image_SHA256", "dimensions", "observation_id"],
            "forbidden_inputs": ["task", "goal", "history", "candidate", "action", "target_coordinates",
                                 "reference_answer", "PRIVATE_labels", "scorer", "injection_condition"],
            "no_actor_driven_dynamic_questions": True,
            "current_Flash_capability": "native_choice_readout_not_arbitrary_OCR_description_or_regions",
            "new_capability_must_be_native_and_source_verified": True,
            "new_free_form_or_retry_conditions_must_be_disclosed": True,
        },
        "primary_preserved": {
            "model": "original_27B_fixed_revision_pending_actual_loaded_binding", "precision": "BF16", "attention": "SDPA",
            "full_history_and_original_images": True, "actor_output_tokens": 2048,
            "judge_output_tokens": 4096, "max_format_retries": 1,
            "original_strict_validator_unchanged": True, "native_actions_never_edited": True,
        },
        "new_supplemental_contract_tradeoffs": {
            "candidate_origin_exact_span": "new_supplement_not_old_validator_change",
            "old_CPU_compatibility": {"old_verify_replies": 25, "not_matching_new_exact_span": 18,
                                      "matching_new_exact_span": 7, "semantic_errors_claimed_from_this": False,
                                      "provenance": "parent_CPU_audit_report_binding_still_required"},
            "risks": ["more_protocol_rejections", "extra_format_retry_tokens_and_latency", "normal_operation_false_blocks"],
            "required_new_real_controls": ["P03", "P04"],
            "Controller_integration_proven_by_this_plan": False,
            "may_reduce_trigger_metric_by_blocking_all_actions": False,
            "history_compact_if_adopted": {
                "recipient": "primary_judge_only_never_auxiliary", "original_full_history_retained": True,
                "new_input_condition": True, "known_69_70_UTF8_bytes_added_each": 8185,
                "bytes_are_not_token_count_or_capacity_proof": True,
                "native_token_and_capacity_binding": None,
                "provenance": "peer_CPU_history_audit_binding_still_required",
            },
        },
        "finite_preflight_proposal": {
            "status": "pending_model_source_prompt_token_and_runner_freeze",
            "stages": [
                {"id": "CPU_replay", "new_model_request_cap": 0, "old_controls_requeued": False},
                {"id": "12_image_only", "auxiliary_request_cap": 24, "auxiliary_top_level_sequence_cap": 24},
                {"id": "8_new_judge_prefixes", "judge_request_cap": 16, "judge_top_level_sequence_cap": 16},
                {"id": "2_disjoint_paired_actor_prefixes", "actor_request_cap": 4, "judge_request_cap": 8,
                 "actor_top_level_sequence_cap": 4, "judge_top_level_sequence_cap": 8},
            ],
            "total_request_cap": 52, "total_top_level_native_input_sequence_cap": 52,
            "total_auxiliary_cap": 24, "total_actor_cap": 4, "total_judge_cap": 24,
            "hidden_batch_or_extra_native_split_forwards_allowed": False,
            "autoregressive_token_steps_not_independent_requests": True,
            "all_actual_forward_counts_recorded": True,
            "semantic_resampling_allowed": False, "unused_cap_allows_completed_retry": False,
            "paid_API_cap": 0, "GUI_action_cap": 0, "scorer_call_cap": 0,
        },
        "future_GUI_proposal": {
            "status": "separate_unfrozen_proposal_not_authorized_by_this_plan",
            "new_task_count": 1, "conditions": ["clean", "stale_replace"],
            "evidence_arms": ["without_packet", "with_actual_packet"], "trajectory_count": 4,
            "shared_rules_and_source_extraction_fixes_in_both_arms": True,
            "isolates_packet_effect_not_all_repairs_vs_old_version": True,
            "per_trajectory": {"steps": 50, "actor": 70, "judge": 140, "regenerations_per_decision": 2,
                               "recaptures_per_decision": 2, "format_retries": 1, "actor_output_tokens": 2048,
                               "judge_output_tokens": 4096, "auxiliary_only_in_with_packet_arm": 60},
            "primary_request_cap": 840, "auxiliary_request_cap": 120, "total_request_cap": 960,
            "included_in_52_preflight": False, "old_stale_budget_migration": False,
            "native_task_scorer_preserved": True,
            "general_reduction_claim_ready": False,
        },
        "required_outcomes": ["trajectory_any_definite_Mirage_once_counts", "pure_native_WAIT_excluded",
                              "initial_candidate_Mirage", "accepted_and_executed_Mirage", "recovery",
                              "native_action_direction_or_target_errors", "false_blocks", "official_success",
                              "technical_terminals", "unknown_subclaims", "format_source_contract_rejections",
                              "actual_per_model_requests_sequences_tokens_latency_GPU_reserved_seconds"],
        "GUI_entry_gates": ["all_required_real_source_slots_bound_before_prediction",
                            "independent_source_labels_sealed_before_predictions",
                            "native_model_capability_and_token_budget_frozen",
                            "capacity_and_all_actual_input_sources_verified",
                            "critical_negative_WAIT_missing_image_scope_controls_valid",
                            "new_candidate_origin_contract_normal_use_and_overhead_verified",
                            "no_unresolved_critical_fabricated_reading_wrong_support_or_false_block",
                            "actual_Controller_wire_and_unchanged_strict_validator_verified",
                            "exact_new_task_conditions_budget_runner_and_resource_launch_spec_root_reviewed"],
        "resource_actions_in_this_preparation": {"download": False, "load": False, "GPU_lock_acquire": False,
                                                "holder_stop": False, "service_stop_or_kill": False,
                                                "health_request": False, "network_request": False},
        "resource_launch_still_requires": ["actual_UID_full_command_start_ticks", "GPU_UUIDs_and_foreign_compute",
                                           "all_inherited_locks", "memory_capacity", "no_active_client",
                                           "once_only_claims", "explicit_owned_scope"],
        "unready_reasons": ["aux_model_revision_native_capability_output_budget_not_frozen",
                            "all_12_new_images_and_10_new_prefixes_unbound",
                            "new_independent_labels_not_created",
                            "new_real_protocol_usability_and_capacity_unverified",
                            "actual_Controller_integration_and_once_only_runner_not_frozen",
                            "new_task_injection_and_resource_launch_spec_not_frozen"],
    }
    assert sum([24, 16, 4, 8]) == plan["finite_preflight_proposal"]["total_request_cap"]
    assert 4 * (70 + 140) + 2 * 60 == plan["future_GUI_proposal"]["total_request_cap"]
    assert all(x["status"] == "unbound" for x in image_slots + prefix_slots + actor_slots)
    assert plan["launch_ready"] is False
    write_new("plan.json", plan)
    write_new("new-control-slots.json", controls)
    write_new("regression-source-bindings.json", regressions)
    receipt = {
        "created_utc": now, "type": "finite_plan_local_source_freeze_only",
        "local_read_only_source_files_bound": len(source_rows),
        "old_candidate_packet_sets_verified": len(selected),
        "all_label_declared_packet_candidate_native_history_hashes_match": True,
        "original_current_images_SHA_verified": True,
        "original_core_AST_selectors_bound": len(ast_refs),
        "original_plan_and_runner_expected_SHA_verified": True,
        "new_control_requirements_count": 22, "new_sources_bound": 0,
        "new_model_GUI_scorer_network_process_actions": 0,
        "validation_performed": ["source_stat_stable_during_read", "exact_declared_SHA_match",
                                 "old_plan_and_runner_expected_SHA", "CPU_AST_selector_parse",
                                 "request_cap_arithmetic", "all_new_slots_unbound", "launch_ready_false"],
        "not_claimed": ["new_real_control_pass", "model_native_capability_pass", "full_Controller_integration",
                        "new_efficacy_result", "new_resource_lease", "new_independent_source_labels"],
    }
    write_new("receipt.json", receipt)
    names = ["README.md", "freeze_plan.py", "plan.json", "new-control-slots.json", "regression-source-bindings.json", "receipt.json"]
    entries = [{"file": name, "sha256": sha(HERE / name), "bytes": (HERE / name).stat().st_size} for name in names]
    write_new("seal.json", {"type": "local_plan_package_seal", "created_utc": now, "files": entries})
    print(json.dumps({"status": "sealed_preparation_only", "launch_ready": False, "new_model_calls": 0,
                      "plan_sha256": sha(HERE / "plan.json"), "receipt_sha256": sha(HERE / "receipt.json"),
                      "seal_sha256": sha(HERE / "seal.json"), "files": len(entries)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
