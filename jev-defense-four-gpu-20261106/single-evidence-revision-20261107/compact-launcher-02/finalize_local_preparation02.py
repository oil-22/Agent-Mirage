"""Audit and seal the root-selected files-list preparation, without launching."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FROZEN = HERE / 'frozen-compact-gpu-02'
OUT = HERE / 'final-preparation-receipt-02'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_bytes())


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


OUT.mkdir(exist_ok=False)
inputs = read(HERE / 'builder-inputs.final.json')
specification = read(FROZEN / 'launch-specification.json')
manifest = read(FROZEN / 'gpu-manifest.json')
spec = importlib.util.spec_from_file_location('compact02_final_check_worker', ROOT / 'native_image_gpu_preflight_compact02.py')
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)
worker.validate_manifest(manifest)
worker.verify_seal(FROZEN, sha(FROZEN / 'seal.json'))
worker.verify_seal(inputs['source_labels']['local_root'], inputs['source_labels']['seal_sha256'])
assert [x['request_id'] for x in manifest['requests']] == ['S04', 'S10', 'S16', 'S19']
assert specification['manifest']['sha256'] == sha(FROZEN / 'gpu-manifest.json')
assert specification['worker_source']['sha256'] == sha(FROZEN / 'native_image_gpu_preflight.py')
assert sha(FROZEN / 'native_image_gpu_preflight.py') == inputs['final_worker_source_sha256']
assert manifest['source_labels']['seal_sha256'] == inputs['source_labels']['seal_sha256']
old_tree = ast.parse((ROOT / 'native_image_gpu_preflight.py').read_text(encoding='utf-8'))
new_tree = ast.parse((ROOT / 'native_image_gpu_preflight_compact02.py').read_text(encoding='utf-8'))
functions = lambda tree: {x.name: ast.dump(x, include_attributes=False) for x in tree.body if isinstance(x, (ast.FunctionDef, ast.ClassDef))}
old, new = functions(old_tree), functions(new_tree)
changed = [name for name in old if old[name] != new[name]]
assert changed == ['validate_manifest', 'current_weight_identity']
assert old['run'] == new['run']
tests = ROOT / 'compact02-weight-reuse-CPU-01'
test_report = read(tests / 'report.json')
assert test_report['passed'] == 35 and test_report['failed'] == 0
assert sha(tests / 'seal.json') == 'eb60a865a5be72d9f45d5767992b08e955c3704da3824933cfd8410bf73507b7'
qualification = {
    'original_test_report_unchanged': True, 'tests_rerun': False,
    'case': 'stop_marker_before_shard_admission',
    'original_generic_outcome_text': 'admitted_without_shard_read',
    'actual_asserted_behavior': 'Requested stop marker RuntimeError was raised and asserted; admission was refused',
    'scope': 'reporter generic success-label qualification only; stop was never admitted',
}
write_new(OUT / 'reporter-qualification.json', qualification)
write_new(OUT / 'AST-diff.json', {
    'changed_function_or_class_ASTs': changed,
    'all_other_function_or_class_ASTs_identical': True, 'run_and_generation_AST_unchanged': True,
    'added_constant': 'WEIGHT_REUSE_SOURCE_ROOT',
    'manifest_change': 'only new ordered image IDs and required current_weight_identity_reuse field',
    'identity_change': 'sealed original full SHA identity plus current exact size/mtime_ns/inode; metadata current hashes',
})
receipt = {
    'status': 'prepared_for_root_review_not_submitted',
    'selected_local_frozen_root': str(FROZEN), 'frozen_seal_sha256': sha(FROZEN / 'seal.json'),
    'GPU_manifest_sha256': sha(FROZEN / 'gpu-manifest.json'),
    'launch_specification_sha256': sha(FROZEN / 'launch-specification.json'),
    'holder_command_sha256': sha(FROZEN / 'holder-command.review-only.json'),
    'worker_sha256': sha(ROOT / 'native_image_gpu_preflight_compact02.py'),
    'resource_gate_sha256': sha(FROZEN / 'resource_gate.py'), 'launcher_sha256': sha(FROZEN / 'launch_once.py'),
    'cpu_proof': manifest['cpu_proof'], 'source_labels': {**manifest['source_labels'], 'local_root': inputs['source_labels']['local_root']},
    'original_source_label_seal_sha256': '688f27b2fa0f28b31f3e3cf5632efe1316f3dcaee364407478fcf94d078485c1',
    'source_label_body_unchanged': True, 'source_label_original_seal_preserved_as': 'source-seal.original.json',
    'CPU_weight_reuse_tests': {'passed': 35, 'failed': 0, 'seal_sha256': sha(tests / 'seal.json'),
        'actual_deployed_weight_bytes_read': 0, 'stop_marker_reporter_qualification': 'reporter-qualification.json'},
    'current_weight_identity_reuse': manifest['current_weight_identity_reuse'],
    'four_first_attempts_only': True, 'output_cap': 2048, 'automatic_format_retries': 0,
    'first_terminal_images_not_retried': True, 'new_source_ids': [x['request_id'] for x in manifest['requests']],
    'new_model_GPU_GUI_network_requests_by_this_preparation': 0,
    'actual_resource_gate_not_run_locally': True, 'GPU_model_not_loaded': True,
    'root_review_required_before_root_submits': True, 'semantic_or_Mirage_success_claimed': False,
    'unselected_plain_map_linked_preparation': {
        'local_root': str(HERE / 'frozen-compact-gpu-plainmap-linked02'),
        'reason': 'created before root clarified to retain the already frozen files-list package; never selected or submitted',
        'preserved_without_modification': True,
    },
}
write_new(OUT / 'receipt.json', receipt)
write_new(OUT / 'source-bindings.json', {str(path): sha(path) for path in [
    ROOT / 'native_image_gpu_preflight_compact02.py', ROOT / 'test_compact02_weight_reuse.py',
    ROOT / 'prepare_compact_gpu_worker02.py', HERE / 'build_compact_gpu_manifest.py',
    HERE / 'freeze_compact_inputs02.py', HERE / 'freeze_plainmap_labels_linked02.py',
    HERE / 'builder-inputs.final.json', Path(__file__),
]})
write_new(OUT / 'seal.json', {p.name: sha(p) for p in sorted(OUT.iterdir()) if p.is_file()})
print(json.dumps({'frozen_seal_sha256': receipt['frozen_seal_sha256'],
    'manifest_sha256': receipt['GPU_manifest_sha256'], 'spec_sha256': receipt['launch_specification_sha256'],
    'final_receipt_seal_sha256': sha(OUT / 'seal.json'), 'submitted': False}))
