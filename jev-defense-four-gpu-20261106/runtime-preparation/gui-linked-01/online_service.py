"""New once-only online GUI model transport; no browser, actor loop or scorer here.

The controller owns the original protocol. This separate stage adds finite run
admission and audit around the unchanged native model methods; it cannot reopen a
preflight attempt or old GUI queue.
"""
import argparse
import base64
from http.server import BaseHTTPRequestHandler, HTTPServer
import hmac
import io
import json
import os
from pathlib import Path
import signal
import sys
import time
import traceback

from online_contract import admit, begin, canonical, digest, finish, validate_plan


def sha(path):
    return digest(path.read_bytes())


def save(path, value):
    with path.open('x', encoding='utf8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


def state_save(path, value):
    temporary = path.with_name(path.name + '.tmp-' + str(os.getpid()))
    with temporary.open('x', encoding='utf8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def journal(path, event, payload):
    # Called only while the independently opened shared inference flock is held.
    previous = None
    index = 0
    if path.exists():
        lines = path.read_bytes().splitlines()
        for line in lines:
            row = json.loads(line)
            content = {k: v for k, v in row.items() if k != 'sha256'}
            if row['index'] != index or row['previous_sha256'] != previous or digest(canonical(content)) != row['sha256']:
                raise RuntimeError('Existing online journal chain is invalid')
            previous = row['sha256']
            index += 1
    content = {'index': index, 'previous_sha256': previous, 'event': event,
               'time': time.time(), 'payload': payload}
    row = {**content, 'sha256': digest(canonical(content))}
    with path.open('ab') as handle:
        handle.write(canonical(row) + b'\n')
        handle.flush()
        os.fsync(handle.fileno())
    return row['sha256']


def health_result(role, state, resources, both_ready):
    ready = both_ready and len(resources['actual_allowed_pids']) == 2
    return {'role': role, 'stage': 'online_ready' if ready else 'waiting_for_owned_peer',
            'phase': 'ready_gui' if ready else 'loading_peer', 'state': state, **resources}


def main(a):
    root = a.root
    root.mkdir(parents=True, exist_ok=False)
    (root / 'requests').mkdir()
    config = json.loads(a.config.read_bytes())
    parent = Path(config['preflight_source_root'])
    for name, expected in config['preflight_source_sha256'].items():
        if sha(parent / name) != expected:
            raise RuntimeError('Reviewed native preflight implementation changed')
    sys.path.insert(0, str(parent))
    from preflight_service import (audited_forward, check_inherited_locks, identity,
        load_flash, load_primary, memory, reset_memory, resource_admission, serial_inference)
    from four_gpu_contract import (FLASH, FLASH_REVISION, identity_matches, validate_actor,
        validate_layout, validate_observation, validate_probabilities)
    plan_path = Path(config['online_plan'])
    if sha(plan_path) != config['online_plan_sha256']:
        raise RuntimeError('Online finite run plan changed')
    plan = json.loads(plan_path.read_bytes())
    validate_plan(plan)
    lease = json.loads(a.lease.read_bytes())
    layout = json.loads(Path(config['layout']).read_bytes())
    validate_layout(layout)
    contract_path = Path(config['flash_observer_contract'])
    if sha(contract_path) != config['flash_observer_contract_sha256']:
        raise RuntimeError('Fixed neutral observer contract changed')
    observer_contract = json.loads(contract_path.read_bytes())
    commands = config['commands']
    actual_self = identity(os.getpid())
    if actual_self['uid'] != 1033 or actual_self['command'] != ' '.join(commands[a.role]):
        raise RuntimeError('Worker UID/full command differs from sealed online config')
    check_inherited_locks(lease)
    group = Path(config['group_root'])
    save(group / 'processes' / (a.role + '.json'), {'role': a.role, 'identity': actual_self,
         'lease_sha256': sha(a.lease), 'worker_sha256': sha(Path(__file__))})
    save(root / 'process.json', {'role': a.role, 'identity': actual_self,
         'CUDA_VISIBLE_DEVICES': os.environ.get('CUDA_VISIBLE_DEVICES'),
         'lease_sha256': sha(a.lease), 'online_plan_sha256': sha(plan_path)})
    expected_visible = '4,5,6,7' if a.role == 'primary' else '7'
    if os.environ.get('CUDA_VISIBLE_DEVICES') != expected_visible:
        raise RuntimeError('Online worker CUDA visibility differs')
    stop = {'value': False}
    signal.signal(signal.SIGUSR1, lambda *_: stop.update(value=True))
    signal.signal(signal.SIGTERM, lambda *_: stop.update(value=True))
    import torch
    from PIL import Image
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    captured = []
    with serial_inference(lease, group, commands):
        started = time.monotonic()
        engine, modules, audit = (load_primary(a, config, layout, root, torch)
                                  if a.role == 'primary' else load_flash(config, root, torch))
        audit.update(load_seconds=time.monotonic() - started, memory=memory(torch), role=a.role,
                     online_plan_sha256=sha(plan_path), stage='new_online_GUI_transport')
        save(root / 'loaded.json', audit)
        hooks = [audited_forward(torch, module, captured, raw_readout)
                 for module, raw_readout in modules]
        journal(group / 'journal.jsonl', 'worker_loaded', {'role': a.role,
                'loaded_sha256': sha(root / 'loaded.json'), 'identity': actual_self})
    signal.signal(signal.SIGUSR1, lambda *_: stop.update(value=True))
    signal.signal(signal.SIGTERM, lambda *_: stop.update(value=True))
    token = Path(config['token_file']).read_text().strip()
    if len(token) < 32:
        raise RuntimeError('Missing new once-only online transport token')
    state_path = group / 'online-state.json'
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass
        def reply(self, code, value):
            raw = canonical(value)
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            try:
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError):
                # The terminal model receipt is already sealed. A lost client
                # does not turn that completed forward into a second request.
                return
        def authenticated(self):
            return hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + token)
        def do_GET(self):
            if not self.authenticated():
                return self.reply(403, {'error': 'unauthorized'})
            if self.path not in {'/', '/health'}:
                return self.reply(404, {'error': 'not_found'})
            try:
                resources = resource_admission(lease, group, commands)
                both_ready = all((group / role / 'ready.json').exists() for role in ('primary', FLASH))
                return self.reply(200, health_result(a.role, json.loads(state_path.read_bytes()),
                                                    resources, both_ready))
            except Exception:
                return self.reply(503, {'error': traceback.format_exc(), 'model_calls': 0})
        def do_POST(self):
            if stop['value'] or (group / 'stop-requested.json').exists():
                return self.reply(503, {'error': 'owned_group_stopping', 'model_calls': 0})
            if not self.authenticated():
                return self.reply(403, {'error': 'unauthorized'})
            paths = {'/observe'} if a.role == FLASH else {'/', '/begin', '/end'}
            if self.path not in paths:
                return self.reply(404, {'error': 'not_found'})
            try:
                count = int(self.headers.get('Content-Length', '0'))
                if not 0 < count <= 64 * 1024 ** 2:
                    return self.reply(413, {'error': 'full_request_size_no_truncation'})
                raw = self.rfile.read(count)
                body = json.loads(raw)
                with serial_inference(lease, group, commands):
                    state = json.loads(state_path.read_bytes())
                    if self.path in {'/begin', '/end'}:
                        return self.transition(raw, body, state)
                    key = digest((str(body.get('trajectory_id')) + '\0' + str(body.get('request_id'))).encode())
                    request = root / 'requests' / key
                    if request.exists():
                        if ((request / 'request.json').read_bytes() == raw and
                                (request / 'response.json').exists()):
                            return self.reply(200, json.loads((request / 'response.json').read_bytes()))
                        return self.reply(409, {'error': 'terminal_or_pending_request_no_retry',
                                              'receipt': str(request), 'model_calls': 0})
                    operation = admit(state, plan, body, a.role)
                    payload = body['payload']
                    payload_native_wire = json.dumps(payload, ensure_ascii=False,
                        separators=(',', ':')).encode('utf8')
                    if a.role == FLASH:
                        validate_observation(payload, observer_contract)
                        if payload['request_id'] != body['request_id']:
                            raise ValueError('Observer inner and outer request IDs must match')
                    elif operation == 'actor':
                        validate_actor(payload)
                    elif set(payload) != {'operation', 'system', 'view', 'candidate'}:
                        raise ValueError('Primary judge payload must remain the original four fields')
                    request.mkdir(exist_ok=False)
                    (request / 'request.json').write_bytes(raw)
                    save(request / 'payload.json', payload)
                    state_save(state_path, state)
                    start_head = journal(group / 'journal.jsonl', 'model_request_started', {
                        'role': a.role, 'operation': operation, 'trajectory_id': body['trajectory_id'],
                        'decision_index': body['decision_index'], 'attempt_index': body['attempt_index'],
                        'request_id': body['request_id'], 'external_wire_sha256': digest(raw),
                        'payload_sha256': digest(canonical(payload)), 'receipt': str(request)})
                    captured.clear()
                    start = time.monotonic()
                    try:
                        reset_memory(torch)
                        if a.role == FLASH:
                            image_raw = base64.b64decode(payload['image_base64'], validate=True)
                            if digest(image_raw) != payload['image_sha256']:
                                raise ValueError('Current original image SHA differs')
                            (request / 'original.image').write_bytes(image_raw)
                            image = Image.open(io.BytesIO(image_raw)); image.load()
                            native = {'state': payload['state'], 'questions': payload['questions']}
                            save(request / 'native-request.json', {**native, 'images_sha256': [digest(image_raw)]})
                            native_result = engine.decide({**native, 'images': [image]})
                            save(request / 'native-result.json', native_result)
                            if list(native_result['answers']) != list(payload['questions']):
                                raise RuntimeError('Native question identities/order differ')
                            for question, query in payload['questions'].items():
                                evidence = native_result['answers'][question]
                                validate_probabilities(evidence['probabilities'], query['criteria'], evidence['choice'])
                            readouts = [r['raw_readout'] for r in captured if 'raw_readout' in r]
                            if (sum('pixel_values' in r.get('tensors', {}) and 'input_ids' in r.get('tensors', {})
                                    for r in captured) != 1 or len(readouts) != 1 or
                                    readouts[0]['shape'] != [3, 255] or native_result['usage']['sequences'] != 1):
                                raise RuntimeError('Expected one image/input-ID forward and three native readouts')
                            result = {'model': FLASH, 'revision': FLASH_REVISION,
                                'request_id': payload['request_id'], 'image_sha256': digest(image_raw),
                                'request_sha256': digest(payload_native_wire),
                                'original_size': list(image.size), 'answers': native_result['answers'],
                                'usage': native_result['usage'], 'native_result': native_result,
                                'scope': 'one_original_frame_only', 'history_verified': False, 'generation_tokens': 0}
                        else:
                            from defense.core import PublicView, VisibleImage
                            if operation == 'actor':
                                original = payload['body']
                                result = {'text': engine.generate(original['messages'], 2048,
                                    request / 'generation.json', seed=42, original_body=original)}
                            else:
                                value = payload['view']
                                view = PublicView(value['observation_id'], value['messages'],
                                    tuple(VisibleImage(base64.b64decode(x['raw_base64']), x['role']) for x in value['images']),
                                    value.get('recent_action', ''), value.get('execution_feedback', ''), value['observed_at'])
                                result = {'verdict': engine.judge(payload['system'], view,
                                    payload['candidate'], request / 'generation.json')}
                            generation = json.loads((request / 'generation.json').read_bytes())
                            result.update(input_tokens=len(generation['input_ids']),
                                output_tokens=len(generation['generated_ids']), seconds=generation['seconds'])
                        for i in range(torch.cuda.device_count()): torch.cuda.synchronize(i)
                        after_resources = resource_admission(lease, group, commands)
                        save(request / 'forward-trace.json', captured)
                        result.update(status='ok', receipt=str(request), trajectory_id=body['trajectory_id'],
                            request_id=body['request_id'],
                            decision_index=body['decision_index'], attempt_index=body['attempt_index'],
                            external_wire_sha256=digest(raw), payload_sha256=digest(canonical(payload)),
                            payload_native_wire_sha256=digest(payload_native_wire),
                            request_started_journal_sha256=start_head,
                            forward_trace_sha256=sha(request / 'forward-trace.json'),
                            seconds_including_audit=time.monotonic() - start, per_device_memory=memory(torch))
                        result['post_forward_resources'] = after_resources
                        save(request / 'response.json', result)
                        save(request / 'seal.json', {p.name: sha(p) for p in request.iterdir() if p.is_file()})
                        journal(group / 'journal.jsonl', 'model_request_completed', {
                            'receipt': str(request), 'response_sha256': sha(request / 'response.json'),
                            'request_seal_sha256': sha(request / 'seal.json')})
                        self.reply(200, result)
                    except BaseException:
                        if not (request / 'forward-trace.json').exists(): save(request / 'forward-trace.json', captured)
                        failure = {'status': 'technical_failure', 'error': traceback.format_exc(),
                            'request_id': body['request_id'],
                            'receipt': str(request), 'semantic_pass': None, 'per_device_memory': memory(torch),
                            'external_wire_sha256': digest(raw), 'payload_sha256': digest(canonical(payload)),
                            'seconds_including_audit': time.monotonic() - start}
                        save(request / 'failure.json', failure)
                        save(request / 'seal.json', {p.name: sha(p) for p in request.iterdir() if p.is_file()})
                        state['phase'] = 'terminal_failure'
                        state['runs'][body['trajectory_id']]['status'] = 'technical_failure'
                        state_save(state_path, state)
                        journal(group / 'journal.jsonl', 'model_request_failed', {'receipt': str(request),
                            'request_seal_sha256': sha(request / 'seal.json')})
                        self.reply(500, failure)
                    finally:
                        captured.clear()
                        import gc
                        gc.collect()
                        torch.cuda.empty_cache()
            except Exception:
                self.reply(403, {'status': 'online_admission_rejected', 'error': traceback.format_exc(), 'model_calls': 0})
        def transition(self, raw, body, state):
            expected = {'trajectory_id', 'request_id'} if self.path == '/begin' else {
                'trajectory_id', 'request_id', 'status', 'terminal_receipt_sha256'}
            if set(body) != expected:
                raise ValueError('Trajectory transition schema differs')
            transitions = group / 'transitions'
            key = digest(str(body['request_id']).encode())
            receipt = transitions / key
            if receipt.exists():
                value = json.loads((receipt / 'response.json').read_bytes())
                if value['wire_sha256'] == digest(raw): return self.reply(200, value)
                raise ValueError('Transition request ID already used with different bytes')
            if self.path == '/begin':
                if any(not (group / role / 'ready.json').exists() for role in ('primary', FLASH)):
                    raise ValueError('Both models must actually be loaded and ready before GUI begins')
                if len(resource_admission(lease, group, commands)['actual_allowed_pids']) != 2:
                    raise ValueError('Both exact owned peer processes must still be alive')
                begin(state, plan, body['trajectory_id'])
            else:
                seal = body['terminal_receipt_sha256']
                if not isinstance(seal, str) or len(seal) != 64 or any(c not in '0123456789abcdef' for c in seal):
                    raise ValueError('Actual controller trajectory terminal SHA is required')
                finish(state, body['trajectory_id'], body['status'])
            state_save(state_path, state)
            value = {'path': self.path, 'wire_sha256': digest(raw),
                     'external_wire_sha256': digest(raw), 'request_id': body['request_id'],
                     'body': body, 'state': state}
            receipt.mkdir(exist_ok=False)
            (receipt / 'request.json').write_bytes(raw)
            save(receipt / 'response.json', value)
            save(receipt / 'seal.json', {p.name: sha(p) for p in receipt.iterdir() if p.is_file()})
            journal(group / 'journal.jsonl', 'trajectory_transition', value)
            return self.reply(200, value)
    server = HTTPServer(('127.0.0.1', a.port), Handler)
    server.timeout = 1
    save(root / 'ready.json', {'port': a.port, 'stage': 'online_ready',
        'loaded_sha256': sha(root / 'loaded.json'), 'online_plan_sha256': sha(plan_path)})
    try:
        while not stop['value'] and not (group / 'stop-requested.json').exists(): server.handle_request()
    finally:
        server.server_close()
        for hook in hooks: hook.remove()
        save(root / 'stopped.json', {'time': time.time(), 'state_sha256': sha(state_path)})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--role', choices=['primary', 'pplx_flash'], required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--lease', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--port', type=int, required=True)
    try:
        main(parser.parse_args())
    except BaseException:
        traceback.print_exc()
        raise SystemExit(1)
