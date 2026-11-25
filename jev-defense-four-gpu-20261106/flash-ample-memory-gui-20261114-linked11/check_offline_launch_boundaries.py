"""New CPU-only negative controls for ownership, completion and the hard call cap."""
import copy
import hashlib
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

from control import HERE, save, sha


def main():
    prep = HERE / 'evidence-discipline-offline-preparation-01'
    sys.path.insert(0, str(prep / 'package'))
    import offline_guard as g
    g.verify_package()
    require = g.require
    cases = []

    def check(name, function, rejected=False):
        try:
            function()
        except RuntimeError:
            require(rejected, 'Unexpected boundary failure: ' + name)
        else:
            require(not rejected, 'Unsafe boundary accepted: ' + name)
        cases.append({'case': name, 'expected_rejection': rejected, 'passed': True})

    uuids = {i: 'frozen-uuid-' + str(i) for i in range(8)}
    empty = {'gpu': {i: {'uuid': uuids[i], 'free_mib': 23500} for i in range(8)}, 'compute': []}
    loaded = copy.deepcopy(empty)
    loaded['compute'] = [{'uuid': uuids[i], 'pid': 321} for i in range(7)]
    check('exclusive_all8_before_load', lambda: g.validate_gpu(empty, uuids))
    check('main_exactly0_through6_and_idle7_after_load', lambda: g.validate_gpu(loaded, uuids, 321))
    for label, changes, after in [
        ('foreign_on_main_GPU', lambda x: x['compute'].append({'uuid': uuids[2], 'pid': 777}), 321),
        ('foreign_on_reserved_idle_GPU7', lambda x: x['compute'].append({'uuid': uuids[7], 'pid': 777}), 321),
        ('old_own_PID_still_using_GPU_before_load', lambda x: x['compute'].append({'uuid': uuids[0], 'pid': 321}), None),
        ('memory_below23000_before_load', lambda x: x['gpu'][3].update(free_mib=22999), None),
        ('UUID_changed', lambda x: x['gpu'][4].update(uuid='other'), None),
        ('missing_physical_device', lambda x: x['gpu'].pop(7), None),
        ('loaded_process_missing_GPU', lambda x: x['compute'].pop(), 321)]:
        value = copy.deepcopy(loaded if after is not None else empty)
        changes(value)
        check(label, lambda value=value, after=after: g.validate_gpu(value, uuids, after), True)
    expected = ['run-' + str(i) for i in range(29)]
    status = {'phase': 'completed', 'done': 29, 'expected': 29, 'active': None}
    terminal = {'status': 'completed', 'done': 29, 'expected': 29}
    exited = {'exit_code': 0, 'failure': None, 'children': [{'exit_code': 0}, {'exit_code': 0}]}
    admission = {'GUI_child_exit': 0, 'actual_GUI_processes_exited': True,
                 'previous_manifest_sha256': sha(prep / 'package/native/manifest.json'),
                 'terminals': [{'run_id': v, 'seal_verified': True, 'chain_verified': True,
                                'infrastructure_failure': False, 'cleanup_error': None} for v in expected]}
    check('complete29_and_verified_normal_exits', lambda: g.validate_completion(status, terminal, exited, admission, expected))
    for name, slot, change in [
        ('running_flag_even_if_done29', 0, lambda x: x.update(phase='generating')),
        ('partial9_of29', 0, lambda x: x.update(done=9)),
        ('active_run_not_closed', 0, lambda x: x.update(active='run-28')),
        ('main_terminal_only28', 1, lambda x: x.update(done=28)),
        ('model_group_failed_exit', 2, lambda x: x.update(exit_code=1)),
        ('child_abnormal_exit', 2, lambda x: x['children'][1].update(exit_code=1)),
        ('GUI_process_not_exited', 3, lambda x: x.update(actual_GUI_processes_exited=False)),
        ('missing29th_terminal', 3, lambda x: x['terminals'].pop()),
        ('duplicated_run_id', 3, lambda x: x['terminals'][28].update(run_id='run-0')),
        ('terminal_seal_unverified', 3, lambda x: x['terminals'][0].update(seal_verified=False)),
        ('terminal_event_chain_unverified', 3, lambda x: x['terminals'][0].update(chain_verified=False)),
        ('terminal_infrastructure_failure', 3, lambda x: x['terminals'][0].update(infrastructure_failure=True)),
        ('terminal_cleanup_failure', 3, lambda x: x['terminals'][0].update(cleanup_error='error'))]:
        values = copy.deepcopy([status, terminal, exited, admission])
        change(values[slot])
        check(name, lambda values=values: g.validate_completion(*values, expected), True)
    check('first_approved_case', lambda: g.allow_next_call(0, 1, []))
    check('last_approved_case', lambda: g.allow_next_call(9, 48, g.CASES[:9]))
    check('eleventh_call_denied', lambda: g.allow_next_call(10, 48, g.CASES), True)
    check('repeated_case_denied', lambda: g.allow_next_call(0, 1, [1]), True)
    check('unapproved_or_reordered_case_denied', lambda: g.allow_next_call(0, 43, []), True)
    cpu = json.loads((HERE / 'evidence-discipline-native-CPU-1794656543839272000/case-48.json').read_bytes())['result']
    exact = {key: {k: value[k] for k in ['shape', 'dtype', 'bytes', 'sha256']} for key, value in cpu['proposed_prepared'].items()}
    check('frozen_full_native_ID_pixel_grid_records', lambda: g.validate_tensor_records(exact, cpu['proposed_prepared']))
    for name in ['input_ids', 'pixel_values', 'image_grid_thw']:
        changed = copy.deepcopy(exact)
        changed[name]['sha256'] = 'f' * 64
        check('changed_' + name + '_denied', lambda changed=changed: g.validate_tensor_records(changed, cpu['proposed_prepared']), True)
    missing = copy.deepcopy(exact)
    missing.pop('pixel_values')
    check('missing_original_pixels_denied', lambda: g.validate_tensor_records(missing, cpu['proposed_prepared']), True)
    require('torch' not in sys.modules, 'CPU guard tests unexpectedly imported model runtime')
    dest = prep / ('CPU-boundaries-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'result.json', {'tests_passed': len(cases), 'cases': cases,
         'offline_manifest_sha256': sha(prep / 'package/offline-manifest.json'),
         'weights_GPU_model_GUI_calls': 0, 'new_ownership_and_once_only_boundaries_only': True,
         'not_generation_capacity_semantic_or_efficacy_proof': True, 'time': time.time()})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'CPU_boundary_receipt': str(dest), 'passed': len(cases), 'model_GPU_GUI_calls': 0}))


if __name__ == '__main__':
    main()
