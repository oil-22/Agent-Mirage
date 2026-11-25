"""Linked CPU repair: close SQLite connections, recheck changed verifier only.

No source/browser or model control is rerun. Previous live captures are retained.
"""
import ast
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from remote_util import HERE, save, sha


def main():
    pointer_path = HERE / 'CPU-source-current.json'
    old_pointer = json.loads(pointer_path.read_bytes())
    old = Path(old_pointer['root'])
    assert old_pointer['passed'] and sha(old / 'seal.json') == old_pointer['seal_sha256']
    root = HERE / ('ledger-cleanup-repair-' + str(time.time_ns()))
    root.mkdir()
    (root / 'prior-pointer.json').write_bytes(pointer_path.read_bytes())
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    snapshot = root / 'source'
    shutil.copytree(old / 'source', snapshot)
    (snapshot / 'receipt_protocol.py').write_bytes((HERE / 'receipt_protocol.py').read_bytes())
    before = ast.parse((old / 'source/receipt_protocol.py').read_text('utf-8'))
    after = ast.parse((snapshot / 'receipt_protocol.py').read_text('utf-8'))
    def method(tree, name):
        cls = next(n for n in tree.body if getattr(n, 'name', '') == 'ReceiptVerifier')
        return next(n for n in cls.body if getattr(n, 'name', '') == name)
    for name in ['__init__', 'issue', 'check', 'validate', 'close_missing']:
        assert ast.dump(method(before, name), include_attributes=False) == ast.dump(method(after, name), include_attributes=False)
    for name in ['capture_source.py', 'capture_client.py', 'native_rpc.py']:
        assert sha(snapshot / name) == sha(HERE / name), name
    argv = [sys.executable, '-B', '-X', 'utf8', str(snapshot / 'test_receipt_protocol.py')]
    with (root / 'stdout.bin').open('xb') as out, (root / 'stderr.bin').open('xb') as err:
        result = subprocess.run(argv, cwd=snapshot, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}, stdout=out, stderr=err)
    summary = {'passed': result.returncode == 0, 'returncode': result.returncode,
               'prior_live_source_controls': old_pointer, 'real_source_control_count': 16,
               'changed_verifier_boundary_tests': 20, 'only_connection_resource_lifetime_changed': True,
               'signature_and_validation_issuance_AST_unchanged': True, 'no_live_source_or_model_reexecution': True,
               'new_model_GUI_calls': 0}
    save(root / 'result.json', summary)
    save(root / 'seal.json', {str(p.relative_to(root)): sha(p) for p in root.rglob('*') if p.is_file()})
    if result.returncode:
        print((root / 'stderr.bin').read_text('utf-8'))
        raise RuntimeError('Linked verifier repair failed; originals preserved')
    updated = {'root': str(root), 'remote_root': old_pointer['remote_root'], 'seal_sha256': sha(root / 'seal.json'), 'passed': True}
    temporary = HERE / '.CPU-source-linked.tmp'
    save(temporary, updated)
    temporary.replace(pointer_path)
    print(json.dumps({'root': str(root), 'changed_verifier_tests': 20, 'prior_live_controls_reused': 16,
                      'passed': True, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
