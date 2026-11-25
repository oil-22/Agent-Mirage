"""Draft builder only. Never stage, submit, import models, hash weights or use SSH.

Root must supply final worker SHA, native CPU proof and source-first label seals.
The launcher reads only source/seal bindings; PRIVATE label bodies never enter a
request or model input. Output paths are new, exclusive local preparation roots.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import traceback

import launch_once as launch


HERE = Path(__file__).resolve().parent
REVISION_ROOT = HERE.parent
IMAGE_IDS = ['S01', 'S07', 'S13', 'S25']
OFFICIAL_API_LOCAL = REVISION_ROOT / 'model-capability-review/native-small-metadata-linked02-1794046900308884400/qwen-fixed-api.json'
FOUR_IMAGE_PACKAGE_SEAL_SHA256 = '6642cda7f28f978a9868a5b82844216cd32765d8788d74a8ba8e350d110c15c8'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def copy_new(source, target):
    with Path(target).open('xb') as stream:
        stream.write(Path(source).read_bytes())
    if sha(source) != sha(target):
        raise ValueError('Local source-copy hash mismatch')


def verify_local_seal(root, expected_sha256):
    root = Path(root)
    path = root / 'seal.json'
    if sha(path) != expected_sha256:
        raise ValueError('Frozen local seal changed')
    value = read(path)
    if isinstance(value, dict) and isinstance(value.get('files'), list):
        entries = [(x.get('path', x.get('file')), x['sha256']) for x in value['files']]
    else:
        entries = list(value.items())
    for name, expected in entries:
        if name is None or not (root / name).resolve().is_relative_to(root.resolve()) or sha(root / name) != expected:
            raise ValueError('Sealed local artifact changed or escaped scope')


def pending_reasons(value):
    missing = []
    if value.get('root_execution_review') is not True:
        missing.append('root_execution_review_not_true')
    for key in ['final_worker_source_sha256', 'lease_sha256', 'official_base_api_sha256',
                'launcher_output_root', 'cpu_input_manifest_local_path']:
        if not value.get(key):
            missing.append(key)
    for role in ['cpu_proof', 'source_labels']:
        item = value.get(role, {})
        for field in ['local_root', 'remote_root', 'seal_sha256']:
            if not item.get(field):
                missing.append(role + '.' + field)
    return missing


def make_manifest(value, cpu, bindings, old, package):
    by_id = {row['id']: row for row in bindings}
    requests = []
    if [x['request_id'] for x in cpu['requests']] != IMAGE_IDS:
        raise ValueError('CPU native source order differs')
    for item in cpu['requests']:
        original = by_id[item['request_id']]
        if item['sha256'] != original['request_sha256']:
            raise ValueError('CPU request body differs from the sealed original package')
        requests.append({**item, 'image_sha256': original['image_sha256']})
    weights = [{'filename': name.split('/', 1)[1], **record} for name, record in old['files'].items()
               if name.startswith('Qwen3.5-9B/') and name.endswith('.safetensors')]
    if len(weights) != 4 or sum(x['bytes'] for x in weights) != 19306310880:
        raise ValueError('Historical complete shard inventory differs')
    return {
        'schema_version': 'single-image-GPU-preflight-v1', 'attempt_id': value['attempt_id'],
        'output_root': value['launcher_output_root'].rstrip('/') + '/worker', 'gpu_authorized': True,
        'cpu_proof': {'root': value['cpu_proof']['remote_root'], 'seal_sha256': value['cpu_proof']['seal_sha256']},
        'source_labels': {'root': value['source_labels']['remote_root'], 'seal_sha256': value['source_labels']['seal_sha256']},
        'input_package': {'path': str(launch.PACKAGE / 'four-image-protocol.original.json'), 'sha256': sha(package / 'protocol.json')},
        'base_model': cpu['base_model'], 'jev_relationship': cpu['jev_relationship'],
        'lease_path': str(launch.LEASE_PATH), 'expected_holder': dict(launch.HOLDER),
        'resource_gate': {'path': str(launch.PACKAGE / 'resource_gate.py'), 'sha256': sha(HERE / 'resource_gate.py')},
        'evidence_contract': {'path': cpu['evidence_contract']['source_path'], 'sha256': cpu['evidence_contract']['sha256']},
        'prior_weight_identity': {'path': cpu['prior_weight_identity']['receipt_path'],
                                  'sha256': cpu['prior_weight_identity']['receipt_sha256']},
        'official_base_api': {'path': str(launch.PACKAGE / 'qwen-fixed-api.json'), 'sha256': value['official_base_api_sha256']},
        'metadata_files': cpu['metadata_files'], 'weight_files': weights, 'requests': requests,
        'generation': {'max_new_tokens': 2048, 'do_sample': False, 'temperature': 1.0, 'top_p': 1.0,
                       'top_k': 0, 'num_beams': 1, 'num_return_sequences': 1, 'eos_token_id': [248044, 248046],
                       'enable_thinking': False, 'seed': 0, 'dtype': 'bfloat16', 'attention_backend': 'sdpa'},
        'limits': {'requests': 4, 'automatic_format_retries': 0, 'semantic_resampling': False,
                   'primary_model_calls': 0, 'GUI_actions': 0, 'scorer': 0, 'paid_API': 0},
    }


def build(value, output):
    output.mkdir(parents=True, exist_ok=False)
    missing = pending_reasons(value)
    if missing:
        write(output / 'pending.json', {'status': 'not_ready', 'missing': missing,
                                       'GPU_manifest_emitted': False, 'no_stage_or_submission': True})
        write(output / 'seal.json', {'pending.json': sha(output / 'pending.json')})
        return
    worker = REVISION_ROOT / 'native_image_gpu_preflight.py'
    if sha(worker) != value['final_worker_source_sha256']:
        raise ValueError('Final root-reviewed worker source SHA is absent or stale')
    if sha(OFFICIAL_API_LOCAL) != value['official_base_api_sha256']:
        raise ValueError('Pinned official base API binding changed')
    api = read(OFFICIAL_API_LOCAL)
    if api.get('id') != launch.MODEL['base_repository'] or api.get('sha') != launch.MODEL['base_revision']:
        raise ValueError('Pinned official base repository/revision differs')
    for role in ['cpu_proof', 'source_labels']:
        item = value[role]
        verify_local_seal(item['local_root'], item['seal_sha256'])
    terminal = read(Path(value['cpu_proof']['local_root']) / 'terminal.json')
    if terminal['status'] != 'completed_native_CPU_admission_no_model' or terminal['admitted_requests'] != 4:
        raise ValueError('Four actual native CPU inputs are not complete')
    cpu = read(value['cpu_input_manifest_local_path'])
    if sha(value['cpu_input_manifest_local_path']) != sha(Path(value['cpu_proof']['local_root']) / 'input-manifest.original.json'):
        raise ValueError('CPU input manifest differs from the sealed actual native proof')
    package = REVISION_ROOT / 'four-image-inputs-01'
    verify_local_seal(package, FOUR_IMAGE_PACKAGE_SEAL_SHA256)
    old_path = Path(value['prior_weight_identity_local_path'])
    if sha(old_path) != cpu['prior_weight_identity']['receipt_sha256']:
        raise ValueError('CPU historical weight identity reference differs')
    old = read(old_path)
    manifest = make_manifest(value, cpu, read(package / 'source-bindings.json'), old, package)
    spec = importlib.util.spec_from_file_location('final_reviewed_native_GPU_worker', worker)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # Final worker has only stdlib imports outside run().
    module.validate_manifest(manifest)  # Pure schema/source condition check; never run().
    for i, request in enumerate(manifest['requests']):
        admission = read(Path(value['cpu_proof']['local_root']) / ('r%03d' % i) / 'admission.json')
        if admission['request_id'] != request['request_id'] or admission['image_sha256'] != request['image_sha256']:
            raise ValueError('CPU proof does not bind the exact request/image order')
        if not admission.get('tensor_artifacts'):
            raise ValueError('CPU full native tensor proof is absent')
    for name, source in [('native_image_gpu_preflight.py', worker), ('resource_gate.py', HERE / 'resource_gate.py'),
                         ('launch_once.py', HERE / 'launch_once.py'), ('qwen-fixed-api.json', OFFICIAL_API_LOCAL),
                         ('four-image-protocol.original.json', package / 'protocol.json')]:
        copy_new(source, output / name)
    write(output / 'gpu-manifest.json', manifest)
    launch_spec = {
        'schema': 'single-jev-image-four-control-launch-v1', 'approved_for_new_auxiliary_preflight': True,
        'launcher_source_sha256': sha(HERE / 'launch_once.py'), 'resource_gate_source_sha256': sha(HERE / 'resource_gate.py'),
        'worker_source': {'path': str(launch.PACKAGE / 'native_image_gpu_preflight.py'), 'sha256': value['final_worker_source_sha256']},
        'manifest': {'path': str(launch.PACKAGE / 'gpu-manifest.json'), 'sha256': sha(output / 'gpu-manifest.json')},
        'lease': {'path': str(launch.LEASE_PATH), 'sha256': value['lease_sha256']},
        'expected_holder': dict(launch.HOLDER), 'python': launch.PYTHON, 'output_root': value['launcher_output_root'],
        'model': dict(launch.MODEL),
        'limits': {'initial_auxiliary_requests': 4, 'automatic_format_retries': 0,
                   'actual_total_auxiliary_requests': 4, 'overall_package_auxiliary_cap': 8,
                   'unused_format_allowance_automatically_spent': False, 'primary_requests': 0, 'GUI_actions': 0,
                   'scorer_calls': 0, 'physical_compute_GPUs': [7], 'reservation_GPUs': [4, 5, 6, 7],
                   'semantic_resampling': False},
    }
    launch.validate_spec(launch_spec)
    write(output / 'launch-specification.json', launch_spec)
    command = launch.holder_command(launch.PACKAGE / 'launch-specification.json',
                                    sha(output / 'launch-specification.json'), value['launcher_output_root'])
    command['script_sha256'] = sha(HERE / 'launch_once.py')
    write(output / 'holder-command.review-only.json', command)
    write(output / 'preparation-receipt.json', {
        'status': 'prepared_for_root_review_not_submitted', 'GPU_manifest_sha256': sha(output / 'gpu-manifest.json'),
        'final_worker_sha256': value['final_worker_source_sha256'], 'new_model_GPU_GUI_health_requests': 0,
        'actual_GPU_resource_gate_has_not_run_by_this_builder': True,
        'source_labels_content_supplied_to_model': False, 'fresh_full_weight_hash_still_required_before_load': True,
        'full_12_control_plan_GUI_launch_ready': False, 'new_generation_first_attempts_cap': 4,
        'overall_package_cap': 8, 'remaining_format_allowance_automatically_spent': False,
    })
    write(output / 'seal.json', {x.name: sha(x) for x in sorted(output.iterdir()) if x.is_file()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Never overwrite or repair an old builder output')
    try:
        build(read(args.inputs), args.output)
    except BaseException:
        if args.output.is_dir():
            write(args.output / 'builder-failure.json', {'error': traceback.format_exc(),
                                                        'new_model_GPU_GUI_network_requests': 0,
                                                        'partial_local_sources_preserved': True,
                                                        'no_automatic_retry': True})
            write(args.output / 'failure-seal.json', {x.name: sha(x) for x in sorted(args.output.iterdir()) if x.is_file()})
        raise
