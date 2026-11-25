"""Freeze a new linked memory-scheduled technical attempt, no experiment launch."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
OLD = BASE / 'full-history-gui-development-20261109-23/runtime-package'
OUT = HERE / 'runtime-package'
FAILED = Path(r'D:\MultiModel\j23evidence/1794223604796828100/3090/output/worker/requests/0044')
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2); stream.write('\n')


def one(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new)


def main():
    assert not OUT.exists()
    old_manifest = json.loads((OLD / 'manifest.json').read_bytes())
    for name, expected in old_manifest['files'].items():
        assert sha(OLD / name) == expected, name
    preservation = BASE / 'full-history-gui-development-20261109-23/failure-preservation-1794223604796828100/receipt.json'
    assert sha(preservation) == 'e081a48900c9ec5ea8019c2c94bd6975c8353d9bfa4caaf4ee574b24cac03838'
    OUT.mkdir()
    excluded = {'gpu_server.py', 'launch_gui_service_once.py', 'private.token'}
    for name in old_manifest['files']:
        if name in excluded:
            continue
        target = OUT / name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(OLD / name, target)
    original = (OLD / 'model_runtime.py').read_text(encoding='utf8')
    runtime = one(original, "'lm_head': 2}", "'lm_head': 2}")
    runtime = one(runtime, "0 if i < 22 else 1 if i < 45 else 2", "0 if i < 18 else 1 if i < 36 else 2 if i < 51 else 3")
    runtime = one(runtime, "'primary_layer_counts': [22, 23, 19]", "'primary_layer_counts': [18, 18, 15, 13]")
    runtime = one(runtime, "device_map={'': 3}, local_files_only=True, trust_remote_code=False).eval()",
                  "device_map={'': 'cpu'}, local_files_only=True, trust_remote_code=False).eval()")
    runtime = one(runtime, "auxiliary_cuda = support.audit_tensors(torch, [('single_auxiliary', auxiliary_model)], ['cuda:3'])",
                  "assert all(t.device.type == 'cpu' for t in auxiliary_model.parameters())\n    auxiliary_cuda = {'devices': ['cpu'], 'storage_only': True, 'CPU_forward_forbidden': True, 'actual_GPU_identity_audited_by_residency_cycle_later': True}")
    def audit_function(source):
        return next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef) and n.name == 'audited_generation')
    assert ast.dump(audit_function(runtime), include_attributes=False) == ast.dump(audit_function(original), include_attributes=False)
    (OUT / 'model_runtime.py').write_text(runtime, encoding='utf8')
    for name in ['resident_schedule.py', 'capacity_worker.py']:
        shutil.copyfile(HERE / name, OUT / name)
    launcher = (OLD / 'launch_gui_service_once.py').read_text(encoding='utf8')
    launcher = launcher.replace('full-history-gui-development-20261109-23', HERE.name)
    launcher = launcher.replace('launch_gui_service_once.py', 'launch_capacity_once.py').replace('gpu_server.py', 'capacity_worker.py')
    launcher = launcher.replace("'primary_physical_GPUs': [4, 5, 6]", "'primary_physical_GPUs': [4, 5, 6, 7]")
    (OUT / 'launch_capacity_once.py').write_text(launcher, encoding='utf8')
    original_folder = OUT / 'original0044'; original_folder.mkdir()
    bindings = json.loads((FAILED / 'seal.json').read_bytes())
    for name in ['payload.json', 'prepared.json', 'first-forward.json', 'effective-generation.json',
                 'failure.json', 'forward-count.json', 'generated-token-progress.jsonl']:
        assert sha(FAILED / name) == bindings[name]
        shutil.copyfile(FAILED / name, original_folder / name)
    for path in OUT.rglob('*.py'):
        compile(path.read_text(encoding='utf8'), str(path), 'exec')
    limits = {'auxiliary': 0, 'judge': 1, 'actor': 0, 'GUI': 0, 'scorer': 0, 'paid_API': 0, 'format_retries': 0}
    manifest = {'schema': 'GUI23-original-budget-idle-weight-RAM-scheduled-technical-attempt-v1',
        'authorized_finite_joint_development': True,
        'authorization': 'Existing active defense goal; technical repair on original authorized four GPUs. All forwards GPU only; CPU storage of idle weights is deployment scheduling, not CPU model inference.',
        'expected_holder': old_manifest['expected_holder'], 'lease_sha256': old_manifest['lease_sha256'],
        'output': '/home/researcher/jev-defense-four-gpu-20261106/' + HERE.name,
        'limits': limits, 'original_track': 'fullhistory23-T000-clean-noaux',
        'original_failed_request': '0044', 'original_manifest_sha256': sha(OLD / 'manifest.json'),
        'failure_preservation_receipt_sha256': sha(preservation),
        'primary_layer_counts': [18, 18, 15, 13], 'authorized_physical_GPUs': [4, 5, 6, 7],
        'CPU_inference_allowed': False, 'idle_weight_RAM_staging': True,
        'new_primary_numerical_bitwise_output_identity_guaranteed': False,
        'auxiliary_model': 'Qwen/Qwen3.5-9B', 'decision_adapter_loaded': False,
        'original_failed_full_input_tokens': 22596, 'original_complete_images': 11,
        'original_input_ids_sha256': 'd7e48edfa1fe9c0ef0b184e3fe1bdea63863022d005872b59efd5d8677b8bacf',
        'original_payload_sha256': sha(FAILED / 'payload.json'),
        'original_budget': {'actor_spent': 11, 'actor_cap': 70, 'judge_spent': 33, 'judge_cap': 140,
                            'pending_actor_candidate_index': 11, 'actions_executed': 10, 'step_cap': 50},
        'one_linked_judge_attempt_index': 34, 'remaining_judge_after_attempt': 106,
        'no_completed_model_call_or_environment_action_reexecution': True,
        'exact_tradeoff': 'Sequentially swap idle BF16 weights through host RAM. Primary uses all four authorized GPUs; auxiliary uses physical7 only when primary groups on7 are stored in RAM. No CPU model forward, checkpoint change, truncation, precision change, decoding or native algorithm modification. Transfer/load time and all four reserved GPUs count toward deployment cost. Placement may alter numerical results; future full-history capacity and paired GUI efficacy remain unproven.',
        'files': {p.relative_to(OUT).as_posix(): sha(p) for p in sorted(OUT.rglob('*')) if p.is_file()}}
    save(OUT / 'manifest.json', manifest)
    save(HERE / 'preparation.json', {'time': time.time(), 'manifest_sha256': sha(OUT / 'manifest.json'),
        'limits': limits, 'old_native_generation_audit_AST_unchanged': True,
        'main_backend_and_full_release_files_unchanged': all(sha(OUT / n) == h for n, h in old_manifest['files'].items() if n.startswith('release/')),
        'no_new_model_GPU_GUI_scorer_paid_calls': True, 'ready_for_GPU_launch': False})
    print(json.dumps({'package': str(OUT), 'manifest_sha256': sha(OUT / 'manifest.json'),
                      'files': len(manifest['files']), 'limits': limits, 'new_experiment_calls': 0}))


if __name__ == '__main__':
    main()
