"""Bind uploaded finite plans to exact native paths; never load a model."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import time

BASE = Path('/home/researcher/jev-defense-four-gpu-20261106')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as handle:
        json.dump(value, handle, indent=2)


def main():
    assert os.getuid() == 1033
    evidence = {}
    for name in ['observer-preflight-frozen-01', 'primary-capacity-frozen-02']:
        root = BASE / 'policy-preparation' / name
        manifest = json.loads((root / 'seal.json').read_bytes())
        for file, expected in manifest.items():
            assert sha(root / file) == expected, name + '/' + file
        evidence[name] = {'path': str(root / 'seal.json'), 'sha256': sha(root / 'seal.json'),
                          'verified_files': len(manifest)}
    completion = BASE / 'flash-preparation/download-attempts/1793972286914423476/download-complete-receipt.json'
    stable = BASE / 'flash-preparation/identity-bindings/1793974145045634334/receipt.json'
    contract = BASE / 'policy-preparation/observer-contract.json'
    backend = BASE / 'primary-release-01/defense/qwen_backend.py'
    assert sha(completion) == '0f9bf26545bc47b941a8094cfe31c794eaeb239960375fce2f9c262b6e3e4cec'
    assert sha(stable) == 'af6e6f7214b0e350877e2e1a7fdb5237b83a498ea8bdb83f9fea6bf6b335ae0d'
    assert sha(contract) == '98a3adb4ecb4939bb500603121e21587d454a99233ee14a32ddca8f68fa35054'
    assert sha(backend) == '11b6cd7a45a31c614b385909b3f43cc1484168fc6c2d2b0796face8495d359eb'
    cpu = BASE / 'flash-preparation/cpu-image-observer-checks/1793974275962676866/receipt.json'
    native = json.loads(cpu.read_bytes())
    assert native['status'] == 'passed' and native['joint_question_count'] == 3
    assert native['observer_contract_sha256'] == sha(contract)
    for file in [BASE / 'original-runtime.json', Path(native['executable'])]:
        assert file.is_file(), str(file)
    transport = BASE / 'transport-01'
    if not transport.exists():
        transport.mkdir(mode=0o700)
    assert transport.stat().st_uid == 1033 and transport.stat().st_mode & 0o077 == 0
    token = transport / 'private.token'
    if not token.exists():
        fd = os.open(str(token), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as handle:
            handle.write(secrets.token_hex(32) + '\n')
    assert token.stat().st_uid == 1033 and token.stat().st_mode & 0o077 == 0
    assert len(token.read_text().strip()) >= 32
    config = {
        'primary_release': str(BASE / 'primary-release-01'),
        'primary_model': '/data/llms/Qwen3.8-27B',
        'primary_expected_runtime': str(BASE / 'original-runtime.json'),
        'primary_backend_sha256': sha(backend),
        'flash_model': json.loads(completion.read_bytes())['checkpoint'],
        'flash_identity_receipt': str(completion),
        'flash_identity_receipt_sha256': sha(completion),
        'flash_stable_identity_receipt': str(stable),
        'flash_stable_identity_receipt_sha256': sha(stable),
        'flash_python': native['executable'],
        'flash_observer_contract': str(contract),
        'flash_observer_contract_sha256': sha(contract),
        'token_file': str(token),
        'primary_admission': str(BASE / 'policy-preparation/primary-capacity-frozen-02/server-admission.json'),
        'flash_admission': str(BASE / 'policy-preparation/observer-preflight-frozen-01/server-admission.json')}
    root = BASE / ('concrete-preparation-' + str(time.time_ns()))
    root.mkdir(exist_ok=False)
    save(root / 'paths.json', config)
    save(root / 'receipt.json', {'scope': 'static preparation only', 'time': time.time(),
        'evidence': evidence, 'flash_cpu_receipt_sha256': sha(cpu),
        'primary_python_source_sha256': {str(path.relative_to(BASE / 'primary-release-01')): sha(path)
            for path in (BASE / 'primary-release-01').rglob('*.py')},
        'private_token_path_only': str(token), 'token_value_not_logged': True,
        'model_calls': 0, 'GPU_allocations': 0, 'GUI_actions': 0})
    save(root / 'seal.json', {path.name: sha(path) for path in root.iterdir() if path.is_file()})
    print(json.dumps({'root': str(root), 'paths': str(root / 'paths.json'),
        'paths_sha256': sha(root / 'paths.json'), 'model_calls': 0, 'GPU_allocations': 0}))


if __name__ == '__main__':
    main()
