"""Seal the original verification timeout and link the existing release proof.

Local receipt finalization only. Never sends another release or launches work.
"""
import hashlib
import json
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent
ATTEMPT = HERE / 'resource-release-1794772681824488900'
FAILED = HERE / 'operations/1794772681830752700-release-only-idle-verified-campaign-broker'
VERIFIED = HERE / 'operations/1794772828405524700-inspect-existing-release-command-no-duplicate'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


def verify_seal(root):
    seal = json.loads((root / 'seal.json').read_bytes())
    for name, expected in seal.items():
        path = root / name
        assert path.is_file() and sha(path) == expected, str(path)
    return sha(root / 'seal.json')


def main():
    assert not (HERE / 'resource-release-current.json').exists(), 'Already finalized; do not repeat'
    failed_seal = verify_seal(FAILED)
    verified_seal = verify_seal(VERIFIED)
    failed_receipt = json.loads((FAILED / 'receipt.json').read_bytes())
    verified_receipt = json.loads((VERIFIED / 'receipt.json').read_bytes())
    assert failed_receipt['returncode'] == 1 and verified_receipt['returncode'] == 0
    assert 'Release not yet verified' in (FAILED / 'stderr.txt').read_text(encoding='utf-8')
    proof = json.loads((VERIFIED / 'stdout.txt').read_bytes())
    assert proof['actual_holder'] is None and proof['saved_holder']['uid'] == 1033
    assert proof['saved_holder']['pid'] == 2568295
    assert proof['saved_holder']['start_ticks'] == '1159211789'
    assert proof['compute'].strip() == '' and proof['read_only'] is True
    assert proof['new_model_GUI_calls'] == 0
    remote_root = '/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01'
    command = proof['files'][remote_root + '/commands/zz-release-four-mode-campaign-20261116.json']
    claimed = proof['files'][remote_root + '/commands/zz-release-four-mode-campaign-20261116.claimed']
    released = proof['files'][remote_root + '/released.json']
    assert command['sha256'] == '41e03227fa0cdb7e447abb28fc870ccce31b943f15de110d4b946df6cbf13c89'
    assert claimed['value']['sha256'] == command['sha256']
    assert released['sha256'] == '2fb82487654ad92ca6c8f8fa324aa07643259a47bfc3d371c09cdf6eca98aa10'
    assert released['value']['model_calls_by_holder'] == 0
    assert claimed['value']['time'] < released['value']['time'] < proof['time']
    assert all(not p.endswith(('holder-failure.json', '/failure.json')) for p in proof['files'])
    bindings = json.loads((ATTEMPT / 'group-bindings.json').read_bytes())
    assert len(bindings) == 2
    for item in bindings:
        root = Path(item['root'])
        assert sha(root / 'seal.json') == item['seal_sha256']
        summary = json.loads((root / 'summary.json').read_bytes())
        assert summary['all_model_GUI_launcher_processes_verified_exited'] is True

    # The original attempt had no final result. Preserve its sources unchanged,
    # classify its verification failure, and close that attempt with a seal.
    save(ATTEMPT / 'failure-preservation.json', {
        'created': time.time(),
        'status': 'verification_timeout_after_one_release_submission',
        'operation': str(FAILED), 'operation_seal_sha256': failed_seal,
        'original_release_source_sha256': sha(ATTEMPT / 'source.py'),
        'original_group_bindings_sha256': sha(ATTEMPT / 'group-bindings.json'),
        'original_sources_unchanged': True,
        'release_command_must_not_be_resubmitted': True,
        'not_a_model_GUI_or_release_failure': True,
    })
    save(ATTEMPT / 'seal.json', {p.name: sha(p) for p in ATTEMPT.iterdir() if p.is_file()})

    root = HERE / ('resource-release-confirmed-' + str(time.time_ns()))
    root.mkdir()
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'result.json', {
        'created': time.time(), 'status': 'released_verified',
        'original_timeout_attempt': str(ATTEMPT),
        'original_timeout_attempt_seal_sha256': verify_seal(ATTEMPT),
        'existing_read_only_verification_operation': str(VERIFIED),
        'verification_operation_seal_sha256': verified_seal,
        'completed_group_bindings': bindings,
        'proof': proof,
        'original_holder_verified_absent': True,
        'original_lease_retired_not_reusable': True,
        'release_submission_count': 1,
        'new_release_submissions': 0, 'new_model_GUI_calls': 0,
        'new_signals_or_foreign_process_changes': False,
        'future_work_requires_fresh_verified_owned_lease': True,
    })
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    pointer = {'root': str(root), 'seal_sha256': verify_seal(root)}
    save(HERE / 'resource-release-current.json', pointer)
    print(json.dumps({**pointer, 'status': 'released_verified', 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
