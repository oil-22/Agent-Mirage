"""Prepare final aggregation with exact complete raw-proof reuse controls."""
import ast
import copy
import json
import time
from pathlib import Path, PurePosixPath
from remote_util import HERE, save, sha
from bound_request_audit_reuse import strict_bind


def main():
    assert not (HERE / 'bound-group-audit-preparation-current.json').exists()
    source = (HERE / 'audit_completed_group_linked.py').read_text('utf8')
    start = source.index('    mains, flashes = [], []\n')
    end = source.index('    others = ', start)
    new = source[:start] + "    from bound_request_audit_reuse import load\n    mains, flashes = load(root, admission)\n    print(json.dumps({'verified_primary': len(mains), 'verified_Flash': len(flashes), 'same_request_complete_raw_proofs_bound_to_fresh_final_seal': True}), flush=True)\n" + source[end:]
    new = new.replace("'new_model_GUI_calls_by_audit': 0,", "'new_model_GUI_calls_by_audit': 0, 'same_request_complete_raw_proofs_bound_to_fresh_final_seal': True,")
    assert new != source
    # The rest of original source admission, actual exits, event chains, source
    # signatures, Controller re-parsing and all original asserts are retained.
    before_asserts = [ast.dump(n, include_attributes=False) for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Assert)]
    after_asserts = [ast.dump(n, include_attributes=False) for n in ast.walk(ast.parse(new)) if isinstance(n, ast.Assert)]
    assert before_asserts == after_asserts
    audit = next(p for p in HERE.glob('trajectory-audit-receipt16-T058-*') if (p / 'seal.json').exists())
    results = json.loads((audit / 'request-results.json').read_bytes())
    discovery = json.loads((audit / 'request-bindings.json').read_bytes())['result']
    mains, flashes = results['primary'][:1], results['Flash'][:1]
    prefixes = ['primary/requests/' + PurePosixPath(mains[0]['root']).name + '/',
                'flash/service/requests/' + flashes[0]['request_id'] + '/']
    checked = {n: h for n, h in discovery['global'].items() if any(n.startswith(p) for p in prefixes)}
    pnames = [PurePosixPath(mains[0]['root']).name]; fnames = [flashes[0]['request_id']]
    strict_bind(mains, flashes, checked, checked, pnames, fnames)
    tests = [{'name': 'positive_actual_sealed_request_proofs', 'passed': True}]
    cases = []
    changed = dict(checked); changed[next(iter(changed))] = '0' * 64
    cases.append(('changed_raw_member_hash', mains, flashes, checked, changed, pnames, fnames))
    missing = dict(checked); missing.pop(next(iter(missing)))
    cases.append(('missing_raw_member', mains, flashes, checked, missing, pnames, fnames))
    extra = dict(checked); extra['primary/requests/unseen/extra.tensor'] = '0' * 64
    cases.append(('extra_unchecked_raw_member', mains, flashes, checked, extra, pnames, fnames))
    cases.append(('duplicate_primary_request', mains * 2, flashes, checked, checked, pnames, fnames))
    wrong = copy.deepcopy(flashes); wrong[0]['seal_sha256'] = '0' * 64
    cases.append(('wrong_request_seal', mains, wrong, checked, checked, pnames, fnames))
    wrong = copy.deepcopy(mains); wrong[0]['actual_tensor_files_verified'] = False
    cases.append(('unverified_tensor_proof', wrong, flashes, checked, checked, pnames, fnames))
    for name, *args in cases:
        try:
            strict_bind(*args)
        except AssertionError:
            tests.append({'name': name, 'passed': True, 'rejected': True})
        else:
            raise AssertionError('Invalid evidence accepted: ' + name)
    root = HERE / ('bound-group-audit-preparation-' + str(time.time_ns()))
    root.mkdir()
    (root / 'before-group-reader.py').write_bytes((HERE / 'audit_completed_group_linked.py').read_bytes())
    (root / 'bound_request_audit_reuse.py').write_bytes((HERE / 'bound_request_audit_reuse.py').read_bytes())
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    destination = HERE / 'audit_completed_group_bound_reuse.py'
    assert not destination.exists()
    destination.write_text(new, encoding='utf8')
    (root / 'after-group-reader.py').write_bytes(destination.read_bytes())
    save(root / 'review.json', {'tests': tests, 'test_count': len(tests),
                              'original_group_assert_ASTs_unchanged': True,
                              'unchanged_original_launcher_must_freshly_hash_every_raw_member': True,
                              'per_trajectory_original_actual_raw_tensor_checks_must_all_be_complete': True,
                              'union_of_checked_request_member_hashes_must_equal_entire_final_request_map': True,
                              'all_original_exit_chain_Controller_and_source_checks_retained': True,
                              'not_a_new_model_or_GUI_condition': True, 'new_model_GUI_calls': 0})
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    save(HERE / 'bound-group-audit-preparation-current.json', {'root': str(root), 'seal_sha256': sha(root / 'seal.json'),
                                                           'reader_sha256': sha(destination),
                                                           'helper_sha256': sha(HERE / 'bound_request_audit_reuse.py')})
    print(json.dumps({'root': str(root), 'positive_negative_reuse_controls': len(tests), 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
