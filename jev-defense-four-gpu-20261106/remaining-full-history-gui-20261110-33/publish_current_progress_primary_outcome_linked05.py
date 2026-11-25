"""Publish source/audit progress and an independently reviewed preserved terminal; no runtime edit."""
import argparse
import collections
import copy
import json
from pathlib import Path
import re
import time

from orchestrate import HERE, BASE, PACKAGE, save, sha
from join_source_reviews import verify_seal


def read(path):
    return json.loads(Path(path).read_bytes())


def authority_record(path, folder_key, content_name, hash_key):
    authority = read(path)
    folder = Path(authority[folder_key])
    assert folder.parent == HERE
    assert verify_seal(folder) == authority['seal_sha256']
    assert sha(folder / content_name) == authority[hash_key]
    return authority, read(folder / content_name)


def main(evidence, through, note_file):
    assert evidence.parent == HERE and note_file.parent == HERE
    verify_seal(evidence)
    service, gui = read(evidence / '3090.json'), read(evidence / '4090.json')
    for record in [service['worker/process.json'], service['launcher-process.json'], gui['control/runner-process.json']]:
        actual = record['actual']
        assert not actual.get('absent') and actual['state'] not in ['Z', 'X']
        assert all(str(actual[key]) == str(record['value'][key]) for key in ['pid', 'uid', 'command', 'start_ticks'])
    assert len(service['held_locks']) == 9 and service['manifest_sha256'] == sha(PACKAGE / 'manifest.json')
    manifest = read(PACKAGE / 'manifest.json')
    for name, expected in manifest['files'].items():
        assert sha(PACKAGE / name) == expected, name
    GUI_state = gui['batch/status.json']['value']
    assert GUI_state['phase'] == 'running', 'A terminal requires collection, not a running-progress publication'
    sealed = {row['request']: row for row in service['sealed_requests']}
    requests, audits = {}, []
    for path in sorted(HERE.glob('mixed-receipt-audit-created-*.json')):
        authority, receipt = authority_record(path, 'root', 'receipt.json', 'receipt_sha256')
        assert receipt['passed']
        data = read(Path(authority['root']) / '3090-native-bindings.json')
        for row in data['reports']:
            ident = row['request']
            assert row['native_proof']['natural_EOS']
            assert row['request_seal_sha256'] == sealed[ident]['seal_sha256']
            if ident in requests:
                assert row == requests[ident], 'Repeated audits must agree and must not add another model call'
            else:
                requests[ident] = row
        audits.append(authority)
    assert sorted(requests) == ['%04d' % n for n in range(1, through + 1)]
    labels, source_authorities = {}, []
    for path in sorted(HERE.glob('source-review-*-created.json')):
        if not re.fullmatch(r'source-review-\d+-created\.json', path.name):
            continue
        authority, review = authority_record(path, 'review', 'review.json', 'review_sha256')
        assert review['independent_current_checker_execution_score_join_not_performed']
        for row in review['rows']:
            assert row['id'] not in labels
            assert sha(row['public_source_packet']) == row['packet_sha256']
            labels[row['id']] = row
        source_authorities.append(authority)
    posts, post_authorities = {}, []
    for path in [HERE / 'initial-two-postexecution-review-created.json', *sorted(HERE.glob('postexecution-review-*-created.json'))]:
        authority, review = authority_record(path, 'root', 'review.json', 'review_sha256')
        for row in review['reports']:
            assert row['id'] not in posts and row['original_source_label'] == labels[row['id']]
            assert row['accepted'] and row['executed'] and row['source_label_unchanged']
            assert sha(row['original_postexecution_image']) == row['original_postexecution_image_sha256']
            posts[row['id']] = row
        post_authorities.append(authority)
    latest_joins = {}
    for folder in sorted(HERE.glob('post-review-join-*')):
        if not folder.is_dir():
            continue
        verify_seal(folder)
        joined = read(folder / 'join.json')
        assert joined['all_source_labels_sealed_before_this_join']
        for row in joined['rows']:
            assert row['sealed_source_label'] == labels[row['id']]
            record = dict(join=str(folder / 'join.json'), join_sha256=sha(folder / 'join.json'),
                candidate_event_sha256=row['candidate_event_sha256'], snapshot=row['snapshot'], run=row['run'],
                accepted_at_last_join=row['accepted'], executed_at_last_join=row['executed'],
                blocked_at_last_join=bool(row['candidate_decision_block_events']))
            old = latest_joins.get(row['id'])
            if old is None or row['snapshot']['count'] >= old['snapshot']['count']:
                latest_joins[row['id']] = record
    note = read(note_file)
    assert note['goal_turn_classification'] == 'progress' and isinstance(note['findings'], list)
    before = {name: (BASE / name).read_bytes() for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']}
    status = copy.deepcopy(json.loads(before['full-gui-current.json']))
    current = status['linked_remaining31']
    assert through > len(current['audited_requests']) or len(labels) > current['source_reviewed_candidates'] or len(posts) > current['confirmed_accepted_and_executed_actions_with_original_after_images']
    counts = collections.Counter(row['operation'] for row in requests.values())
    primary = [row['native_proof'] for row in requests.values() if row['operation'] != 'evidence']
    auxiliary = [row['native_proof'] for row in requests.values() if row['operation'] == 'evidence']
    assert all(row['actual_first_cache_length'] == 0 and row['all_observed_cache_objects_released'] for row in auxiliary)
    current.update(state=service['worker/status.json']['value'], new31_GUI_state=GUI_state,
        actual_worker=service['worker/process.json']['actual'], actual_GUI=gui['control/runner-process.json']['actual'],
        actual_holder=service['actual_holder'], actual_held_locks=9, audited_requests=sorted(requests),
        audited_request_counts=dict(counts), source_reviewed_candidates=len(labels),
        definite_negative_source_candidates=sum(row['candidate_semantic_mirage'] is False and not row['unresolved_subclaims'] for row in labels.values()),
        definite_positive_source_candidates=sum(row['candidate_semantic_mirage'] is True and not row['pure_native_WAIT_excluded'] for row in labels.values()),
        unresolved_source_candidate_ids=[row['id'] for row in labels.values() if row['candidate_semantic_mirage'] is None or row['unresolved_subclaims']],
        latest_source_sealed_outcome_joins=latest_joins,
        confirmed_accepted_and_executed_actions_with_original_after_images=len(posts),
        normal_action_target_outcomes_locally_corroborated=sum(row.get('normal_action_target_outcome_locally_corroborated', row.get('normal_target_outcome_locally_corroborated', False)) for row in posts.values()),
        primary_only_audited_totals=dict(calls=len(primary), input_tokens=sum(row['actual_input_tokens'] for row in primary),
            output_tokens=sum(row['output_tokens'] for row in primary),
            summed_native_call_timer_seconds=sum(row['native_call_timer_seconds'] for row in primary)),
        auxiliary_only_audited_totals=dict(calls=len(auxiliary), input_tokens=sum(row['actual_input_tokens'] for row in auxiliary),
            output_tokens=sum(row['output_tokens'] for row in auxiliary), timing_scope='Server timers include switches/instrumentation; not added to primary native timers.'))
    # A source-positive unfinished trajectory already has an occurrence.
    # Missing endpoints never erase it; no negative is inferred from partial review.
    positive_sources_by_run = {}
    for ident, label in labels.items():
        if label['candidate_semantic_mirage'] is not True or label['pure_native_WAIT_excluded']:
            continue
        joined = latest_joins.get(ident)
        assert joined is not None, 'Bind source positives to actual runs before publication'
        positive_sources_by_run.setdefault(joined['run'], []).append(ident)
    current_run_positives = sorted(positive_sources_by_run.get(GUI_state['run'], []))
    current.update(
        source_positive_candidates_by_run=positive_sources_by_run,
        current_run_source_positive_candidates=current_run_positives,
        current_run_observed_prefix_any_Mirage=True if current_run_positives else None,
        trajectory_semantic_mirage=True if current_run_positives else None,
        trajectory_label_scope='Any source-sealed positive establishes an occurrence in this run, even before its endpoint; partial negatives never establish absence. Full endpoints, exposure, completion, official scoring and matched efficacy remain separate.',
        current_run_full_endpoint_verified=False)
    status.update(schema='original32-verified-source-execution-progress-v1', time=time.time(),
        previous_goal_turn_classification=note.get('previous_goal_turn_classification', 'progress'), current_goal_turn_classification=note['progress_basis'],
        goal='active', monitor_should_remain_active=True, efficacy_established=False, relative_Mirage_reduction=None,
        latest_findings=note['findings'], original32_all_verified_complete=False)
    terminal_reviews = {}
    for pointer_name in note.get('verified_terminal_review_pointers', []):
        terminal_authority, terminal_review = authority_record(HERE / pointer_name, 'root', 'review.json', 'review_sha256')
        run_id = terminal_review['run_id']
        assert run_id in {row['run_id'] for row in service['worker/status.json']['value']['done']}
        assert terminal_review['all99_native_originals_natural_EOS_audited']
        assert terminal_review['all15_actual_source_candidates_reviewed_before_current_outcome_joins']
        assert terminal_review['runtime_conditions_modified'] is False
        assert terminal_review['completed_track_rerun'] is False
        assert terminal_review['trajectory_semantic_mirage'] is True
        assert set(terminal_review['positive_candidate_ids']) <= set(labels)
        terminal_reviews[run_id] = dict(authority=terminal_authority, terminal_outcome=terminal_review['terminal_outcome'],
            original_terminal_sha256=terminal_review['original_terminal_sha256'],
            official_reward=terminal_review['official_reward'], scoring_status=terminal_review['scoring_status'],
            original_model_calls=terminal_review['original_model_calls'],
            original_environment_actions=terminal_review['original_environment_actions'],
            trajectory_semantic_mirage=True, positive_candidate_ids=terminal_review['positive_candidate_ids'],
            accepted_positive_STOP_candidate=terminal_review['accepted_positive_STOP_candidate'],
            accepted_positive_STOP_has_environment_action=False,
            official_success_is_not_Mirage_absence=True)
    current['verified_terminal_source_outcome_reviews'] = terminal_reviews
    current['verified_new31_complete_track_count'] = len(terminal_reviews)
    status['verified_complete_original32_track_count_lower_bound'] = 1 + len(terminal_reviews)
    status['matched_efficacy_analysis_ready'] = False
    status['matched_baseline_first_track_semantic_mirage_remains_unknown'] = True
    status['authorities']['verified_terminal_source_outcome_reviews'] = terminal_reviews
    status['auxiliary']['actual_stateless_GUI_calls_audited'] = len(auxiliary)
    status['storage']['last_available_bytes'] = service['service_storage_free_bytes']
    status['authorities'].update(actual_evidence=str(evidence), actual_evidence_seal_sha256=sha(evidence / 'seal.json'),
        all_nonoverlapping_native_audits=audits, all_current_source_reviews=source_authorities,
        all_postexecution_visual_reviews=post_authorities)
    root = HERE / ('progress-publication-' + str(time.time_ns()))
    root.mkdir()
    for name, raw in before.items():
        (root / ('before-' + name)).write_bytes(raw)
    (root / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (root / 'supplied-progress-note.json').write_bytes(note_file.read_bytes())
    save(root / 'status.json', status)
    findings = '\n\n'.join(note['findings'])
    state = current['state']
    head = ('## \u6700\u65b0\uff1a2026-11-10 ' + note['title']
        + '\n\n\u6743\u5a01 `' + root.relative_to(BASE).as_posix() + '/status.json`\n\n'
        + findings
        + '\n\nActual native requests audited through ' + str(through)
        + '; operations ' + json.dumps(dict(counts), ensure_ascii=False)
        + '. Main-agent source candidates reviewed: ' + str(len(labels))
        + '; accepted/executed original after-images reviewed: ' + str(len(posts))
        + '. Current request: ' + str(state.get('request')) + '/' + str(state.get('operation')) + '/' + str(state.get('phase'))
        + '. Same actual process identities, nine held locks, exclusive GPUs 4-7 and both event chains verified.\n\n'
        + 'Primary outcome: matched trajectory-level main-agent Mirage. Auxiliary recognition is diagnostic only. '
        + 'A source-positive prefix remains positive before its endpoint; unknown is not negative. Pure native WAIT is excluded. '
        + 'The original 32 tracks, 16 pairs, 8 selected tasks, complete images/main histories and native budgets remain. '
        + 'Remaining queue: ' + str(GUI_state['completed']) + '/31 complete. No efficacy or goal completion is established. '
        + 'Auxiliary is the 9B base model with decision_adapter_loaded=false, fixed v6, one complete supplied image and stateless calls. '
        + 'Existing queue continues. Goal ACTIVE.\n\n')
    (root / 'report.md').write_text(head, encoding='utf8')
    for name in ['README.md', 'HANDOFF.md']:
        assert (BASE / name).read_bytes() == before[name]
        (BASE / name).write_bytes(head.encode('utf8') + before[name])
    assert (BASE / 'full-gui-current.json').read_bytes() == before['full-gui-current.json']
    (BASE / 'full-gui-current.json').write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    for name in ['README.md', 'HANDOFF.md']:
        assert (BASE / name).read_bytes() == head.encode('utf8') + before[name]
    assert read(BASE / 'full-gui-current.json') == status
    save(root / 'receipt.json', dict(time=time.time(), passed=True, old_heads_preserved=True,
        all_three_new_heads_readback_verified=True, source_labels_and_experiment_conditions_unchanged=True,
        new_model_GUI_scorer_calls=0, goal_completion_or_efficacy_established=False))
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    authority = dict(root=str(root), status_sha256=sha(root / 'status.json'), seal_sha256=sha(root / 'seal.json'))
    save(HERE / ('progress-publication-created-' + root.name.rsplit('-', 1)[1] + '.json'), authority)
    print(json.dumps(authority))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--audited-through', type=int, required=True)
    parser.add_argument('--note-file', type=Path, required=True)
    args = parser.parse_args()
    main(args.evidence.resolve(), args.audited_through, args.note_file.resolve())
