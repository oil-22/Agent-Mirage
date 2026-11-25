"""Seal the new observer wiring checks without changing the earlier receipt."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'observer-wiring-CPU-evidence-01'
OUT.mkdir(exist_ok=False)
test = ROOT / 'evidence-contract/test_evidence_observer.py'
result = subprocess.run([sys.executable, str(test)], cwd=test.parent, capture_output=True)
(OUT / 'stdout.txt').write_bytes(result.stdout)
(OUT / 'stderr.txt').write_bytes(result.stderr)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

sources = ['evidence-contract/image_evidence.py', 'evidence-contract/evidence_observer.py',
           'evidence-contract/test_evidence_observer.py', Path(__file__).name]
receipt = {
    'status': 'passed' if result.returncode == 0 else 'failed',
    'returncode': result.returncode,
    'CPU_wiring_tests': 7,
    'source_sha256': {name: sha(ROOT / name) for name in sources},
    'new_model_GPU_GUI_scorer_calls': 0,
    'real_backend_admitted': False,
    'semantic_quality_or_live_Controller_proven': False,
    'checks': ['one_auxiliary_image_only', 'original_actor_history_and_correction_preserved',
               'raw_invalid_response_preserved_before_validation', 'exact_input_reuse',
               'no_implicit_retry', 'finite_cap', 'wire_image_mismatch_rejected'],
}
(OUT / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(OUT / 'seal.json').write_text(json.dumps({p.name: sha(p) for p in OUT.iterdir() if p.is_file()}, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': receipt['status'], 'receipt_sha256': sha(OUT / 'receipt.json'),
                  'seal_sha256': sha(OUT / 'seal.json')}))
raise SystemExit(result.returncode)
