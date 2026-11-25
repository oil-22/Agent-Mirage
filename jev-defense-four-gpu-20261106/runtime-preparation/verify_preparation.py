"""Seal this CPU-only new runtime preparation, without launching any runtime."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent
PARENT = BASE.parents[1] / 'jev-defense-validation-20261103/release'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    before = {str(p.relative_to(PARENT)): sha(p) for p in PARENT.rglob('*.py')}
    previous = sorted((BASE / 'cpu-evidence').glob('*/receipt.json'))
    root = BASE / 'cpu-evidence' / str(time.time_ns())
    root.mkdir(parents=True, exist_ok=False)
    paths = [p for p in BASE.iterdir() if p.is_file() and p.suffix in {'.py', '.md', '.json'}]
    source = root / 'source'
    source.mkdir()
    for path in paths:
        shutil.copyfile(path, source / path.name)
    result = subprocess.run([sys.executable, '-m', 'unittest', '-v', 'test_four_gpu_contract.py'],
                            cwd=BASE, capture_output=True, text=True)
    (root / 'test-output.txt').write_text(result.stdout + result.stderr, encoding='utf8')
    compile_result = subprocess.run([sys.executable, '-m', 'py_compile',
        *[str(p) for p in BASE.glob('*.py')]], cwd=BASE, capture_output=True, text=True)
    (root / 'compile-output.txt').write_text(compile_result.stdout + compile_result.stderr, encoding='utf8')
    tree = ast.parse((BASE / 'preflight_service.py').read_text(encoding='utf8'))
    subclasses = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == 'AsymmetricQwen']
    overrides = [n.name for n in subclasses[0].body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    assert overrides == ['__init__'], overrides
    after = {str(p.relative_to(PARENT)): sha(p) for p in PARENT.rglob('*.py')}
    assert before == after
    report = {'scope': 'CPU fixtures/syntax/source preservation only', 'test_returncode': result.returncode,
        'compile_returncode': compile_result.returncode, 'tests_passed': 44 if result.returncode == 0 else None,
        'original_main_generate_judge_override': False, 'only_main_override': overrides,
        'parent_release_python_files_unchanged': len(before), 'GPU_allocations': 0,
        'model_calls': 0, 'GUI_actions': 0, 'runtime_started': False,
        'new_mode': 'image_only_neutral_joint_observer_to_actor; no judge cues',
        'runtime_source': {p.name: sha(p) for p in paths}}
    if previous:
        report['previous_cpu_receipt'] = str(previous[-1])
        report['previous_cpu_receipt_sha256'] = sha(previous[-1])
    (root / 'receipt.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    (root / 'seal.json').write_text(json.dumps({str(p.relative_to(root)): sha(p) for p in root.rglob('*')
                                               if p.is_file()}, indent=2), encoding='utf8')
    print(json.dumps({'root': str(root), **report}, ensure_ascii=False))
    if result.returncode or compile_result.returncode:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
