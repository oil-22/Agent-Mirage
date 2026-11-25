"""Create new linked runtime sources only. Never launches or calls services."""
import ast
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
TARGET = HERE / 'gui-three-linked-02'
TARGET.mkdir(exist_ok=False)
old = HERE / 'gui-linked-01'
capacity = HERE.parent / 'capacity-replay-launcher-01'

contract = (old / 'online_contract.py').read_text(encoding='utf8')
start = contract.index('    expected = [(condition, observer)')
end = contract.index("    if (plan['max_steps']", start)
contract = contract[:start] + '''    expected = [
        {'dataset': 'vwa', 'run_id': 'image-observer-v1--classifieds_112--clean--joint--observer',
         'condition': 'clean', 'arm': 'joint', 'observer_enabled': True},
        {'dataset': 'vwa', 'run_id': 'image-observer-v1--classifieds_112--stale_replace--joint--no-observer',
         'condition': 'stale_replace', 'arm': 'joint', 'observer_enabled': False},
        {'dataset': 'vwa', 'run_id': 'image-observer-v1--classifieds_112--stale_replace--joint--observer',
         'condition': 'stale_replace', 'arm': 'joint', 'observer_enabled': True}]
    queue = plan['queue']
    if (queue != expected or any(type(r['observer_enabled']) is not bool for r in queue)):
        raise ValueError('Only the exact last three unstarted original trajectories are allowed')
''' + contract[end:]
contract = contract.replace('new four-trajectory GUI group', 'new exact-three GUI group')
contract = contract.replace("elif state['next_run_index'] == 4:", "elif state['next_run_index'] == 3:")
# The old nonzero-exit exception is for a different completed capacity stage.
contract = contract[:contract.index('\n\ndef validate_completed_stage_shutdown')]+ '\n'
with (TARGET / 'online_contract.py').open('x',encoding='utf8') as f: f.write(contract)

service = (old / 'online_service.py').read_text(encoding='utf8')
native = (capacity / 'preflight_service.py').read_text(encoding='utf8')
tree = ast.parse(native)
node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'save')
atomic_save = ast.get_source_segment(native, node)
service = service.replace('import traceback\n', 'import traceback\nimport uuid\n')
begin = service.index('def save(path, value):')
end = service.index('\n\ndef state_save', begin)
service = service[:begin] + atomic_save + service[end:]
needle = "    expected_visible = '4,5,6,7' if a.role == 'primary' else '7'\n"
assert service.count(needle) == 1
service = service.replace(needle, '''    if config.get('layer_counts') != [14, 22, 22, 6] or config.get('primary_allocator') != 'expandable_segments:True':
        raise RuntimeError('New common capacity-proven placement/allocator required')
    expected_allocator = config['primary_allocator'] if a.role == 'primary' else None
    if os.environ.get('PYTORCH_CUDA_ALLOC_CONF') != expected_allocator:
        raise RuntimeError('Actual process allocator differs from sealed new runtime')
''' + needle)
with (TARGET / 'online_service.py').open('x',encoding='utf8') as f: f.write(service)
shutil.copyfile(capacity / 'marker_stop_helpers.py', TARGET / 'marker_stop_helpers.py')
print(json.dumps({'new_source':str(TARGET),'model_GUI_calls':0,'launch_ready':False}))
