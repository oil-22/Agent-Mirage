"""Measure normal-image gate wait on exact paired paths, with tasks as units."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
from statistics import median
import time

from audit_recovery_alignment import compare_decision, request_binding
from collect import HERE, read, save, sha
from link import verify
from summarize import quantiles_ns


def audit(ledger, metrics):
    tasks = defaultdict(dict)
    for row, metric in zip(ledger['rows'], metrics, strict=True):
        assert all(row['slot'][k] == metric[k] for k in ('run_id', 'task_id', 'arm', 'condition'))
        assert row['version'] == metric['version']
        if metric['condition'] == 'clean_control':
            assert metric['arm'] not in tasks[metric['task_id']]
            tasks[metric['task_id']][metric['arm']] = row, metric

    pairs, task_medians = [], defaultdict(list)
    for task, arms in sorted(tasks.items()):
        assert set(arms) == {'on', 'off'}
        rows, stats = zip(*(arms[a] for a in ('on', 'off')), strict=True)
        version = rows[0]['version']
        assert rows[1]['version'] == version
        row = {'task': task, 'version': version, 'terminal_SHA256': {m['arm']: m['terminal_sha256'] for m in stats},
               'on_and_off_scored': all(m['official_scored'] for m in stats), 'aligned_submissions': [],
               'path_status': 'not_yet_both_sealed'}
        pairs.append(row)
        if not all(r['evidence'] for r in rows):
            continue

        histories = [r['evidence']['steps'] for r in rows]
        rows_by_decision = [{s['decision']: s for s in m['steps']} for m in stats]
        assert all(not s['triggered'] and not s['altered_bytes'] for steps in histories for s in steps)
        count = 0
        difference = None
        for on, off in zip(*histories):
            reasons = compare_decision(on, off)
            if reasons:
                difference = {'decision': on['step'], 'fields': reasons}
                break
            count += 1
            step = on['step']
            a, b = (m[step] for m in rows_by_decision)
            if not (a['initial_signed_normal_independently_reviewed'] and
                    b['initial_signed_normal_independently_reviewed'] and
                    a['initial_raw_sha256'] == b['initial_raw_sha256']):
                continue
            t_on, t_off = (s['first_frame_to_actor_ns'] for s in (on, off))
            assert t_on is not None and t_off is not None and min(t_on, t_off) >= 0
            row['aligned_submissions'].append({'decision': step, 'initial_normal_PNG_sha256': a['initial_raw_sha256'],
                'on_first_frame_to_submit_ns': t_on, 'off_first_frame_to_submit_ns': t_off,
                'on_minus_off_ns': t_on - t_off,
                'on_actual_forward': request_binding(on), 'off_actual_forward': request_binding(off)})
        entire = count > 0 and count == len(histories[0]) == len(histories[1])
        if difference is None and len(histories[0]) != len(histories[1]):
            difference = {'decision': count + 1, 'fields': ['different_observed_path_lengths']}
        ns = [s['on_minus_off_ns'] for s in row['aligned_submissions']]
        row.update({'path_status': 'exact_entire_observed_path' if entire else 'sealed_no_entire_exact_match',
                    'exact_prefix_decisions': count, 'first_path_difference': difference,
                    'wait_on_minus_off_seconds': quantiles_ns(ns),
                    'elapsed_on_minus_off_seconds': (stats[0]['elapsed_ns'] - stats[1]['elapsed_ns']) / 1e9
                    if row['on_and_off_scored'] else None})
        if ns:
            task_medians[version].append(median(ns) / 1e9)

    return {'normal_pairs': pairs, 'within_task_wait_by_version': [
        {'version': v, 'tasks_with_exact_normal_prefix': len(x), 'median_of_task_medians_seconds': median(x),
         'range_of_task_medians_seconds': [min(x), max(x)]} for v, x in sorted(task_medians.items())],
        'scope': 'Initial genuine usable frame ready to actor submit, on minus off in the exact shared prefix. '
                 'The actual ordered messages, current image, EOS text, and native action acknowledgment must match. '
                 'This latency subset does not substitute for the complete clean-arm false-rejection denominators.',
        'new_model_GUI_scorer_calls': 0}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('ledger', type=Path)
    p.add_argument('report', type=Path)
    a = p.parse_args()
    for source in (a.ledger, a.report):
        verify(source)
    ledger_seal = sha(a.ledger / 'seal.json')
    assert ledger_seal == read(a.report / 'condition-by-version.json')['ledger_seal_sha256']
    data = audit(read(a.ledger / 'private-linked.json'), read(a.report / 'trajectory-metrics.json'))
    out = HERE / 'normal-alignment-audits' / str(time.time_ns())
    out.mkdir(parents=True, exist_ok=False)
    save(out / 'normal-alignment.json', {'ledger_seal_sha256': ledger_seal,
        'report_seal_sha256': sha(a.report / 'seal.json'), 'auditor_sha256': sha(Path(__file__)), **data})
    save(out / 'seal.json', {'normal-alignment.json': sha(out / 'normal-alignment.json')})
    print(json.dumps({'normal_alignment': str(out), 'seal_sha256': sha(out / 'seal.json'),
                      'by_version': data['within_task_wait_by_version']}))


if __name__ == '__main__':
    main()
