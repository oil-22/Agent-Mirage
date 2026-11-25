"""Freeze a GPU-placement-only full-input technical repair, without launching."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import shutil
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
OLD = BASE / 'source-bound-controls-20261109-08/runtime-package'
OUT = HERE / 'runtime-package'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, value):
    with p.open('x', encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.write('\n')


assert not OUT.exists(); OUT.mkdir()
old_manifest = json.loads((OLD / 'manifest.json').read_bytes())
for name, expected in old_manifest['files'].items():
    assert sha(OLD / name) == expected
    if name in ['controls_worker.py', 'launch_controls_once.py', 'controls-plan.json'] or name.startswith('control-inputs/'):
        continue
    target = OUT / name; target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(OLD / name, target)

runtime_path = OUT / 'model_runtime.py'
original = runtime_path.read_text(encoding='utf8')
new = original.replace("device_map = {'model.visual': 0, 'model.language_model.embed_tokens': 0,",
                       "device_map = {'model.visual': 3, 'model.language_model.embed_tokens': 3,")
new = new.replace('0 if i < 19 else 1 if i < 43 else 2', '0 if i < 22 else 1 if i < 45 else 2')
new = new.replace('parameter_lower = {i: 0 for i in range(3)}', 'parameter_lower = {i: 0 for i in range(4)}')
new = new.replace("'primary_layer_counts': [19, 24, 21]", "'primary_layer_counts': [22, 23, 19]")
new = new.replace("'primary_physical': [4, 5, 6]", "'primary_physical': [4, 5, 6, 7]")
new = new.replace("[('primary', engine.model)], ['cuda:0', 'cuda:1', 'cuda:2'])",
                   "[('primary', engine.model)], ['cuda:0', 'cuda:1', 'cuda:2', 'cuda:3'])")
assert new != original and 'i < 19 else' not in new
def nested(text, name):
    return next(n for n in ast.walk(ast.parse(text)) if isinstance(n, ast.FunctionDef) and n.name == name)
assert ast.dump(nested(new, 'audited_generation'), include_attributes=False) == ast.dump(nested(original, 'audited_generation'), include_attributes=False)
runtime_path.write_text(new, encoding='utf8')
shutil.copyfile(HERE / 'capacity_worker.py', OUT / 'capacity_worker.py')

launcher = (OLD / 'launch_controls_once.py').read_text(encoding='utf8')
launcher = launcher.replace('source-bound-controls-20261109-08', HERE.name)
launcher = launcher.replace('controls_worker.py', 'capacity_worker.py').replace('launch_controls_once.py', 'launch_capacity_once.py')
launcher = launcher.replace("'primary_physical_GPUs': [4, 5, 6]", "'primary_physical_GPUs': [4, 5, 6, 7]")
(OUT / 'launch_capacity_once.py').write_text(launcher, encoding='utf8')

failed = Path(r'D:\MultiModel\jev-oom-evidence\1794210643888300200\3090\original\originals\worker\requests\0178')
seal = json.loads((failed / 'seal.json').read_bytes())
(OUT / 'original0178').mkdir()
source_names = ['payload.json', 'prepared.json', 'first-forward.json', 'effective-generation.json',
                'failure.json', 'forward-count.json', 'generated-token-progress.jsonl']
for name in source_names:
    assert sha(failed / name) == seal[name], name
    shutil.copyfile(failed / name, OUT / 'original0178' / name)
assert (failed / 'generated-token-progress.jsonl').stat().st_size == 0
assert json.loads((failed / 'forward-count.json').read_bytes())['actual_forward_calls'] == 1
full = json.loads((OLD / 'control-inputs/E06.json').read_bytes())['view']['images'][0]
raw = base64.b64decode(full['raw_base64']); (OUT / 'new-auxiliary-full.png').write_bytes(raw)
known = [json.loads((OLD / ('control-inputs/' + name + '.json')).read_bytes())['image_sha256'] for name in ['U01', 'U02', 'U03']]
assert hashlib.sha256(raw).hexdigest() not in known

limits = {'auxiliary': 1, 'judge': 1, 'actor': 0, 'GUI': 0, 'scorer': 0, 'paid_API': 0, 'format_retries': 0}
manifest = {'schema': 'GPU-placement-only-exact-zero-token-OOM-preflight-v1',
            'authorized_finite_joint_development': True,
            'authorization': 'Active sustained defense goal; full-input GPU-only technical capacity repair on original authorized4-7.',
            'expected_holder': old_manifest['expected_holder'], 'lease_sha256': old_manifest['lease_sha256'],
            'output': '/home/researcher/jev-defense-four-gpu-20261106/' + HERE.name,
            'limits': limits, 'primary_language_layer_counts': [22, 23, 19],
            'primary_visual_and_embeddings_physical_GPU': 7, 'single_auxiliary_physical_GPU': 7,
            'four_cards_counted_as_reserved': True, 'no_CPU_model_inference_or_offload': True,
            'original_failed_request_id': '0178', 'original_payload_sha256': sha(failed / 'payload.json'),
            'original_failed_request_input_tokens': 20382, 'original_complete_images': 4,
            'original_input_ids_sha256': '087461cba951b41de5cfc47ddbfd8baa48030106bc9b7b7b88aafd3ec993d844',
            'original_main_output_cap': 4096, 'old_GUI_or_completed_semantic_control_resumed': False,
            'no_bitwise_output_identity_or_future_full_history_fit_claim': True,
            'model_parameters_precision_native_backend_and_full_inputs_unchanged': True,
            'must_first_close_and_audit_controls08_then_fresh_resource_admission': True,
            'files': {p.relative_to(OUT).as_posix(): sha(p) for p in sorted(OUT.rglob('*')) if p.is_file()}}
save(OUT / 'manifest.json', manifest)
save(HERE / 'preparation.json', {'time': time.time(), 'manifest_sha256': sha(OUT / 'manifest.json'),
      'stage_only_no_submission': True, 'limits': limits, 'load_ready': False,
      'native_generation_audit_AST_unchanged': True,
      'actual_joint_fit_not_proven': True, 'new_model_GPU_GUI_calls': 0})
save(HERE / 'condition-and-tradeoff.json', {
      'change': 'Keep primary64 language layers on4/5/6 but use22/23/19 cuts; primary visual and embeddings move to7 alongside resident single9B. Calls remain sequential under the same inherited locks and inference mutex.',
      'purpose': 'Reduce parameter baseline and make headroom for original long prefills on language devices.',
      'tradeoff': 'GPU7 headroom shrinks; native cross-device transport and joint activation fit are unproven. MultiGPU placement may change numerical outputs. Still four reserved GPUs, no CPU inference, no cost-saving claim.',
      'unchanged': 'Original full20382-token/four-image failed input, full effective generation config, BF16/SDPA, checkpoint files, main backend, strict validator,4096 output; no old trajectory resumes.',
      'finite_test': 'One new full-image auxiliary call, then one technical attempt of original0-token prefill failure. No retry or budget expansion after terminal.',
      'original_model_backend_sha256': sha(OUT / 'release/defense/qwen_backend.py'),
      'old_model_runtime_sha256': sha(OLD / 'model_runtime.py'),
      'new_model_runtime_sha256': sha(runtime_path), 'launch_submitted': False})
print(json.dumps({'package': str(OUT), 'manifest_sha256': sha(OUT / 'manifest.json'),
                  'source_files': len(manifest['files']), 'stage_only': True}, ensure_ascii=False))
