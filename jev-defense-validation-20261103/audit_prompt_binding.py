"""Read-only comparison of recovered prompt constants to archived wire requests."""
import hashlib
import importlib.util
import json
from pathlib import Path
import time

BASE = Path('/data/researcher/jev-defense-validation-20261103')
source = BASE / 'runtime-stage-01/release/defense/prompts.py'
spec = importlib.util.spec_from_file_location('recovered_prompts', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
names = ['SCREEN', 'READINESS', 'VERIFY', 'POINT_PIXEL', 'ALIGN', 'COMPLETION',
         'COMPLETION_RELATION', 'HISTORY_REPORT', 'NATIVE_NAVIGATION', 'FACTUAL_SOURCE_ROUTING']
values = {name: getattr(module, name) for name in names}
sha = lambda b: hashlib.sha256(b).hexdigest()
normalize = lambda s: s.replace('\r\n', '\n').replace('\r', '\n')
found = {}
near = {}
count = 0
for path in Path('/data/researcher/defense-resume-20261102/archive-evidence').rglob('request.json'):
    raw = path.read_bytes()
    try:
        request = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        continue
    systems = []
    if isinstance(request.get('system'), str):
        systems.append(request['system'])
    for m in request.get('messages', request.get('body', {}).get('messages', [])):
        if m.get('role') == 'system' and isinstance(m.get('content'), str):
            systems.append(m['content'])
    count += 1
    for name, value in values.items():
        for system in systems:
            if name not in found and value in system:
                found[name] = {'request': str(path), 'request_sha256': sha(raw),
                               'constant_sha256': sha(value.encode()), 'exact_string': True}
            elif name not in found and name not in near and normalize(value) in normalize(system):
                near[name] = {'request': str(path), 'request_sha256': sha(raw),
                              'constant_sha256': sha(value.encode()), 'line_endings_only': True}
out = {'time': time.time(), 'source_sha256': sha(source.read_bytes()),
       'requests_examined': count, 'exact': found,
       'line_endings_only': {k: v for k, v in near.items() if k not in found},
       'unbound': [k for k in names if k not in found and k not in near],
       'model_calls': 0, 'source_edits': 0, 'whole_prompts_file_historical_sha_restored': False}
target = BASE / ('prompt-binding-audit-' + str(time.time_ns()) + '.json')
target.write_text(json.dumps(out, indent=2))
print(json.dumps({'receipt': str(target), 'exact': list(found),
                  'line_endings_only': list(out['line_endings_only']), 'unbound': out['unbound']}))
