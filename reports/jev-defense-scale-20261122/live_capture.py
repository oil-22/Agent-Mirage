"""Trusted one-action capture sessions shared by preflight and the live panel."""

import base64
from dataclasses import asdict
import io
import os
from pathlib import Path
import sys
import time
import traceback

from gate_core import Frame, Journal, check_image_presence
from PIL import Image
from live_common import Child, load, process, save, sha, verify_input
from receipt_protocol import ReceiptVerifier
from temporal_request import action_json, png_size

ROOT = Path(__file__).resolve().parent


def event(state, name):
    return [row for row in state['events'] if row['kind'] == name]


def phase(case, audit):
    """Independent fixture label, not passed to either inference interface."""
    before, after = audit['before'], audit['after']
    if audit['receipt']['action_sequence'] == 0:
        return 'before_action'
    if case['action'] == 'boundary':
        return 'boundary_candidate'
    assert all(len(event(p, 'input')) == 1 and event(p, 'input')[0]['trusted'] for p in (before, after))
    if not event(after, 'render_applied'):
        return 'early_before_render'
    if event(before, 'render_painted'):
        return 'after_visible_render'
    return 'straddling_render'


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


class Episode:
    def __init__(self, browser, case, out, plan):
        self.browser, self.case, self.plan = browser, case, plan
        self.journal = Journal(out / case['id'])
        self.path = self.journal.root
        self.binding = browser.call('new', case['id'])
        assert self.binding['viewport'] == plan['viewport']
        self.verifier = ReceiptVerifier(self.path / 'challenges.sqlite', **{
            k: self.binding[k] for k in ('public_key', 'session_id', 'environment_id', 'source_code_sha256')})
        self.journal.emit('session', self.binding)
        self.sequence = 0
        self.frames = []
        self.previous_accepted = None
        self.post_captures = 0

    def capture(self):
        expected = self.verifier.issue(self.sequence)
        captured = self.browser.call('capture', expected)
        raw = base64.b64decode(captured['png'], validate=True)
        receipt, audit = captured['receipt'], captured['audit']
        assert receipt == audit['receipt'] and (audit['target'], audit['loader']) == (self.binding['target'], self.binding['loader'])
        assert Frame(raw, receipt['capture_id'], 0).sha256 == receipt['image_sha256']
        fault = None
        candidate = raw
        if self.sequence == 1:
            self.post_captures += 1
            if self.post_captures == 1 and self.case['scenario'] in ('missing', 'replaced'):
                fault = self.case['scenario']
                assert self.previous_accepted is not None
                candidate = None if fault == 'missing' else self.previous_accepted.png
        frame = Frame(candidate, receipt['capture_id'], time.time(), receipt, expected)
        assert frame.capture_id not in {r['capture_id'] for r in self.frames}
        if fault:
            self.journal.emit('candidate_transport_fault', {
                'kind': fault, 'capture_id': frame.capture_id, 'source_sha256': receipt['image_sha256'],
                'candidate_sha256': frame.sha256, 'receipt_kept_unchanged': True, 'sequence': self.sequence})
        self.journal.image(frame)
        present = check_image_presence(frame.png)
        self.journal.emit('presence', {'capture_id': frame.capture_id, **asdict(present)})
        if present.value == 'NO':
            verified = self.verifier.close_missing(expected)
        else:
            assert png_size(frame.png) == tuple(self.plan['viewport'])
            verified = self.verifier.check(frame.png, receipt, expected=expected)
        self.journal.emit('receipt', {'capture_id': frame.capture_id, 'expected': expected,
                                      'receipt': receipt, 'decision': asdict(verified)})
        self.frames.append({'capture_id': frame.capture_id, 'sha256': frame.sha256, 'phase_after_the_fact': phase(self.case, audit),
                            'receipt': verified.value, 'receipt_reason': verified.reason, 'presence': present.value,
                            'source_sha256': receipt['image_sha256'], 'transport_fault': fault,
                            'action_sequence': self.sequence, 'visual_source': audit['constituent_source'],
                            'stable_fixture_visual': audit['before']['visual'] if audit['before']['visual'] == audit['after']['visual'] else None,
                            'capture_index': receipt['capture_index'], 'started_ns': audit['capture_started_ns'],
                            'finished_ns': audit['capture_finished_ns']})
        return frame, audit, present.value == verified.value == 'YES'

    def action(self, accepted):
        assert self.sequence == 0 and self.frames and self.frames[-1]['capture_id'] == accepted.capture_id
        assert self.frames[-1]['presence'] == self.frames[-1]['receipt'] == 'YES'
        self.previous_accepted = accepted
        self.journal.emit('initial_accepted', {'capture_id': accepted.capture_id, 'sha256': accepted.sha256})
        self.sequence = 1
        action = self.browser.call('action', 1)
        assert action['action_sequence'] == 1 and action['dispatch_calls'] == 1
        assert action['environment'] == self.binding['environment_id']
        action_json(action['native_action'])
        self.journal.emit('actual_native_action', action)
        return action

    def finish(self, row):
        final = self.browser.call('finish', self.case['id'])
        assert final['dispatch_calls'] == self.sequence and final['capture_count'] == len(self.frames)
        row = {**row, 'case': self.case, 'frames': self.frames, 'finish': final, 'session': self.binding['session_id']}
        self.journal.emit('terminal', row)
        save(self.path / 'terminal.json', {**row, 'events': self.journal.seq, 'journal_head': self.journal.head,
                                          'journal_sha256': sha(self.path / 'events.jsonl')})
        return row


def child_source(out):
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': ''}
    return Child([sys.executable, '-B', '-u', str(ROOT / 'capture_gui.py')], out / 'source-worker-stderr.log', env=env)


def pixel_counts(png):
    # Instrumentation only. The measurements never enter either gate or either model.
    with Image.open(io.BytesIO(png)) as img:
        rgb = img.convert('RGB')
        hist = rgb.histogram()
        box = rgb.point([255]*255 + [0] + [255]*255 + [0] + [255]*255 + [0]).getbbox()
        return {'pixels': rgb.width * rgb.height, 'white_channel_counts': [hist[255], hist[511], hist[767]],
                'nonwhite_bounding_box': list(box) if box else None}


def preflight():
    assert os.getuid() == 1033 and os.environ.get('CUDA_VISIBLE_DEVICES') == ''
    manifest = verify_input(ROOT)
    assert manifest['mode'] == 'capture-preflight'
    plan = load(ROOT / 'live_plan.json')
    run = ROOT / 'run'
    run.mkdir()
    out = run / 'episodes'; out.mkdir()
    browser = None
    rows, error, exitcode = [], None, None
    try:
        browser = child_source(run)
        print('Chromium ready:', browser.call('connect', timeout=30)['browser_version'], flush=True)
        for name in manifest['preflight_ids']:
            case = next(r for r in plan['cases'] if r['id'] == name)
            ep = Episode(browser, case, out, plan)
            first, _, receipt = ep.capture(); assert receipt
            bound = ep.action(first)
            if not case['delay_ms']:
                time.sleep(plan['fast_control_wait_seconds'])
            second, audit, receipt = ep.capture()
            check = {}
            if case['delay_ms']:
                assert receipt and phase(case, audit) == 'early_before_render'
                if case['scenario'] in ('white', 'buttons'):
                    assert audit['before']['visual'] == audit['after']['visual'] == case['scenario'] and first.sha256 != second.sha256
                    check = pixel_counts(second.png)
                    box = check['nonwhite_bounding_box']
                    if case['scenario'] == 'white':
                        assert box is None and check['white_channel_counts'] == [check['pixels']] * 3
                    else:
                        assert box and 40 < box[2]-box[0] < 150 and 25 < box[3]-box[1] < 70
                elif case['flow'] in ('search', 'type'):
                    assert first.sha256 == second.sha256
                time.sleep(max(0, case['delay_ms'] / 1000 + .22 - (time.monotonic_ns()-bound['send_end_ns'])/1e9))
                third, audit, receipt = ep.capture()
                assert receipt and phase(case, audit) == 'after_visible_render' and first.sha256 != third.sha256
            elif case['scenario'] in ('missing', 'replaced'):
                assert not receipt and phase(case, audit) == 'after_visible_render'
                assert ep.frames[-1]['receipt_reason'] == {'missing': 'missing_image', 'replaced': 'capture_bytes_replaced'}[case['scenario']]
                third, audit, receipt = ep.capture()
                assert receipt and phase(case, audit) == 'after_visible_render' and first.sha256 != third.sha256
            elif case['action'] == 'boundary':
                assert receipt and certified_boundary(first, second, bound['native_action'], audit)
            else:
                assert receipt and phase(case, audit) == 'after_visible_render' and first.sha256 != second.sha256
            rows.append(ep.finish({'state': 'technical_preflight_passed', 'real_inference': False, 'image_checks': check}))
            print('Capture preflight passed:', name, [f['phase_after_the_fact'] for f in ep.frames], flush=True)
    except Exception:
        error = traceback.format_exc()
        print(error, file=sys.stderr, flush=True)
    finally:
        if browser is not None:
            exitcode = browser.close()
        save(run / 'terminal.json', {'status': 'passed' if error is None and exitcode == 0 else 'technical_failure',
                                     'completed': rows, 'source_worker_exit': exitcode, 'error': error,
                                     'new_model_calls': 0, 'gpu_allocations': 0, 'scope': 'live capture technical preflight only'})
    return 0 if error is None and exitcode == 0 else 1


if __name__ == '__main__':
    raise SystemExit(preflight())
