"""New mechanical replay of immutable old replies; zero new inference or labels."""
import hashlib
import json
from pathlib import Path
from claim_origin import check_claim_origins

HERE = Path(__file__).parent
BASE = HERE.parents[1]
SOURCE = BASE / 'complete-review-three-01' / 'judge-legal-projection-linked03' / 'review' / 'judges'
OUT = HERE / 'original-reply-regression-01'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not OUT.exists()
    rows = []
    for path in sorted(SOURCE.glob('*.json')):
        packet = json.loads(path.read_text(encoding='utf-8'))
        if packet['phase'] != 'verify':
            continue
        candidate = packet['original_verifier_request']['candidate']
        verdict = json.loads(packet['raw_response'])
        check = check_claim_origins(verdict, candidate)
        rows.append({'source': str(path.relative_to(BASE)), 'source_sha256': sha(path),
                     'actual_wire_sha256': packet['actual_wire_sha256'],
                     'judge_ordinal': int(path.stem), 'check': check})
    assert len(rows) == 25
    # Known synthetic JSON-looking claim text must not gain candidate origin.
    for ordinal in (72, 73):
        row = next(x for x in rows if x['judge_ordinal'] == ordinal)
        assert row['check']['reject']
    OUT.mkdir()
    report = {'status': 'completed_CPU_original_reply_origin_regression',
        'original_verify_replies': len(rows),
        'replies_with_any_claim_not_exact_candidate_span_under_NEW_contract': sum(x['check']['reject'] for x in rows),
        'replies_with_all_claims_exactly_source_bound': sum(not x['check']['reject'] for x in rows),
        'scope': 'Old raw replies are frozen regression data. A paraphrase rejected by the new quote contract is not retroactively a semantic error or old protocol failure. No missing assertion or negation-scope semantics are certified.',
        'known_72_73_fabricated_claim_extraction_caught': True,
        'new_model_GUI_scorer_calls': 0, 'labels_or_verdicts_modified': False,
        'new_generalization_or_Mirage_reduction_result': False, 'rows': rows}
    target = OUT / 'receipt.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (OUT / 'seal.json').write_text(json.dumps({'receipt.json': sha(target),
        '../replay_original_extraction.py': sha(Path(__file__)), '../claim_origin.py': sha(HERE / 'claim_origin.py')}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key != 'rows'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
