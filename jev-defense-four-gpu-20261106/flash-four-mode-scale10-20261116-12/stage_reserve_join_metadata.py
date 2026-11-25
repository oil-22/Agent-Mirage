"""Stage count-only joins for future one-task reserves; no runtime package.

All image review, signed capture, raw-audit, and delivery-assessment code stays
unchanged. The prior complete ledger replaces the initial fixed +2 baseline.
"""
import ast
import json
import time
from pathlib import Path

from control import HERE, save, sha
from join_reviewed_results import verify


def replace_once(text, before, after):
    assert text.count(before) == 1, before
    return text.replace(before, after)


def original_function(source, name):
    return next(node for node in ast.parse(source).body
                if isinstance(node, ast.FunctionDef) and node.name == name)


def assessment_loop(source):
    main = original_function(source, 'main')
    return next(node for node in main.body if isinstance(node, ast.For)
                and isinstance(node.target, ast.Name) and node.target.id == 'audit_root')


def main():
    original = (HERE / 'join_reviewed_results.py').read_text('utf8')
    root = HERE / ('reserve-join-metadata-staging-' + str(time.time_ns()))
    root.mkdir()
    variants = []
    for count in range(2, 6):
        source = replace_once(original, 'from control import HERE, PACKAGE, manifest, save, sha',
                              'from control import HERE, PACKAGE, manifest, save, sha\n'
                              'from reserve_cumulative_accounting import combine_reviewed_rows')
        source = replace_once(source, "group['processed_GUI_trajectories'] == 40",
                              "group['processed_GUI_trajectories'] == %d" % count)
        source = replace_once(source, "len({v['run_id'] for v in rows}) == 40",
                              "len({v['run_id'] for v in rows}) == %d" % count)
        source = replace_once(source, "len({v['run_id'] for v in clean}) == 8",
                              "len({v['run_id'] for v in clean}) == 1")
        anchor = "    result = {'version': manifest()['version'],"
        extra = (
            "    previous = json.loads((PACKAGE / 'previous-completed-campaign.json').read_bytes())['report']\n"
            "    prior_root = verify(previous['root'], previous['seal_sha256'])\n"
            "    prior_report = json.loads((prior_root / 'report.json').read_bytes())\n"
            "    ledger = combine_reviewed_rows(prior_report, rows)\n"
            "    assert ledger['new_counts'] == counts\n"
        )
        source = replace_once(source, anchor, extra + anchor)
        source = replace_once(source, "'complete_GUI_trajectories': 40,",
                              "'complete_GUI_trajectories': %d," % count)
        source = replace_once(source,
            "'cumulative_successful_complete_trajectories_per_condition': {k:v+2 for k,v in counts.items()},",
            "'cumulative_successful_complete_trajectories_per_condition': ledger['cumulative_counts'],\n"
            "        'cumulative_rows': ledger['cumulative_rows'],\n"
            "        'previous_completed_report_binding': previous,")
        source = replace_once(source,
            "'four_modes_ten_successful_examples_each': all(v+2 >= 10 for v in counts.values()),",
            "'four_modes_ten_successful_examples_each': ledger['all_four_modes_at_least_ten_successes'],")
        source = replace_once(source, "'clean_control_trajectories': 8,",
                              "'clean_control_trajectories': 1,")
        source = replace_once(source, "'new_task_ids': [0,3,17,58,89,94,112,131],",
                              "'new_task_ids': [task['task_id'] for task in json.loads((PACKAGE / 'plan.json').read_bytes())['tasks']],")
        source = replace_once(source, "'prior_verified_successes_per_mode': 2,",
                              "'prior_verified_successes_per_mode': ledger['prior_counts'],")
        ast.parse(source)
        # The entire frame/trajectory assessment loop, strict seal verifier,
        # and pointer verifier are the exact same syntax trees.
        for name in ('verify', 'pointer'):
            assert ast.dump(original_function(source, name)) == ast.dump(original_function(original, name))
        assert ast.dump(assessment_loop(source)) == ast.dump(assessment_loop(original))
        folder = root / ('count-%d' % count)
        folder.mkdir()
        (folder / 'join_reviewed_results.py').write_text(source, encoding='utf8')
        (folder / 'reserve_cumulative_accounting.py').write_bytes((HERE / 'reserve_cumulative_accounting.py').read_bytes())
        variants.append({'trajectories': count, 'new_task_count': 1,
                         'clean_control_required': True,
                         'join_source_sha256': sha(folder / 'join_reviewed_results.py'),
                         'actual_image_assessment_loop_AST_identical': True,
                         'seal_and_pointer_verifiers_AST_identical': True,
                         'all_previous_failed_and_clean_rows_retained': True})
    save(root / 'qualification.json', {
        'scope': 'CPU syntax/source comparison of future reserve join metadata only',
        'parent_join_source_sha256': sha(HERE / 'join_reviewed_results.py'),
        'accounting_source_sha256': sha(HERE / 'reserve_cumulative_accounting.py'),
        'variants': variants, 'current_runtime_and_auditors_unchanged': True,
        'reserve_runtime_package_ready': False, 'reporting_not_integrated': True,
        'no_new_model_GUI_calls': True,
    })
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p)
                            for p in root.rglob('*') if p.is_file()})
    verify(root)
    print(json.dumps({'root': str(root), 'seal_sha256': sha(root / 'seal.json'),
                      'draft_variants': [row['trajectories'] for row in variants],
                      'new_model_GUI_calls': 0, 'current_sources_unchanged': True}))


if __name__ == '__main__':
    main()
