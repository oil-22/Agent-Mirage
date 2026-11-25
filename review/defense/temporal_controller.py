"""Original browser-panel per-episode controller without the machine-specific launcher. See README."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import time
import uuid

ROOT = Path(__file__).resolve().parent

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def hash_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def event(state, name):
    return [row for row in state['events'] if row['kind'] == name]


def certified_boundary(previous, current, action, audit):
    # Only for the fixture's static, top-level scroll panel; never inferred from
    # identical pixels alone. No application telemetry is used for click/type.
    if action != {'type': 'scroll', 'direction': 'down'} or previous.sha256 != current.sha256:
        return False
    before, after = audit['before'], audit['after']
    if before['kind'] != 'boundary' or after['kind'] != 'boundary' or not audit['receipt']['action_sequence'] == 1:
        return False
    wheels = event(after, 'wheel')
    if len(wheels) != 1 or wheels[0]['trusted'] is not True or wheels[0]['delta_y'] <= 0:
        return False
    def dimensions(p):
        return tuple(p[k] for k in ('scroll_top', 'client_height', 'scroll_height', 'scroll_width', 'client_width'))
    return (dimensions(before) == dimensions(after) and before['scroll_top'] > 0
            and before['scroll_top'] + before['client_height'] == before['scroll_height'])


def url(frame):
    return 'data:image/png;base64,' + base64.b64encode(frame.png).decode('ascii')


def image(frame):
    return {'type': 'image_url', 'image_url': {'url': url(frame)}}


def main_body(template, ep, action, previous, current):
    stock = copy.deepcopy(template)
    assert [p['role'] for p in stock['messages']] == ['system']
    stock['messages'] += [{'role': 'user', 'content': [{'type': 'text', 'text': 'Task: ' + ep.case['task']}, image(previous)]},
                          {'role': 'assistant', 'content': '<action>' + canonical(action).decode() + '</action>'},
                          {'role': 'user', 'content': [image(current)]}]
    return stock


def run_case(ep, flash, main, template, stop_dir):
    case = ep.case
    counts = {'quality': 0, 'temporal': 0, 'primary': 0}
    holds = []
    decisions = []
    action = None
    action_event = None

    def stop():
        return (stop_dir / case['id']).is_file() or (stop_dir / 'all').is_file()

    def flash_decide(kind, previous, frame, action=None):
        identifier = uuid.uuid4().hex
        if kind == 'quality':
            body = {'request_id': identifier, 'image_png_base64': url(frame).split(',', 1)[1], 'image_sha256': frame.sha256}
            images = [frame.sha256]
        else:
            assert previous is not None and action is not None
            body = {'previous': url(previous), 'action': action, 'current': url(frame)}
            images = [previous.sha256, frame.sha256]
        wire = {'request_id': identifier, 'kind': kind, 'body': body}
        counts[kind] += 1
        ep.journal.emit('flash_requested', {'request_id': identifier, 'kind': kind, 'capture_id': frame.capture_id,
                                           'wire_sha256': hash_bytes(canonical(wire)+b'\n'), 'images': images})
        started_ns = time.monotonic_ns()
        result = flash.call('infer', wire, timeout=60)
        finished_ns = time.monotonic_ns()
        elapsed_seconds = (finished_ns-started_ns)/1e9
        assert result['request_id'] == identifier and result['choice'] in {'YES', 'NO'} and result['ordered_images'] == images
        assert result['revision'] == ep.plan['revision'] and result['wire_sha256'] == hash_bytes(canonical(wire)+b'\n')
        assert result['quality_contract_sha256'] == (sha(ROOT / 'gate-contract.json') if kind == 'quality' else None)
        row = {'request_id': identifier, 'kind': kind, 'capture_id': frame.capture_id, 'images': images,
               'decision': result['choice'], 'p_yes': result['probabilities']['YES'], 'native_seconds': result['native_seconds_with_trace'],
               'roundtrip_seconds': elapsed_seconds, 'started_ns': started_ns, 'finished_ns': finished_ns,
               'wire_sha256': result['wire_sha256'], 'forward_sha256': result['forward_sha256']}
        ep.journal.emit('flash_replied', row)
        decisions.append(row)
        print(case['id'], frame.receipt['capture_index'], kind, result['choice'], f"pYES={row['p_yes']:.3f}", flush=True)
        return row

    def report(status, main_result=None, delivery=None):
        return ep.finish({'status': status, 'calls': counts, 'holds': holds, 'flash': decisions,
                          'delivery': delivery, 'main_result': main_result, 'native_action': action,
                          'role_of_first_action': 'actual scripted fixture action' if action is not None else None,
                          'subsequent_action_executed': False})

    def gate(old, stage, start_ns):
        """Study censor stops observation without ever changing a NO to YES."""
        end_ns = start_ns + int(ep.plan['observation_seconds'] * 1e9)
        ep.journal.emit('study_window_started', {'stage': stage, 'start_ns': start_ns, 'end_ns': end_ns})
        latest = None

        def ended():
            if stop():
                return 'operator_stopped'
            if time.monotonic_ns() >= end_ns:
                return f'{stage}_observation_window_ended'
            return None

        while (end_state := ended()) is None:
            frame, audit, verified = ep.capture()
            latest = frame.capture_id
            if ended():
                break
            evidence = ep.frames[-1]
            if evidence['presence'] == 'NO':
                reason = 'image_presence_NO'
            elif not verified:
                reason = 'receipt_NO'
            else:
                reason = None
            if verified and old is not None and case['temporal']:
                if case['action'] == 'boundary' and certified_boundary(old, frame, action, audit):
                    ep.journal.emit('trusted_static_boundary', {'capture_id': frame.capture_id, 'same_png': True,
                                                               'source': 'isolated static top-level Chromium fixture',
                                                               'scope': 'trusted downward wheel at the measured physical bottom',
                                                               'not_a_flash_yes': True})
                elif flash_decide('temporal', old, frame, action)['decision'] == 'NO':
                    reason = 'temporal_pending_or_unsupported'
            if verified and reason is None and not ended():
                if flash_decide('quality', None, frame)['decision'] == 'NO':
                    reason = 'single_image_quality_NO'
            if reason is not None:
                row = {'capture_id': frame.capture_id, 'sha256': frame.sha256, 'reason': reason, 'stage': stage,
                       'sleep_seconds': ep.plan['recapture_seconds'], 'action_repeated': False}
                holds.append(row)
                ep.journal.emit('withhold_and_recapture', row)
                next_ns = time.monotonic_ns() + int(ep.plan['recapture_seconds'] * 1e9)
                while time.monotonic_ns() < next_ns and not ended():
                    time.sleep(min(.1, max(0, (next_ns-time.monotonic_ns())/1e9)))
                continue
            if not ended():
                accepted_ns = time.monotonic_ns()
                if accepted_ns >= end_ns:
                    break
                assert decisions[-1]['kind'] == 'quality' and decisions[-1]['decision'] == 'YES'
                assert decisions[-1]['capture_id'] == frame.capture_id
                ep.journal.emit('gate_accepted', {'stage': stage, 'capture_id': frame.capture_id, 'accepted_ns': accepted_ns,
                                                 'window_end_ns': end_ns, 'quality_request_id': decisions[-1]['request_id']})
                return frame, accepted_ns, None
        status = ended()
        assert status
        ep.journal.emit('study_window_closed', {'stage': stage, 'status': status, 'capture_id': latest,
                                                'end_ns': end_ns, 'closed_ns': time.monotonic_ns(),
                                                'fail_open': False})
        return None, None, status

    old, _, status = gate(None, 'initial', time.monotonic_ns())
    if status or stop():
        return report(status or 'operator_stopped')
    action_event = ep.action(old)
    action = action_event['native_action']
    if not case['delay_ms']:
        time.sleep(ep.plan['fast_control_wait_seconds'])
    frame, accepted, status = gate(old, 'post_action', action_event['send_end_ns'])
    if status or stop():
        return report(status or 'operator_stopped')
    identifier = uuid.uuid4().hex
    body = main_body(template, ep, action, old, frame)
    delivered = {'request_id': identifier, 'capture_id': frame.capture_id, 'image_sha256': frame.sha256,
                 'body_sha256': hash_bytes(canonical(body)), 'previous_sha256': old.sha256, 'previous_capture_id': old.capture_id,
                 'gate_accepted_ns': accepted, 'last_quality_request_id': decisions[-1]['request_id'],
                 'no_extra_auxiliary_text': True}
    ep.journal.emit('main_request_started', delivered)
    counts['primary'] += 1
    actual = main.call('infer', {'request_id': identifier, 'body': body, 'images': [old.sha256, frame.sha256]}, timeout=220)
    assert actual['request_id'] == identifier and actual['current_image_sha256'] == frame.sha256 and actual['body_sha256'] == delivered['body_sha256']
    ep.journal.emit('actual_main_inference', {'request_id': identifier, 'capture_id': frame.capture_id,
                                           'image_sha256': actual['current_image_sha256'], 'reply_sha256': actual['reply_sha256'],
                                           'native_forward_count': actual['forward_count'], 'eos': actual['natural_eos']})
    print(case['id'], '27B real reply:', actual['output_tokens'], 'output tokens', 'EOS', actual['natural_eos'], flush=True)
    return report('main_inference_completed', actual, delivered)
