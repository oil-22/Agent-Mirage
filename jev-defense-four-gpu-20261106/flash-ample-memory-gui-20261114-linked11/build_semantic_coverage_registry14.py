"""Index existing source labels without adding judgments or model calls."""
import collections
import hashlib
import json
import time
from pathlib import Path
from control import HERE, save, sha


def load(path):
    return json.loads(path.read_bytes())


def verify(root):
    assert root.parent == HERE
    assert all(sha(root / n) == h for n, h in load(root / 'seal.json').items())


def main():
    native = HERE / 'live-evidence-incremental-1794663808202958600'
    terminal_path = HERE / 'terminal-audit-1794663830845946000.json'
    verify(native)
    terminals = {v['run']['run_id']: v for v in load(terminal_path)['result']['terminals']}
    assert len(terminals) == 14
    mains = {v['request_id']: v for v in load(native / '3090.json')['sealed_main_requests']}
    rows, bindings = {}, []

    def add(rid, seal, label, wait, publication, published_row, candidate):
        actual = mains[rid]
        assert rid not in rows and actual['seal_sha256'] == seal
        assert actual['decision'] == candidate and actual['run_id'] in terminals
        assert label is None or type(label) is bool
        rows[rid] = {
            'request_id': rid, 'run_id': actual['run_id'], 'candidate': candidate,
            'request_seal_sha256': seal, 'image_sha256': actual['current_image_sha256'],
            'source_judgment': label, 'pure_native_WAIT': bool(wait),
            'publication': str(publication), 'publication_seal_sha256': sha(publication / 'seal.json'),
            'published_row_sha256': hashlib.sha256(json.dumps(published_row, sort_keys=True,
                                          ensure_ascii=False, separators=(',', ':')).encode()).hexdigest(),
            'semantic_label_added_or_changed_by_registry': False}

    clean = HERE / 'T017-clean-paired-publication-1794656865993420400'
    verify(clean)
    paired = load(clean / 'review-joined.json')
    assert paired['same_existing_review_reused_only_after_full_input_image_reply_equality']
    for row in paired['rows']:
        assert row['exact_full_body_and_text_and_images_equal'] and row['same_prior_source_review_reused']
        for run_id, execution in row['execution_joins'].items():
            assert mains[execution['request_id']]['run_id'] == run_id
            add(execution['request_id'], execution['request_seal_sha256'], row['source_review_label'],
                False, clean, row, row['candidate'])
    bindings.append(str(clean))
    for name in ['T017-stale-paired-publication-1794658396227176000',
                 'T058-clean-paired-publication-1794660693901785100',
                 'T058-stale-paired-publication-1794659425276406500']:
        publication = HERE / name
        verify(publication)
        for arm in load(publication / 'review-joined.json')['arms'].values():
            for row in arm['rows']:
                source = row['source_review']
                rid = row.get('actual_request_id', row.get('actual_native_request_id'))
                seal = row.get('actual_request_seal_sha256', row.get('request_seal_sha256'))
                assert mains[rid]['run_id'] == arm['run_id']
                assert mains[rid]['current_image_sha256'] == source['current_image_sha256']
                add(rid, seal, source['candidate_semantic_Mirage'], source['pure_native_WAIT'],
                    publication, row, source['candidate'])
        bindings.append(str(publication))
    for name in ['completed-source-native-join-1794663789685623000',
                 'completed-source-native-join-1794663886298961000']:
        publication = HERE / name
        verify(publication)
        joined = load(publication / 'review-joined.json')
        for row in joined['rows']:
            source, bound = row['source_label_unchanged'], row['native_and_controller_binding']
            assert mains[bound['request_id']]['run_id'] == joined['run_id']
            assert source['current_image_sha256'] == bound['image_sha256']
            add(bound['request_id'], bound['request_seal_sha256'], source['candidate_semantic_Mirage'],
                source['pure_native_WAIT'], publication, row, source['candidate'])
        bindings.append(str(publication))

    completed_ids = {rid for rid, v in mains.items() if v['run_id'] in terminals}
    invalid_ids = completed_ids - rows.keys()
    assert len(invalid_ids) == 4 and len(rows) == 271 and len(completed_ids) == 275
    excluded = []
    for rid in sorted(invalid_ids):
        actual = mains[rid]
        terminal = terminals[actual['run_id']]
        assert terminal['outcome'] == 'native_contract_failure' and terminal['actor_calls'] == 1
        assert terminal['environment_actions'] == 0 and actual['natural_EOS']
        excluded.append({'request_id': rid, 'run_id': actual['run_id'],
                         'request_seal_sha256': actual['seal_sha256'],
                         'semantic_label': None, 'native_contract_failure_not_semantic_zero': True})
    by_run = []
    for run_id, terminal in sorted(terminals.items()):
        selected = sorted((v for v in rows.values() if v['run_id'] == run_id), key=lambda v: v['candidate'])
        if selected:
            assert len(selected) == terminal['actor_calls']
            assert [v['candidate'] for v in selected] == list(range(1, len(selected) + 1))
        positive = [v['candidate'] for v in selected if v['source_judgment'] is True and not v['pure_native_WAIT']]
        unresolved = [v['candidate'] for v in selected if v['source_judgment'] is None and not v['pure_native_WAIT']]
        whole = True if positive else None if unresolved or not selected else False
        by_run.append({'run_id': run_id, 'candidate_total': terminal['actor_calls'],
                       'source_labels_indexed': len(selected), 'definite_positive_candidates': positive,
                       'unresolved_candidates': unresolved, 'trajectory_semantic_Mirage': whole,
                       'unpaired_diagnostic': terminal['run']['task_id'] == 0,
                       'native_contract_failure': terminal['outcome'] == 'native_contract_failure',
                       'official_reward_not_used_for_label': terminal['official_reward'],
                       'terminal_sha256': terminal['terminal_sha256']})
    counts = collections.Counter('WAIT_excluded' if v['pure_native_WAIT'] else
                                'definite_positive' if v['source_judgment'] is True else
                                'literal_negative' if v['source_judgment'] is False else 'unresolved'
                                for v in rows.values())
    pending = [v for rid, v in mains.items() if rid not in completed_ids]
    dest = HERE / ('semantic-coverage-registry-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'registry.json', {
        'time': time.time(), 'terminal_audit': str(terminal_path), 'terminal_audit_sha256': sha(terminal_path),
        'native_audit': str(native), 'native_audit_seal_sha256': sha(native / 'seal.json'),
        'native_raw_checks_referenced_at_original_times': True,
        'fresh_full_postexit_rehash_still_required': True,
        'completed_trajectories': 14, 'completed_native_replies': 275,
        'source_labels_indexed': 271, 'source_label_counts': dict(counts),
        'native_format_failures_without_semantic_labels': 4,
        'all_completed_reply_IDs_accounted_for': True,
        'unreviewed_audited_replies_in_ongoing_trajectory': len(pending),
        'ongoing_request_IDs_without_source_judgments': [v['request_id'] for v in pending],
        'new_or_changed_semantic_labels': 0, 'new_independent_reviewers': 0,
        'transparent_equal_trace_review_reuse_retained': True,
        'unknown_not_converted_to_no_Mirage': True,
        'counts_are_coverage_not_independent_trials_or_Mirage_rate': True,
        'prior_publications': bindings, 'runs': by_run, 'excluded_format_replies': excluded,
        'rows': sorted(rows.values(), key=lambda v: (v['run_id'], v['candidate'])),
        'effectiveness_proven': False, 'Mirage_reduction': None, 'new_model_GUI_calls': 0, 'goal': 'active'})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    save(HERE / 'semantic-coverage-current.json', {'registry': str(dest),
         'registry_sha256': sha(dest / 'registry.json'), 'seal_sha256': sha(dest / 'seal.json'),
         'coverage_not_effectiveness': True, 'time': time.time(), 'goal': 'active'})
    print(json.dumps({'registry': str(dest), 'completed_replies_accounted_for': 275,
                      'source_labels_indexed': 271, 'label_counts': dict(counts),
                      'native_format_failures_without_labels': 4, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
