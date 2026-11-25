"""Extend a sealed coverage index using complete, source-native joined reviews.

No labels are inferred. Pending semantic reviews, format failures, and technical
failures stay separate; none becomes a negative semantic label.
"""
import argparse
import collections
import hashlib
import json
import time
from pathlib import Path
from control import HERE, save, sha


def load(path):
    return json.loads(path.read_bytes())


def verify(root):
    assert root.resolve().parent == HERE
    assert all(sha(root / n) == h for n, h in load(root / 'seal.json').items())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prior', type=Path, required=True)
    parser.add_argument('--joins', type=Path, nargs='+', required=True)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--terminals', type=Path, required=True)
    parser.add_argument('--parent-raw', type=Path, required=True)
    parser.add_argument('--parent-controller', type=Path, required=True)
    args = parser.parse_args()
    prior, native = args.prior.resolve(), args.native.resolve()
    verify(prior)
    verify(native)
    assert args.terminals.resolve().parent == HERE
    previous = load(prior / 'registry.json')
    parent_raw, parent_controller = args.parent_raw.resolve(), args.parent_controller.resolve()
    verify(parent_raw)
    verify(parent_controller)
    raw_summary = load(parent_raw / 'summary.json')
    parent_bindings = load(parent_controller / 'bindings.json')
    assert raw_summary['group'] == parent_bindings['group'] == 'parent'
    assert raw_summary['actual_original_group_process_exits_verified']
    assert parent_bindings['source_full_raw_audit'] == str(parent_raw)
    assert parent_bindings['source_full_raw_seal_sha256'] == sha(parent_raw / 'seal.json')
    assert parent_bindings['all_actual_requests_replies_PNGs_Flash_and_native_actions_bound']
    parent_records = load(parent_controller / 'GUI-collection.json')['result']['controllers']
    preserved_technical = [v for v in parent_records if v['terminal']['infrastructure_failure']]
    assert len(preserved_technical) == 1
    parent_normal = [v for v in parent_records if not v['terminal']['infrastructure_failure']]
    assert len(parent_normal) == 16
    terminal_rows = [{**v['terminal'], 'terminal_sha256': v['terminal_sha256'],
        'event_chain_head': v['chain']['head'], 'event_chain_count': v['chain']['verified_prefix_events']}
        for v in parent_normal] + load(args.terminals)['result']['terminals']
    terminals = {v['run']['run_id']: v for v in terminal_rows}
    assert len(terminals) == len(terminal_rows)
    assert all(not v['infrastructure_failure'] for v in terminals.values())
    mains = {v['request_id']: v for v in load(native / '3090.json')['sealed_main_requests']}
    normal_parent_ids = {v['terminal']['run']['run_id'] for v in parent_normal}
    for row in load(parent_raw / '3090.json')['sealed_main_requests']:
        if row['run_id'] in normal_parent_ids:
            assert row['request_id'] not in mains
            mains[row['request_id']] = row
    rows = {v['request_id']: v for v in previous['rows']}
    assert len(rows) == previous['source_labels_indexed']
    for rid, row in rows.items():
        assert mains[rid]['run_id'] == row['run_id'] and mains[rid]['seal_sha256'] == row['request_seal_sha256']
        assert mains[rid]['decision'] == row['candidate'] and row['run_id'] in terminals
    additions, bindings = [], []
    for root in (p.resolve() for p in args.joins):
        verify(root)
        joined = load(root / 'review-joined.json')
        run_id = joined['run_id']
        terminal = terminals[run_id]
        controller = joined['completed_controller_binding']
        assert controller['terminal_sha256'] == terminal['terminal_sha256']
        assert controller['chain']['head'] == terminal['event_chain_head']
        assert controller['chain']['verified_prefix_events'] == terminal['event_chain_count']
        assert len(joined['rows']) == joined['candidate_coverage'] == terminal['actor_calls']
        assert [v['source_label_unchanged']['candidate'] for v in joined['rows']] == list(range(1, terminal['actor_calls'] + 1))
        for item in joined['rows']:
            label, bound = item['source_label_unchanged'], item['native_and_controller_binding']
            rid = bound['request_id']
            assert rid not in rows, 'Never replace an existing source label'
            actual = mains[rid]
            assert actual['run_id'] == run_id and actual['decision'] == label['candidate']
            assert actual['seal_sha256'] == bound['request_seal_sha256']
            assert actual['current_image_sha256'] == label['current_image_sha256'] == bound['image_sha256']
            assert actual['actual_tensor_files_verified'] and actual['natural_EOS']
            row = {'request_id': rid, 'run_id': run_id, 'candidate': label['candidate'],
                   'request_seal_sha256': actual['seal_sha256'], 'image_sha256': actual['current_image_sha256'],
                   'source_judgment': label['candidate_semantic_Mirage'], 'pure_native_WAIT': label['pure_native_WAIT'],
                   'publication': str(root), 'publication_seal_sha256': sha(root / 'seal.json'),
                   'published_row_sha256': hashlib.sha256(json.dumps(item, sort_keys=True,
                                                ensure_ascii=False, separators=(',', ':')).encode()).hexdigest(),
                   'semantic_label_added_or_changed_by_registry': False}
            rows[rid] = row
            additions.append(rid)
        bindings.append({'root': str(root), 'seal_sha256': sha(root / 'seal.json')})
    assert additions
    completed = {rid for rid, v in mains.items() if v['run_id'] in terminals}
    assert set(rows).issubset(completed)
    excluded, pending, runs = [], [], []
    for rid in sorted(completed - rows.keys()):
        actual, terminal = mains[rid], terminals[mains[rid]['run_id']]
        row = {'request_id': rid, 'run_id': actual['run_id'], 'request_seal_sha256': actual['seal_sha256'],
               'semantic_label': None}
        if terminal['outcome'] == 'native_contract_failure':
            excluded.append({**row, 'native_contract_failure_not_semantic_zero': True})
        else:
            pending.append({**row, 'source_review_not_completed': True,
                            'infrastructure_failure': terminal['infrastructure_failure']})
    for run_id, terminal in sorted(terminals.items()):
        selected = sorted((v for v in rows.values() if v['run_id'] == run_id), key=lambda v: v['candidate'])
        assert len(selected) <= terminal['actor_calls']
        positive = [v['candidate'] for v in selected if v['source_judgment'] is True and not v['pure_native_WAIT']]
        unresolved = [v['candidate'] for v in selected if v['source_judgment'] is None and not v['pure_native_WAIT']]
        complete = bool(selected) and len(selected) == terminal['actor_calls'] and not terminal['infrastructure_failure'] and terminal['outcome'] != 'native_contract_failure'
        whole = True if positive else None if unresolved or not complete else False
        runs.append({'run_id': run_id, 'candidate_total': terminal['actor_calls'],
                     'source_labels_indexed': len(selected), 'source_review_complete': complete,
                     'definite_positive_candidates': positive, 'unresolved_candidates': unresolved,
                     'trajectory_semantic_Mirage': whole, 'unpaired_diagnostic': terminal['run']['task_id'] == 0,
                     'native_contract_failure': terminal['outcome'] == 'native_contract_failure',
                     'official_reward_not_used_for_label': terminal['official_reward'],
                     'terminal_sha256': terminal['terminal_sha256']})
    counts = collections.Counter('WAIT_excluded' if v['pure_native_WAIT'] else
                                'definite_positive' if v['source_judgment'] is True else
                                'literal_negative' if v['source_judgment'] is False else 'unresolved'
                                for v in rows.values())
    assert len(rows) + len(excluded) + len(pending) == len(completed)
    active = [v for rid, v in mains.items() if rid not in completed]
    dest = HERE / ('semantic-coverage-registry-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    (dest / 'previous-semantic-coverage-current.json').write_bytes(
        (HERE / 'semantic-coverage-current.json').read_bytes())
    save(dest / 'registry.json', {
        'time': time.time(), 'prior_registry': str(prior), 'prior_registry_seal_sha256': sha(prior / 'seal.json'),
        'terminal_audit': str(args.terminals), 'terminal_audit_sha256': sha(args.terminals),
        'native_audit': str(native), 'native_audit_seal_sha256': sha(native / 'seal.json'),
        'native_raw_checks_referenced_at_original_times': True, 'fresh_full_postexit_rehash_still_required': True,
        'parent_fresh_full_raw_audit': str(parent_raw),
        'parent_fresh_full_raw_seal_sha256': sha(parent_raw / 'seal.json'),
        'parent_fresh_full_controller_audit': str(parent_controller),
        'parent_fresh_full_controller_seal_sha256': sha(parent_controller / 'seal.json'),
        'parent396_public_replies199_Flash_and1_undelivered_generation_freshly_verified': True,
        'preserved_technical_parent_attempts_excluded_from_normal_registry': [
            {'terminal_sha256': v['terminal_sha256'], 'seal_sha256': v['seal_sha256']}
            for v in preserved_technical],
        'old_partial_occurrences_and_costs_retained_not_independent_new_trials': True,
        'completed_trajectories': len(terminals), 'completed_native_replies': len(completed),
        'source_labels_indexed': len(rows), 'source_label_counts': dict(counts),
        'native_format_failures_without_semantic_labels': len(excluded),
        'completed_replies_waiting_for_source_review': len(pending),
        'all_completed_reply_IDs_accounted_for': True,
        'unreviewed_audited_replies_in_ongoing_trajectory': len(active),
        'ongoing_request_IDs_without_source_judgments': [v['request_id'] for v in active],
        'existing_labels_replaced': 0, 'new_or_changed_semantic_labels': 0,
        'newly_indexed_existing_source_labels': len(additions), 'new_independent_reviewers': 0,
        'transparent_equal_trace_review_reuse_retained': True, 'unknown_not_converted_to_no_Mirage': True,
        'counts_are_coverage_not_independent_trials_or_Mirage_rate': True,
        'newly_joined_review_bindings': bindings, 'runs': runs, 'excluded_format_replies': excluded,
        'pending_completed_replies_without_source_labels': pending,
        'rows': sorted(rows.values(), key=lambda v: (v['run_id'], v['candidate'])),
        'effectiveness_proven': False, 'Mirage_reduction': None, 'new_model_GUI_calls': 0, 'goal': 'active'})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    (HERE / 'semantic-coverage-current.json').write_text(json.dumps({'registry': str(dest),
         'registry_sha256': sha(dest / 'registry.json'), 'seal_sha256': sha(dest / 'seal.json'),
         'coverage_not_effectiveness': True, 'time': time.time(), 'goal': 'active'},
         ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'registry': str(dest), 'completed_replies_accounted_for': len(completed),
                      'source_labels_indexed': len(rows), 'pending_source_reviews': len(pending),
                      'native_format_failures_without_labels': len(excluded), 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
