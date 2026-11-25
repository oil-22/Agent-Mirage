"""Foreground follow-through on this new finite group; never launches a model."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from remote_util import HERE, save


def main():
    root = HERE / 'current-turn-watcher'; root.mkdir(exist_ok=False)
    save(root / 'process.json', {'pid': os.getpid(), 'argv': sys.argv, 'time': time.time(), 'model_or_GUI_launch': False})
    commands = root / 'commands'; commands.mkdir()
    def run(script, *args):
        op = commands / (str(time.time_ns()) + '-' + Path(script).stem); op.mkdir()
        argv = [sys.executable,'-B','-u','-X','utf8',str(HERE / script),*args]
        save(op / 'command.json', {'argv': argv})
        with (op / 'stdout.bin').open('xb') as out, (op / 'stderr.bin').open('xb') as err:
            result = subprocess.run(argv, stdout=out, stderr=err)
        save(op / 'result.json', {'exit_code': result.returncode, 'time': time.time()})
        if result.returncode:
            print(json.dumps({'read_only_watcher_failure': str(op), 'no_model_or_GUI_retry': True}), flush=True)
            raise RuntimeError('Preserved read-only failure; linked audit repair may be needed')
        return op
    while not (HERE / 'STOP-WATCH').exists():
        run('collect_progress.py')
        pp = json.loads((HERE / 'live-progress-current.json').read_bytes())
        progress = json.loads((Path(pp['root']) / 'result.json').read_bytes())['result']; status = progress['status'] or {}
        print(json.dumps({'time': time.time(), 'status': status, 'actual_main_replies': sum(v['main_replies'] for v in progress['rows']), 'precheck_NO': sum(v['precheck_NO'] for v in progress['rows']), 'source_NO': sum(v['receipt_NO'] for v in progress['rows']), 'Flash_NO': sum(v['Flash_NO'] for v in progress['rows']), 'not_final_success_without_full_audit_and_images': True}), flush=True)
        if status.get('phase') in ['technical_failure','manually_stopped']:
            raise RuntimeError('New experiment stopped; inspect preserved evidence, no automatic trial retry')
        for row in progress['rows']:
            if not row['complete']: continue
            existing = list(HERE.glob('trajectory-audit-' + row['run_id'] + '-*'))
            if any((p / 'seal.json').exists() for p in existing): continue
            if existing: raise RuntimeError('An unfinished audit needs a new linked continuation')
            print(json.dumps({'new_finished_trajectory': row['run_id'], 'full_raw_audit_starting': True}), flush=True)
            run('audit_finished_trajectory.py', row['run_id'])
            exported = run('export_examples.py')
            print(json.dumps({'trajectory_audit_complete': row['run_id'], 'image_export_output': str(exported / 'stdout.bin'), 'independent_image_review_pending': True}), flush=True)
        if status.get('phase') == 'completed':
            op = run('control.py','inspect')
            snapshots = [json.loads(v) for v in (op / 'stdout.bin').read_text('utf8').splitlines() if v.strip()]
            if not any(v['same'] for s in snapshots for v in s['actual']):
                run('audit_completed_group_bound_reuse.py')
                run('audit_resource_interval.py')
                run('audit_released_resources.py')
                print(json.dumps({'whole_group_raw_audit_and_release_complete': True, 'independent_image_join_and_report_remaining': True}), flush=True)
                return
        time.sleep(45)


if __name__ == '__main__':
    main()
