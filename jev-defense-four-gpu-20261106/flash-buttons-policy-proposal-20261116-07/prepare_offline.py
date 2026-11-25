"""Bind the direct human approval to the previously sealed twenty-image proposal."""
import ast
import importlib.util
import json
import time
import uuid
from pathlib import Path

from remote_util import HERE, save, sha


def verify(root):
    for name, value in json.loads((root / 'seal.json').read_bytes()).items():
        assert sha(root / name) == value, name


def main():
    assert not (HERE / 'preparation-current.json').exists()
    prior = json.loads((HERE / 'proposal-current.json').read_bytes())
    proposal = Path(prior['root']); verify(proposal)
    assert sha(proposal / 'seal.json') == prior['seal_sha256'] == '235183292b7d74bb92707343d3d6ef14b5f793b01655d8bb7bfb7be091014294'
    plan = json.loads((proposal / 'control-plan.json').read_bytes())
    contract = proposal / 'proposed-gate-contract.json'
    assert sha(contract) == '23bc09d7f8efaea03d94865feade15312e4d953d6e6329c06a1d1087192fa8f6'
    assert len(plan['rows']) == plan['max_new_Flash_calls'] == 20 and plan['automatic_retries'] == 0
    root = HERE / ('preparation-' + str(time.time_ns())); root.mkdir()
    decision_before = json.loads((HERE / 'decision-request-current.json').read_bytes())
    save(root / 'user-authorization.json', {
        'created': time.time(), 'direct_human_reply_in_this_chat': True,
        'question_item_id': '["request_user_input_async","call_677bb0e98e6b4128bae13af888b91607",0]',
        'human_answer': '批准20次离线预检，审查后再定GUI（推荐）',
        'proposal': prior, 'prior_decision_pointer': decision_before,
        'scope': {'Flash_calls': 20, 'calls_per_frozen_image': 1, 'automatic_retries': 0, 'primary_calls': 0, 'GUI_actions': 0, 'official_scores': 0, 'paid_API_calls': 0},
        'new_GUI_release_authorized': False, 'prompt_threshold_or_model_changes_beyond_frozen_contract': False})
    parent = HERE.parent / 'flash-trusted-capture-protocol-20261116-06'
    old = json.loads((parent / 'preparation-current.json').read_bytes())
    old_package = Path(old['package']); old_manifest = json.loads((old_package / 'manifest.json').read_bytes())
    assert sha(old_package / 'manifest.json') == old['manifest_sha256']
    package = root / 'package'; package.mkdir(); flash = package / 'flash'; flash.mkdir(); (package / 'images').mkdir()
    copied = {}
    for name in ['flash_runtime.py', 'gate_core.py', 'wire_contract.py', 'flash-identity.json']:
        source = old_package / 'flash' / name
        assert sha(source) == old_manifest['files']['flash/' + name]
        (flash / name).write_bytes(source.read_bytes()); copied[name] = sha(source)
    (flash / 'gate-contract.json').write_bytes(contract.read_bytes())
    config = json.loads((old_package / 'flash/service-config.json').read_bytes())
    config['physical_gpu'] = 7
    save(flash / 'service-config.json', config)
    guard_source = (HERE / 'resource_guard.py').read_text('utf8')
    original_guard = (old_package / 'flash/resource_guard.py').read_text('utf8')
    assert sha(old_package / 'flash/resource_guard.py') == old_manifest['files']['flash/resource_guard.py']
    node = next(v for v in ast.parse(original_guard).body if isinstance(v, ast.FunctionDef) and v.name == 'checkpoint')
    checkpoint = ast.get_source_segment(original_guard, node)
    (flash / 'resource_guard.py').write_text(guard_source + '\n\n' + checkpoint + '\n', encoding='utf8')
    (package / 'run_offline.py').write_bytes((HERE / 'run_offline.py').read_bytes())
    cases = []
    for row in plan['rows']:
        source = proposal / row['image']; assert sha(source) == row['sha256']
        target = package / 'images' / (row['id'] + '.png'); target.write_bytes(source.read_bytes())
        cases.append({'id': row['id'], 'sha256': row['sha256'], 'request_id': uuid.uuid4().hex})
    assert len({v['sha256'] for v in cases}) == 20
    (package / 'user-authorization.json').write_bytes((root / 'user-authorization.json').read_bytes())
    for code in package.rglob('*.py'):
        compile(code.read_text('utf8'), str(code), 'exec')
    spec = importlib.util.spec_from_file_location('buttons_resource_test', flash / 'resource_guard.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    base = {'gpu': {7: {'uuid': 'test-UUID', 'free_mib': 23000}}, 'compute': []}
    tests = []
    module.check_card(base, 7, 'test-UUID', False, 123)
    tests.append({'name': 'empty_full_headroom', 'passed': True})
    module.check_card({**base, 'compute': [{'uuid': 'other', 'pid': 666}]}, 7, 'test-UUID', False, 123)
    tests.append({'name': 'other_card_foreign_allowed', 'passed': True})
    module.check_card({**base, 'compute': [{'uuid': 'test-UUID', 'pid': 123}]}, 7, 'test-UUID', True, 123)
    tests.append({'name': 'only_loaded_self_allowed', 'passed': True})
    rejected = [
        ('foreign_on_selected_card', {**base, 'compute': [{'uuid': 'test-UUID', 'pid': 666}]}, False, 'test-UUID'),
        ('late_foreign_after_load', {**base, 'compute': [{'uuid': 'test-UUID', 'pid': 123}, {'uuid': 'test-UUID', 'pid': 666}]}, True, 'test-UUID'),
        ('missing_loaded_self', base, True, 'test-UUID'),
        ('insufficient_headroom', {'gpu': {7: {'uuid': 'test-UUID', 'free_mib': 22999}}, 'compute': []}, False, 'test-UUID'),
        ('changed_UUID', base, False, 'unexpected-UUID')]
    for name, value, loaded, expected_uuid in rejected:
        try:
            module.check_card(value, 7, expected_uuid, loaded, 123)
        except RuntimeError:
            tests.append({'name': name, 'passed': True, 'rejected': True})
        else:
            raise AssertionError(name)
    save(root / 'prelaunch-review.json', {'resource_boundary_tests': tests, 'native_runtime_byte_identical': copied, 'native_checkpoint_function_AST_identical': ast.dump(ast.parse(checkpoint), include_attributes=False) == ast.dump(ast.parse(ast.get_source_segment((flash / 'resource_guard.py').read_text('utf8'), next(v for v in ast.parse((flash / 'resource_guard.py').read_text('utf8')).body if isinstance(v, ast.FunctionDef) and v.name == 'checkpoint'))), include_attributes=False), 'frozen_contract_sha256': sha(contract), 'twenty_complete_distinct_PNGs': True, 'private_labels_not_in_package': True, 'new_model_GUI_calls': 0})
    manifest = {'created': time.time(), 'study': HERE.name, 'max_calls': 20, 'automatic_retries': 0, 'cases': cases,
                'output': '/data/researcher/jev-defense-four-gpu-20261106/flash-buttons-policy-proposal-20261116-07/model-attempt-01',
                'remote_package': '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/flash-buttons-offline-20261116-07',
                'contract_sha256': sha(contract), 'proposal_seal_sha256': prior['seal_sha256'],
                'private_labels_not_sent': True, 'new_primary_GUI_paid_calls': 0,
                'files': {q.relative_to(package).as_posix(): sha(q) for q in package.rglob('*') if q.is_file()}}
    save(package / 'manifest.json', manifest)
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {q.relative_to(root).as_posix(): sha(q) for q in root.rglob('*') if q.is_file()})
    pointer = {'root': str(root), 'package': str(package), 'manifest_sha256': sha(package / 'manifest.json'), 'seal_sha256': sha(root / 'seal.json'), 'authorized_Flash_calls': 20, 'new_GUI_authorized': False}
    save(HERE / 'preparation-current.json', pointer)
    save(HERE / 'user-authorization-current.json', {'root': str(root), 'seal_sha256': sha(root / 'seal.json'), 'status': 'approved_development_only'})
    temporary = HERE / ('.decision-' + str(time.time_ns()))
    save(temporary, {'root': str(root), 'seal_sha256': sha(root / 'seal.json'), 'status': 'approved_development_only', 'prior_pointer_preserved': decision_before})
    temporary.replace(HERE / 'decision-request-current.json')
    print(json.dumps({'package': str(package), 'manifest_sha256': pointer['manifest_sha256'], 'resource_tests': len(tests), 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
