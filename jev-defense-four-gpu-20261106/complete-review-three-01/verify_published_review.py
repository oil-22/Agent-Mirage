"""Final local verification of receipt references and published document heads."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def check_seal(path):
    for rel, expected in load(path).items():
        assert sha(path.parent / rel) == expected, (str(path), rel)


assert not (ROOT / 'final-verification.json').exists()
check_seal(ROOT / 'completion-seal.json')
receipt = load(ROOT / 'completion-receipt.json')
for rel, expected in receipt['source_sha256_relative_to_experiment_directory'].items():
    assert sha(BASE / rel) == expected, rel
publication = ROOT / 'publication-01'
check_seal(publication / 'seal.json')
pub = load(publication / 'receipt.json')
for rel, expected in pub['before_document_SHA256'].items():
    assert sha(publication / (rel + '.before')) == expected
for rel, expected in pub['after_document_SHA256'].items():
    assert sha(BASE / rel) == expected
    text = (BASE / rel).read_text(encoding='utf-8')
    assert '完整审查' in text[:500]
pointer = load(BASE / 'complete-review-three-current.json')
assert pointer['completion_receipt_sha256'] == sha(ROOT / 'completion-receipt.json')
assert pointer['completion_seal_sha256'] == sha(ROOT / 'completion-seal.json')
assert (BASE / pointer['report']).is_file()
assert receipt['new_model_GUI_health_scorer_calls_during_review'] == 0
assert not receipt['substantial_defense_effect_demonstrated']
assert receipt['candidate_semantics']['ordinals'] == [23]
assert receipt['additional_unresolved_candidates']['ordinals'] == [5, 7, 11]
result = {
    'status': 'passed_completion_sources_seals_and_published_heads',
    'source_references_verified': len(receipt['source_sha256_relative_to_experiment_directory']),
    'completion_receipt_sha256': sha(ROOT / 'completion-receipt.json'),
    'completion_seal_sha256': sha(ROOT / 'completion-seal.json'),
    'publication_receipt_sha256': sha(publication / 'receipt.json'),
    'publication_seal_sha256': sha(publication / 'seal.json'),
    'source_labels_unchanged': True,
    'historical_document_bytes_backed_up': True,
    'new_model_GUI_health_scorer_or_remote_calls': 0,
    'defense_efficacy_demonstrated': False
}
(ROOT / 'final-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(ROOT / 'final-verification-seal.json').write_text(json.dumps({
    'final-verification.json': sha(ROOT / 'final-verification.json'),
    'verify_published_review.py': sha(Path(__file__))}, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
