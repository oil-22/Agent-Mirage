import json
from pathlib import Path
base = Path('/home/researcher/jev-defense-four-gpu-20261106')
group = base / 'online-service-group-1793978182501156243'
print(json.dumps({'audit_roots': [str(p) for p in (base / 'online-readiness-independent-audits').iterdir()],
    'loaded': {role: {key: value for key, value in json.loads((group / role / 'loaded.json').read_bytes()).items()
        if key in ('dtype_elements', 'tensor_count', 'devices', 'class', 'revision', 'primary_native_class_source_sha256')}
        for role in ('primary', 'pplx_flash')}}))
