"""Local-only SHA and coverage audit; never imports any model or remote helper."""
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / 'source-verification-01'

EXPECTED = {
    'structure-three-audit01/service-audit-public-1794040226300580000/receipt.json': 'ed32b419a92d671ffe2aebec0a69150ad8cf20b02bef407aa365bf78fcfcbff0',
    'structure-three-audit01/service-audit-public-1794040226300580000/seal.json': 'dd11d1db5572f7613c006c7ac192ca7097572e878f265d9f3297dd468a218cac',
    'structure-three-audit01/controller-audit-public-1794041050905022800/audit.json': '458dd8c85733ef6a52ec0ef1bc33741c608afe55b1484b5a3804378487f87bf7',
    'structure-three-audit01/controller-audit-public-1794041050905022800/seal.json': '2ff8c651eaeb8cc3d469758999be705b106479a5d9ee59de62172c019d630519',
    'structure-three-audit01/structural-summary-1794041050905022800/summary.json': 'c19db2279d7ccc0409b57f3488bb5fa43a42b8879b65a88ebb7bc43ca2c335bb',
    'structure-three-audit01/structural-summary-1794041050905022800/seal.json': '41a98bac5496a89eae0799d15f58da59b3ca82046947ec27ce628cf90a4fb3e1',
    'independent-actor-three-terminal-review-01/labels.json': '06acee5ddcb9c2b3d3b24e90f4d7752ad65233b246392e9d2625f1f8a95b8d6b',
    'independent-actor-three-terminal-review-01/summary.json': 'dc0feafc6a63fe42c02ef10c25cbd0fb5b2303f75310122bc52f28f7a5d41ebd',
    'complete-review-three-01/judge-semantic-review-seal.json': 'fefb3f60a67312535838b14bdda494338056d7b0979e8c0c5a0392c81cf0b14f',
    'complete-review-three-01/judge-legal-projection-linked03/seal.json': 'c957edb509f19fe7135a07fab95db46a18ec44b404dcc80db0fda315e453b248',
    'complete-review-three-01/observer-image-review-01/source-first-visual-seal.json': '18c849b55c22da4633224449e1166061f3d2acc54490a97e35acfcfe9133cc6c',
    'complete-review-three-01/observer-image-review-01/replies.json': '8c268d2954b8cf90056e2193b6633e08b664e44c4a3b346a67be773a3875abe5',
    'complete-review-three-01/listing-row-coverage-root-seal.json': 'f491c6b94d568e3c4e803b669665ec2ccfa313b0d20b9ff4a037515df1c95858',
    'three-preservation-completion-report-01/report.json': '1d36f5671c5809972b07b8047b87a288a91a88f79971d12f56b04adcbc10a1e5',
    'three-preservation-completion-report-01/seal.json': '287e2674c073351cc25e5fa636efbb28c029bf1fd7310ba250c2ea8898bac778',
    'three-terminal-postexit-public/1794040388947724400/report.json': 'd90bb52aec860bcc3ca418537543fe58fa50df795a7347995698a7ed92a666b2',
}

SEALS = [
    'structure-three-audit01/service-audit-public-1794040226300580000/seal.json',
    'structure-three-audit01/controller-audit-public-1794041050905022800/seal.json',
    'structure-three-audit01/structural-summary-1794041050905022800/seal.json',
    'independent-actor-three-terminal-review-01/seal.json',
    'complete-review-three-01/judge-semantic-review-seal.json',
    'complete-review-three-01/judge-legal-projection-linked03/seal.json',
    'complete-review-three-01/judge-semantic-reading-linked02/seal.json',
    'complete-review-three-01/observer-image-review-01/seal.json',
    'complete-review-three-01/observer-image-review-01/source-first-visual-seal.json',
    'complete-review-three-01/observer-image-review-01/prediction-join-seal.json',
    'complete-review-three-01/listing-row-coverage-root-seal.json',
    'complete-review-three-01/last-frame-source-01/seal.json',
    'complete-review-three-01/service-stop-evidence/1794040246954317800/seal.json',
    'three-preservation-completion-report-01/seal.json',
    'three-terminal-postexit-public/1794040388947724400/seal.json',
]


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(rel):
    return json.loads((BASE / rel).read_text(encoding='utf-8-sig'))


def main():
    assert not OUT.exists(), 'Once-only output already exists; do not overwrite.'
    verified = {}
    for rel, expected in EXPECTED.items():
        actual = sha(BASE / rel)
        assert actual == expected, (rel, expected, actual)
        verified[rel] = actual
    seal_audits = []
    for rel in SEALS:
        path = BASE / rel
        value = json.loads(path.read_text(encoding='utf-8-sig'))
        mapping = value.get('files', value)
        checked = []
        for name, expected in mapping.items():
            if not isinstance(expected, str) or len(expected) != 64:
                continue
            resolved = path.parent / name
            # Two root-created source-first seals name the script basename;
            # the original writer is explicitly one directory above the data.
            if not resolved.exists() and name.endswith('.py'):
                alternate = path.parent.parent / name
                assert alternate.exists(), (rel, name)
                resolved = alternate
            assert resolved.is_file(), (rel, name)
            actual = sha(resolved)
            assert actual == expected, (rel, name, expected, actual)
            checked.append({'name_in_original_seal': name,
                            'actual_local_path': str(resolved.relative_to(BASE)),
                            'sha256': actual})
        assert checked, rel
        seal_audits.append({'seal': rel, 'sha256': sha(path),
                            'verified_entries': len(checked), 'entries': checked})

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
    assert controller['runs'][0]['candidate_count'] == 24
    assert controller['runs'][0]['accepted_count'] == 19
    assert controller['runs'][0]['actual_execution_log_count'] == 19
    assert controller['runs'][0]['observer_packets'] == 24
    assert controller['runs'][0]['same_response_reuses'] == 4
    assert controller['two_stale_runs_zero_calls_unstarted']
    assert actor['complete_candidates'] == len(labels) == 24
    assert actor['definite_candidate_ordinals'] == [23]
    assert actor['unresolved_candidate_ordinals'] == [5, 7, 11]
    assert actor['native_action_error_ordinals'] == [23, 24]
    assert len(judge['rows']) == judge['count'] == 73
    assert sum(judge['phase_counts'].values()) == 73
    assert judge['actual_duplicate_key_replies'] == 0
    assert observer['count'] == len(observer['rows']) == 20
    assert preservation['actual_worker_exit_codes'] == {'primary': 0, 'pplx_flash': 0}
    assert preservation['all_workers_and_launcher_absent']
    assert preservation['holder9locks_remain']
    assert preservation['terminal_manifest_entries_verified'] == 848
    report = {'status': 'passed_local_source_SHA_and_coverage_coherence',
              'scope': 'Local public artifacts and sealed audit receipts only; remote source audits remain separately attributed.',
              'expected_reference_hashes_verified': verified,
              'seal_audits': seal_audits,
              'total_seal_entries_checked': sum(x['verified_entries'] for x in seal_audits),
              'candidate_judge_observer_counts': [24, 73, 20],
              'postlabel_execution_join_not_in_this_receipt': True,
              'new_model_GUI_health_scorer_or_remote_calls': 0}
    OUT.mkdir()
    (OUT / 'receipt.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (OUT / 'seal.json').write_text(json.dumps({'receipt.json': sha(OUT / 'receipt.json'),
        '../verify_complete_review_sources.py': sha(Path(__file__))}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'seal_entries': report['total_seal_entries_checked'],
                      'receipt_sha256': sha(OUT / 'receipt.json'), 'seal_sha256': sha(OUT / 'seal.json')}))


if __name__ == '__main__':
    main()
