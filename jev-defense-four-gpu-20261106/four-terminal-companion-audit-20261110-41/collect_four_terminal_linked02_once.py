"""Linked read-only audit repair: bounded individual terminal-chain reads."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import time
import traceback

from collect_four_terminal_once import HERE, REMOTE_SOURCE, transport, remote, save, sha


def main():
    assert not (HERE / 'four-terminal-collected.json').exists()
    assert not (HERE / 'four-terminal-linked02-intent.json').exists()
    failure_pointer = json.loads((HERE / 'audit-timeout-preserved.json').read_bytes())
    preservation = Path(failure_pointer['root'])
    assert sha(preservation / 'seal.json') == failure_pointer['seal_sha256']
    actual = json.loads((preservation / 'posttimeout-actual-handles.json').read_bytes())
    assert actual['other_actual_stdin_python_handles'] == [], 'Inspect the same live reader before any new read'
    source_root = HERE / 'four-terminal-source-and-events-1794309362430107500'
    for name, expected in json.loads((source_root / 'pre-join-source-seal.json').read_bytes()).items():
        assert sha(source_root / name) == expected
    inventory = source_root / 'source-labels-before-downstream-join.json'
    rows = json.loads(inventory.read_bytes())['rows']
    assert len(rows) == 84
    grouped = {}
    for row in rows:
        target = {key: row[key] for key in ['source_attempt', 'source_candidate_seq',
                  'candidate_event_sha256', 'candidate_text', 'candidate_text_sha256']}
        grouped.setdefault(row['source_attempt'], []).append(target)
    assert len(grouped) == 6
    out = HERE / ('four-terminal-events-linked02-' + str(time.time_ns()))
    out.mkdir()
    save(HERE / 'four-terminal-linked02-intent.json', dict(time=time.time(), root=str(out),
        original_failed_operation=str(preservation), source_inventory_sha256=sha(inventory),
        independent_terminal_reads=6, max_concurrent_CPU_readers=2, model_GUI_calls=0))
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())

    def read_one(index, attempt, targets):
        code = 'ROWS=' + repr(targets) + '\n' + transport.COMMON + REMOTE_SOURCE
        compile(code, 'linked02-single-terminal-chain-readonly', 'exec')
        output, operation = remote('4090', code, 'companion-linked02-chain-' + str(index) + '-readonly', timeout=55)
        value = json.loads(output)
        assert len(value['chains']) == 1 and len(value['rows']) == len(targets)
        assert value['chains'][0]['attempt'] == attempt
        save(out / ('chain-' + str(index) + '.json'), dict(value, operation=str(operation)))
        return index, value

    completed = []
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(read_one, index, attempt, targets)
                       for index, (attempt, targets) in enumerate(grouped.items())]
            for future in as_completed(futures):
                index, value = future.result()
                completed.append((index, value))
                print(json.dumps(dict(chain=index, candidates=len(value['rows']),
                    committed_events=value['chains'][0]['snapshot']['count'],
                    original_environment_executions=value['chains'][0]['actual_environment_execution_events'])), flush=True)
        ordered = [value for _, value in sorted(completed)]
        aggregate = dict(time=time.time(), rows=[row for value in ordered for row in value['rows']],
            chains=[chain for value in ordered for chain in value['chains']],
            remote_read_only=True, new_model_GUI_capture_action_scorer_paid_calls=0,
            source_inventory=str(inventory), source_inventory_sha256=sha(inventory),
            previous_aggregate_timeout_preserved=str(preservation), actual_old_audit_handles_absent_before_new_reads=True,
            per_chain_bounded_reads_without_experimental_reexecution=True)
        assert len(aggregate['rows']) == 84 and len(aggregate['chains']) == 6
        save(out / 'actual-terminal-event-evidence.json', aggregate)
        save(out / 'completion.json', dict(status='completed_CPU_readonly_audit', time=time.time(),
            candidates=84, original_event_chains=6, new_experimental_calls=0))
    except BaseException:
        save(out / 'failure.json', dict(time=time.time(), traceback=traceback.format_exc(),
            completed_chain_indices=sorted(index for index, _ in completed),
            no_model_or_GUI_job_was_started=True, completed_audit_shards_not_automatically_repeated=True))
        raise
    finally:
        save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    pointer = dict(root=str(out), event_evidence_sha256=sha(out / 'actual-terminal-event-evidence.json'),
        source_inventory=str(inventory), source_inventory_sha256=sha(inventory),
        seal_sha256=sha(out / 'seal.json'), candidates=84, actual_attempts=6,
        actual_original_environment_executions=sum(c['actual_environment_execution_events'] for c in aggregate['chains']))
    save(HERE / 'four-terminal-collected.json', pointer)
    print(json.dumps(pointer), flush=True)


if __name__ == '__main__':
    main()
