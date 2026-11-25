"""Create, but do not execute, builder source referring to the linked safety fix."""
import json
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
old = HERE / 'build_gpu_manifest.py'
old_sha = hashlib.sha256(old.read_bytes()).hexdigest()
assert old_sha == 'e72f881daeb0ce5c07c4e57d2678947c213fe866e12decd202c6c316d2b61283'
text = old.read_text(encoding='utf-8')
text = text.replace('REVISION_ROOT = HERE.parent\n', "REVISION_ROOT = HERE.parent\nLINKED_SOURCE = HERE / 'launcher-linked02'\n")
assert text.count("HERE / 'resource_gate.py'") == 2
assert text.count("HERE / 'launch_once.py'") == 3
text = text.replace("HERE / 'resource_gate.py'", "LINKED_SOURCE / 'resource_gate.py'")
text = text.replace("HERE / 'launch_once.py'", "LINKED_SOURCE / 'launch_once.py'")
with (HERE / 'build_gpu_manifest_linked02.py').open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(text)
base = '/home/researcher/jev-defense-four-gpu-20261106'
local = 'D:/MultiModel/jev-defense-four-gpu-20261106/single-evidence-revision-20261107'
pending = {
    'root_execution_review': False,
    'attempt_id': 'single-jev-9b-four-first-attempts-01',
    'final_worker_source_sha256': None,
    'lease_sha256': None,
    'official_base_api_sha256': 'aeea4ace23a6c865d20b47b20626e18738e0dee9f24045c679d0d9008bc8c1b2',
    'launcher_output_root': None,
    'cpu_input_manifest_local_path': local + '/native-auxiliary-admission-01/cpu-native-four-linked02/collected/admission-01/input-manifest.original.json',
    'prior_weight_identity_local_path': 'D:/MultiModel/attention-audit-20261031/model-sha256-3090.json',
    'cpu_proof': {
        'local_root': local + '/native-auxiliary-admission-01/cpu-native-four-linked02/collected/admission-01',
        'remote_root': base + '/runtime-preparation/single-evidence-native-auxiliary-01/admission-01',
        'seal_sha256': '4b4505c4c0bb9cd165f5261b6b3c2d66b441b1b480943b2f94cd2e4838ff6ba0',
    },
    'source_labels': {
        'local_root': local + '/source-first-four-root-review-01',
        'remote_root': base + '/runtime-preparation/single-jev-9b-preflight-01/source-first-four-root-review-01',
        'seal_sha256': 'fbcff9cdc43380775f496d9a7e5da2fbd0a2a8a89549604544fd82e25995ae79',
    },
}
with (HERE / 'builder-inputs-linked02.pending.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(pending, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'old_builder_SHA256': old_sha,
                  'linked_builder_SHA256': hashlib.sha256((HERE / 'build_gpu_manifest_linked02.py').read_bytes()).hexdigest(),
                  'actual_builder_executed': False, 'root_review': False,
                  'final_worker_SHA_and_lease_SHA_still_required': True}))
