"""Prove the stopped NF4 parent is closed and the exact remaining queue was never started."""

import json
from pathlib import Path

from resource_guard import sha


def read(path):
    return json.loads(path.read_bytes())


def checked(root, seal, *files):
    for name in files:
        assert sha(root/name) == seal[name], (root, name)


def verify_resource_parent(package, host, full, gone, events, check_gui):
    link = read(package/'resource-stop-resume-link.json')
    old = Path(link['parent_package'][host])
    m = read(old/'manifest.json')
    assert sha(old/'manifest.json') == link['parent_manifest_sha256']
    assert sha(old/'plan.json') == m['plan_sha256'] == link['parent_plan_sha256']
    assert read(old/'plan.json')['queue'] == full[29:]
    assert len(full) == 100 and link['cutoff_in_original_100'] == 61
    started = list(full[29:61])
    ids = [r['run_id'] for r in started]
    assert ids[-1] == link['failed_run_id']
    assert sorted(ids) == sorted(link['terminal_sha256_by_run'])
    assert list(link['model_end_sha256_by_run']) == ids[:-1]
    unused = [r['run_id'] for r in full[61:]]
    assert read(package/'plan.json')['queue'] == full[61:]
    assert unused == link['never_started_run_ids'] and set(unused).isdisjoint(ids)

    if host == '3090':
        out = Path(m['output3090'])
        model, flash = out/'primary', old/'flash/service'
        assert all(gone(read(q)) for q in (out/'launcher-process.json', model/'process.json', flash/'process.json'))
        post_path = out/'postexit-seal.json'
        post = read(post_path)
        assert sha(post_path) == link['model_postexit_sha256']
        checked(out, post, 'exit.json', 'released.json', 'lease.json', 'primary/terminal.json',
                'primary/journal/events.jsonl', 'primary/status.json')
        checked(old, post, 'flash/service/journal/events.jsonl')
        assert read(out/'exit.json')['exit_code'] == 1
        assert read(out/'released.json')['fresh_lease_locks_closed'] == 9
        state = read(model/'terminal.json')
        assert state['status'] == 'stopped' and state['done'] == 31 and state['expected'] == 71
        assert state['attempted_actor_calls'] == state['complete_actor_replies'] + 1
        records, head = events(model/'journal/events.jsonl')
        assert head == link['model_journal_head']
        assert events(flash/'journal/events.jsonl')[1] == link['Flash_journal_head']
        assert [x['data']['run_id'] for x in records if x['kind'] == 'run_begin'] == ids
        ends = [x['data'] for x in records if x['kind'] == 'run_end']
        assert [x['run_id'] for x in ends] == ids[:-1]
        assert all(not x['infrastructure_failure'] and not x['manual_stop'] for x in ends)
        assert {x['run_id']:x['terminal_sha256'] for x in ends} == link['model_end_sha256_by_run']
        assert {k:link['terminal_sha256_by_run'][k] for k in ids[:-1]} == link['model_end_sha256_by_run']
        failures = [x['data'] for x in records if x['kind'] == 'technical_failure']
        assert len(failures) == 1 and failures[0]['no_automatic_retry'] and failures[0]['not_semantic_NO']
        q = Path(link['failed_request_directory'])
        assert q == model/'requests'/f"{state['attempted_actor_calls']:05d}"
        req_seal = read(q/'seal.json')
        checked(out, post, (q/'seal.json').relative_to(out).as_posix(), link['resource_conflict_name'])
        assert sha(q/'seal.json') == link['failed_request_seal_sha256']
        assert sha(out/link['resource_conflict_name']) == link['resource_conflict_sha256']
        checked(q, req_seal, 'failure.json', 'wire-request.bin', 'actual-generation.json', 'first-forward.json')
        failed = read(q/'wire-request.bin')
        assert failed['run_id'] == ids[-1] and failed['request_id'] == link['failed_request_id']
        assert read(q/'actual-generation.json')['natural_EOS'] and not (q/'response.json').exists()
        assert read(q/'failure.json') == failures[0]
        assert 'Unverified compute on reserved GPU 3' in failures[0]['error']
        gpu_lease = read(out/'lease.json')['gpu']
        assert [r['index'] for r in gpu_lease] == [0,1,2,3]
        assert [r['uuid'] for r in gpu_lease] == link['original_GPU_UUIDs_in_order']
    else:
        assert host == '4090'
        root = old/'control'
        assert sha(root/'postexit-seal.json') == link['GUI_postexit_sha256']
        post = read(root/'postexit-seal.json')
        checked(root, post, 'process.json', 'runner-process.json', 'runner.log', 'exit.json', 'batch-terminal-seal.json')
        checked(old/'batch', read(root/'batch-terminal-seal.json'), 'status.json')
        assert read(old/'batch/status.json')['expected'] == 71
        previous = check_gui(old, started, 1)
        assert previous['terminals_scored'] == link['model_end_sha256_by_run']
        assert previous['technical_terminal_sha256'] == link['terminal_sha256_by_run'][ids[-1]]
        assert previous['controller_heads'][ids[-1]] == link['failed_controller_chain_head']
        assert previous['batch_seal_sha256'] == post['batch-terminal-seal.json']
    return {'started_before_stop':len(ids),'verified_previous_score_receipts':len(ids)-1,
            'verified_previous_terminal_sha256_by_run':link['terminal_sha256_by_run'],
            'failed_arm_never_to_be_reexecuted':ids[-1], 'untouched_slots':len(unused),
            'first_untouched_slot':unused[0]}
