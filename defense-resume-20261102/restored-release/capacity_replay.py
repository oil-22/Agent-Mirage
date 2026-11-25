"""Same-byte technical OOM replay and one frozen native-actor placement control.

No GUI access or new task trajectory. No semantic result is redrawn.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path
import requests
import os
import sys

# The standalone worker is saved beside an older defense/ directory. Bind imports
# to the immutable release rather than allowing the script directory to shadow it.
sys.path.insert(0, os.environ['PYTHONPATH'])

ap = argparse.ArgumentParser()
ap.add_argument('--old-service', type=Path, required=True)
ap.add_argument('--root', type=Path, required=True)
ap.add_argument('--token-file', type=Path, required=True)
args = ap.parse_args()
args.root.mkdir(exist_ok=False)
headers = {'Authorization': 'Bearer ' + args.token_file.read_text().strip(), 'Content-Type': 'application/json'}
old = args.old_service
failed = old / 'requests/1792911523173290976'
assert 'OutOfMemoryError' in (failed / 'failure.json').read_text()
actor = None
for path in sorted((old / 'requests').iterdir()):
    if int(path.name) < 1792907943000000000 or not (path / 'response.json').exists():
        continue
    if json.loads((path / 'request.json').read_text())['operation'] == 'actor':
        actor = path
        break
assert actor is not None
state = {'phase': 'running', 'cases': [], 'scope': 'capacity/placement development controls only; no online completion or independent Mirage labels'}

def save():
    (args.root / 'progress.json').write_text(json.dumps(state, indent=2), encoding='utf-8')

save()
for name, source in [('native_actor_placement', actor), ('preserved_oom_exact_request', failed)]:
    raw = (source / 'request.json').read_bytes()
    case = args.root / name
    case.mkdir()
    (case / 'request.json').write_bytes(raw)
    state['current'] = name
    state['started'] = time.time()
    save()
    response = requests.post('http://127.0.0.1:18127', headers=headers, data=raw, timeout=(15,1800))
    (case / 'response.json').write_bytes(response.content)
    response.raise_for_status()
    result = response.json()
    server_path = Path(result['receipt'])
    assert (server_path / 'request.json').read_bytes() == raw
    row = {'name': name, 'source': str(source), 'new_receipt': str(server_path),
           'byte_identical_request': True, 'request_sha256': hashlib.sha256(raw).hexdigest(),
           'input_tokens': result['input_tokens'], 'output_tokens': result['output_tokens'],
           'seconds': result['seconds'], 'http_success': True}
    if name == 'native_actor_placement':
        previous = json.loads((source / 'generation.json').read_text())
        current = json.loads((server_path / 'generation.json').read_text())
        row['input_ids_identical'] = previous['input_ids'] == current['input_ids']
        row['generated_ids_identical'] = previous['generated_ids'] == current['generated_ids']
        row['generation_config_identical'] = previous['generation_config'] == current['generation_config']
        row['passed'] = all(row[k] for k in ['input_ids_identical','generated_ids_identical','generation_config_identical'])
    else:
        from defense.core import PublicView, VisibleImage, decode_judge, validate_verdict
        import base64
        body = json.loads(raw)
        data = body['view']
        view = PublicView(data['observation_id'], data['messages'],
                          tuple(VisibleImage(base64.b64decode(image['raw_base64']), image['role']) for image in data['images']),
                          data['recent_action'], data['execution_feedback'], data['observed_at'])
        candidate = body['candidate']
        payload = json.loads(candidate.split('<action>')[1].split('</action>')[0])
        proposal = {'name': payload['type'], 'parsed': True, 'executor_fallback_wait': False,
                    'payload': payload, 'coordinate_space': 'normalized_1000'}
        value, _ = decode_judge(result['verdict'], 'verify')
        validated = validate_verdict(value, view, candidate, proposal)
        (case / 'validated-verdict.json').write_text(json.dumps(validated, indent=2), encoding='utf-8')
        row.update(passed=True, protocol_valid=True,
                   semantic_acceptance=validated['action']['status']=='supported' and all(c['status']=='supported' for c in validated['claims'] if c['kind'] in {'gui_fact','history_report'}))
    state['cases'].append(row)
    save()
    if not row['passed']:
        state['phase'] = 'failed_control'
        save()
        raise RuntimeError('Native actor placement control changed; do not launch formal batch')
state['phase'] = 'completed'
state['passed'] = all(case['passed'] for case in state['cases'])
save()
(args.root / 'summary.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
print(json.dumps(state), flush=True)
