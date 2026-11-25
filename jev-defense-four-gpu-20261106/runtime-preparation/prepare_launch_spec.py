"""Create a concrete sealed launcher specification; never starts a process."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(a):
    base = Path('/home/researcher/jev-defense-four-gpu-20261106')
    local = Path(__file__).resolve().parent
    config = json.loads(a.paths.read_bytes())
    # `paths` is a reviewed concrete path list supplied after downloads/env checks.
    required = ['primary_release', 'primary_model', 'primary_expected_runtime',
                'primary_backend_sha256', 'flash_model', 'flash_identity_receipt',
                'primary_native_layout_receipt', 'primary_native_layout_receipt_sha256',
                'primary_dependency_receipt', 'primary_dependency_receipt_sha256',
                'flash_identity_receipt_sha256', 'flash_python', 'token_file',
                'flash_stable_identity_receipt', 'flash_stable_identity_receipt_sha256',
                'flash_observer_contract', 'flash_observer_contract_sha256',
                'primary_admission', 'flash_admission']
    if set(config) != set(required):
        raise ValueError('Concrete paths/config must contain exactly the required keys')
    spec = {k: config[k] for k in required if k not in
            {'primary_admission', 'flash_admission', 'flash_python'}}
    spec.update(layout=str(base / 'runtime-preparation/layout.proposed.json'),
                worker_source_sha256=sha(local / 'preflight_service.py'),
                contract_source_sha256=sha(local / 'four_gpu_contract.py'),
                admission_sha256={'primary': sha(Path(config['primary_admission'])),
                                  'pplx_flash': sha(Path(config['flash_admission']))},
                roles={
                    'primary': {'python': '/opt/whz/conda-envs/webmall-vlm/bin/python',
                                'admission': config['primary_admission'], 'port': 18127},
                    'pplx_flash': {'python': config['flash_python'],
                                   'admission': config['flash_admission'], 'port': 18223}})
    with a.output.open('x', encoding='utf8') as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
    print(json.dumps({'specification': str(a.output), 'sha256': sha(a.output),
                      'GPU_allocations': 0, 'model_calls': 0, 'GUI_actions': 0}))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--paths', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    main(p.parse_args())
