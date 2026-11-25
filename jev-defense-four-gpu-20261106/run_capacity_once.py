"""Send the one sealed new-layout capacity request, with no model retry."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import traceback
import urllib.error
import urllib.request


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


def main(a):
    for name, expected in json.loads((a.frozen / 'seal.json').read_bytes()).items():
        if sha((a.frozen / name).read_bytes()) != expected:
            raise RuntimeError('Frozen capacity source seal differs: ' + name)
    plan = json.loads((a.frozen / 'plan.json').read_bytes())
    raw = (a.frozen / 'request.json').read_bytes()
    if (sha(raw) != plan['request_wire_sha256'] or
            plan['max_primary_judge_calls'] != 1 or
            plan['max_output_tokens'] != 4096 or
            plan['max_format_retries'] != 0 or
            plan['automatic_retry'] is not False):
        raise RuntimeError('Capacity request is not the single frozen full-input call')
    token = a.token_file.read_text().strip()
    if len(token) < 32:
        raise RuntimeError('Missing private transport token')
    a.root.mkdir(parents=True, exist_ok=False)
    (a.root / 'request.json').write_bytes(raw)
    (a.root / 'plan.json').write_bytes((a.frozen / 'plan.json').read_bytes())
    save(a.root / 'request-started.json', {
        'time': time.time(), 'wire_sha256': sha(raw),
        'single_transport_attempt': True, 'automatic_model_retry': False})
    started = time.monotonic()
    summary = {'terminal': True, 'status': 'technical_failure',
        'transport_attempts': 1, 'max_new_primary_calls': 1,
        'actual_service_calls_require_remote_audit': True,
        'semantic_pass': None, 'GUI_actions': 0, 'scorer_calls': 0,
        'auxiliary_calls': 0, 'paid_API_calls': 0,
        'known_source_engineering_capacity_only': True,
        'full_history_unchanged': True, 'full_images_unchanged': True,
        'max_output_tokens': 4096, 'automatic_retry': False}
    try:
        request = urllib.request.Request(a.url, data=raw,
            headers={'Authorization': 'Bearer ' + token,
                     'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(request, timeout=3600) as response:
                code, result_raw = response.status, response.read()
        except urllib.error.HTTPError as error:
            code, result_raw = error.code, error.read()
        (a.root / 'response.raw.json').write_bytes(result_raw)
        result = json.loads(result_raw)
        save(a.root / 'response.json', result)
        if (code != 200 or 'verdict' not in result or
                type(result.get('input_tokens')) is not int or
                type(result.get('output_tokens')) is not int or
                result['input_tokens'] <= 0 or not 0 < result['output_tokens'] <= 4096):
            raise RuntimeError('Full-input capacity reply failed; inspect preserved service evidence')
        summary.update(status='reply_received_pending_service_audit',
            receipt=result['receipt'], input_tokens=result['input_tokens'],
            output_tokens=result['output_tokens'],
            response_wire_sha256=sha(result_raw))
    except Exception:
        save(a.root / 'failure.json', {'time': time.time(), 'error': traceback.format_exc(),
            'automatic_retry': False, 'semantic_pass': None})
        summary['error'] = traceback.format_exc()
    finally:
        summary.update(elapsed_client_seconds=time.monotonic() - started, time=time.time())
        save(a.root / 'summary.json', summary)
        save(a.root / 'terminal-sha256.json', {
            str(path.relative_to(a.root)): sha(path.read_bytes())
            for path in a.root.rglob('*') if path.is_file()})
        print(json.dumps(summary), flush=True)
    if summary['status'] == 'technical_failure':
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ['frozen', 'root', 'token-file']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--url', required=True)
    main(parser.parse_args())
