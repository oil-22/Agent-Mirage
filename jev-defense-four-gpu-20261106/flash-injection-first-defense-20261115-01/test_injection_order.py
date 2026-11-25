"""New injection-order and routing checks with fake callbacks; no model evidence."""
import hashlib
import io
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
P = HERE / 'package'
sys.path[:0] = [str(P / 'flash'), str(P)]
from PIL import Image
from injection import eligible, whiteout
from gate_core import Frame, Decision, ImageGate, Journal, GateController
from gui_experiment import LiveAdapter, Bypass


def main():
    assert not (HERE / 'CPU-injection-order.json').exists(), 'Completed checks must not be repeated'
    checks = []
    def check(name, condition):
        assert condition, name
        checks.append(name)
    def png(color):
        stream = io.BytesIO(); Image.new('RGB', (1280, 720), color).save(stream, format='PNG')
        return stream.getvalue()
    previous, current = png('navy'), png('green')
    injected = whiteout(current)
    check('whole_source_sized_valid_PNG', Image.open(io.BytesIO(injected)).size == (1280, 720))
    check('actual_pixels_whitened', Image.open(io.BytesIO(injected)).getextrema() == ((255, 255),) * 3)
    check('not_same_image_bytes', injected != current)
    check('only_eligible_changed_original', eligible(False, previous, current, {'type': 'click'}))
    check('not_before_original_capture', not eligible(False, None, current, {'type': 'click'}))
    check('not_on_unchanged_original', not eligible(False, current, current, {'type': 'click'}))
    check('no_repeat_injection', not eligible(True, previous, current, {'type': 'click'}))
    check('not_after_scroll_or_WAIT', all(not eligible(False, previous, current, {'type': t}) for t in ['wait', 'scroll', 'stop']))
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        log = Journal(root / 'journal')
        adapter = LiveAdapter.__new__(LiveAdapter)
        adapter.obs = current; adapter.png = lambda obs: obs; adapter.fired = False
        adapter.last_image = previous; adapter.previous = {'type': 'click'}; adapter.step = 2
        adapter.item = {'condition': 'whiteout_once'}; adapter.root = root; adapter.log = log
        frame = adapter.initial_frame()
        check('adapter_supplies_injected_frame_before_any_checker', frame.png == injected and adapter.fired)
        check('both_original_and_delivered_bytes_preserved', (root / '002-actually-captured.png').read_bytes() == current and (root / '002-initial-delivered.png').read_bytes() == injected)
        calls, actor_images, captures, actions = [], [], [], []
        class Checker:
            def decide(self, data):
                calls.append(data)
                return Decision('NO' if data == injected else 'YES', hashlib.sha256(data).hexdigest(), str(len(calls)), 'fixture', 'fixture')
        def capture():
            captures.append('same-live-capture')
            return Frame.captured(current)
        def actor(accepted):
            actor_images.append(accepted.png)
            return 'fixture native reply'
        gate = ImageGate(Checker(), revision='fixture', contract_sha256='fixture', journal=log, recapture_seconds=0)
        result = GateController(gate, max_steps=50, max_actor_calls=70).step(
            frame, capture, actor, lambda value: value,
            lambda value: actions.append(value) or {'environment_action': True}, cancelled=lambda: False)
        check('checker_sees_attack_then_new_capture', calls == [injected, current])
        check('main_never_receives_rejected_bytes', actor_images == [current])
        check('one_new_capture_no_intervening_environment_action', len(captures) == 1 and len(actions) == 1)
        check('original_controller_reports_real_routing_counts', result['status'] == 'dispatched' and gate.calls == 2 and gate.recaptures == 1)
        bypass = Bypass(log).acquire(frame, capture, cancelled=lambda: False)
        check('no_gate_control_preserves_same_injected_bytes', bypass['frame'].png == injected and bypass['model_calls'] == 0)
    value = {'passed': len(checks), 'checks': checks, 'CPU_fake_callback_only': True,
             'real_NO_or_WAIT_semantics_NOT_tested': True, 'new_model_GUI_calls': 0}
    with (HERE / 'CPU-injection-order.json').open('x', encoding='utf8') as f:
        json.dump(value, f, indent=2)
    print(json.dumps(value))


if __name__ == '__main__':
    main()
