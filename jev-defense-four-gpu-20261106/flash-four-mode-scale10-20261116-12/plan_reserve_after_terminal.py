"""Freeze the next unused reserve task only after a complete audited campaign.

This is local planning. It neither starts models nor edits any runtime package.
The original reserve ordering and every unsuccessful terminal remain intact.
"""
import json
import re
import time
from pathlib import Path

from control import HERE, PACKAGE, save, sha
from join_reviewed_results import MODES, pointer, verify


def main():
    report_root, report_binding = pointer('completed-report-current.json')
    report = json.loads((report_root / 'report.json').read_bytes())
    reviewed_root, reviewed_binding = pointer('reviewed-campaign-current.json')
    reviewed = json.loads((reviewed_root / 'result.json').read_bytes())
    assert report['current_review_binding'] == reviewed_binding
    assert reviewed['manifest_sha256'] == sha(PACKAGE / 'manifest.json')
    assert reviewed['group']['all_model_GUI_launcher_processes_verified_exited']
    assert reviewed['group']['full_wire_input_tensors_history_EOS_probability_seal_chain_and_actions_verified']
    release = reviewed['release_binding']
    release_root = verify(release['root'], release['seal_sha256'])
    assert json.loads((release_root / 'result.json').read_bytes())['all_17_kernel_locks_absent']
    site_root, site_binding = pointer('site-lock-postexit-current.json')
    site = json.loads((site_root / 'result.json').read_bytes())
    assert site['original_holder_absent']
    assert report['site_lock_release_binding'] == site_binding

    rows = report['cumulative_rows']
    assert len(rows) == len({row['run_id'] for row in rows})
    counts = {
        mode: sum(row['condition'] == mode and row.get('user_normal_frame_delivery_passed', False)
                  for row in rows)
        for mode in MODES
    }
    assert counts == report['cumulative_counts']
    deficits = {mode: max(0, 10 - counts[mode]) for mode in MODES}
    assert any(deficits.values()), 'Every mode has already reached ten verified recoveries'

    selection_binding = json.loads((HERE / 'task-selection-current.json').read_bytes())
    selection_root = verify(selection_binding['root'], selection_binding['seal_sha256'])
    selection = json.loads((selection_root / 'selection.json').read_bytes())
    used = set()
    for row in rows:
        match = re.search(r'(?:^|-)T([0-9]+)(?:-|$)', row['run_id'])
        assert match, row['run_id']
        used.add(int(match.group(1)))
    remaining = [task for task in selection['reserve_task_ids'] if task not in used]
    assert remaining, 'The frozen reserve catalog is exhausted; preserve results and report the deficit'
    task = remaining[0]
    conditions = [mode for mode in selection['conditions']
                  if mode == 'clean_control' or deficits.get(mode, 0) > 0]
    assert conditions[-1] == 'clean_control' and len(conditions) >= 2
    bindings = json.loads((selection_root / 'structural-bindings.json').read_bytes())['result']['rows']
    task_binding = next(row for row in bindings if row['task_id'] == task)
    assert task_binding['eligible'] and task_binding['private_scorer_answers_or_reference_urls_exported'] is False

    root = HERE / ('reserve-plan-' + str(time.time_ns()))
    root.mkdir()
    value = {
        'time': time.time(), 'completed_campaign_report': report_binding,
        'reviewed_campaign_binding': reviewed_binding, 'selection_binding': selection_binding,
        'verified_cumulative_successes': counts, 'deficits': deficits,
        'next_task_id': task, 'conditions': conditions, 'task_binding': task_binding,
        'all_used_task_ids': sorted(used), 'remaining_frozen_reserve_order': remaining,
        'all_cumulative_rows_preserved': rows,
        'same_protocol_unchanged_runtime_required': True,
        'new_independent_lease_and_once_only_package_required': True,
        'no_terminal_rerun': True, 'private_answers_exported': False,
        'model_GUI_launch': False, 'new_model_GUI_calls': 0,
    }
    save(root / 'plan.json', value)
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    verify(root)
    print(json.dumps({'root': str(root), 'seal_sha256': sha(root / 'seal.json'),
                      'next_task_id': task, 'conditions': conditions, 'deficits': deficits,
                      'model_GUI_launch': False}))


if __name__ == '__main__':
    main()
