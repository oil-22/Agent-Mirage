"""Invoke only saved read-only code via original SSH helper; keep raw receipt local."""
import sys
import json
import time
import hashlib
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOST = sys.argv[1]
assert HOST in ['3090', '4090']
target = HERE / (HOST + '-readonly.json')
assert not target.exists(), 'Never overwrite a captured snapshot'
helper = Path(r'D:\MultiModel\defense-resume-20261102\restored-release\remote.py')
spec = importlib.util.spec_from_file_location('original_readonly_remote_helper', helper)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
started = time.time()
try:
    code = (HERE / 'remote_readonly.py').read_text(encoding='utf-8').replace('HOST_ALIAS_PLACEHOLDER', HOST)
    raw = module.remote(code, timeout=120, host=HOST)
    parsed = json.loads(raw)
    with target.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(raw)
    result = {'host_alias': HOST, 'local_capture': str(target), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
              'started_unix': started, 'completed_unix': time.time(), 'network_read_only': True,
              'existing_model_roots': [x['path'] for x in parsed['asset_roots'] if x['exists']],
              'receipt_candidates_count': len(parsed['receipt_candidates'])}
    with (HERE / (HOST + '-invocation.json')).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(result, ensure_ascii=False))
except Exception as exc:
    result = {'host_alias': HOST, 'started_unix': started, 'failed_unix': time.time(),
              'error_type': type(exc).__name__, 'error': str(exc), 'no_confirmed_remote_model_actions': True}
    failure = HERE / (HOST + '-invocation-failure-' + str(time.time_ns()) + '.json')
    failure.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'failure_file': str(failure), 'error_type': type(exc).__name__}))
    raise
