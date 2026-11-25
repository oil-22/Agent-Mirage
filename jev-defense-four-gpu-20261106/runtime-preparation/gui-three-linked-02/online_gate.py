"""Exact new three-trajectory runtime gate; no model imports or HTTP."""
import json
from pathlib import Path

from online_contract import validate_plan
from online_service import sha

BASE = Path('/home/researcher/jev-defense-four-gpu-20261106')
CAPACITY_SHA = 'fc5919611dc79e478684cbffc226cd98e40285b645f856029c694ad0173be366'
CAPACITY_SPEC_SHA = '1b8c78a9127f81af006f78221dfece70b898a158b1c0cca30b6bae881fc11a6f'
CAPACITY_TERMINAL_SHA = 'ad5cb5df1809a13b021cd71120cac4b54fc8eb9c36cb58ef41d29067c1d9881a'
PLAN_SHA = '838c63ac36560040df0c9257f4080d7c5ef33e7a0858f9b42bbdb73f486a2cef'
OBSERVER_SHA = 'fa0140293d55d9525f2558fc17d1214931bf7a718b6e78c3eb8b91208c13ba26'


def read(path): return json.loads(Path(path).read_bytes())


def bound(item, expected=None):
    path = Path(item['path'])
    if path.is_symlink() or sha(path) != item['sha256'] or (expected and item['sha256'] != expected):
        raise RuntimeError('Required evidence bytes differ: ' + str(path))
    return read(path)


def validate_capacity(capacity):
    flags = ('capacity_passed', 'native_IDs_pixels_grid_exact_original_failed_CPU_proof',
        'original_config_and_schema_exact', 'original_native_generation_budget4096_preserved',
        'BF16_SDPA_and_original_model_methods', 'new_device_map_14_22_22_6_actual',
        'both_native_CUDA_tensor_audits_bound', 'natural_native_EOS',
        'client_seal_verified_without_self_reference', 'new_atomic_evidence_files_actual_seals_verified',
        'new_marker_stop_no_force_no_launcher_failure', 'new_workers_absent_and_target_compute_empty',
        'old_unknown_worker_exit_not_rewritten')
    if (capacity.get('status') != 'passed' or any(capacity.get(k) is not True for k in flags) or
            capacity.get('input_tokens') != 21470 or capacity.get('original_images') != 12 or
            capacity.get('output_tokens') != 693 or capacity.get('primary_calls') != 1 or
            capacity.get('helper_calls') != 0 or capacity.get('pending_requests') != 0 or
            capacity.get('actor_GUI_scorer_calls') != 0 or
            capacity.get('primary_process_allocator_actual') != 'expandable_segments:True' or
            capacity.get('new_stop_actual_exit_codes') != {'primary': 0, 'pplx_flash': 0} or
            capacity.get('reviewed_spec_sha256') != CAPACITY_SPEC_SHA or
            capacity.get('terminal_manifest_sha256') != CAPACITY_TERMINAL_SHA):
        raise RuntimeError('Only actual exact21470/12image/4096 new capacity completion admits this runtime')


def validate_static(spec, here):
    if (spec.get('stage') != 'new_exact_three_online14_22_22_6' or
            spec.get('layer_counts') != [14,22,22,6] or
            spec.get('primary_allocator') != 'expandable_segments:True' or
            spec.get('resume_old_GUI_budget') is not False or
            spec.get('automatic_retry') is not False or spec.get('maximum_primary_calls') != 630 or
            spec.get('maximum_auxiliary_calls') != 120 or spec.get('online_plan_sha256') != PLAN_SHA):
        raise RuntimeError('Exact new three-run/common-layout/allocator/no-resume contract differs')
    if sha(Path(spec['online_plan'])) != PLAN_SHA:
        raise RuntimeError('Exact three-trajectory plan differs')
    validate_plan(read(spec['online_plan']))
    for name, expected in spec['online_source_sha256'].items():
        if sha(Path(here) / name) != expected:
            raise RuntimeError('Online source differs: ' + name)
    for name, expected in spec['preflight_source_sha256'].items():
        if sha(Path(spec['preflight_source_root']) / name) != expected:
            raise RuntimeError('Actual proven native implementation differs: ' + name)
    if sha(Path(spec['capacity_spec'])) != CAPACITY_SPEC_SHA:
        raise RuntimeError('Actual completed capacity specification differs')
    if (sha(Path(spec['layout'])) != spec['layout_sha256'] or
            sha(Path(spec['primary_native_layout_receipt'])) != spec['primary_native_layout_receipt_sha256']):
        raise RuntimeError('Actual native layout or header provenance differs')


def verify_gate(spec, verify_manifest, validate_old_terminal, inspect_identity, same):
    path = Path(spec['online_launch_gate'])
    if sha(path) != spec['online_launch_gate_sha256']:
        raise RuntimeError('New explicit runtime gate differs')
    gate = read(path)
    if (gate.get('stage') != 'new_exact_three_online_authorization' or gate.get('approved') is not True or
            gate.get('once_only') is not True or gate.get('online_plan_sha256') != PLAN_SHA or
            gate.get('observer_contract_sha256') != spec['flash_observer_contract_sha256']):
        raise RuntimeError('Root-reviewed new once-only runtime gate is required')
    capacity = bound(gate['evidence']['primary_full_input_capacity'], CAPACITY_SHA)
    validate_capacity(capacity)
    observer = bound(gate['evidence']['observer_independent_review'], OBSERVER_SHA)
    if any(observer.get(k) is not True for k in ('actual_input_forward_audited',
            'original_source_images_reviewed','passed_for_gui_development','no_defense_success_claim')):
        raise RuntimeError('Original observer review does not admit development')
    terminal = Path(gate['capacity_terminal_manifest'])
    if str(terminal.parent) != capacity['group'] or gate['capacity_terminal_manifest_sha256'] != CAPACITY_TERMINAL_SHA:
        raise RuntimeError('Actual completed capacity terminal binding differs')
    verify_manifest(terminal.parent, terminal, CAPACITY_TERMINAL_SHA)
    exited = read(terminal.parent / 'exit.json')
    if {r['role']:r['exit_code'] for r in exited['workers']} != {'primary':0,'pplx_flash':0}:
        raise RuntimeError('Actual new capacity workers did not both exit normally')
    for row in exited['workers']:
        if same(inspect_identity(row['identity']['pid']), row['identity']):
            raise RuntimeError('Old exact capacity worker still live')
    # Preserve the old real OOM and unknown original exit metadata; no exception
    # is applied to its semantic/model failure or repeated trajectory budget.
    old = validate_old_terminal(read(spec['capacity_spec']))
    return path, gate, old
