"""Install exact native pinned wheels/dependencies into the separate env. No GPU or model import."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

BASE = Path(__file__).resolve().parent
ENV = BASE / 'env-flash-01'
CHECKPOINT = BASE / 'download-attempts/1793972286914423476/checkpoint'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b''):
            h.update(block)
    return h.hexdigest()


def main():
    assert os.getuid() == 1033
    root = BASE / 'env-install-attempts' / str(time.time_ns())
    root.mkdir(parents=True, exist_ok=False)
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '', 'PYTHONDONTWRITEBYTECODE': '1'}
    python = str(ENV / 'bin/python')
    try:
        wheels = json.loads((BASE / 'native-wheel-current.json').read_bytes())['wheels']
        for row in wheels:
            assert sha(Path(row['file'])) == row['sha256']
        steps = [
            [python, '-m', 'pip', 'install', '--no-deps', *[row['file'] for row in wheels],
             '--report', str(root / 'exact-native-wheel-report.json')],
            [python, '-m', 'pip', 'install', '-r', str(CHECKPOINT / 'requirements.txt'),
             '--index-url', 'https://pypi.tuna.tsinghua.edu.cn/simple', '--report', str(root / 'native-dependencies-report.json')],
            [python, '-m', 'pip', 'check'],
            [python, '-m', 'pip', 'freeze', '--all'],
        ]
        for index, command in enumerate(steps):
            with (root / ('step-' + str(index) + '.log')).open('xb') as log:
                p = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
            assert p.returncode == 0, ('Install step failed', index)
            print(json.dumps({'completed_step': index}), flush=True)
        receipt = {'status': 'complete', 'python': python,
                   'environment': str(ENV), 'native_requirements_sha256': sha(CHECKPOINT / 'requirements.txt'),
                   'torch_cuda_build': '2.14.0+cu126', 'torchvision_cuda_build': '0.29.0+cu126',
                   'model_calls': 0, 'GPU_allocations': 0,
                   'source_package': str(CHECKPOINT / 'source/src'),
                   'source_import_mode': 'Direct fixed-source path, matching publisher quickstart',
                   'old_environments_modified': False, 'pip_check_passed': True}
        (root / 'receipt.json').write_text(json.dumps(receipt, indent=2))
        (BASE / 'environment-current.json').write_text(json.dumps({'root': str(root),
            'receipt_sha256': sha(root / 'receipt.json'), **receipt}, indent=2))
        print(json.dumps({'root': str(root), 'status': 'complete', 'python': python}), flush=True)
    except BaseException:
        import traceback
        (root / 'failure.txt').write_text(traceback.format_exc())
        raise
    finally:
        (root / 'seal.json').write_text(json.dumps({str(p.relative_to(root)): sha(p)
                                                   for p in root.rglob('*') if p.is_file()}, indent=2))


if __name__ == '__main__':
    main()
