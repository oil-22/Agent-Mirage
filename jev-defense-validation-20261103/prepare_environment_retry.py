"""Preserve the first source and add bounded HTTP readiness before browser login."""
import hashlib
import json
from pathlib import Path

base = Path(__file__).resolve().parent
source = base / 'environment_preflight.py'
raw = source.read_bytes()
text = raw.decode()
text = text.replace('import traceback\n', 'import traceback\nimport urllib.request\n')
old = "        result['site_resumed'] = True\n        auth = root / '.auth';auth.mkdir()"
new = """        result['site_resumed'] = True
        result['linked_predecessor'] = '/data/researcher/jev-defense-validation-20261103/environment-preflight-1793684288933578077'
        result['preflight_source_sha256'] = sha(Path(__file__))
        # Docker running does not establish that PHP is accepting HTTP connections.
        attempts = []
        for _ in range(30):
            try:
                with urllib.request.urlopen('http://192.0.2.10:29980/index.php?page=login', timeout=2) as response:
                    attempts.append({'time': time.time(), 'http_status': response.status})
                    if response.status == 200:break
            except OSError as error:
                attempts.append({'time': time.time(), 'error': type(error).__name__ + ': ' + str(error)})
            time.sleep(1)
        else:raise RuntimeError('Owned site did not become HTTP ready within bounded startup check')
        result['site_http_readiness'] = attempts
        auth = root / '.auth';auth.mkdir()"""
assert old in text
target = base / 'environment_preflight_v2.py'
assert not target.exists()
target.write_text(text.replace(old, new), encoding='utf-8')
receipt = {'parent_source_sha256': hashlib.sha256(raw).hexdigest(),
           'new_source_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
           'change': 'Wait for HTTP200 after exact owned container start, before original login',
           'model_calls': 0, 'task_actions': 0, 'native_runtime_edits': False}
(base / 'environment-startup-repair.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
