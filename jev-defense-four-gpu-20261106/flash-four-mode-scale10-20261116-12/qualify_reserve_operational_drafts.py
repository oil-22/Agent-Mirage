"""Check future operational drafts while the real initial campaign continues."""
import ast
import json
import time
from pathlib import Path

from control import HERE, PACKAGE, save, sha
from join_reviewed_results import verify
from prepare_reserve_campaign import PARENT_CODE, load_plan
from write_reserve_report import previous_cohorts
from reserve_cumulative_accounting import counts_from_rows


def main():
    assert not (HERE / 'completed-report-current.json').exists()
    source_names = ['prepare_reserve_campaign.py', 'qualify_reserve_campaign.py',
                    'write_reserve_report.py', 'qualify_reserve_operational_drafts.py']
    for name in source_names:
        ast.parse((HERE / name).read_text('utf8'))
    compile(PARENT_CODE, 'future-parent-readonly-binding', 'exec')
    root = HERE / ('reserve-operational-draft-qualification-' + str(time.time_ns()))
    root.mkdir()
    fixture = root / 'CPU-ONLY-incomplete-parent'
    fixture.mkdir()
    save(fixture / 'plan.json', {
        'scope': 'CPU-only negative guard fixture; not an experiment or parent proof',
        'completed_campaign_report': {'root': str(HERE / 'unavailable-completed-report-fixture')},
    })
    save(fixture / 'seal.json', {'plan.json': sha(fixture / 'plan.json')})
    rejected = None
    try:
        load_plan(fixture)
    except AssertionError as exc:
        rejected = str(exc)
    assert rejected == 'A running campaign cannot prepare a reserve child'
    assert not (HERE / 'reserve-child-intent.json').exists()
    previous = json.loads((PACKAGE / 'previous-completed-campaign.json').read_bytes())['report']
    cohorts = previous_cohorts(previous)
    assert len(cohorts) == 1 and len(cohorts[0]['report']['rows']) == 10
    assert counts_from_rows(cohorts[0]['report']['rows']) == dict.fromkeys(
        ['silent_drop', 'blank_replace', 'stale_replace', 'buttons_only'], 2)
    for name in source_names:
        (root / name).write_bytes((HERE / name).read_bytes())
    save(root / 'result.json', {
        'scope': 'local syntax, actual old report read and incomplete-parent refusal only',
        'all_draft_sources_compile': True, 'remote_parent_binding_code_compiles': True,
        'incomplete_running_parent_refused_before_any_claim_or_remote_call': rejected,
        'actual_prior_report_binding': previous,
        'actual_prior_cohort_rows_verified': 10,
        'actual_prior_cost_interval_read_once': True,
        'new_reserve_package_created': False, 'new_GPU_lease': False,
        'model_GUI_launch': False, 'new_model_GUI_calls': 0,
        'current_runtime_and_auditors_unchanged': True,
        'requires_actual_complete_report_release_and_frozen_next_task_before_prepare': True,
        'future_prepared_package_requires_fresh_metadata_qualification_and_owned_GPU_admission': True,
    })
    save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p)
                            for p in root.rglob('*') if p.is_file()})
    verify(root)
    print(json.dumps({'root': str(root), 'seal_sha256': sha(root / 'seal.json'),
                      'incomplete_parent_refused': True, 'actual_prior_rows_read': 10,
                      'reserve_package_created': False, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
