"""New CPU checks of repeated NO/cancellation; not real model or GUI results."""
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE / 'package/flash'), str(HERE / 'package')]
from gate_core import Decision, Frame, GateController, ImageGate, Journal


def run_case(white, clean, negative_calls, stop_at=None):
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary); journal = Journal(root / 'journal')
        calls, captures, actor_calls, actions = [], [], [], []
        stopped = [False]
        class FixtureChecker:
            def decide(self, png):
                calls.append(png)
                value = 'NO' if len(calls) <= negative_calls else 'YES'
                if stop_at is not None and len(calls) == stop_at:
                    stopped[0] = True
                return Decision(value, hashlib.sha256(png).hexdigest(), str(len(calls)), 'CPU-fixture', 'CPU-fixture')
        def capture():
            frame = Frame.captured(white if len(calls) < negative_calls else clean)
            captures.append(frame)
            return frame
        def actor(frame):
            actor_calls.append({'png': frame.png, 'checker_calls_at_forward': len(calls)})
            return 'CPU-fixture-native-reply'
        gate = ImageGate(FixtureChecker(), revision='CPU-fixture', contract_sha256='CPU-fixture',
                         journal=journal, recapture_seconds=0)
        initial = Frame.captured(white)
        result = GateController(gate, max_steps=50, max_actor_calls=70).step(
            initial, capture, actor, lambda text: text,
            lambda proposal: actions.append(proposal) or {'environment_action': True},
            cancelled=lambda: stopped[0])
        ids = [initial.capture_id] + [f.capture_id for f in captures]
        assert len(ids) == len(set(ids))
        if stop_at is None:
            assert calls == [white] * negative_calls + [clean]
            assert gate.recaptures == negative_calls and gate.calls == negative_calls + 1
            assert actor_calls == [{'png': clean, 'checker_calls_at_forward': negative_calls + 1}]
            assert len(actions) == 1 and result['status'] == 'dispatched'
        else:
            assert result['status'] == 'cancelled' and not actor_calls and not actions
            assert len(calls) == stop_at and gate.recaptures == stop_at - 1
        rows = [json.loads(line) for line in (root / 'journal/events.jsonl').read_bytes().splitlines()]
        decisions = [r for r in rows if r['kind'] == 'gate_decision']
        assert len(decisions) == len(calls)
        forwarded = [r for r in rows if r['kind'] == 'main_image_forwarded']
        assert len(forwarded) == (0 if stop_at else 1)
        return {'negative_calls_requested': negative_calls, 'manual_stop_after': stop_at,
                'actual_fixture_checker_calls': len(calls), 'new_capture_calls': len(captures),
                'unique_capture_IDs': len(set(ids)), 'actor_calls': len(actor_calls),
                'environment_action_fixture_calls': len(actions), 'status': result['status'],
                'all_routing_assertions_passed': True}


def main():
    assert not (HERE / 'continuous-recapture-CPU-current.json').exists(), 'Do not repeat completed fixtures'
    published = json.loads((HERE / 'first-interception-publication-current.json').read_bytes())
    images = Path(published['root']) / 'images'
    white = (images / 'injected-whiteout.png').read_bytes()
    clean = (images / 'fresh-accepted.png').read_bytes()
    rows = [run_case(white, clean, 3), run_case(white, clean, 7), run_case(white, clean, 100, stop_at=4)]
    root = HERE / ('continuous-recapture-CPU-' + str(time.time_ns())); root.mkdir()
    result = {'scenarios': rows, 'passed_scenarios': len(rows),
              'original_gate_source_sha256': hashlib.sha256((HERE / 'package/flash/gate_core.py').read_bytes()).hexdigest(),
              'unchanged_original_while_loop_tested': True, 'finite_recapture_limit': None,
              'CPU_fixture_only': True, 'new_real_model_GUI_calls': 0,
              'real_consecutive_NO_semantics_NOT_proven': True}
    with (root / 'result.json').open('x', encoding='utf8') as f: json.dump(result, f, indent=2)
    members = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir() if p.is_file()}
    with (root / 'seal.json').open('x', encoding='utf8') as f: json.dump(members, f, indent=2)
    with (HERE / 'continuous-recapture-CPU-current.json').open('x', encoding='utf8') as f:
        json.dump({'root': str(root), 'seal_sha256': hashlib.sha256((root / 'seal.json').read_bytes()).hexdigest()}, f, indent=2)
    print(json.dumps({'receipt': str(root), **result}))


if __name__ == '__main__': main()
