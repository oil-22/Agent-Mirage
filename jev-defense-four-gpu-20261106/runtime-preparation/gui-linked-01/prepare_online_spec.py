"""Create a new concrete GUI specification without launch or GPU allocation."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main(a):
    previous = json.loads(a.preflight_spec.read_bytes())
    keep = ['primary_release', 'primary_model', 'primary_expected_runtime',
        'primary_backend_sha256', 'primary_native_layout_receipt',
        'primary_native_layout_receipt_sha256', 'flash_model', 'flash_identity_receipt',
        'primary_dependency_receipt', 'primary_dependency_receipt_sha256',
        'flash_identity_receipt_sha256', 'flash_stable_identity_receipt',
        'flash_stable_identity_receipt_sha256', 'flash_observer_contract',
        'flash_observer_contract_sha256', 'layout']
    here = Path(__file__).resolve().parent
    native = a.native_source_root.resolve()
    if (sha(native / 'preflight_service.py') != previous['worker_source_sha256'] or
            sha(native / 'four_gpu_contract.py') != previous['contract_source_sha256']):
        raise RuntimeError('Online must reuse the exact reviewed native implementation from the completed preflight')
    spec = {key: previous[key] for key in keep}
    spec.update(roles={role: {key: value[key] for key in ('python', 'port')}
                       for role, value in previous['roles'].items()},
        preflight_source_root=str(native),
        preflight_source_sha256={name: sha(native / name) for name in
            ('preflight_service.py', 'four_gpu_contract.py', 'launch_preflight_group.py')},
        online_source_sha256={name: sha(here / name) for name in
            ('online_service.py', 'online_contract.py', 'launch_online_group.py')},
        online_plan=str(a.plan), online_plan_sha256=sha(a.plan),
        online_launch_gate=str(a.gate), online_launch_gate_sha256=sha(a.gate),
        previous_token_file=previous['token_file'], token_file=str(a.token))
    with a.output.open('x', encoding='utf8') as handle:
        json.dump(spec, handle, ensure_ascii=False, indent=2)
    print(json.dumps({'spec': str(a.output), 'sha256': sha(a.output),
        'GPU_allocations': 0, 'model_calls': 0, 'GUI_actions': 0}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--preflight-spec', type=Path, required=True)
    parser.add_argument('--native-source-root', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--gate', type=Path, required=True)
    parser.add_argument('--token', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    main(parser.parse_args())
