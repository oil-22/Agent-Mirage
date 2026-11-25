"""Inspect the same submitted service/GUI; never launch or restart anything."""
import contextlib
import json
from pathlib import Path
import time

import orchestrate


def main():
    root = Path(__file__).resolve().parent
    assert orchestrate.HERE == root
    prior = sorted(path for path in root.glob('actual-evidence-*')
                   if path.is_dir() and (path / 'seal.json').is_file())
    log = root / ('inspect-console-' + str(time.time_ns()) + '.log')
    with log.open('x', encoding='utf-8') as stream, contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
        orchestrate.inspect(prior[-1] if prior else None)
    current = max((path for path in root.glob('actual-evidence-*') if path.is_dir() and (path / 'seal.json').is_file()), key=lambda path: path.name)
    service = json.loads((current / '3090.json').read_bytes())
    gui = json.loads((current / '4090.json').read_bytes())
    def val(key):
        return service.get(key, {}).get('value')
    result = {'evidence': str(current), 'actual_worker': service.get('worker/process.json', {}).get('actual'),
              'actual_launcher': service.get('launcher-process.json', {}).get('actual'),
              'service_state': val('worker/status.json'), 'ready': val('worker/ready.json'),
              'service_terminal': val('worker/terminal.json'), 'service_exit': val('exit.json'),
              'held_locks': len(service['held_locks']), 'sealed_request_count': len(service['sealed_requests']),
              'latest_sealed_requests': service['sealed_requests'][-5:],
              'GUI_state': gui.get('batch/status.json', {}).get('value'),
              'GUI_runner': gui.get('control/runner-process.json', {}).get('actual'),
              'GUI_exit': gui.get('control/exit.json', {}).get('value'),
              'service_journal': service.get('journal'), 'GUI_chains': gui.get('GUI_event_chains'),
              'service_log_tail': service.get('log_tail'), 'GUI_log_tail': gui.get('runner_log_tail'),
              'new_model_or_GUI_calls_by_observer': 0}
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
