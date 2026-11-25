"""Freeze local inputs only. No SSH, model import, launch or new weight hash."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def copy_new(source, target):
    with Path(target).open('xb') as stream:
        stream.write(Path(source).read_bytes())
    assert sha(source) == sha(target)


original = ROOT / 'source-first-compact-four-peer-notes-02'
expected = '688f27b2fa0f28b31f3e3cf5632efe1316f3dcaee364407478fcf94d078485c1'
assert sha(original / 'seal.json') == expected
envelope = read(original / 'seal.json')
assert isinstance(envelope.get('entries'), list)
normalized = HERE / 'source-first-labels-envelope-02'
normalized.mkdir(exist_ok=False)
for item in envelope['entries']:
    source = original / item['path']
    assert source.resolve().is_relative_to(original.resolve())
    assert sha(source) == item['sha256'] and source.stat().st_size == item['bytes']
    copy_new(source, normalized / item['path'])
copy_new(original / 'seal.json', normalized / 'source-seal.original.json')
write_new(normalized / 'envelope-provenance.json', {
    'original_source_root': str(original), 'original_envelope_sha256': expected,
    'source_file_bytes_unchanged': True,
    'scope': 'files-list seal envelope for unchanged worker.verify_seal; no semantic label edits',
    'model_GUI_network_requests': 0, 'labels_supplied_to_model': False,
})
write_new(normalized / 'seal.json', {'files': [
    {'path': x.name, 'bytes': x.stat().st_size, 'sha256': sha(x)} for x in sorted(normalized.iterdir()) if x.is_file()
]})

value = read(HERE / 'builder-inputs.pending.json')
value['root_execution_review'] = True  # Root explicitly authorizes local freeze, then reviews before submit.
value['final_worker_source_local_path'] = str(ROOT / 'native_image_gpu_preflight_compact02.py')
value['final_worker_source_sha256'] = sha(value['final_worker_source_local_path'])
proof = ROOT / 'native-auxiliary-admission-compact02/cpu-native-compact-four-02/collected/admission-01'
assert sha(proof / 'seal.json') == 'b6822b4beff04616500705fadb5d728a7d212d95f9532546a157d3aef1233590'
value['cpu_input_manifest_local_path'] = str(proof / 'input-manifest.original.json')
value['cpu_proof'] = {
    'local_root': str(proof),
    'remote_root': '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/single-evidence-compact-native-02/admission-01',
    'seal_sha256': sha(proof / 'seal.json'),
}
inputs = ROOT / 'compact-four-image-inputs-02'
assert sha(inputs / 'seal.json') == '3473bf5a7a5a28c37ee14d329a72359d43bea3da531025a8d56d6e89d49c8706'
value['input_package_local_root'] = str(inputs)
value['input_package_seal_sha256'] = sha(inputs / 'seal.json')
value['source_labels'] = {
    'local_root': str(normalized),
    'remote_root': '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/single-jev-9b-compact-preflight-02/source-first-compact-four-peer-notes-02',
    'seal_sha256': sha(normalized / 'seal.json'),
}
first = ROOT / 'gpu-four-terminal-collection-01/original'
remote_first = '/home/researcher/jev-defense-four-gpu-20261106/single-evidence-revision-20261107/gpu-four-first-attempts-01'
value['current_weight_identity_reuse'] = {
    'identity_path': remote_first + '/worker/current-weight-identity.json',
    'identity_sha256': sha(first / 'worker/current-weight-identity.json'),
    'worker_seal_path': remote_first + '/worker/seal.json',
    'worker_seal_sha256': sha(first / 'worker/seal.json'),
    'terminal_manifest_path': remote_first + '/terminal-manifest.json',
    'terminal_manifest_sha256': sha(first / 'terminal-manifest.json'),
}
assert value['current_weight_identity_reuse']['identity_sha256'] == 'c2a7d4debed4ae682d673b7e4a2946e2cf3da72caa4820ac756c613bbfbffea3'
assert value['current_weight_identity_reuse']['worker_seal_sha256'] == 'f6f3e95e2673aa28e9b25964513cffe66dc161100ad0c0642eec9d4b3c8260ef'
assert value['current_weight_identity_reuse']['terminal_manifest_sha256'] == 'd3adf24eb77d801c52428923acc27d3a511936c0f8a64839206e433f46ba9d75'
write_new(HERE / 'builder-inputs.final.json', value)
print(json.dumps({'worker_sha256': value['final_worker_source_sha256'], 'normalized_label_seal_sha256': value['source_labels']['seal_sha256'],
                  'final_inputs_sha256': sha(HERE / 'builder-inputs.final.json'), 'submitted': False}))
