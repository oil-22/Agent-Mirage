"""Stage, run, and collect a new read-only-observation replay. No old workers are used."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import time

HERE = Path(__file__).resolve().parent
PROBE = HERE.parent / 'crop-visual-token-probe-20261120'
sys.path.insert(0, str(PROBE))
from crop_token_probe import LINKED11, SCALE12, PROJECT, REMOTE_ARCHIVES, ENV_PYTHON, make_plan, sha_file

SSH = ['ssh', '-p', '2223', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', 'researcher@192.0.2.11']
ROOT = '/data/researcher/crop-visual-replay-20261120'
WORKER = HERE / 'worker.py'
PROTOCOL = HERE / 'PROTOCOL.md'
# Fixed before any new output. Two early trajectories and several branches from their
# actual normal (post-gate when applicable) delivered observations. No outcome keys.
DESIGN = [
    (SCALE12, 'scale10-T000-clean_control-gate', (1, 4, 8)),
    (SCALE12, 'scale10-T003-clean_control-gate', (1,)),
    (LINKED11, 'native16b-T114-clean_control-gate', (2, 8, 15, 20)),
    (LINKED11, 'native16b-T125-clean_control-gate', (1, 3)),
    (SCALE12, 'scale10-T017-silent_drop-gate', (12, 40)),
]
ARMS = ['original', 'append_duplicate', 'append_zoom']


def plan():
    frozen = make_plan()
    rows = []
    keys = ('root', 'request_id', 'run_id', 'decision', 'seal_sha256', 'wire_sha256', 'body_sha256',
            'input_tokens', 'current_image_sha256', 'all_image_sha256s', 'history_messages')
    for campaign, run, decisions in DESIGN:
        audit, = (PROJECT / campaign).glob(f'trajectory-audit-{run}-*')
        requests = audit / 'request-results.json'
        seal = json.loads((audit / 'seal.json').read_bytes())
        digest = sha_file(requests)
        if seal[requests.name] != digest:
            raise ValueError('Archive manifest mismatch')
        source = json.loads(requests.read_bytes())['primary']
        for decision in decisions:
            old, = [r for r in source if r['decision'] == decision]
            if not (old['actual_tensor_files_verified'] and old['exact_full_history_preserved'] and old['natural_EOS'] and
                    old['run_id'] == run and old['root'].startswith(f'{REMOTE_ARCHIVES}/{campaign}/model-attempt-01/primary/requests/')):
                raise ValueError('Archive row provenance mismatch')
            case = run.split('-')[1] + f'-d{decision:02d}'
            rows.append({'case': case, 'campaign': campaign, 'local_audit_receipt': str(requests),
                         'local_audit_member_sha256': digest, 'local_audit_seal_sha256': sha_file(audit / 'seal.json'),
                         **{k: old[k] for k in keys}})
    rows.sort(key=lambda r: (r['input_tokens'], r['case']))
    for i, row in enumerate(rows):
        row['arm_order'] = ARMS[i % 3:] + ARMS[:i % 3]
        if i == len(rows) - 1:
            row['arm_order'] = ARMS[:]
    return {'version': 'crop-visual-replay-v1', 'packages': frozen['packages'], 'cases': rows, 'arms': ARMS,
            'max_calls': len(rows) * 3, 'max_output': 2048, 'seed': 42, 'physical_gpus': [4, 5, 6, 7],
            'batch_rules': 'One native generation per arm; no retries; any resource conflict or CUDA memory fault stops further calls.',
            'worker_sha256': sha_file(WORKER), 'probe_sha256': frozen['probe_source_sha256'], 'protocol_sha256': sha_file(PROTOCOL)}


def transport(command, data=None, capture=False):
    out = subprocess.run(SSH + [command], input=data, stdout=subprocess.PIPE if capture else None)
    if out.returncode:
        raise SystemExit(out.returncode)
    return out.stdout


def stage():
    frozen = plan()
    name = 'attempt-' + str(time.time_ns())
    local = HERE / name
    local.mkdir()
    remote = ROOT + '/' + name
    files = {'plan.json': json.dumps(frozen, ensure_ascii=False, indent=2).encode('utf-8'),
             'worker.py': WORKER.read_bytes(), 'PROTOCOL.md': PROTOCOL.read_bytes(),
             'crop_token_probe.py': (PROBE / 'crop_token_probe.py').read_bytes()}
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w') as archive:
        for key, data in files.items():
            (local / key).write_bytes(data)
            entry = tarfile.TarInfo(key)
            entry.size, entry.mode = len(data), 0o600
            archive.addfile(entry, io.BytesIO(data))
    (local / 'remote-root.txt').write_text(remote + '\n', encoding='ascii')
    print(f'FROZEN {name} {sha_file(local / "plan.json")}', flush=True)
    transport(f'umask 077; mkdir -p {ROOT} && mkdir {remote} && tar -xf - -C {remote}', stream.getvalue())
    return name


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('action', choices=('stage', 'prepare', 'run', 'collect', 'plan'))
    cli.add_argument('attempt', nargs='?')
    args = cli.parse_args()
    if args.action == 'plan':
        for row in plan()['cases']:
            print(row['case'], row['input_tokens'], row['arm_order'])
        return
    if args.action == 'stage':
        stage()
        return
    name = args.attempt
    if not name or not name.startswith('attempt-') or not name[8:].isdigit():
        raise ValueError('Explicit staged attempt ID required')
    local = HERE / name
    remote = ROOT + '/' + name
    if (local / 'remote-root.txt').read_text().strip() != remote:
        raise ValueError('Remote stage identity mismatch')
    if args.action in ('prepare', 'run'):
        env = ('HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false '
               'OMP_NUM_THREADS=4 MKL_NUM_THREADS=4')
        clean_cuda = 'CUDA_VISIBLE_DEVICES= ' if args.action == 'prepare' else ''
        transport(f'umask 077; cd {remote} && env {clean_cuda}{env} {ENV_PYTHON} -B -u worker.py {args.action}')
    else:
        # Export lightweight CPU summaries, exact source images, and blind-review packets.
        raw = transport(f'cd {remote} && tar -cf - public cases', capture=True)
        dest = local / f'export-{time.time_ns()}'
        dest.mkdir()
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
            archive.extractall(dest, filter='data')
        print(dest, flush=True)


if __name__ == '__main__':
    main()
