"""Inspect only the NEW linked native runner and its committed event chains."""
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'full-history-gui-development-20261109-23'
sys.path.insert(0, str(OLD))
from remote_control import remote


def main():
    spec = importlib.util.spec_from_file_location('read_only_GUI_inspector23_source', OLD / 'inspect_gui.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    code = module.CODE.replace('/data/researcher/jev-defense-four-gpu-20261106/full-history-gui-development-20261109-23',
        '/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name)
    before = 'print(json.dumps(out,ensure_ascii=False))'
    assert code.count(before) == 1
    code = code.replace(before, "out['native_restoration_receipts']=[{'path':str(p),'receipt':json.loads(p.read_bytes()),'sha256':sha(p)}for p in (r/'batch/runs').glob('*/attempt-*/native-restoration-receipt.json')]\n" + before)
    output, operation = remote('4090', code, 'inspect-same-new32-GUI-handles-live-capture-and-chains-no-model', timeout=55)
    value = json.loads(output)
    print(json.dumps({'evidence': str(operation), 'time': value['time_unix'],
        'state': value.get('batch/status.json', {}).get('value'),
        'actual_runner': value.get('control/runner-process.json', {}).get('value', {}).get('actual'),
        'exit': value.get('control/exit.json', {}).get('value'),
        'restoration': value['native_restoration_receipts'], 'runs': value['runs'],
        'log_tail': value.get('control/runner.log', {}).get('tail') if value.get('control/exit.json') else None,
        'outer_log_tail': value.get('background/outer.log', {}).get('tail') if not value.get('control/runner-process.json') else None}, ensure_ascii=False))


if __name__ == '__main__':
    main()
