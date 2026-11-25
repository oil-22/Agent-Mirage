"""Prepare a new namespace only; never construct a manifest, stage or submit."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REVISION = HERE.parent
PRIOR = REVISION / 'gpu-preflight-launcher-01'
OLD_SOURCE = PRIOR / 'launcher-linked02'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def copy_bytes(name, raw):
    with (HERE / name).open('xb') as stream:
        stream.write(raw)


def function_AST(text):
    return {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(text).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}


assert sha(OLD_SOURCE / 'resource_gate.py') == 'ceb7d82c9be30f67fe84813aced2db61704e05ab45f5230166c25f36060dcfb5'
assert sha(OLD_SOURCE / 'launch_once.py') == '43b51d6e2d4ca6e6dd537931671e9ba383e03c72e938c239dc1e3837a88630f6'
gate_raw = (OLD_SOURCE / 'resource_gate.py').read_bytes()
copy_bytes('resource_gate.py', gate_raw)
old_launcher = (OLD_SOURCE / 'launch_once.py').read_text(encoding='utf-8')
old_package = "PACKAGE = RUNTIME / 'single-jev-9b-preflight-01'"
new_package = "PACKAGE = RUNTIME / 'single-jev-9b-compact-preflight-02'"
assert old_launcher.count(old_package) == 1
launcher = old_launcher.replace(old_package, new_package)
assert function_AST(launcher) == function_AST(old_launcher), 'All safety/preservation/claim/journal function ASTs remain identical'
copy_bytes('launch_once.py', launcher.encode('utf-8'))

old_builder_path = PRIOR / 'build_gpu_manifest_linked02.py'
assert sha(old_builder_path) == '1d30f18f26c59c822d9482f0c0ebf0b25c7d0d3cfd97373db8c1b225b8e5ed8f'
builder = old_builder_path.read_text(encoding='utf-8')
changes = [
    ("LINKED_SOURCE = HERE / 'launcher-linked02'", 'LINKED_SOURCE = HERE'),
    ("IMAGE_IDS = ['S01', 'S07', 'S13', 'S25']", "IMAGE_IDS = ['S04', 'S10', 'S16', 'S19']"),
    ("FOUR_IMAGE_PACKAGE_SEAL_SHA256 = '6642cda7f28f978a9868a5b82844216cd32765d8788d74a8ba8e350d110c15c8'\n", ''),
    ("                'launcher_output_root', 'cpu_input_manifest_local_path']:",
     "                'launcher_output_root', 'cpu_input_manifest_local_path', 'final_worker_source_local_path',\n                'input_package_local_root', 'input_package_seal_sha256', 'current_weight_identity_reuse']:") ,
    ("        'metadata_files': cpu['metadata_files'], 'weight_files': weights, 'requests': requests,",
     "        'metadata_files': cpu['metadata_files'], 'weight_files': weights, 'requests': requests,\n        'current_weight_identity_reuse': value['current_weight_identity_reuse'],"),
    ("    worker = REVISION_ROOT / 'native_image_gpu_preflight.py'", "    worker = Path(value['final_worker_source_local_path'])"),
    ("    package = REVISION_ROOT / 'four-image-inputs-01'", "    package = Path(value['input_package_local_root'])"),
    ('    verify_local_seal(package, FOUR_IMAGE_PACKAGE_SEAL_SHA256)', "    verify_local_seal(package, value['input_package_seal_sha256'])"),
    ("'fresh_full_weight_hash_still_required_before_load': True,",
     "'reuse_first_terminal_current_weight_identity_with_complete_new_stat_gate': True,\n        'new_full_weight_rehash_requested': False,"),
]
for old, new in changes:
    assert builder.count(old) == 1, 'Only expected new-attempt source changes are allowed'
    builder = builder.replace(old, new)
ast.parse(builder)
copy_bytes('build_compact_gpu_manifest.py', builder.encode('utf-8'))

pending = {
    'root_execution_review': False,
    'attempt_id': 'single-jev-9b-compact-four-first-attempts-02',
    'final_worker_source_local_path': None,
    'final_worker_source_sha256': None,
    'lease_sha256': '8f5da746fbb45c587d23a0073f8dc62dcd9510b321b4cef0995c09aa8c92a89a',
    'official_base_api_sha256': 'aeea4ace23a6c865d20b47b20626e18738e0dee9f24045c679d0d9008bc8c1b2',
    'launcher_output_root': '/home/researcher/jev-defense-four-gpu-20261106/single-evidence-revision-20261107/gpu-compact-four-first-attempts-02',
    'cpu_input_manifest_local_path': None,
    'input_package_local_root': None,
    'input_package_seal_sha256': None,
    'prior_weight_identity_local_path': 'D:/MultiModel/attention-audit-20261031/model-sha256-3090.json',
    'current_weight_identity_reuse': None,
    'cpu_proof': {'local_root': None, 'remote_root': None, 'seal_sha256': None},
    'source_labels': {'local_root': None, 'remote_root': None, 'seal_sha256': None},
}
with (HERE / 'builder-inputs.pending.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(pending, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
receipt = {
    'mode': 'new_compact_namespace_code_preparation_only',
    'source_gate_sha256': sha(HERE / 'resource_gate.py'),
    'source_gate_identical_to_prior_linked02': True,
    'prior_launcher_sha256': sha(OLD_SOURCE / 'launch_once.py'),
    'new_launcher_sha256': sha(HERE / 'launch_once.py'),
    'all_launcher_functions_and_classes_AST_identical_to_prior': True,
    'launcher_only_literal_change': {'old_package': 'single-jev-9b-preflight-01',
                                     'new_package': 'single-jev-9b-compact-preflight-02'},
    'builder_sha256': sha(HERE / 'build_compact_gpu_manifest.py'),
    'new_request_ids': ['S04', 'S10', 'S16', 'S19'],
    'new_condition': 'compact: up to6texts+6elements+2uncertainties; one lossless single-json fence allowed',
    'new_output_tokens': 2048, 'new_first_attempts_cap': 4, 'automatic_format_retries': 0,
    'original_24_auxiliary_cap_cumulative_after_this_future_stage': 8,
    'completed_first_four_controls_requeued': False,
    'first_terminal_weight_identity_reuse_field_schema': 'pending_root_final_worker_and_121_file_terminal_bindings',
    'new_19GB_weight_hash_requested': False,
    'new_manifest_constructed_or_GPU_launched': False,
    'root_new_CPU_proof_source_labels_contract_worker_bindings_pending': True,
    'new_tests_repeated': 0, 'stage_submit_model_GPU_GUI_health_network_calls': 0,
}
with (HERE / 'source-preparation-receipt.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(receipt, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(receipt))
