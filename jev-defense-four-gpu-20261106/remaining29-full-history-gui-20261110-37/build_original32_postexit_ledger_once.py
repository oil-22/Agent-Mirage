"""Original32 downstream ledger supporting later original queue boundaries.

No experiment imports, launches, new labels, modified endpoints or relaxed math.
Completed results require immutable source-gated terminal collection. Partial
source coverage, unknown claims and technical endpoints never become negatives.
"""
import argparse
from collections import Counter
import copy
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import time

from orchestrate import HERE, PACKAGE, admitted, save, sha
from join_source_reviews import verify_seal


SEED = HERE / 'original32-live-ledger-1794300594343043300'
SEED_SHA = '5be16a1965e07eea832b3b35f6bb10c471d8afb68c5f4c72493bb24c4e884090'
MANIFEST_SHA = '368b0a594822f5e294fcd21927aa924a18a80f23249f160857b5de7090c1c02d'
PLAN_SHA = '51e35415fc7df2d0309e67f117310de8ecffd59b51ece6bcfdda176e5ae4f98c'


def read(path):
    return json.loads(path.read_bytes())


def authority(pointer, key, filename, digest):
    value = read(pointer)
    folder = Path(value[key])
    assert folder.parent == HERE
    assert verify_seal(folder) == value['seal_sha256']
    assert sha(folder / filename) == value[digest]
    return folder, read(folder / filename), value


def source_labels(remaining_ids):
    labels = {ident: [] for ident in remaining_ids}
    authorities, seen = [], set()
    for pointer in sorted(HERE.glob('source-review-*-created.json')):
        if not re.fullmatch(r'source-review-\d+-created\.json', pointer.name):
            continue
        folder, review, origin = authority(pointer, 'review', 'review.json', 'review_sha256')
        assert review['independent_current_checker_execution_score_join_not_performed']
        for label in review['rows']:
            packet_path = Path(label['public_source_packet'])
            assert packet_path.parent.parent.parent == HERE / 'source-first-packets'
            verify_seal(packet_path.parent.parent)
            assert sha(packet_path) == label['packet_sha256']
            packet = read(packet_path)
            assert packet['checker_labels_current_acceptance_execution_scoring_private_delivery_excluded']
            assert packet['candidate_event_sha256'] == label['candidate_event_sha256'] not in seen
            assert hashlib.sha256(packet['candidate'].encode()).hexdigest() == label['candidate_text_sha256']
            # Evaluation provenance is opened only after verifying a sealed label.
            # It is never returned to the actor, auxiliary or checker.
            index = read(packet_path.parent.parent / 'PRIVATE-source-index.json')
            mapping = next(row for row in index if row['id'] == label['id'])
            assert mapping['candidate_text_sha256'] == label['candidate_text_sha256']
            assert mapping['actor_request_body_sha256'] == label['actor_request_body_sha256']
            run = PurePosixPath(mapping['attempt']).parent.name
            assert run in labels
            labels[run].append(dict(candidate_id=label['candidate_event_sha256'],
                pure_native_WAIT=label['pure_native_WAIT_excluded'],
                definite_semantic_Mirage=label['candidate_semantic_mirage'],
                original_source_review=origin, original_source_packet_sha256=label['packet_sha256'],
                unresolved_subclaims=label.get('unresolved_subclaims', label.get('uncertain_subclaims', [])),
                native_action_error=label['native_action_error']))
            seen.add(label['candidate_event_sha256'])
        authorities.append(origin)
    return labels, authorities


def current_terminal(run):
    pointer = HERE / ('logical-terminal-' + run + '-collected.json')
    if not pointer.exists():
        return None
    folder, receipt, origin = authority(pointer, 'collection', 'receipt.json', 'receipt_sha256')
    assert receipt['ready'] and receipt['run_id'] == run
    assert receipt['original_source_reviews_sealed_before_terminal_score_join']
    assert receipt['original_GUI_run_end_and_service_ack_and_budget_counters_bound']
    gui, service = read(folder / 'GUI-preservation.json'), read(folder / 'service-preservation.json')
    assert gui['ready'] and service['run_id'] == run
    assert service['run_end_event']['data'] == gui['run_end']['body']
    terminal = folder / 'selected-originals' / gui['terminal_name']
    assert sha(terminal) == gui['terminal_sha256'] == receipt['GUI_original_terminal_sha256']
    assert read(terminal) == gui['terminal']
    return dict(root=folder, receipt=receipt, origin=origin, gui=gui, service=service, terminal=terminal)


def build(evidence):
    assert evidence.parent == HERE
    evidence_seal = verify_seal(evidence)
    admitted()
    assert sha(PACKAGE / 'manifest.json') == MANIFEST_SHA and sha(PACKAGE / 'plan.json') == PLAN_SHA
    plan, continuation = read(PACKAGE / 'plan.json'), read(PACKAGE / 'continuation.json')
    remaining, excluded = continuation['remaining_run_ids'], continuation['excluded_run_ids']
    assert len(remaining) == 29 and len(excluded) == 3
    assert [row['run_id'] for row in plan['queue']] == excluded + remaining
    verify_seal(SEED)
    assert sha(SEED / 'ledger.json') == SEED_SHA
    seed, old_records = read(SEED / 'ledger.json'), read(SEED / 'records-for-unchanged-math.json')
    assert seed['original_full32_plan_sha256'] == PLAN_SHA
    assert seed['original_scope'] == dict(tracks=32, matched_pairs=16, selected_tasks=8)
    assert sha(Path(seed['original_three_terminal_authority'])) == seed['original_three_terminal_authority_sha256']
    for old in seed['original_terminal_evidence']:
        assert sha(PACKAGE / old['copy']) == old['sha256'] == sha(Path(old['raw']))
        assert verify_seal(Path(old['collection_authority']['collection'])) == old['collection_authority']['seal_sha256']
    # Keep the already audited historical candidate judgments and budget replay.
    # Seed coverage is provenance reuse, not a fresh independent semantic review.
    for origin in seed['source_review_authorities']:
        folder = Path(origin.get('review', origin.get('root')))
        assert verify_seal(folder) == origin['seal_sha256']
    service, gui = read(evidence / '3090.json'), read(evidence / '4090.json')
    worker = service['worker/process.json']['actual']
    runner = gui['control/runner-process.json']['actual']
    preservation = read(HERE / 'postexit-preservation-linked02-created.json')
    preserved_root = Path(preservation['root'])
    assert verify_seal(preserved_root) == preservation['seal_sha256']
    assert sha(preserved_root / 'receipt.json') == preservation['receipt_sha256']
    for actual, saved, expected in [
        (worker, service['worker/process.json']['value'], (252807, 1033, '1191243649')),
        (runner, gui['control/runner-process.json']['value'], (3333015, 1015, '127695701')),
    ]:
        assert actual.get('absent') is True
        assert (saved['pid'], saved['uid'], saved['start_ticks']) == expected
        assert HERE.name in saved['command']
    assert service['worker/terminal.json']['value']['status'] == 'technical_failure'
    assert service['worker/terminal.json']['value']['total_model_attempts'] == 75
    assert service['exit.json']['value']['worker_exit_code'] == 1
    assert gui['batch/status.json']['value']['phase'] == 'technical_failure'
    assert gui['control/exit.json']['value']['automatic_retry'] is False
    assert len(service['sealed_requests']) == 75
    assert len(service['held_locks']) == 9
    state = service['worker/status.json']['value']
    assert state.get('active') is None or state['active'] in remaining
    chains = {}
    for chain in gui['GUI_event_chains']:
        run = PurePosixPath(chain['path']).parent.parent.name
        assert run in remaining and run not in chains
        chains[run] = chain
    assert set(chains).issubset(set(remaining))
    for row in service['sealed_requests']:
        assert row['trajectory_id'] in chains
    labels, review_authorities = source_labels(remaining)
    previous_by_id = {row['run_id']: row for row in old_records}
    ledger, records, terminal_origins = [], [], []
    for planned in plan['queue']:
        run = planned['run_id']
        if run in excluded:
            row = copy.deepcopy(next(row for row in seed['rows'] if row['run_id'] == run))
            assert sha(Path(row['terminal_receipt']['path'])) == row['terminal_receipt']['sha256']
            ledger.append(row)
            records.append(copy.deepcopy(previous_by_id[run]))
            continue
        candidates = labels[run]
        record = dict(run_id=run, status='pending', candidates=candidates, source_review_complete=False,
                      official_score=None, executed_actions=0, actor_calls=0,
                      any_definite_false_rejection=None, false_rejection_assessment_complete=False)
        entry = dict(**planned, exposure_state='never_started', source_reviewed_candidates=len(candidates),
            original_source_labels_unchanged=True, terminal_receipt=None, raw_recorded_official_reward=None,
            analysis_official_score=None, false_rejection_assessment='unresolved',
            source_contract='approved decoded-native-answer source representation; runtime v4.0.12')
        chain = chains.get(run)
        if chain is None:
            assert not candidates and current_terminal(run) is None
            entry['zero_exposure_provenance'] = 'No started GUI chain or request for this original remaining-queue identity in the inspected snapshot.'
        else:
            counts = chain['counts']
            assert len(candidates) <= counts.get('candidate', 0)
            record['executed_actions'] = counts.get('action_executed', 0)
            record['actor_calls'] = (state['counts']['actor'] if state.get('active') == run else
                sum(row['operation'] == 'actor' and row['trajectory_id'] == run for row in service['sealed_requests']))
            entry.update(exposure_state='verified_live' if state.get('active') == run else 'started_endpoint_uncollected',
                actual_process_evidence=str(evidence), GUI_event_chain=chain,
                all_candidate_events_at_snapshot=counts.get('candidate', 0),
                all_original_candidate_records_covered=len(candidates) == counts.get('candidate', 0),
                completed_trajectory_or_negative_not_inferred_from_reviewed_prefix=True)
            endpoint = current_terminal(run)
            if endpoint is not None:
                terminal = read(endpoint['terminal'])
                ids = endpoint['gui']['original_candidate_event_hashes']
                assert len(ids) == len(set(ids)) and set(ids) == {row['candidate_id'] for row in candidates}
                assert len(ids) == counts.get('candidate', 0)
                transport = endpoint['service']['original_transport_counts_including_carried_technical_expenditure']
                kind = endpoint['gui']['terminal_name']
                technical = (kind not in ['complete.json', 'paused.json'] or
                    terminal.get('technical_status') in ['verifier_failure', 'scoring_failure'])
                complete = kind == 'complete.json' and not technical
                if 'run' in terminal:
                    assert terminal['run'] == planned
                assert all(transport[key] <= maximum for key, maximum in [('actor', 70), ('judge', 140), ('evidence', 60)])
                assert planned['observer_enabled'] or transport['evidence'] == 0
                raw_score = terminal.get('official_reward')
                score = int(raw_score) if complete and terminal.get('scoring_status') == 'complete' else None
                record.update(status='completed' if complete else 'technical_failure' if technical else 'pending',
                    official_score=score, actor_calls=transport['actor'],
                    executed_actions=terminal.get('environment_actions', record['executed_actions']),
                    source_review_complete=len(ids) == transport['actor'])
                entry.update(exposure_state='immutable_budget_or_model_terminal' if complete else
                    'immutable_technical_terminal' if technical else 'immutable_stopped_endpoint',
                    terminal_receipt=dict(path=str(endpoint['terminal']), sha256=sha(endpoint['terminal']),
                        original_authority=endpoint['origin']), raw_recorded_official_reward=raw_score,
                    analysis_official_score=score, technical_failure_not_model_zero=technical,
                    original_outcome=terminal.get('outcome'), original_technical_status=terminal.get('technical_status'),
                    actual_call_counts=transport, all_original_candidate_records_covered=record['source_review_complete'],
                    no_terminal_rerun_or_rewrite=True)
                terminal_origins.append(endpoint['origin'])
        entry.update(definite_positive_candidates=sum(row['definite_semantic_Mirage'] is True and not row['pure_native_WAIT'] for row in candidates),
            unknown_candidate_labels=sum(row['definite_semantic_Mirage'] is None and not row['pure_native_WAIT'] for row in candidates),
            environment_actions=record['executed_actions'])
        ledger.append(entry)
        records.append(record)
    math_path = HERE.parent / 'prefill-scheduled-full-history-gui-20261109-32/matched_outcome_analysis.py'
    assert sha(math_path) == seed['math_module_sha256']
    spec = importlib.util.spec_from_file_location('unchanged_original32_queue_math', math_path)
    math = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(math)
    analysis = math.analyze(plan, records, resample=False)
    for row, record in zip(ledger, records):
        row['trajectory_any_definite_Mirage'] = math.endpoint(record)
    assert analysis['planned_tracks'] == 32 and analysis['planned_pairs'] == 16 and analysis['unique_tasks'] == 8
    data = dict(schema='source-bound-original32-postexit-ledger-v1', time=time.time(),
        original_scope=seed['original_scope'], original_full32_plan_sha256=PLAN_SHA,
        actual_live_evidence=str(evidence), actual_live_evidence_seal_sha256=evidence_seal,
        actual_runtime_confirmed_exited=True, original_postexit_preservation=preservation,
        all_candidate_coverage_separate_from_technical_status=True,
        approved_runtime_manifest_sha256=MANIFEST_SHA, worker=worker, GUI_runner=runner, held_locks=9,
        original_three_seed_ledger=str(SEED), original_three_seed_ledger_sha256=SEED_SHA,
        original_three_terminal_authority=seed['original_three_terminal_authority'],
        original_three_terminal_authority_sha256=seed['original_three_terminal_authority_sha256'],
        source_review_authorities=review_authorities, new_terminal_collection_authorities=terminal_origins,
        rows=ledger, exposure_states=dict(Counter(row['exposure_state'] for row in ledger)),
        original16_pairs_primary_14_wholly_prospective_pairs_only_version_stratum=True,
        unknowns_remain_in_original_denominators_no_candidate_count_rate=True,
        private_mapping_is_downstream_evaluation_only_never_checker_input=True,
        historical_labels_reused_not_new_blind_review=True, source_selected_single_reviewer_legal_feedback_not_fully_blind=True,
        companion_false_block_and_exposure_reviews_require_separate_evidence=True,
        math_module_sha256=sha(math_path), relative_Mirage_reduction=analysis['primary']['relative_reduction_point'],
        efficacy_established=False, final_completion_audit_not_passed=True, goal='active',
        new_model_GUI_capture_action_scorer_calls=0, frozen_runtime_unchanged=True)
    return data, records, analysis


def main(evidence):
    ledger, records, analysis = build(evidence)
    folder = HERE / ('original32-postexit-ledger-' + str(time.time_ns()))
    folder.mkdir()
    (folder / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(folder / 'ledger.json', ledger)
    save(folder / 'records-for-unchanged-math.json', records)
    save(folder / 'descriptive-analysis.json', analysis)
    save(folder / 'seal.json', {p.name: sha(p) for p in folder.iterdir() if p.is_file()})
    value = dict(root=str(folder), ledger_sha256=sha(folder / 'ledger.json'),
        analysis_sha256=sha(folder / 'descriptive-analysis.json'), seal_sha256=sha(folder / 'seal.json'),
        original_scope=ledger['original_scope'], exposure_states=ledger['exposure_states'],
        primary_effect_estimate=ledger['relative_Mirage_reduction'], efficacy_established=False,
        new_model_GUI_scorer_calls=0)
    save(HERE / ('original32-postexit-ledger-created-' + folder.name.rsplit('-', 1)[1] + '.json'), value)
    print(json.dumps(value))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    main(parser.parse_args().evidence.resolve())
