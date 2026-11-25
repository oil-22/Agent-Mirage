"""Admission for a new paired cohort; keep all older queues sealed and paused."""
import os
from pathlib import Path

from paired_contract import load_plan


def verify(package, host):
    from resource_guard import sha
    from historical_admission import verify_gui_parent as old_gui, verify_native_parent as old_models

    manifest, plan = load_plan(package)
    assert Path(manifest['package' + host]) == package
    old = Path(manifest['historical_package' + host])
    assert sha(old / 'manifest.json') == manifest['historical_manifest_sha256']
    assert not (old / 'background').exists()
    if host == '4090':
        assert os.getuid() == 1015 and not (old / 'control').exists() and not (old / 'batch').exists()
        proof = old_gui(old)
        for task in plan['tasks']:
            assert sha(Path(task['original_private_path'])) == task['source_config_sha256'], task['task_id']
    else:
        assert os.getuid() == 1033 and not Path(manifest['historical_output3090']).exists()
        proof = old_models(old)
    return {'new_independent_paired_cohort': True, 'expected_trajectories': len(plan['queue']),
            'historical_proof_only': proof, 'old_paused_queue_resumed': False}


def verify_native_parent(package):
    return verify(package, '3090')


def verify_gui_parent(package):
    return verify(package, '4090')
