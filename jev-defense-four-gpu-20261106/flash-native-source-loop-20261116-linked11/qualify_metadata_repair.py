"""New CPU binding boundaries; reuse unchanged completed protocol controls."""
import ast
import copy
import json
import time
from pathlib import Path
from remote_util import HERE, save, sha


def main():
    pp = json.loads((HERE / 'preparation-current.json').read_bytes()); package = Path(pp['package']); m = json.loads((package / 'manifest.json').read_bytes())
    assert sha(package / 'manifest.json') == pp['manifest_sha256']
    for name, h in m['files'].items(): assert sha(package / name) == h
    old = HERE.parent / 'flash-native-source-loop-20261116-09'
    prior = json.loads((old / 'CPU-routing-current.json').read_bytes()); prior_root = Path(prior['root'])
    assert sha(prior_root / 'seal.json') == prior['seal_sha256']
    assert json.loads((prior_root / 'result.json').read_bytes())['routing_controls'] == 11
    assert sha(HERE / 'test_trusted_routing.py') == sha(old / 'test_trusted_routing.py')
    parent = Path(json.loads((old / 'preparation-current.json').read_bytes())['package'])
    for name in ['gui_experiment.py','injection.py','capture_source.py','capture_client.py','native_fault.py','flash/gate_core.py','flash/flash_runtime.py','flash/gate-contract.json','actor-template.json','primary_server.py','parent-capacity.json']:
        assert sha(package / name) == sha(parent / name), name
    tree = ast.parse((package / 'historical_memory.py').read_text('utf8'))
    fn = next(n for n in tree.body if getattr(n,'name','') == 'validate_active_sources')
    scope = {'json': json}; exec(compile(ast.Module(body=[fn], type_ignores=[]), '<isolated-source-binding-check>', 'exec'), scope)
    binding = json.loads((package / 'parent-capacity.json').read_bytes())
    check = scope['validate_active_sources']; current = check(binding, package, sha)
    tests = [{'name': 'actual_active_and_historical_sources_bound', 'passed': True}]
    for name in ['flash/gate-contract.json','reference-original-Flash-contract.json','active-Flash-quality-readiness.json','flash/flash_runtime.py','memory_lifetime.py','actor-template.json','release/defense/qwen_backend.py']:
        def tampered(path, name=name):
            return '0'*64 if Path(path) == package / name else sha(path)
        try:
            check(binding, package, tampered)
        except AssertionError:
            tests.append({'name': 'reject_modified_' + name, 'passed': True})
        else:
            raise AssertionError(name)
    wrong = copy.deepcopy(binding); wrong['source_hashes']['flash/gate-contract.json'] = current['active_contract_sha256']
    try:
        check(wrong, package, sha)
    except AssertionError:
        tests.append({'name': 'reject_rewriting_historical_contract_as_new', 'passed': True})
    else:
        raise AssertionError('Historical evidence may not be silently rewritten')
    root = HERE / ('metadata-CPU-qualification-' + str(time.time_ns())); root.mkdir()
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'result.json', {'passed': True, 'new_metadata_boundaries': tests, 'original_11_routing_checks_exact_source_reused': prior, 'original_19_native_browser_checks_exact_source_reused': json.loads((HERE / 'CPU-source-current.json').read_bytes()), 'all_actual_historical_model_proofs_retained_not_reexecuted': True, 'new_model_GUI_calls': 0, 'manifest_sha256': pp['manifest_sha256']})
    save(root / 'seal.json', {q.name: sha(q) for q in root.iterdir() if q.is_file()})
    save(HERE / 'CPU-routing-current.json', {'root': str(root), 'seal_sha256': sha(root / 'seal.json'), 'passed': True, 'manifest_sha256': pp['manifest_sha256']})
    print(json.dumps({'root': str(root), 'new_metadata_tests': len(tests), 'old_controls_reused_not_rerun': True, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
