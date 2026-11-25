"""Source-exact CPU carryover replay, no model/browser/action execution."""
import ast
import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
CAPACITY = BASE / 'memory-scheduled-capacity-20261109-26'
PACKAGE = CAPACITY / 'runtime-package'
sys.path[:0] = [str(PACKAGE), str(PACKAGE / 'release')]
from defense.core import Controller, Journal, Limits, PublicView, VisibleImage

sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
read = lambda path: json.loads(Path(path).read_bytes())


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2); stream.write('\n')


def view(value):
    return PublicView(value['observation_id'], copy.deepcopy(value['messages']),
                      tuple(VisibleImage(base64.b64decode(im['raw_base64']), im['role']) for im in value['images']),
                      value['recent_action'], value['execution_feedback'], value['observed_at'])


def equal(actual, frozen):
    assert actual.observation_id == frozen['observation_id']
    assert actual.messages == frozen['messages']
    assert actual.recent_action == frozen['recent_action']
    assert actual.execution_feedback == frozen['execution_feedback']
    assert len(actual.images) == len(frozen['images'])
    for image, original in zip(actual.images, frozen['images']):
        assert image.raw == base64.b64decode(original['raw_base64']) and image.role == original['role']


def main():
    assert not (HERE / 'pending-pipeline-replay-created.json').exists()
    checkpoint_pointer = read(HERE / 'checkpoint-created.json')
    checkpoint = Path(checkpoint_pointer['checkpoint'])
    assert sha(checkpoint / 'requirements.json') == checkpoint_pointer['requirements_sha256']
    capacity_pointer = read(CAPACITY / 'terminal-collection-created.json')
    collection = Path(capacity_pointer['collection'])
    assert sha(collection / 'audit.json') == capacity_pointer['audit_sha256']
    assert read(collection / 'audit.json')['passed']
    for name, expected in read(checkpoint / 'seal.json').items():
        assert sha(checkpoint / name) == expected
    original_ready = read(checkpoint / '0042/payload.json')
    original_post = read(checkpoint / '0044/payload.json')
    ready_reply = read(checkpoint / '0042/response.json')['verdict']
    linked_reply = (collection / 'original/worker/judge/J01/raw-output.txt').read_text(encoding='utf8')
    candidate = read(checkpoint / '0043/response.json')['text']
    records = [original_ready, original_post]
    replies = [ready_reply, linked_reply]
    out = HERE / ('pending-pipeline-replay-' + str(time.time_ns())); out.mkdir()
    state = {'judge_replays': 0, 'actor_replays': 0}

    def recorded(system, actual_view, actual_candidate):
        index = state['judge_replays']
        assert index < 2, 'Further real judge request is not replayed or silently invented'
        source = records[index]
        assert system == source['system'] and actual_candidate == source['candidate']
        equal(actual_view, source['view'])
        state['judge_replays'] += 1
        return replies[index]

    def actor(actual_view, corrections):
        assert not corrections and state['actor_replays'] == 0
        equal(actual_view, original_ready['view'])
        state['actor_replays'] += 1
        return candidate

    tree = ast.parse((PACKAGE / 'native-parser-source.py').read_text(encoding='utf8'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'parse')
    namespace = {'json': json, 're': re}
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'exact-original-native-parse', 'exec'), namespace)

    def parser(content):
        native = namespace['parse'](content)
        assert native == {'type': 'scroll', 'direction': 'down'}
        return {'name': native['type'], 'parsed': True, 'executor_fallback_wait': False,
                'payload': native, 'coordinate_space': 'normalized_1000'}

    def recapture():
        raise RuntimeError('No fabricated live recapture in source-only CPU replay')

    original_plan = read(BASE / 'full-history-gui-development-20261109-23/runtime-package/plan.json')
    lim = original_plan['limits']
    controller = Controller(recorded, Journal(out / 'unchanged-original-Controller'), 'joint',
        Limits(max_recaptures=lim['max_recaptures_per_decision'], max_regenerations=lim['max_regenerations_per_decision'],
               max_actor_calls=lim['max_actor_calls'], max_verifier_calls=lim['max_verifier_calls'],
               wait_seconds=tuple(lim['wait_seconds']), probe_current_targets=True, probe_target_alignment=True,
               full_completion_history=True, probe_completion=True, probe_history_reports=True, probe_observation_readiness=True),
        sleeper=lambda _: None)
    # Original pre-decision counts31judge/10actor, plus the already-spent OOM44.
    # Replayed readiness32 and linked reply34 fill the same pending decision.
    # Cache-replay indexing is local; actual network admission remains judge35+.
    controller.actor_calls = 10
    controller.verifier_calls = 32
    result = controller.decide(view(original_ready['view']), actor, parser, recapture)
    assert state == {'judge_replays': 2, 'actor_replays': 1}
    assert controller.actor_calls == 11 and controller.verifier_calls == 34
    assert result['candidate'] == candidate and result['status'] == 'accepted'
    assert result['recaptures'] == result['regenerations'] == 0
    receipt = {'schema': 'pending-GUI23-decision11-source-exact-Controller-CPU-carryover-v1',
        'time': time.time(), 'passed': True, 'result': result,
        'replayed_original_readiness_and_actor_and_once_completed_linked_judge': True,
        'all_actual_judge_system_candidate_public_view_full_images_messages_exact': True,
        'original_failed_prefill_count_preserved': True,
        'original_actor_attempts_spent': 11, 'original_judge_attempts_spent': 34,
        'next_actual_actor_attempt': 12, 'next_actual_judge_attempt': 35,
        'original_10_actions_reexecuted': False, 'pending_action_executed': False,
        'strict_Controller_and_validators_unchanged': True,
        'frame_source_review': 'Current original image shows coherent listings; Ethernet Cables entry continues below viewport. Downward exploratory scrolling is grounded. Judge reason ends with an incomplete The fragment at the original480character bound; complete JSON/EOS is preserved, no semantic correctness extrapolation.',
        'original_candidate_event_sha256': read(checkpoint / 'requirements.json')['pending_candidate_event_sha256'],
        'no_new_candidate_label_or_duplicate_semantic_trial': True,
        'technical_capacity_audit_sha256': sha(collection / 'audit.json'),
        'GUI_live_state_restoration_still_required_before_execution': True,
        'launch_ready': False, 'new_model_GUI_scorer_paid_calls': 0}
    save(out / 'receipt.json', receipt)
    save(out / 'seal.json', {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()})
    save(HERE / 'pending-pipeline-replay-created.json', {'replay': str(out), 'receipt_sha256': sha(out / 'receipt.json'),
                                                      'seal_sha256': sha(out / 'seal.json'), 'launch_ready': False})
    print(json.dumps({'replay': str(out), 'result': result['status'], 'actor_spent': 11, 'judge_spent': 34,
                      'pending_action_executed': False, 'launch_ready': False, 'new_experiment_calls': 0}))


if __name__ == '__main__':
    main()
