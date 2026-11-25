"""Compare paired traces across two roots; preserve the old failed partial separately."""
import ast
import json
import time
from control import HERE, remote, save, sha
from capture_live_evidence import COMMON


def main():
    old = HERE.parent / 'flash-ample-memory-gui-20261114-linked11'
    original = old / 'audit_pair_trace_equivalence.py'
    constants = [n.value for n in ast.walk(ast.parse(original.read_text('utf8')))
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    source = next(v for v in constants if v.startswith("\nr=Path(ROOT);out={'time':time.time(),'new_model_GUI_calls':0,'runs':[]}"))
    before = "for attempt in sorted((r/'batch/runs').glob('*/attempt-*')):"
    after = "for attempt in sorted([p for root in ROOTS for p in (Path(root)/'batch/runs').glob('*/attempt-*')]):"
    assert source.count(before) == 1
    source = source.replace(before, after)
    roots = ['/data/researcher/jev-defense-four-gpu-20261106/' + old.name,
             '/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name]
    raw, op = remote('4090', 'ROOT=' + repr(roots[0]) + '\nROOTS=' + repr(roots) + '\n' + COMMON + source,
                     'aggregate-original-pair-trace-comparison-preserve-failed-partial', timeout=55)
    value = json.loads(raw)
    plan = json.loads((HERE / 'package/plan.json').read_bytes())
    by_run, preserved = {}, []
    for record in value['runs']:
        run = record['run']['run_id']
        previous = by_run.get(run)
        if previous is not None:
            # The only overlap is the technical T089 partial in the old root.
            assert old.name in previous['attempt'] and HERE.name in record['attempt']
            assert previous['sealed_terminal'] and previous['terminal_summary']['infrastructure_failure']
            assert run == 'flash14-T089-stale_replace-gate'
            preserved.append(previous)
        by_run[run] = record
    assert len(preserved) == 1
    fields = ['body_sha256', 'candidate_text_sha256', 'delivered_PNG_sha256',
              'actually_captured_PNG_sha256', 'native_environment_action', 'post_execution_PNG_sha256']
    pairs = []
    for task in plan['tasks']:
        if task['task_id'] == 0:
            continue
        for condition in ['clean', 'stale_replace']:
            key = 'flash14-T%03d-%s-' % (task['task_id'], condition)
            baseline, gate = by_run.get(key + 'baseline'), by_run.get(key + 'gate')
            a = baseline['closed_actor_prefix'] if baseline else []
            b = gate['closed_actor_prefix'] if gate else []
            compared = []
            for left, right in zip(a, b):
                assert left['step'] == right['step']
                compared.append({'step': left['step'], 'equal': {k: left[k] == right[k] for k in fields}})
            complete = bool(baseline and gate and baseline['sealed_terminal'] and gate['sealed_terminal']
                            and not baseline['terminal_summary']['infrastructure_failure']
                            and not gate['terminal_summary']['infrastructure_failure'])
            same_length = len(a) == len(b)
            first_difference = next((v for v in compared if not all(v['equal'].values())), None)
            pairs.append({'task_id': task['task_id'], 'condition': condition,
                 'baseline_closed': len(a), 'gate_closed': len(b), 'compared_decisions': len(compared),
                 'both_noninfrastructure_sealed_terminals': complete, 'same_closed_length': same_length,
                 'all_compared_fields_equal': all(all(v['equal'].values()) for v in compared) if compared else None,
                 'complete_trace_equal': bool(complete and same_length and compared and first_difference is None),
                 'first_difference': first_difference,
                 'baseline_terminal': baseline['terminal_summary'] if baseline else None,
                 'gate_terminal': gate['terminal_summary'] if gate else None,
                 'baseline_attempt': baseline['attempt'] if baseline else None,
                 'gate_attempt': gate['attempt'] if gate else None,
                 'comparisons': compared})
    dest = HERE / ('aggregate-pair-trace-equivalence-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(__import__('pathlib').Path(__file__).read_bytes())
    save(dest / 'source-traces.json', value)
    save(dest / 'comparison.json', {'time': time.time(), 'source_operation': str(op),
         'original_single_root_reader_sha256': sha(original), 'pairs': pairs,
         'preserved_technical_attempts_excluded_from_normal_pair_replacement': preserved,
         'failed_source_occurrences_and_costs_not_erased': True,
         'trace_equality_not_semantic_or_current_tensor_validation': True,
         'T000_unpaired_excluded': True, 'native_contract_failure_not_no_Mirage': True,
         'Mirage_reduction': None, 'new_model_GUI_calls': 0})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'comparison': str(dest),
         'completed_pairs': sum(v['both_noninfrastructure_sealed_terminals'] for v in pairs),
         'equal_complete_pairs': sum(v['complete_trace_equal'] for v in pairs),
         'preserved_technical_attempts': len(preserved),
         'T089_stale': next(v for v in pairs if v['task_id'] == 89 and v['condition'] == 'stale_replace'),
         'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
