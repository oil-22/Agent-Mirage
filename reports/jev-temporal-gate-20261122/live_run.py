"""A one-action browser panel: original gate versus the stateless double-frame gate."""

import base64
import copy
import os
from pathlib import Path
import time
import traceback
import uuid

from live_capture import Episode, certified_boundary, child_source
from live_common import Child, canonical, hash_bytes, load, save, sha, verify_input
from live_lease import Cohort

ROOT = Path(__file__).resolve().parent

TASK = {
    'search': 'Click Search for the existing bicycle keyword, then report the listings you can see.',
    'type': 'Type Virginia into the focused City field, then report what the City field displays.',
    'boundary': 'Scroll down once and report what you can see at the bottom of the current page.',
}


def url(frame):
    return 'data:image/png;base64,' + base64.b64encode(frame.png).decode('ascii')


def image(frame):
    return {'type': 'image_url', 'image_url': {'url': url(frame)}}


def main_body(template, ep, action, previous, current):
    stock = copy.deepcopy(template)
    assert [p['role'] for p in stock['messages']] == ['system']
    stock['messages'] += [{'role': 'user', 'content': [{'type': 'text', 'text': 'Task: ' + TASK[ep.case['action']]}, image(previous)]},
                          {'role': 'assistant', 'content': '<action>' + canonical(action).decode() + '</action>'},
                          {'role': 'user', 'content': [image(current)]}]
    return stock


def run_case(ep, flash, main, template, stop_dir):
    case = ep.case
    counts = {'quality': 0, 'temporal': 0, 'primary': 0}
    holds = []
    decisions = []

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
        elapsed_seconds = (time.monotonic_ns()-started_ns)/1e9
        assert result['request_id'] == identifier and result['choice'] in {'YES', 'NO'} and result['ordered_images'] == images
        assert result['revision'] == ep.plan['revision'] and result['wire_sha256'] == hash_bytes(canonical(wire)+b'\n')
        assert result['quality_contract_sha256'] == (sha(ROOT / 'gate-contract.json') if kind == 'quality' else None)
        row = {'request_id': identifier, 'kind': kind, 'capture_id': frame.capture_id, 'images': images,
               'decision': result['choice'], 'p_yes': result['probabilities']['YES'], 'native_seconds': result['native_seconds_with_trace'],
               'roundtrip_seconds': elapsed_seconds, 'wire_sha256': result['wire_sha256'], 'forward_sha256': result['forward_sha256']}
        ep.journal.emit('flash_replied', row)
        decisions.append(row)
        print(case['id'], frame.receipt['capture_index'], kind, result['choice'], f"pYES={row['p_yes']:.3f}", flush=True)
        return row

    old, _, verified = ep.capture()
    if not verified or flash_decide('quality', None, old)['decision'] != 'YES':
        raise RuntimeError('Initial fixture observation not accepted by the original gate')
    if stop():
        raise RuntimeError('Manual stop before the fixture action')
    action_event = ep.action()
    action = action_event['native_action']
    if not case['delay_ms']:
        time.sleep(ep.plan['fast_control_wait_seconds'])

    def report(status, main_result=None, delivery=None):
        return ep.finish({'status': status, 'calls': counts, 'holds': holds, 'flash': decisions,
                          'delivery': delivery, 'main_result': main_result, 'native_action': action,
                          'role_of_first_action': 'actual scripted fixture action', 'subsequent_action_executed': False})

    while not stop():
        frame, audit, verified = ep.capture()
        reason = 'presence_or_receipt_NO' if not verified else None
        if verified and case['temporal']:
            if case['action'] == 'boundary' and certified_boundary(old, frame, action, audit):
                ep.journal.emit('trusted_static_boundary', {'capture_id': frame.capture_id, 'same_png': True,
                                                           'source': 'isolated static top-level Chromium fixture',
                                                           'scope': 'trusted downward wheel at the measured physical bottom',
                                                           'not_a_flash_yes': True})
            elif flash_decide('temporal', old, frame, action)['decision'] == 'NO':
                reason = 'temporal_pending_or_unsupported'
        if verified and reason is None and not stop():
            if flash_decide('quality', None, frame)['decision'] == 'NO':
                reason = 'single_image_quality_NO'
        if stop():
            return report('operator_stopped')
        if reason is not None:
            row = {'capture_id': frame.capture_id, 'sha256': frame.sha256, 'reason': reason,
                   'sleep_seconds': ep.plan['recapture_seconds'], 'action_repeated': False}
            holds.append(row)
            ep.journal.emit('withhold_and_recapture', row)
            deadline = time.monotonic() + ep.plan['recapture_seconds']
            while time.monotonic() < deadline and not stop():
                time.sleep(min(.1, max(0, deadline-time.monotonic())))
            continue
        identifier = uuid.uuid4().hex
        body = main_body(template, ep, action, old, frame)
        delivered = {'request_id': identifier, 'capture_id': frame.capture_id, 'image_sha256': frame.sha256,
                     'body_sha256': hash_bytes(canonical(body)), 'previous_sha256': old.sha256,
                     'gate_accepted_ns': time.monotonic_ns(), 'last_quality_request_id': decisions[-1]['request_id'],
                     'no_extra_auxiliary_text': True}
        assert decisions[-1]['kind'] == 'quality' and decisions[-1]['decision'] == 'YES' and decisions[-1]['capture_id'] == frame.capture_id
        ep.journal.emit('main_request_started', delivered)
        counts['primary'] += 1
        actual = main.call('infer', {'request_id': identifier, 'body': body, 'images': [old.sha256, frame.sha256]}, timeout=220)
        assert actual['request_id'] == identifier and actual['current_image_sha256'] == frame.sha256 and actual['body_sha256'] == delivered['body_sha256']
        ep.journal.emit('actual_main_inference', {'request_id': identifier, 'capture_id': frame.capture_id,
                                               'image_sha256': actual['current_image_sha256'], 'reply_sha256': actual['reply_sha256'],
                                               'native_forward_count': actual['forward_count'], 'eos': actual['natural_eos']})
        print(case['id'], '27B real reply:', actual['output_tokens'], 'output tokens', 'EOS', actual['natural_eos'], flush=True)
        return report('main_inference_completed', actual, delivered)
    return report('operator_stopped')


def main():
    assert os.getuid() == 1033 and os.environ.get('CUDA_VISIBLE_DEVICES') == ''
    manifest = verify_input(ROOT)
    assert manifest['mode'] == 'live' and manifest['max_primary_calls'] == 7 and manifest['retries_of_model_or_action'] == 0
    plan, template = load(ROOT / 'live_plan.json'), load(ROOT / 'actor-template.json')
    assert len(plan['cases']) == len({r['id'] for r in plan['cases']}) == 7
    out = ROOT / 'run'; out.mkdir()
    episodes = out / 'episodes'; episodes.mkdir()
    stop_dir = ROOT / 'operator-stop'; stop_dir.mkdir()
    sources = {}
    cohort = None
    sessions, errors, exits = [], [], {}
    try:
        cohort = Cohort(plan, out)
        print('3090 cohort acquired:', cohort.indexes, flush=True)
        envs = {'primary': manifest['python'], 'flash': load(ROOT / 'service-config.json')['python']}
        for role in ('flash', 'primary'):
            sources[role] = Child([envs[role], '-B', '-u', str(ROOT / 'live_models.py'), role],
                                  out / (role + '-stderr.log'), **cohort.worker(role))
        for role in ('flash', 'primary'):
            state = sources[role].call('ready', timeout=180)
            assert state['process']['pid'] == sources[role].p.pid and state['process']['uid'] == 1033 and state['BF16']
            print('Ready:', role, 'load', round(state['load_seconds'], 2), 'seconds', flush=True)
        browser = sources['browser'] = child_source(out)
        print('Chrome GUI:', browser.call('connect', timeout=30)['browser_version'], flush=True)
        for case in plan['cases']:
            if (stop_dir / 'all').is_file():
                break
            ep = Episode(browser, case, episodes, plan)
            sessions.append(run_case(ep, sources['flash'], sources['primary'], template, stop_dir))
    except Exception:
        errors.append(traceback.format_exc())
        print(errors[-1], flush=True)
    finally:
        for name, service in reversed(list(sources.items())):
            try:
                exits[name] = service.close()
                if exits[name] != 0:
                    errors.append(f'{name} exited with code {exits[name]}')
            except Exception:
                errors.append(traceback.format_exc())
        if cohort is not None:
            try:
                cohort.close({child.p.pid for role, child in sources.items() if role != 'browser'})
            except Exception:
                errors.append(traceback.format_exc())
        counts = {k: sum(s['calls'][k] for s in sessions) for k in ('quality', 'temporal', 'primary')}
        status = ('technical_failure' if errors else 'completed_panel' if len(sessions) == len(plan['cases']) else 'operator_stopped')
        save(out / 'terminal.json', {'status': status, 'error': '\n'.join(errors) if errors else None,
                                    'sessions': sessions, 'closed_workers': exits, 'completed_sessions_call_counts': counts,
                                    'official_score_calls': 0, 'paid_API_calls': 0, 'old_queues_launched': 0})
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
