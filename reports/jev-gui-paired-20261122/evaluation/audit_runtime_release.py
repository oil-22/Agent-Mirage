"""Verify an NF4 stage's actual exits and its sealed original evidence."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time

from collect import HERE, control, latest_nf4_stage, manifest_for, measurement_version, read, save, sha, stages
from link import verify


REMOTE = r'''
import os
import sys
p = Path(ROOT)
sys.path[:0] = [str(p/'flash'), str(p)]
from continuation_guard import gone
from resource_guard import gpu_snapshot
assert os.getuid() == (1033 if HOST == '3090' else 1015)
assert sha(p/'manifest.json') == MANIFEST and sha(p/'plan.json') == PLAN

def inventory(root):
    return {q.relative_to(root).as_posix() for q in root.rglob('*') if q.is_file()}

def locks_on(paths):
    stats = [q.stat() for q in paths]
    keys = {f'{os.major(s.st_dev):02x}:{os.minor(s.st_dev):02x}:{s.st_ino}' for s in stats}
    lines = Path('/proc/locks').read_text().splitlines()
    return [line for line in lines if line.split()[5] in keys and line.split()[1] != '->']

def checked_processes(items):
    result = {role: read(path) for role, path in items.items()}
    assert all(v['uid'] == os.getuid() and gone(v) for v in result.values())
    return result

if HOST == '4090':
    ctl, batch = p/'control', p/'batch'
    post = read(ctl/'postexit-seal.json')
    for key in ('exit.json', 'runner.log', 'process.json', 'runner-process.json', 'batch-terminal-seal.json'):
        sealed(ctl, post, key)
    roles = checked_processes({'outer': ctl/'process.json', 'runner': ctl/'runner-process.json'})
    assert read(ctl/'exit.json')['no_automatic_retry']
    exit_code = read(ctl/'exit.json')['child_exit']
    assert exit_code == 0
    batch_index = read(ctl/'batch-terminal-seal.json')
    status = read(sealed(batch, batch_index, 'status.json'))
    assert status['processed'] == len(TARGET) and status['expected'] == FROZEN_QUEUE_COUNT
    assert status['phase'] == PHASE
    assert set(batch_index) == inventory(batch)
    actual_runs = {q.name for q in (batch/'runs').iterdir() if q.is_dir()}
    assert actual_runs == set(TARGET)
    for rid, digest in TARGET.items():
        attempt, = (batch/'runs'/rid).glob('attempt-*')
        idx = sealed(batch, batch_index, (attempt/'seal.json').relative_to(batch).as_posix())
        term = sealed(batch, batch_index, (attempt/'terminal.json').relative_to(batch).as_posix())
        assert read(idx)['terminal.json'] == sha(term) == digest
    site = Path('/data/researcher/jev-defense-four-gpu-20261106/.full-gui-site29980.lock')
    live_locks = locks_on([site])
    assert not {int(l.split()[4]) for l in live_locks} & {q['pid'] for q in roles.values()}
    result = {'status': status, 'runner_exit_code': exit_code,
              'verified_GUI_terminal_SHAs': len(TARGET), 'postexit_sha256': sha(ctl/'postexit-seal.json'),
              'batch_index_entries': len(batch_index), 'site_locks_at_sample': live_locks}
else:
    out = Path(OUT)
    aux = p/'flash/service'
    post = read(out/'postexit-seal.json')
    roles = checked_processes({'launcher': out/'launcher-process.json', 'primary': out/'primary/process.json',
                               'Flash': aux/'process.json'})
    control_files = {'launcher-process.json', 'exit.json', 'released.json', 'lease.json', 'primary.log',
                     'Flash-service.log', 'primary/process.json', 'primary/terminal.json',
                     'primary/journal/events.jsonl', 'flash/service/process.json',
                     'flash/service/terminal.json', 'flash/service/journal/events.jsonl'}
    for name in sorted(control_files | {n for n in post if n.endswith('/seal.json')}):
        sealed(p if name.startswith('flash/service/') else out, post, name)
    assert set(post) == (inventory(out) - {'postexit-seal.json'}) | {
        n for n in inventory(p) if n.startswith('flash/service/') and Path(n).name != 'token'}
    primary, primary_head = journal(out/'primary/journal/events.jsonl')
    flash, flash_head = journal(aux/'journal/events.jsonl')
    assert OLD_PRIMARY in {x['sha256'] for x in primary} and OLD_FLASH in {x['sha256'] for x in flash}
    assert [b['run_id'] for b in data(primary, 'run_begin')] == list(TARGET)
    ends = data(primary, 'run_end')
    assert unique(ends, lambda x: x['run_id'], lambda x: x['terminal_sha256']) == MODEL_ENDS
    assert read(aux/'terminal.json')['journal_head'] == flash_head
    end = read(out/'primary/terminal.json')
    assert end['expected'] == FROZEN_QUEUE_COUNT and end['done'] == len(ends)
    launcher_end = read(out/'exit.json')
    assert launcher_end['exit_code'] == (0 if PHASE == 'completed' else 1)
    if PHASE == 'completed':
        assert end['status'] == 'completed' and len(ends) == len(TARGET)
    assert {v['pid'] for k, v in roles.items() if k != 'launcher'} == {q['pid'] for q in launcher_end['children']}
    lease, released = read(out/'lease.json'), read(out/'released.json')
    assert lease['manifest_sha256'] == MANIFEST and lease['holder'] == roles['launcher']
    assert released['fresh_lease_locks_closed'] == len(lease['lock_records']) == 9
    assert released['no_broker_left_running'] and launcher_end['reserved_GPUs_for_run_cost'] == len(lease['gpu']) == 4
    live_locks = locks_on([Path(r['path']) for r in lease['lock_records']])
    pids = {v['pid'] for v in roles.values()}
    assert not {int(l.split()[4]) for l in live_locks} & pids
    g = gpu_snapshot()
    uuids = {x['uuid'] for x in lease['gpu']}
    current_cards = [x for x in g['compute'] if x['uuid'] in uuids]
    assert not any(q['pid'] in pids for q in current_cards)
    elapsed = released['time'] - lease['created']
    assert elapsed > 0
    result = {'primary_terminal': end, 'launcher_exit_code': launcher_end['exit_code'],
              'model_end_bindings': len(ends), 'primary_chain_head': primary_head, 'Flash_chain_head': flash_head,
              'postexit_sha256': sha(out/'postexit-seal.json'), 'postexit_inventory_entries': len(post),
              'postexit_request_seals_byte_checked': sum(n.endswith('/seal.json') for n in post),
              'postexit_note': 'Raw tensors remain indexed by the original postexit and request seals; no redundant full tensor rehash.',
              'reserve_scope': 'Recorded ' + STAGE_ID + ' lease creation to closure of inherited GPU locks',
              'GPU_count': len(uuids), 'reserved_seconds': elapsed,
              'reserved_GPU_hours': len(uuids) * elapsed / 3600, 'GPU_compute_at_sample': current_cards,
              'lease_file_locks_at_sample': live_locks}
print(json.dumps({'expected_manifest': MANIFEST, 'actual_UID': os.getuid(), 'exited_processes': roles,
                  'new_model_GUI_scorer_calls': 0, **result}))
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('ledger', type=Path)
    p.add_argument('--stage', choices=[s for s in stages() if measurement_version(s)=='NF4'],
                   default=latest_nf4_stage())
    p.add_argument('--closed-technical-prefix', metavar='ABSOLUTE_SLOT_COUNT', type=int,
                   help='Audit an exited, sealed technical-stop prefix and prove its remaining slots never started.')
    args = p.parse_args()
    verify(args.ledger)
    ledger = read(args.ledger/'private-linked.json')
    ptr, manifest, plan = manifest_for(args.stage)
    _, start, end = stages()[args.stage]
    rows = ledger['rows'][start:end]
    assert all(r['stage_id'] == args.stage for r in rows)
    assert [r['slot'] for r in rows] == plan[:end-start]
    cutoff = args.closed_technical_prefix
    if cutoff is not None:
        assert start < cutoff <= end and cutoff < start+len(plan)
        remaining = ledger['rows'][cutoff:start+len(plan)]
        assert all(row['status'] == 'not_started_at_collection' and row['evidence'] is None
                   for row in remaining)
        unstarted = [row['slot']['run_id'] for row in remaining]
        rows = rows[:cutoff-start]
        assert rows[-1]['evidence']['terminal']['infrastructure_failure']
    else:
        unstarted = []
    if not all(row['evidence'] and row['status'] == 'verified_terminal' for row in rows):
        print(json.dumps({'ready': False, 'reason': 'NF4 stage still has unsealed slots'}))
        return 1
    target = {r['slot']['run_id']: r['evidence']['terminal_sha256'] for r in rows}
    ends = {r['slot']['run_id']: r['evidence']['terminal_sha256'] for r in rows if r['evidence']['model_run_end_bound']}
    t = rows[-1]['evidence']['terminal']
    phase = ('technical_failure' if t['infrastructure_failure'] else
             'manually_stopped' if t['outcome'] == 'manually_stopped' else 'completed')
    source = ledger['collections'][args.stage]
    collection = Path(source['path'])
    verify(collection)
    assert sha(collection/'seal.json') == source['seal_sha256']
    record = read(collection/(args.stage + '.json'))['hosts']['3090']
    lib = (HERE/'extract_on_host.py').read_text(encoding='utf-8')
    dst = HERE/'runtime-release-audits'/str(time.time_ns())
    dst.mkdir(parents=True, exist_ok=False)
    control.ROOT = dst

    def probe(host):
        data = {'HOST': host, 'ROOT': manifest['package'+host], 'OUT': manifest['output3090'],
                'MANIFEST': ptr['manifest_sha256'], 'PLAN': ptr['plan_sha256'], 'TARGET': target, 'MODEL_ENDS': ends,
                'STAGE_ID': args.stage, 'FROZEN_QUEUE_COUNT': len(plan),
                'PHASE': phase, 'OLD_PRIMARY': record['primary_chain_head'], 'OLD_FLASH': record['flash_chain_head']}
        text = "__name__='evidence_library'\n" + ''.join(f'{k}={v!r}\n' for k,v in data.items()) + lib + REMOTE
        compile(text, host, 'exec')
        receipt = control.remote(host, text, 'verify-actual-runtime-release', timeout=90)
        operation = Path(receipt['operation'])
        verify(operation)
        return {'operation': str(operation), 'operation_seal': sha(operation/'seal.json'), 'result': receipt['result']}

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = dict(zip(('3090', '4090'), pool.map(probe, ('3090', '4090'))))
    save(dst/'index.json', {'ledger_seal_sha256': sha(args.ledger/'seal.json'), 'stage': args.stage,
                           'verified_suffix_slots': len(target), 'cutoff_in_original_100': start+len(target),
                           'phase': phase, 'verified_never_started_in_stage': unstarted, 'hosts': results})
    save(dst/'seal.json', {'index.json': sha(dst/'index.json')})
    print(json.dumps({'audit': str(dst), 'seal_sha256': sha(dst/'seal.json'),
                      'GPU_hours': results['3090']['result']['reserved_GPU_hours']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
