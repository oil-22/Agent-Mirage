"""Read-only recovery of an uploaded package after a receipt-byte assertion.

Original upload/source/stderr and both differently serialized receipts remain
unchanged. This never stages again and does not change any runtime/source SHA.
"""
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from orchestrate import PACKAGE, GUIROOT, COMMON, remote, save, sha, admitted


def main():
    admitted()
    assert (HERE / 'stage-4090-intent.json').exists() and not (HERE / 'stage-4090.json').exists()
    old = HERE.parent / 'full-history-gui-development-20261109-23/operations/1794226880122664200-stage-linked29-4090-once'
    preservation = HERE / ('stage-reporter-failure-preservation-' + str(time.time_ns())); preservation.mkdir()
    save(preservation / 'receipt.json', {'schema': 'linked29-staging-report-only-failure-preservation-v1',
        'original_operation': str(old), 'original_operation_files_SHA256': {p.name: sha(p) for p in old.iterdir() if p.is_file()},
        'failure': 'Byte comparison of an immutable original receipt and the same parsed JSON reserialized with trailing newline. Upload and118frozen runtime files had already passed their raw SHA checks.',
        'runtime_or_inputs_edited': False, 'model_GPU_GUI_scorer_paid_calls': 0})
    code = 'ROOT=' + repr(GUIROOT) + '\nMSHA=' + repr(sha(PACKAGE / 'manifest.json')) + '\n' + COMMON + r'''
root=Path(ROOT);assert os.getuid()==1015 and root.is_dir()
assert not(root/'background').exists()and not(root/'control').exists()and not(root/'batch').exists()
assert sha(root/'manifest.json')==MSHA
manifest=json.loads((root/'manifest.json').read_bytes())
for name,expected in manifest['files'].items():assert sha(root/name)==expected,name
assert sha(root/'private.token')==manifest['auth_token_sha256']and root.joinpath('private.token').stat().st_mode&0o077==0
old=root.parent/'full-history-gui-development-20261109-23/environment-preflight/receipt.json'
new=root/'environment-preflight/receipt.json'
original=json.loads(old.read_bytes());copied=json.loads(new.read_bytes())
assert original==copied and original['status']=='passed'
source=Path('/data/researcher/jev-defense-validation-20261103/runtime-stage-01/upstream/browser_env/actions.py').read_text()
assert 'MOUSE_CLICK' in source and 'def create_mouse_click_action' in source
state=json.loads((root/'carryover/state.json').read_bytes())
for name,expected in state['native_source_SHA'].items():assert sha(name)==expected,name
assert sha(state['original_trace'])==state['original_trace_sha256']and sha(state['original_private_trajectory'])==state['original_private_trajectory_sha256']
print(json.dumps({'root':str(root),'uid':os.getuid(),'manifest_sha256':MSHA,'files_verified':len(manifest['files']),
 'original_environment_receipt_sha256':sha(old),'copied_environment_receipt_sha256':sha(new),
 'full_parsed_receipts_exact_equal':True,'existing_upload_collected_read_only':True,
 'package_bytes_or_runtime_changed':False,'new_upload_model_GPU_GUI_scorer_calls':0}))
'''
    output, operation = remote('4090', code, 'linked02-read-existing29-staged-package-no-upload-or-model', timeout=55)
    result = json.loads(output)
    save(HERE / 'stage-4090.json', {'result': result, 'operation': str(operation), 'failure_preservation': str(preservation),
        'previous_operation_reexecuted': False})
    print(output)


if __name__ == '__main__':
    main()
