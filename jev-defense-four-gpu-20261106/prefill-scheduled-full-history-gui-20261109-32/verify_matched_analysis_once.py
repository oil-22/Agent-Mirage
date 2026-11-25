"""Seal one synthetic CPU analysis check, with no runtime or model mutation."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
PACKAGE = HERE / 'runtime-package'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write('\n')


def main():
    pointer = HERE / 'matched-analysis-preparation-created.json'
    assert not pointer.exists(), 'Completed preparation is immutable; do not rerun it'
    root = HERE / ('matched-analysis-preparation-' + str(time.time_ns()))
    root.mkdir()
    manifest_sha = sha(PACKAGE / 'manifest.json')
    assert manifest_sha == 'c83af050ba64c4edb4d9a1aeff6ebc9f4195e04ef576dd1906791d690e07a5f1'
    manifest = json.loads((PACKAGE / 'manifest.json').read_bytes())
    for name, expected in manifest['files'].items():
        assert sha(PACKAGE / name) == expected, name
    assert sha(PACKAGE / 'private.token') == manifest['auth_token_sha256']
    names = ['matched_outcome_analysis.py', 'check_matched_outcome_analysis.py',
             'verify_matched_analysis_once.py', 'matched_outcome_analysis.initial-unexecuted.py.txt']
    sources = {name: sha(HERE / name) for name in names}
    for name in names:
        (root / name).write_bytes((HERE / name).read_bytes())
    (root / 'frozen-plan.json').write_bytes((PACKAGE / 'plan.json').read_bytes())
    evidence = HERE / 'actual-evidence-1794248679500548200'
    for name, expected in json.loads((evidence / 'seal.json').read_bytes()).items():
        assert sha(evidence / name) == expected
    primary, gui = [json.loads((evidence / name).read_bytes()) for name in ['3090.json', '4090.json']]
    save(root / 'intent.json', dict(time=time.time(),
        purpose='Synthetic descriptive analysis controls for the original32, not inference or semantic controls',
        previous_goal_turn_classification='prompt disclosure; original auxiliary receipt hashes independently rechecked',
        preparation_timing='After source review through candidate38 and known c37 false rejection/c38 uncertainty; not fully blind preregistration',
        last_actual_evidence=str(evidence), last_actual_evidence_seal_sha256=sha(evidence/'seal.json'),
        primary_state=primary['worker/status.json']['value'],
        GUI_state=gui['batch/status.json']['value'],
        model_GUI_scorer_paid_calls=0, actual32_result_records_fed_to_math=False,
        frozen_runtime_modified=False, original32_endpoints_scope_and_budgets_unchanged=True))
    result = subprocess.run([sys.executable, '-B', str(HERE / 'check_matched_outcome_analysis.py')],
                            cwd=HERE, capture_output=True)
    (root / 'checks.stdout.txt').write_bytes(result.stdout)
    (root / 'checks.stderr.txt').write_bytes(result.stderr)
    for name, expected in sources.items():
        assert sha(HERE / name) == expected, name
    for name, expected in manifest['files'].items():
        assert sha(PACKAGE / name) == expected, name
    assert sha(PACKAGE / 'manifest.json') == manifest_sha
    save(root / 'receipt.json', dict(time=time.time(), passed=result.returncode == 0,
        test_process_exit_code=result.returncode, sources=sources,
        frozen_manifest_sha256=manifest_sha, frozen_plan_sha256=sha(PACKAGE/'plan.json'),
        frozen_runtime_bytes_reverified_unchanged=True,
        labels_generated=False, new_model_GUI_scorer_paid_calls=0,
        actual32_result_records_fed_to_math=False,
        provenance_flags_or_supplied_references_do_not_verify_source_receipts=True,
        no_efficacy_or_goal_completion_established=True))
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    record = dict(root=str(root), passed=result.returncode == 0,
        receipt_sha256=sha(root/'receipt.json'), seal_sha256=sha(root/'seal.json'))
    save(HERE / (('matched-analysis-preparation-created' if result.returncode == 0 else
                  'matched-analysis-preparation-failed-' + root.name.split('-')[-1]) + '.json'), record)
    print(json.dumps(record))
    if result.returncode:
        print(result.stderr.decode('utf8', errors='replace'))
        raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
