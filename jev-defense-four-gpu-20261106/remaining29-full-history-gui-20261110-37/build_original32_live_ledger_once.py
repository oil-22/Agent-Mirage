"""Bind the frozen32 plan to immutable prior endpoints and the current live prefix.

This is downstream evaluation only. It does not start experiments, add labels,
infer negatives from incomplete exposure, or modify the frozen runtime package.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import time

from orchestrate import HERE, save, sha
from join_source_reviews import verify_seal


def read(path):
    return json.loads(path.read_bytes())


def main(evidence):
    assert evidence.parent == HERE
    evidence_seal = verify_seal(evidence)
    service, gui = read(evidence / '3090.json'), read(evidence / '4090.json')
    worker, runner = service['worker/process.json']['actual'], gui['control/runner-process.json']['actual']
    assert (worker['pid'], worker['uid'], worker['start_ticks']) == (252807, 1033, '1191243649')
    assert (runner['pid'], runner['uid'], runner['start_ticks']) == (3333015, 1015, '127695701')
    assert HERE.name in worker['command'] and HERE.name in runner['command']
    assert len(service['held_locks']) == 9
    state = service['worker/status.json']['value']
    active = state['active']
    assert active == 'fullhistory23-T000-stale_replace-noaux'
    assert state['done'] == [] and service['journal']['counts']['GUI_run_begin'] == 1
    assert len(gui['GUI_event_chains']) == 1
    assert all(row['trajectory_id'] == active for row in service['sealed_requests'])
    assert service['worker/terminal.json'] is None and gui['control/exit.json'] is None
    manifest_sha = sha(HERE / 'runtime-package/manifest.json')
    assert manifest_sha == '368b0a594822f5e294fcd21927aa924a18a80f23249f160857b5de7090c1c02d'
    preparation = HERE.parent / 'remaining29-primary-outcome-staging-20261110-35/preparation-1794281890507436600'
    preparation_seal = verify_seal(preparation)
    plan_path = preparation / 'original-full32-plan.json'
    assert sha(plan_path) == '51e35415fc7df2d0309e67f117310de8ecffd59b51ece6bcfdda176e5ae4f98c'
    plan, exclusions = read(plan_path), read(preparation / 'terminal-exclusions.json')
    queue, excluded = plan['queue'], {row['run_id']: row for row in exclusions}
    assert len(queue) == 32 and len(excluded) == 3 and active not in excluded
    pending_queue = read(preparation / 'remaining29-queue.json')['queue']
    assert pending_queue == [row for row in queue if row['run_id'] not in excluded]
    assert len(pending_queue) == 29 and pending_queue[0]['run_id'] == active
    prior_path = HERE.parent / 'remaining-full-history-gui-20261110-33/closed-terminal-publication-linked02-1794280835290980000/status.json'
    prior_seal = verify_seal(prior_path.parent)
    assert sha(prior_path) == '71c250b00b2ba5d959412905c88a013d1b80c59fddc76a9afcb75a08214d3154'
    prior = read(prior_path)
    authorities = prior['authorities']
    verified_folders = {}

    def verify(folder, expected=None):
        folder = folder.resolve()
        if folder not in verified_folders:
            verified_folders[folder] = verify_seal(folder)
        actual = verified_folders[folder]
        assert expected is None or actual == expected
        return actual

    candidates, source_authorities = defaultdict(list), []
    original38 = authorities['original38_source_ledger']
    first_root = Path(original38['root'])
    verify(first_root, original38['seal_sha256'])
    assert sha(first_root / 'ledger.json') == original38['ledger_sha256']
    first = read(first_root / 'ledger.json')
    assert first['run_id'] == 'fullhistory23-T000-clean-noaux' and len(first['rows']) == 38
    for row in first['rows']:
        origin = row['review_authority']
        review_path = Path(origin['path'])
        verify(review_path.parent, origin['seal_sha256'])
        assert sha(review_path) == origin['sha256']
        assert sha(Path(row['source_packet_path'])) == row['source_packet_sha256']
        candidates[first['run_id']].append(dict(candidate_id=row['candidate_id'],
            pure_native_WAIT=row['pure_native_WAIT'], definite_semantic_Mirage=row['definite_semantic_Mirage'],
            original_source_review=origin, original_source_packet_sha256=row['source_packet_sha256'],
            unresolved_subclaims=row['unresolved_semantic_subclaims'],
            native_action_error=row['native_action_target_or_direction_error']))
    source_authorities.append(original38)

    def add_review(authority):
        folder = Path(authority['review'])
        verify(folder, authority['seal_sha256'])
        assert sha(folder / 'review.json') == authority['review_sha256']
        review = read(folder / 'review.json')
        assert review['independent_current_checker_execution_score_join_not_performed']
        for label in review['rows']:
            packet_path = Path(label['public_source_packet'])
            collection = packet_path.parent.parent
            verify(collection)
            assert sha(packet_path) == label['packet_sha256']
            packet = read(packet_path)
            assert packet['checker_labels_current_acceptance_execution_scoring_private_delivery_excluded']
            assert packet['candidate_event_sha256'] == label['candidate_event_sha256']
            assert hashlib.sha256(packet['candidate'].encode()).hexdigest() == label['candidate_text_sha256']
            # This PRIVATE mapping is read only after source-label sealing. It is
            # downstream evaluation provenance and never supplied to a checker.
            index = read(collection / 'PRIVATE-source-index.json')
            mapping = next(row for row in index if row['id'] == label['id'])
            assert mapping['candidate_text_sha256'] == label['candidate_text_sha256']
            assert mapping['actor_request_body_sha256'] == label['actor_request_body_sha256']
            run = PurePosixPath(mapping['attempt']).parent.name
            assert run in {row['run_id'] for row in queue}
            candidates[run].append(dict(candidate_id=label['candidate_event_sha256'],
                pure_native_WAIT=label['pure_native_WAIT_excluded'],
                definite_semantic_Mirage=label['candidate_semantic_mirage'],
                original_source_review=authority, original_source_packet_sha256=label['packet_sha256'],
                unresolved_subclaims=label.get('unresolved_subclaims', label.get('uncertain_subclaims', [])),
                native_action_error=label['native_action_error']))
        source_authorities.append(authority)

    for authority in authorities['all_current_source_reviews']:
        add_review(authority)
    current_authorities = []
    for pointer in sorted(HERE.glob('source-review-*-created.json')):
        if re.fullmatch(r'source-review-\d+-created\.json', pointer.name):
            authority = read(pointer)
            add_review(authority)
            current_authorities.append(authority)
    assert len(candidates['fullhistory23-T000-clean-aux']) == 15
    assert len(candidates['fullhistory23-T000-stale_replace-aux']) == 16
    live_counts = gui['GUI_event_chains'][0]['counts']
    assert len(candidates[active]) <= live_counts['candidate']
    replay_authority = authorities['original_terminal_replay']
    replay_root = Path(replay_authority['root'])
    verify(replay_root, replay_authority['seal_sha256'])
    assert sha(replay_root / 'receipt.json') == replay_authority['receipt_sha256']
    replay = read(replay_root / 'receipt.json')
    assert replay['passed'] and replay['classification_replay']['termination_axis'] == 'local_verifier_budget_terminal'
    terminal_evidence, records, ledger = [], [], []
    for planned in queue:
        run = planned['run_id']
        rows = candidates.get(run, [])
        assert len({row['candidate_id'] for row in rows}) == len(rows)
        record = dict(run_id=run, status='pending', candidates=rows, source_review_complete=False,
            official_score=None, executed_actions=0, actor_calls=0,
            any_definite_false_rejection=None, false_rejection_assessment_complete=False)
        entry = dict(**planned, exposure_state='never_started', terminal_receipt=None,
            raw_recorded_official_reward=None, analysis_official_score=None,
            original_source_labels_unchanged=True, source_reviewed_candidates=len(rows),
            definite_positive_candidates=sum(row['definite_semantic_Mirage'] is True and not row['pure_native_WAIT'] for row in rows),
            unknown_candidate_labels=sum(row['definite_semantic_Mirage'] is None and not row['pure_native_WAIT'] for row in rows),
            false_rejection_assessment='unresolved', accepted_executed_errors='requires separate verified outcome join',
            source_contract='approved decoded-native-answer source representation; runtime v4.0.12',
            cost_measurement_scope='Actual per-model calls and independently audited request timers/tokens; no walltime/currency/energy inference')
        if run in excluded:
            ex = excluded[run]
            terminal_path = HERE / 'runtime-package' / ex['copy']
            assert sha(terminal_path) == ex['sha256'] == sha(Path(ex['raw']))
            assert sha(Path(ex['semantic_authority'])) == ex['semantic_authority_sha256'] == sha(prior_path)
            collection = ex['collection_authority']
            collection_root = Path(collection['collection'])
            verify(collection_root, collection['seal_sha256'])
            assert sha(collection_root / 'receipt.json') == collection['receipt_sha256']
            terminal = read(terminal_path)
            assert terminal['run'] == planned
            assert len(rows) == terminal['actor_calls']
            technical = terminal['technical_status'] == 'verifier_failure'
            if run == first['run_id']:
                assert ex['sha256'] == replay['original_terminal_sha256']
                technical = False
                record['any_definite_false_rejection'] = replay['candidate_level_normal_operation_false_rejection_lower_bound'] > 0
                entry['classification_replay'] = replay_authority
                entry['original_raw_technical_category_preserved'] = terminal['technical_status']
                entry['termination_axis'] = 'local_verifier_budget_terminal'
            raw_score = terminal['official_reward']
            assert raw_score in [0.0, 1.0] and terminal['scoring_status'] == 'complete'
            record.update(status='technical_failure' if technical else 'completed', source_review_complete=True,
                official_score=None if technical else int(raw_score),
                executed_actions=terminal['environment_actions'], actor_calls=terminal['actor_calls'])
            entry.update(exposure_state='immutable_technical_terminal' if technical else 'immutable_budget_or_model_terminal',
                terminal_receipt=dict(path=str(terminal_path), sha256=ex['sha256'], original_authority=collection),
                raw_recorded_official_reward=raw_score, analysis_official_score=record['official_score'],
                technical_failure_not_model_zero=technical,
                original_outcome=terminal['outcome'], original_technical_status=terminal['technical_status'],
                decisions=terminal['decisions'], environment_actions=terminal['environment_actions'],
                actual_call_counts=ex['counts'], source_contract='original immutable pre-v4.0.12 endpoint',
                all_original_candidate_records_covered=True,
                original_candidate_unknowns_remain=True, original_terminal_never_rewritten_or_rerun=True)
            terminal_evidence.append(ex)
        elif run == active:
            record.update(actor_calls=state['counts']['actor'], executed_actions=live_counts['action_executed'])
            entry.update(exposure_state='verified_live', actual_process_evidence=str(evidence),
                actual_call_counts=state['counts'], environment_actions=live_counts['action_executed'],
                all_candidate_events_at_snapshot=live_counts['candidate'],
                all_original_candidate_records_covered=len(rows) == live_counts['candidate'],
                completed_trajectory_or_negative_not_inferred_from_reviewed_prefix=True)
        else:
            assert not rows
            entry['zero_exposure_provenance'] = 'Inspected sole GUI begin/active chain and all sealed request trajectory IDs; remaining original plan order preserved.'
        records.append(record)
        ledger.append(entry)
    module_path = HERE.parent / 'prefill-scheduled-full-history-gui-20261109-32/matched_outcome_analysis.py'
    spec = importlib.util.spec_from_file_location('frozen32_math_without_new_labels', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    analysis = module.analyze(plan, records, resample=False)
    for entry, record in zip(ledger, records):
        entry['trajectory_any_definite_Mirage'] = module.endpoint(record)
    assert analysis['planned_tracks'] == 32 and analysis['planned_pairs'] == 16 and analysis['unique_tasks'] == 8
    assert analysis['primary']['relative_reduction_point'] is None
    assert not analysis['numeric_development_target_pattern_supported']
    assert sum(row['exposure_state'] == 'never_started' for row in ledger) == 28
    assert sum(row['exposure_state'] == 'verified_live' for row in ledger) == 1
    folder = HERE / ('original32-live-ledger-' + str(time.time_ns()))
    folder.mkdir()
    (folder / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(folder / 'records-for-unchanged-math.json', records)
    save(folder / 'descriptive-analysis.json', analysis)
    save(folder / 'ledger.json', dict(schema='source-bound-original32-live-ledger-v1', time=time.time(),
        original_scope=dict(tracks=32, matched_pairs=16, selected_tasks=8), original_full32_plan_sha256=sha(plan_path),
        preparation=str(preparation), preparation_seal_sha256=preparation_seal,
        analysis_contract_sha256=sha(preparation / 'primary-outcome-analysis-contract.json'),
        historic_source_decision_pending_superseded_by_real_approval_and_live_frozen_runtime=True,
        approved_runtime_manifest_sha256=manifest_sha,
        original_three_terminal_authority=str(prior_path), original_three_terminal_authority_sha256=sha(prior_path),
        original_three_terminal_authority_seal_sha256=prior_seal,
        original_terminal_evidence=terminal_evidence, source_review_authorities=source_authorities,
        private_mapping_is_downstream_evaluation_only_never_checker_input=True,
        actual_live_evidence=str(evidence), actual_live_evidence_seal_sha256=evidence_seal,
        worker=worker, GUI_runner=runner, held_locks=9, rows=ledger,
        exposure_states=dict(Counter(row['exposure_state'] for row in ledger)),
        original16_pairs_primary_14_wholly_prospective_pairs_only_version_stratum=True,
        selected_tasks_not_random_population_and_conditions_within_task_correlated=True,
        source_selected_single_reviewer_legal_feedback_not_fully_blind=True,
        unknowns_remain_in_original_denominators_no_candidate_count_rate=True,
        prior_technical_raw_score0_preserved_separately_from_analysis_unknown=True,
        no_auxiliary_recognition_accuracy_or_official_score_used_as_Mirage_label=True,
        previous_goal_turn_classification='progress: prior native24/source06 evidence; intervening configuration answer was read-only, not goal progress',
        current_goal_turn_classification='progress: actual request32/source07 and executed sort evidence; complete original32 live ledger connected to frozen matched math',
        goal='active', efficacy_established=False, relative_Mirage_reduction=None,
        math_module_sha256=sha(module_path), source_bound_companion_review_not_complete=True,
        new_model_GUI_capture_action_scorer_calls=0, frozen_runtime_unchanged=True))
    save(folder / 'seal.json', {path.name: sha(path) for path in folder.iterdir() if path.is_file()})
    result = dict(root=str(folder), ledger_sha256=sha(folder / 'ledger.json'),
        analysis_sha256=sha(folder / 'descriptive-analysis.json'), seal_sha256=sha(folder / 'seal.json'),
        original_scope=dict(tracks=32, matched_pairs=16, selected_tasks=8),
        exposure_states=dict(Counter(row['exposure_state'] for row in ledger)),
        primary_effect_estimate=None, efficacy_established=False, new_model_GUI_scorer_calls=0)
    save(HERE / ('original32-live-ledger-created-' + folder.name.rsplit('-', 1)[1] + '.json'), result)
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    main(parser.parse_args().evidence.resolve())
