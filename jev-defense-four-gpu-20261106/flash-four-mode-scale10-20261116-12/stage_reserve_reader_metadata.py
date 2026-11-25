"""Qualify count-only reader variants for later, separately frozen reserves.

These drafts cannot launch anything: they have no runtime package, submission,
or qualification pointer. Current experiment sources are never edited.
"""
import ast
import hashlib
import json
import time
from pathlib import Path

from control import HERE, save, sha
from join_reviewed_results import verify


def replace_exact(text, before, after, occurrences=1):
    assert text.count(before) == occurrences, before
    return text.replace(before, after)


def function_source(text, name):
    node = next(n for n in ast.parse(text).body
                if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.dump(node, include_attributes=False)


def evaluate_readers(text):
    node = next(n for n in ast.parse(text).body
                if isinstance(n, ast.FunctionDef) and n.name == 'readers')
    namespace = {'ast': ast, 'HERE': HERE, 'Path': Path}
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'count-only-readers', 'exec'), namespace)
    return namespace['readers']()[1]


def main():
    names = ['control.py', 'audit_completed_group_bound_reuse.py',
             'bound_request_audit_reuse.py', 'audit_finished_trajectory.py']
    originals = {name: (HERE / name).read_text('utf8') for name in names}
    base_readers = evaluate_readers(originals['audit_completed_group_bound_reuse.py'])
    root = HERE / ('reserve-reader-metadata-staging-' + str(time.time_ns()))
    root.mkdir()
    results = []
    for count in range(2, 6):
        sources = dict(originals)
        sources['control.py'] = replace_exact(
            sources['control.py'], "m['trajectories']==40", "m['trajectories']==%d" % count)
        sources['control.py'] = replace_exact(
            sources['control.py'], "h['expected']==40", "h['expected']==%d" % count)
        sources['control.py'] = replace_exact(
            sources['control.py'], "'expected_trajectories':40", "'expected_trajectories':%d" % count)
        group = sources['audit_completed_group_bound_reuse.py']
        group = replace_exact(group, "status['expected']==40", "status['expected']==%d" % count, 2)
        group = replace_exact(group, '<=40*70', '<=%d*70' % count)
        group = replace_exact(group, 'len(controllers)==40', 'len(controllers)==%d' % count)
        group = replace_exact(group, "'target_per_condition': 8", "'target_per_condition': 1")
        sources['audit_completed_group_bound_reuse.py'] = group
        sources['bound_request_audit_reuse.py'] = replace_exact(
            sources['bound_request_audit_reuse.py'], 'assert len(run_ids) == 40',
            'assert len(run_ids) == %d' % count)
        for name, source in sources.items():
            ast.parse(source)
        current = evaluate_readers(group)
        for name in ['COMMON', 'PRIMARY', 'FLASH']:
            assert current[name] == base_readers[name], name
        for name in ['ADMISSION', 'GUI']:
            expected = base_readers[name].replace("status['expected']==40", "status['expected']==%d" % count)
            expected = expected.replace('<=40*70', '<=%d*70' % count)
            expected = expected.replace('len(controllers)==40', 'len(controllers)==%d' % count)
            assert current[name] == expected, name
        assert sources['audit_finished_trajectory.py'] == originals['audit_finished_trajectory.py']
        assert function_source(sources['bound_request_audit_reuse.py'], 'strict_bind') == function_source(
            originals['bound_request_audit_reuse.py'], 'strict_bind')
        folder = root / ('count-%d' % count)
        folder.mkdir()
        for name, source in sources.items():
            (folder / name).write_text(source, encoding='utf8')
        results.append({'trajectories': count, 'one_new_task': True,
                        'matched_clean_control_required': True,
                        'source_hashes': {name: sha(folder / name) for name in names},
                        'unchanged_primary_Flash_raw_readers': {
                            name: hashlib.sha256(current[name].encode()).hexdigest()
                            for name in ['COMMON', 'PRIMARY', 'FLASH']},
                        'same_request_union_and_tensor_EOS_history_probability_rules_unchanged': True})
    save(root / 'qualification.json', {
        'scope': 'CPU compilation and exact source comparison for later queue-count metadata only',
        'parent_sources': {name: sha(HERE / name) for name in names}, 'variants': results,
        'current_runtime_unchanged': True, 'no_new_model_GUI_calls': True,
        'formal_reserve_package_prepared': False,
        'requires_completed_initial_report_then_original_frozen_reserve_order': True,
        'requires_new_runtime_package_qualification_and_owned_lease_before_launch': True,
    })
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p)
                            for p in root.rglob('*') if p.is_file()})
    verify(root)
    print(json.dumps({'root': str(root), 'seal_sha256': sha(root / 'seal.json'),
                      'CPU_metadata_variants': [r['trajectories'] for r in results],
                      'current_runtime_unchanged': True, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
