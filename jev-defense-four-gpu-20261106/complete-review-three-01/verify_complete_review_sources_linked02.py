"""Linked local audit: remote Controller seal is intentionally selectively mirrored."""
import importlib.util
import json
from pathlib import Path

SOURCE = Path(__file__).with_name('verify_complete_review_sources.py')
spec = importlib.util.spec_from_file_location('original_local_audit', SOURCE)
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)
BASE, sha, read = original.BASE, original.sha, original.read
OUT = Path(__file__).parent / 'source-verification-linked02'
assert not OUT.exists()

failure = {
    'status': 'preserved_local_audit_scope_assumption_failure',
    'original_source': SOURCE.name,
    'original_source_sha256': sha(SOURCE),
    'exception': "AssertionError: ('structure-three-audit01/controller-audit-public-1794041050905022800/seal.json', 'service-public-seal.json')",
    'reason': 'The full remote Controller audit seal was selectively mirrored as audit.json, seal.json and technical-terminal-original.json; the first local checker incorrectly assumed the full remote directory had been copied.',
    'output_receipt_was_written': False,
    'source_results_labels_model_conditions_changed': False,
    'new_model_GUI_health_scorer_calls': 0,
    'repair': 'Verify every available local artifact and explicit expected receipt SHA; list remote-only entries separately, attribute their verification to the sealed completed remote structural audit. Do not fabricate missing local copies.'
}
FAILURE = Path(__file__).parent / 'source-verification-failure-01.json'
assert not FAILURE.exists()
FAILURE.write_text(json.dumps(failure, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

verified = {}
for rel, expected in original.EXPECTED.items():
    actual = sha(BASE / rel)
    assert actual == expected, (rel, expected, actual)
    verified[rel] = actual

seal_audits = []
for rel in original.SEALS:
    path = BASE / rel
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    mapping = value.get('files', value)
    checked, remote_only = [], []
    for name, expected in mapping.items():
        if not isinstance(expected, str) or len(expected) != 64:
            continue
        resolved = path.parent / name
        if not resolved.exists() and name.endswith('.py'):
            alternate = path.parent.parent / name
            if alternate.exists():
                resolved = alternate
        if not resolved.is_file():
            assert rel == 'structure-three-audit01/controller-audit-public-1794041050905022800/seal.json', (rel, name)
            remote_only.append({'name_in_original_remote_seal': name, 'sha256': expected})
            continue
        actual = sha(resolved)
        assert actual == expected, (rel, name, expected, actual)
        checked.append({'name_in_original_seal': name,
                        'actual_local_path': str(resolved.relative_to(BASE)), 'sha256': actual})
    assert checked, rel
    seal_audits.append({'seal': rel, 'sha256': sha(path), 'verified_local_entries': len(checked),
        'local_entries': checked, 'remote_only_entries': remote_only,
        'remote_only_scope': 'Previously completed original remote structural audit; not newly re-read locally.' if remote_only else None})

service = read('structure-three-audit01/service-audit-public-1794040226300580000/receipt.json')
controller = read('structure-three-audit01/controller-audit-public-1794041050905022800/audit.json')
actor = read('independent-actor-three-terminal-review-01/summary.json')
labels = read('independent-actor-three-terminal-review-01/labels.json')
judge = read('complete-review-three-01/judge-semantic-review.json')
observer = read('complete-review-three-01/observer-image-review-01/prediction-join-review.json')
preservation = read('three-preservation-completion-report-01/report.json')
assert service['request_count'] == 119 and service['native_primary_EOS'] == 97
assert service['all20_observer_raw_BF16_to_CPU_native_probabilities_exact']
assert controller['integrity_audit_passed']
for key, value in {'candidate_count': 24, 'accepted_count': 19, 'actual_execution_log_count': 19,
                   'observer_packets': 24, 'same_response_reuses': 4}.items():
    assert controller['runs'][0][key] == value
assert controller['two_stale_runs_zero_calls_unstarted']
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
    'status': 'passed_local_available_source_SHA_and_coverage_coherence',
    'scope': 'Every available selected public copy and explicit expected receipt SHA is checked. Full remote Controller seal remains separately attributed to completed remote audit; not a claim of full local mirroring.',
    'expected_reference_hashes_verified': verified, 'seal_audits': seal_audits,
    'total_local_seal_entries_checked': sum(x['verified_local_entries'] for x in seal_audits),
    'remote_only_seal_entries_not_newly_local_rehashed': sum(len(x['remote_only_entries']) for x in seal_audits),
    'candidate_judge_observer_counts': [24, 73, 20],
    'postlabel_execution_join_not_in_this_receipt': True,
    'original_actor_labels_sha256_unchanged': sha(BASE / 'independent-actor-three-terminal-review-01/labels.json'),
    'linked_failure_record_sha256': sha(FAILURE),
    'new_model_GUI_health_scorer_or_remote_calls': 0
}
OUT.mkdir()
(OUT / 'receipt.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(OUT / 'seal.json').write_text(json.dumps({'receipt.json': sha(OUT / 'receipt.json'),
    '../verify_complete_review_sources.py': sha(SOURCE),
    '../verify_complete_review_sources_linked02.py': sha(Path(__file__)),
    '../source-verification-failure-01.json': sha(FAILURE)}, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': report['status'], 'local_entries': report['total_local_seal_entries_checked'],
    'remote_only_entries': report['remote_only_seal_entries_not_newly_local_rehashed'],
    'receipt_sha256': sha(OUT / 'receipt.json'), 'seal_sha256': sha(OUT / 'seal.json')}))
