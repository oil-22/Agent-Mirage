"""Seal actual local tests and new original-reply mechanical regression."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / 'contract-CPU-evidence-01'
assert not OUT.exists()
OUT.mkdir()
commands = [('evidence-contract', 'test_image_evidence.py'), ('candidate-origin', 'test_claim_origin.py'),
            ('candidate-origin', 'replay_original_extraction.py')]
records = []
for folder, name in commands:
    command = [sys.executable, str(ROOT / folder / name)]
    result = subprocess.run(command, cwd=ROOT / folder, capture_output=True)
    (OUT / (name + '.stdout')).write_bytes(result.stdout)
    (OUT / (name + '.stderr')).write_bytes(result.stderr)
    records.append({'source': folder + '/' + name, 'returncode': result.returncode,
                    'stdout': name + '.stdout', 'stderr': name + '.stderr'})
    if result.returncode:
        (OUT / 'failure.json').write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')
        raise SystemExit(result.returncode)
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
sources = ['evidence-contract/image_evidence.py', 'evidence-contract/test_image_evidence.py',
           'candidate-origin/claim_origin.py', 'candidate-origin/test_claim_origin.py',
           'candidate-origin/replay_original_extraction.py', Path(__file__).name]
receipt = {'status': 'passed_17_CPU_boundary_tests_and_25_original_reply_regression',
    'evidence_contract_tests': 9, 'candidate_origin_tests': 8, 'commands': records,
    'source_sha256': {name: sha(ROOT / name) for name in sources},
    'replay_receipt_sha256': sha(ROOT / 'candidate-origin/original-reply-regression-01/receipt.json'),
    'live_controller_integrated': False, 'GPU_or_new_model_GUI_scorer_calls': 0,
    'claim_scope_or_semantic_correctness_certified_by_CPU': False}
(OUT / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
seal = {str(p.relative_to(OUT)): sha(p) for p in OUT.iterdir() if p.is_file()}
(OUT / 'seal.json').write_text(json.dumps(seal, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': receipt['status'], 'receipt_sha256': sha(OUT / 'receipt.json'),
                  'seal_sha256': sha(OUT / 'seal.json')}))
