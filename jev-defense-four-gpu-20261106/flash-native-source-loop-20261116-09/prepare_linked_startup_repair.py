"""New linked attempt: repair source metadata, preserve zero-call failure."""
import ast
import json
import secrets
import time
from pathlib import Path
from remote_util import HERE, save, sha


SOURCE_GUARD = '''def validate_active_sources(binding, package, sha):
    # Historical primary-memory proof and original Flash contract are immutable.
    # The independently audited active prompt is a separate source binding.
    names = ['memory_lifetime.py', 'torch_chunk_lifetime.py', 'mlp_lifetime.py',
             'explicit-placement.json', 'actor-template.json', 'release/defense/qwen_backend.py',
             'flash/flash_runtime.py']
    for name in names:
        assert sha(package / name) == binding['source_hashes'][name], name
    current = json.loads((package / 'active-Flash-contract-binding.json').read_bytes())
    assert current['historical_contract_sha256'] == binding['source_hashes']['flash/gate-contract.json']
    assert sha(package / 'reference-original-Flash-contract.json') == current['historical_contract_sha256']
    assert sha(package / 'flash/gate-contract.json') == current['active_contract_sha256']
    readiness = json.loads((package / 'active-Flash-quality-readiness.json').read_bytes())
    assert sha(package / 'active-Flash-quality-readiness.json') == current['readiness_sha256']
    assert readiness['passed'] and readiness['contract_sha256'] == current['active_contract_sha256']
    assert current['primary_memory_arithmetic_history_generation_unchanged'] is True
    return current


'''


def main():
    pointer = json.loads((HERE / 'preparation-current.json').read_bytes()); before = Path(pointer['package']); m = json.loads((before / 'manifest.json').read_bytes())
    failure = json.loads((HERE / 'startup-failure-preservation-current.json').read_bytes()); failed = Path(failure['root'])
    assert sha(failed / 'seal.json') == failure['seal_sha256']
    for name, h in json.loads((failed / 'seal.json').read_bytes()).items(): assert sha(failed / name) == h
    preserved = json.loads((failed / 'result.json').read_bytes()); assert preserved['actual_new_actor_Flash_GUI_calls'] == 0 and preserved['all_original_exited_and_17_locks_released']
    study = HERE.parent / 'flash-native-source-loop-20261116-linked11'; study.mkdir(exist_ok=False)
    manager_names = ['remote_util.py','control.py','collect_progress.py','inspect_owned_runtime.py','watch_current_campaign.py','audit_completed_group.py','audit_completed_group_bound_reuse.py','audit_finished_trajectory.py','protocol_audit_components.py','bound_request_audit_reuse.py','export_examples.py','audit_resource_interval.py','audit_released_resources.py','test_trusted_routing.py','CPU-source-current.json','source-review-current.json','independent-source-image-notes-current.json','completed-parent-3090.json','completed-parent-4090.json']
    for name in manager_names: (study / name).write_bytes((HERE / name).read_bytes())
    root = study / ('preparation-' + str(time.time_ns())); root.mkdir(); package = root / 'package'; package.mkdir()
    assert sha(before / 'manifest.json') == pointer['manifest_sha256']
    for name, h in m['files'].items():
        assert sha(before / name) == h, name
        dest = package / name; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes((before / name).read_bytes())
    source = (before / 'historical_memory.py').read_text('utf8')
    start = source.index("    for name in ['memory_lifetime.py'")
    end = source.index('    resource(True)', start)
    historical_checks = source[start:end]
    source = source[:start] + '    active_Flash_binding = validate_active_sources(binding, package, sha)\n' + source[end:]
    pos = source.index('def install('); source = source[:pos] + SOURCE_GUARD + source[pos:]
    source = source.replace("        'historical_proof_only': True,", "        'active_Flash_prompt_source_binding': active_Flash_binding,\n        'historical_proof_only': True,")
    (package / 'historical_memory.py').write_text(source, encoding='utf8')
    (root / 'original-source-checks.txt').write_text(historical_checks, encoding='utf8')
    # Every line after resource admission that touches model functions is unchanged,
    # apart from adding the explicit binding to the installation's audit record.
    old_body = (before / 'historical_memory.py').read_text('utf8').split('    resource(True)',1)[1]
    new_body = source.split('    resource(True)',1)[1].replace("        'active_Flash_prompt_source_binding': active_Flash_binding,\n", '')
    assert old_body == new_body
    contract = HERE.parent / 'flash-buttons-policy-proposal-20261116-07/proposal-1794806203093537600/original-gate-contract.json'
    (package / 'reference-original-Flash-contract.json').write_bytes(contract.read_bytes())
    quality = HERE.parent / 'flash-quality-only-development-20261116-10'
    (package / 'active-Flash-quality-readiness.json').write_bytes((quality / 'release-readiness-current.json').read_bytes())
    save(package / 'active-Flash-contract-binding.json', {'historical_contract_sha256': sha(contract), 'active_contract_sha256': sha(package / 'flash/gate-contract.json'), 'readiness_sha256': sha(package / 'active-Flash-quality-readiness.json'), 'primary_memory_arithmetic_history_generation_unchanged': True, 'purpose': 'explicit audited Flash prompt rebinding; historical capacity proof remains original and is not reclassified as new prompt or current-process proof'})
    (package / 'private.token').write_text(secrets.token_hex(32), encoding='utf8')
    queue = [{**v, 'run_id': v['run_id'].replace('native16-', 'native16b-')} for v in m['remaining_queue']]
    version = 'trusted-native-capture-quality-v3-four-mode-linked1'
    plan = json.loads((package / 'plan.json').read_bytes()); plan.update(version=version, queue=queue, linked_zero_call_startup_failure=failure)
    (package / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf8')
    analysis = json.loads((package / 'analysis-plan.json').read_bytes()); analysis.update(queue=queue, linked_zero_call_startup_failure=failure)
    (package / 'analysis-plan.json').write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding='utf8')
    guard = (package / 'continuation_guard.py').read_text('utf8').replace(m['study'], version)
    guard = guard.replace("    return {'host': host,", "    failed = json.loads((package / ('failed-startup-binding-' + host + '.json')).read_bytes())\n    for path, row in failed['files'].items():\n        assert sha(Path(path)) == row['sha256'], path\n    for path in failed.get('absent', []):\n        assert not Path(path).exists(), path\n    for row in failed.get('processes', []):\n        saved = row['saved']; proc = Path('/proc', str(saved['pid']))\n        actual = identity(saved['pid']) if proc.exists() else None\n        assert actual is None or actual['state'] in ['Z', 'X'] or any(actual[k] != saved[k] for k in ['uid', 'command', 'start_ticks'])\n    return {'host': host,")
    (package / 'continuation_guard.py').write_text(guard, encoding='utf8')
    save(package / 'failed-startup-binding-3090.json', {'files': {name: {'sha256': row['sha256']} for name, row in preserved['files'].items()}, 'processes': preserved['processes'], 'preservation_seal_sha256': failure['seal_sha256'], 'actual_model_calls': 0})
    save(package / 'failed-startup-binding-4090.json', {'files': {m['package4090'] + '/manifest.json': {'sha256': pointer['manifest_sha256']}}, 'absent': [m['package4090'] + '/' + v for v in ['batch','control','background']], 'actual_GUI_trajectories': 0})
    launch = (package / 'launch_group.py').read_text('utf8').replace('jev-native-source-loop-20261116-09.lock','jev-native-source-loop-20261116-linked11.lock')
    (package / 'launch_group.py').write_text(launch, encoding='utf8')
    for name in ['primary_server.py','gui_experiment.py','flash/gate_core.py','flash/flash_runtime.py','flash/gate-contract.json','actor-template.json','capture_source.py','capture_client.py','native_fault.py','injection.py','parent-capacity.json']:
        assert sha(package / name) == sha(before / name), name
    for q in package.rglob('*.py'): ast.parse(q.read_text('utf8'))
    files = {q.relative_to(package).as_posix(): sha(q) for q in package.rglob('*') if q.is_file() and q.name != 'private.token'}
    manifest = {**m, 'created': time.time(), 'version': version, 'study': version, 'remaining_queue': queue, 'files': files, 'auth_token_sha256': sha(package / 'private.token'), 'package3090': '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/' + study.name, 'package4090': '/data/researcher/jev-defense-four-gpu-20261106/' + study.name + '/runtime', 'output3090': '/data/researcher/jev-defense-four-gpu-20261106/' + study.name + '/model-attempt-01', 'linked_failed_manifest_sha256': pointer['manifest_sha256'], 'linked_failure_preservation': failure, 'source_metadata_binding_repair_only': True}
    save(package / 'manifest.json', manifest)
    save(root / 'source-invariance.json', {'historical_capacity_original_proof_and_contract_retained': True, 'all_primary_memory_kernel_installation_operations_unchanged': True, 'active_Flash_contract_not_claimed_covered_by_old_capacity_test': True, 'new_quality_prompt_exact_same_as_completed20': True, 'same_unsent10_GUI_configs_and_per_trajectory_budget': True, 'no_completed_model_control_rerun': True})
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {q.relative_to(root).as_posix(): sha(q) for q in root.rglob('*') if q.is_file()})
    save(study / 'preparation-current.json', {'root': str(root), 'package': str(package), 'manifest_sha256': sha(package / 'manifest.json'), 'seal_sha256': sha(root / 'seal.json')})
    print(json.dumps({'study': str(study), 'manifest_sha256': sha(package / 'manifest.json'), 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
