"""Preserve a read-only exporter race and prepare a linked audit continuation."""
import json
import shutil
import time
from pathlib import Path
from control import HERE, save, sha
from join_reviewed_results import verify


def main():
    command = HERE / 'current-turn-watcher/commands/1794826205538155200-export_examples'
    operation = HERE / 'operations/1794826205605133600-export-actual-original-images'
    assert json.loads((command / 'result.json').read_bytes())['exit_code'] == 1
    assert 'FileNotFoundError' in (command / 'stderr.bin').read_text('utf8')
    assert 'native16b-T125-blank_replace-gate' in (command / 'stderr.bin').read_text('utf8')
    verify(operation)
    root = HERE / ('readonly-export-failure-preservation-' + str(time.time_ns()))
    root.mkdir()
    shutil.copytree(command, root / 'failed-command')
    shutil.copytree(operation, root / 'failed-remote-operation')
    before = root / 'before'
    before.mkdir()
    for name in ['export_examples.py', 'watch_current_campaign.py', 'REVIEW_HANDOFF.md']:
        (before / name).write_bytes((HERE / name).read_bytes())

    old_export = (HERE / 'export_examples.py').read_text('utf8')
    marker = "for a in sorted((p/'batch/runs').glob('*/attempt-*')):\n events=[];raw=(a/'controller/events.jsonl').read_bytes()"
    assert old_export.count(marker) == 1
    new_export = old_export.replace(marker,
        "for a in sorted((p/'batch/runs').glob('*/attempt-*')):\n if not(a/'terminal.json').exists()or not(a/'seal.json').exists():continue\n export_seal=json.loads((a/'seal.json').read_bytes())\n assert hashlib.sha256((a/'terminal.json').read_bytes()).hexdigest()==export_seal['terminal.json']\n events=[];raw=(a/'controller/events.jsonl').read_bytes()\n assert hashlib.sha256(raw).hexdigest()==export_seal['controller/events.jsonl']")
    with (HERE / 'export_examples_sealed.py').open('x', encoding='utf8') as handle:
        handle.write(new_export)

    old_watch = (HERE / 'watch_current_campaign.py').read_text('utf8')
    old_root = "root = HERE / 'current-turn-watcher'; root.mkdir(exist_ok=False)"
    new_root = "root = HERE / ('linked-readonly-watcher-' + str(time.time_ns())); root.mkdir(exist_ok=False)"
    assert old_watch.count(old_root) == 1
    assert old_watch.count("run('export_examples.py')") == 1
    new_watch = old_watch.replace(old_root, new_root).replace("run('export_examples.py')", "run('export_examples_sealed.py')")
    with (HERE / 'watch_campaign_review_linked.py').open('x', encoding='utf8') as handle:
        handle.write(new_watch)
    for name in ['export_examples_sealed.py', 'watch_campaign_review_linked.py']:
        (root / name).write_bytes((HERE / name).read_bytes())
    save(root / 'repair.json', {'time': time.time(), 'predecessor_exec_session': 49839,
        'predecessor_tool_exit_code': 1, 'predecessor_live_again': False,
        'failure': 'Exporter enumerated a newly created running attempt before its controller journal existed.',
        'repair': 'New linked read-only exporter selects terminal attempts with a seal, verifies terminal/journal hashes, and skips in-progress attempts; original exporter and failed evidence remain unchanged.',
        'experiment_actual_UID_command_start_and_new_replies_verified_live': True,
        'latest_verified_progress': json.loads((HERE / 'live-progress-current.json').read_bytes()),
        'model_GUI_package_prompt_images_budgets_actions_changed': False,
        'all_completed_trajectories_preserved': True,
        'failed_command': str(command), 'failed_remote_operation': str(operation),
        'failed_remote_operation_seal_sha256': sha(operation / 'seal.json'),
        'prior_export_source_sha256': sha(before / 'export_examples.py'),
        'linked_export_source_sha256': sha(HERE / 'export_examples_sealed.py'),
        'prior_watcher_source_sha256': sha(before / 'watch_current_campaign.py'),
        'linked_watcher_source_sha256': sha(HERE / 'watch_campaign_review_linked.py'),
        'new_model_GUI_calls': 0})
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p)
         for p in root.rglob('*') if p.is_file()})
    save(HERE / 'readonly-review-repair-current.json', {'root': str(root),
        'seal_sha256': sha(root / 'seal.json'), 'previous_watcher_exited': True,
        'new_linked_watcher_not_yet_started': True, 'new_model_GUI_calls': 0})
    print(json.dumps({'root': str(root), 'seal_sha256': sha(root / 'seal.json'),
        'only_readonly_export_and_watcher_changed': True, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
