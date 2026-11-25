"""Current-turn foreground follow-through only; no scheduler or model relaunch.

Polls the already-running new queue, audits new sealed finished trajectories once,
and performs the full group audit only after actual original identities exit.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from remote_util import HERE, save


def main():
    root = HERE / 'current-turn-watcher'
    root.mkdir(exist_ok=False)
    save(root / 'process.json', {'pid': os.getpid(), 'argv': sys.argv,
                                'time': time.time(), 'no_model_or_GUI_launch': True})
    commands = root / 'commands'
    commands.mkdir()

    def run(script, *arguments):
        operation = commands / (str(time.time_ns()) + '-' + Path(script).stem)
        operation.mkdir()
        argv = [sys.executable, '-B', '-u', '-X', 'utf8', str(HERE / script), *arguments]
        save(operation / 'command.json', {'argv': argv, 'time': time.time()})
        with (operation / 'stdout.bin').open('xb') as stdout, (operation / 'stderr.bin').open('xb') as stderr:
            child = subprocess.run(argv, stdout=stdout, stderr=stderr)
        save(operation / 'result.json', {'return_code': child.returncode, 'time': time.time()})
        if child.returncode:
            print(json.dumps({'watcher_failure': str(operation), 'no_automatic_model_or_GUI_retry': True}), flush=True)
            raise RuntimeError('Read-only collection/audit failed: ' + str(operation))
        return operation

    while not (HERE / 'STOP-WATCH').exists():
        run('collect_progress.py')
        pointer = json.loads((HERE / 'live-progress-current.json').read_bytes())
        progress = json.loads((Path(pointer['root']) / 'result.json').read_bytes())['result']
        status = progress['status'] or {}
        print(json.dumps({'time': time.time(), 'processed': status.get('processed', 0),
                          'expected': 8, 'active': status.get('run_id'), 'step': status.get('step'),
                          'actual_complete_main_replies': sum(v['main_replies'] for v in progress['rows']),
                          'precheck_NO': sum(v['precheck_NO'] for v in progress['rows']),
                          'Flash_NO': sum(v['Flash_NO'] for v in progress['rows']),
                          'progress_receipt': pointer['root']}), flush=True)
        if status.get('phase') in ['technical_failure', 'manually_stopped']:
            raise RuntimeError('New experiment terminal needs review; preserve and do not relaunch')
        for row in progress['rows']:
            if not row['complete']:
                continue
            prefix = 'trajectory-audit-' + row['run_id'] + '-*'
            existing = list(HERE.glob(prefix))
            if any((p / 'seal.json').exists() for p in existing):
                continue
            if existing:
                raise RuntimeError('Unfinished prior audit requires linked technical continuation')
            print(json.dumps({'new_finished_trajectory': row['run_id'], 'read_only_raw_audit_starting': True}), flush=True)
            run('audit_finished_trajectory.py', row['run_id'])
            operation = run('export_examples.py')
            exported = json.loads((operation / 'stdout.bin').read_text('utf8'))
            print(json.dumps({'actual_original_image_export': exported['root'],
                              'image_review_still_required': True}), flush=True)
            run('join_acceptance_checkpoint.py')
            acceptance = json.loads((HERE / 'acceptance-checkpoint-current.json').read_bytes())
            joined = json.loads((Path(acceptance['root']) / 'summary.json').read_bytes())
            print(json.dumps({'audited_successes': joined['successful_complete_trajectories_per_condition'],
                              'acceptance_receipt': acceptance['root'], 'whole_group_postexit_pending': True}), flush=True)
        if status.get('phase') == 'completed':
            inspection = run('control.py', 'inspect')
            snapshots = [json.loads(line) for line in (inspection / 'stdout.bin').read_text('utf8').splitlines() if line.strip()]
            assert len(snapshots) == 2
            still_alive = [v for s in snapshots for v in s['actual'] if v['same']]
            if not still_alive:
                print(json.dumps({'all_original_model_GUI_launcher_identities_exited': True,
                                  'whole_group_raw_audit_starting': True}), flush=True)
                run('audit_completed_group.py')
                print(json.dumps({'whole_group_raw_audit_complete': True,
                                  'independent_original_image_review_and_final_report_remaining': True}), flush=True)
                return
        time.sleep(45)
    print(json.dumps({'watcher_stopped_only': True, 'model_and_GUI_not_stopped_by_watcher': True}), flush=True)


if __name__ == '__main__':
    main()
