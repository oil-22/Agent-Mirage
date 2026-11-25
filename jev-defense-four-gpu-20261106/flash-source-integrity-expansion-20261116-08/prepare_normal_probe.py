"""One new complete-input normal-minimal probe under the original Flash prompt."""
import json
import time
import uuid
from pathlib import Path
from remote_util import HERE, save, sha


def main():
    assert not (HERE / 'preparation-current.json').exists()
    parent = HERE.parent / 'flash-buttons-policy-proposal-20261116-07'
    pp = json.loads((parent / 'proposal-current.json').read_bytes())
    proposal = Path(pp['root'])
    assert sha(proposal / 'seal.json') == pp['seal_sha256']
    for n, h in json.loads((proposal / 'seal.json').read_bytes()).items():
        assert sha(proposal / n) == h
    row = next(v for v in json.loads((proposal / 'control-plan.json').read_bytes())['rows'] if v['id'] == 'n01')
    previous = json.loads((parent / 'preparation-current.json').read_bytes())
    package_before = Path(previous['package']); old = json.loads((package_before / 'manifest.json').read_bytes())
    assert sha(package_before / 'manifest.json') == previous['manifest_sha256']
    root = HERE / ('normal-probe-preparation-' + str(time.time_ns())); root.mkdir()
    package = root / 'package'; package.mkdir(); (package / 'flash').mkdir(); (package / 'images').mkdir()
    for name in ['flash_runtime.py', 'gate_core.py', 'wire_contract.py', 'flash-identity.json', 'resource_guard.py', 'service-config.json']:
        source = package_before / 'flash' / name
        assert sha(source) == old['files']['flash/' + name]
        (package / 'flash' / name).write_bytes(source.read_bytes())
    (package / 'flash/gate-contract.json').write_bytes((proposal / 'original-gate-contract.json').read_bytes())
    worker = (package_before / 'run_offline.py').read_text('utf8')
    assert sha(package_before / 'run_offline.py') == old['files']['run_offline.py']
    for before, after in [(' == 20', ' == 1'), (' < 20', ' < 1'), ("'max_calls'] == 20", "'max_calls'] == 1"), ('jev-flash-buttons-offline-20261116-07.lock', 'jev-normal-minimal-probe-20261116-08.lock')]:
        worker = worker.replace(before, after)
    (package / 'run_offline.py').write_text(worker, encoding='utf8')
    (package / 'images/n01.png').write_bytes((proposal / row['image']).read_bytes())
    assert sha(package / 'images/n01.png') == row['sha256']
    save(package / 'user-authorization.json', {
        'created': time.time(), 'direct_human_goal_in_this_chat': True,
        'human_instruction': '给你一个目标，不断进行实验，直到修复到能完整出现好的防御效果并且尽可能减少过度防御',
        'scope_this_attempt': 'one new original-prompt Flash call on the previously strict-prompt-refused normal-minimal original PNG; zero retry/primary/GUI/paid calls',
        'broader_goal_authorizes_separate_new_source_bound_iterations': True,
        'old_terminals_and_budget_caps_immutable': True})
    manifest = {'created': time.time(), 'study': HERE.name, 'max_calls': 1, 'automatic_retries': 0,
                'cases': [{'id': 'n01', 'sha256': row['sha256'], 'request_id': uuid.uuid4().hex}],
                'output': '/data/researcher/jev-defense-four-gpu-20261106/flash-source-integrity-expansion-20261116-08/normal-probe-attempt-01',
                'remote_package': '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/flash-normal-probe-20261116-08',
                'contract_sha256': sha(package / 'flash/gate-contract.json'),
                'original_prior_strict_prompt_result_separate': True,
                'private_labels_not_sent': True, 'new_primary_GUI_paid_calls': 0,
                'files': {q.relative_to(package).as_posix(): sha(q) for q in package.rglob('*') if q.is_file()}}
    save(package / 'manifest.json', manifest)
    for q in package.rglob('*.py'):compile(q.read_text('utf8'), str(q), 'exec')
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {q.relative_to(root).as_posix(): sha(q) for q in root.rglob('*') if q.is_file()})
    save(HERE / 'preparation-current.json', {'root': str(root), 'package': str(package), 'manifest_sha256': sha(package / 'manifest.json'), 'seal_sha256': sha(root / 'seal.json')})
    print(json.dumps({'root': str(root), 'max_new_Flash_calls': 1, 'original_prompt_restored_only_for_new_attempt': True, 'model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
