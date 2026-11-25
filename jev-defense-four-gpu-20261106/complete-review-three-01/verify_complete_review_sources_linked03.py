"""Local, finite public-copy validation with explicit seal-relative resolution."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parent
original_spec = importlib.util.spec_from_file_location('original_local_audit', ROOT / 'verify_complete_review_sources.py')
original = importlib.util.module_from_spec(original_spec)
original_spec.loader.exec_module(original)
BASE, sha, read = original.BASE, original.sha, original.read
OUT = ROOT / 'source-verification-linked03'
assert not OUT.exists()
failure_file = ROOT / 'source-verification-failure-02.json'
assert not failure_file.exists()
failure = {
    'status': 'preserved_local_seal_resolution_assumption_failure',
    'failed_script_sha256': sha(ROOT / 'verify_complete_review_sources_linked02.py'),
    'first_failure_record_sha256': sha(ROOT / 'source-verification-failure-01.json'),
    'exception': 'controller_audit_remote.py original remote seal SHA 84919fd42de498815dd95ac1083c065150b2ded01c26c5d6f60c5d901069b4b2 differs from parent working script SHA 77c06435576433cd422be976d1f359946691c63d644f601ed9f507ac9d4fa34e',
    'reason': 'The checker incorrectly resolved a missing remote basename against a mutable parent working script. This is not an original sealed source mutation.',
    'repair': 'Do not resolve remote Controller missing basenames against working sources. Only validate its three actual local copies and retain the original remote map SHA; attribute exhaustive remote verification to the completed structural audit.',
    'new_model_GUI_health_scorer_or_remote_calls': 0,
    'original_labels_or_model_inputs_modified': False
}
failure_file.write_text(json.dumps(failure, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

refs = {}
for rel, expected in original.EXPECTED.items():
    actual = sha(BASE / rel)
    assert actual == expected, (rel, expected, actual)
    refs[rel] = actual

allowed_parent_scripts = {
    ('complete-review-three-01/observer-image-review-01/source-first-visual-seal.json', 'seal_observer_source_notes.py'),
    ('complete-review-three-01/observer-image-review-01/prediction-join-seal.json', 'join_observer_review.py'),
}
controller_seal = 'structure-three-audit01/controller-audit-public-1794041050905022800/seal.json'
seal_audits = []
for rel in original.SEALS:
    path = BASE / rel
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    local_entries, remote_entries = [], []
    for name, expected in value.get('files', value).items():
        if not isinstance(expected, str) or len(expected) != 64:
            continue
        resolved = path.parent / name
        if (rel, name) in allowed_parent_scripts:
            resolved = path.parent.parent / name
        if not resolved.is_file():
            assert rel == controller_seal, (rel, name)
            remote_entries.append({'name_in_remote_seal': name, 'sha256': expected})
            continue
        assert sha(resolved) == expected, (rel, name)
        local_entries.append({'path': str(resolved.relative_to(BASE)), 'sha256': expected})
    assert local_entries, rel
    seal_audits.append({'seal': rel, 'sha256': sha(path), 'verified_local_entries': local_entries,
        'remote_only_entries_not_newly_locally_rehashed': remote_entries})

service = read('structure-three-audit01/service-audit-public-1794040226300580000/receipt.json')
controller = read('structure-three-audit01/controller-audit-public-1794041050905022800/audit.json')
actor = read('independent-actor-three-terminal-review-01/summary.json')
labels = read('independent-actor-three-terminal-review-01/labels.json')
judge = read('complete-review-three-01/judge-semantic-review.json')
observer = read('complete-review-three-01/observer-image-review-01/prediction-join-review.json')
preservation = read('three-preservation-completion-report-01/report.json')
assert service['request_count'] == 119 and service['native_primary_EOS'] == 97
assert service['all20_observer_raw_BF16_to_CPU_native_probabilities_exact']
assert controller['integrity_audit_passed'] and controller['two_stale_runs_zero_calls_unstarted']
for key, value in {'candidate_count': 24, 'accepted_count': 19, 'actual_execution_log_count': 19,
                   'observer_packets': 24, 'same_response_reuses': 4}.items():
    assert controller['runs'][0][key] == value
assert actor['complete_candidates'] == len(labels) == 24
assert actor['definite_candidate_ordinals'] == [23]
assert actor['unresolved_candidate_ordinals'] == [5, 7, 11]
assert actor['native_action_error_ordinals'] == [23, 24]
assert len(judge['rows']) == judge['count'] == sum(judge['phase_counts'].values()) == 73
assert judge['actual_duplicate_key_replies'] == 0
assert observer['count'] == len(observer['rows']) == 20
assert preservation['actual_worker_exit_codes'] == {'primary': 0, 'pplx_flash': 0}
assert preservation['all_workers_and_launcher_absent'] and preservation['holder9locks_remain']
assert preservation['terminal_manifest_entries_verified'] == 848
report = {
    'status': 'passed_local_selected_public_SHA_and_coverage_coherence',
    'scope': 'All available local public copies and fixed expected hashes checked. Exhaustive original remote source validation is attributed to the completed sealed structural audit; no claim of full local mirroring.',
    'fixed_reference_hashes_verified': refs, 'seal_audits': seal_audits,
    'total_local_seal_entries_checked': sum(len(x['verified_local_entries']) for x in seal_audits),
    'remote_only_entries_not_newly_locally_rehashed': sum(len(x['remote_only_entries_not_newly_locally_rehashed']) for x in seal_audits),
    'candidate_judge_observer_counts': [24, 73, 20],
    'postlabel_execution_join_not_in_this_receipt': True,
    'original_actor_labels_sha256_unchanged': sha(BASE / 'independent-actor-three-terminal-review-01/labels.json'),
    'new_model_GUI_health_scorer_or_remote_calls': 0,
    'local_audit_scope_failures_preserved': ['source-verification-failure-01.json', failure_file.name]
}
OUT.mkdir()
(OUT / 'receipt.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
seal_files = ['verify_complete_review_sources.py', 'verify_complete_review_sources_linked02.py',
              Path(__file__).name, 'source-verification-failure-01.json', failure_file.name]
seal = {'receipt.json': sha(OUT / 'receipt.json')}
seal.update({'../' + name: sha(ROOT / name) for name in seal_files})
(OUT / 'seal.json').write_text(json.dumps(seal, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': report['status'], 'local_entries': report['total_local_seal_entries_checked'],
    'remote_only_entries': report['remote_only_entries_not_newly_locally_rehashed'],
    'receipt_sha256': sha(OUT / 'receipt.json'), 'seal_sha256': sha(OUT / 'seal.json')}))
