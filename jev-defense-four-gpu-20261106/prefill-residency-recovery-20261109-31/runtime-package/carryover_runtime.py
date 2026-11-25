"""Source-bound restoration of one unfinished decision, never a model retry.

Browser URLs and the private trajectory are execution provenance only. They
never enter a PublicView, actor body, auxiliary request or checker input.
"""
import base64
import copy
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import pickle
import time

from defense.core import PublicView, VisibleImage


canonical = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
digest = lambda raw: hashlib.sha256(raw).hexdigest()
read = lambda path: json.loads(Path(path).read_bytes())


def first_track(package, run_id):
    return run_id == read(package / 'carryover/state.json')['original_track']


def image_bytes(message):
    values = [block['image_url']['url'] for block in message['content'] if block['type'] == 'image_url']
    assert len(values) == 1
    assert values[0].startswith('data:image/png;base64,')
    return base64.b64decode(values[0].split(',', 1)[1], validate=True)


def original_view(value):
    return PublicView(value['observation_id'], copy.deepcopy(value['messages']),
        tuple(VisibleImage(base64.b64decode(im['raw_base64'], validate=True), im['role']) for im in value['images']),
        value['recent_action'], value['execution_feedback'], value['observed_at'])


def equal_view(actual, expected, timestamp=True):
    for field in ['observation_id', 'messages', 'recent_action', 'execution_feedback']:
        assert getattr(actual, field) == expected[field], 'Carryover public source differs: ' + field
    if timestamp:
        assert actual.observed_at == expected['observed_at'], 'Archived timestamp was altered'
    assert len(actual.images) == len(expected['images'])
    for image, frozen in zip(actual.images, expected['images']):
        assert image.role == frozen['role']
        assert image.raw == base64.b64decode(frozen['raw_base64'], validate=True)


def require_same_live_image(actual, expected):
    # Exact PNG identity is stronger than equal decoded pixels. No archived
    # image may stand in for a new screenshot if restoration differs.
    assert digest(actual) == expected, 'Restored live PNG differs; pending action must not execute'


def hydrate_history(package, transcript, controller):
    state = read(package / 'carryover/state.json')
    history = read(package / 'carryover/checkpoint/accepted-actual-history.json')
    assert transcript.system == history['system']
    messages = history['accepted_messages']
    assert len(messages) == 20 and digest(canonical(messages)) == state['accepted_history_sha256']
    transcript.messages = copy.deepcopy(messages)
    transcript.accepted = [copy.deepcopy(row['data']) for row in history['accepted_source_events']]
    assert len(transcript.accepted) == 10
    controller.valid_state = copy.deepcopy(state['controller_valid_state'])
    controller.reference_bank = []
    for index, record in enumerate(transcript.accepted):
        controller.reference_bank.append({'observation_id': record['accepted_observation_id'],
            'image': VisibleImage(image_bytes(messages[index * 2]), 'current'),
            'candidate': messages[index * 2 + 1]['content']})
    assert len(controller.reference_bank) == 10
    # Replaying cached readiness32 + linked34 and actor11 must not charge
    # completed calls twice. Judge33 was the spent original zero-token OOM.
    controller.actor_calls = 10
    controller.verifier_calls = 32
    view = read(package / 'carryover/checkpoint/0044/payload.json')['view']
    return {'sequence': 10, 'previous': json.loads(view['recent_action']),
        'execution_feedback': view['execution_feedback'], 'last_image': image_bytes(messages[-2])}


def restore_native(package, env, png, attempt, log):
    from browser_env.actions import ActionTypes
    state = read(package / 'carryover/state.json')
    for name, expected in state['native_source_SHA'].items():
        assert digest(Path(name).read_bytes()) == expected, name
    trajectory_path = Path(state['original_private_trajectory'])
    assert digest(trajectory_path.read_bytes()) == state['original_private_trajectory_sha256']
    assert digest(Path(state['original_trace']).read_bytes()) == state['original_trace_sha256']
    original = pickle.loads(trajectory_path.read_bytes())
    assert len(original) == 22
    assert original[-1]['action_type'] == ActionTypes.STOP and original[-1]['answer'] == 'Defense blocked'
    assert original[-2]['info']['page'].url == state['navigation_urls'][-1]
    trajectory = copy.deepcopy(original[:-1])
    assert len(trajectory) == 21 and sum('action_type' in value for value in trajectory) == 10
    # env.reset has already genuinely opened the original initial page. Rebuild
    # its four navigation entries, including back history, without repeating
    # any of the ten native actor actions. Restoration is separately logged.
    assert len(env.context.pages) == 1 and env.page.url == state['navigation_urls'][1]
    for url in state['navigation_urls'][2:]:
        env.page.goto(url)
        env.page.wait_for_timeout(500)
    last_click = next(value for value in reversed(trajectory) if 'action_type' in value and value.get('coords') is not None
                      and value['action_type'] == ActionTypes.MOUSE_CLICK)
    pointer = [float(last_click['coords'][0]) * 1280, float(last_click['coords'][1]) * 720]
    assert max(abs(actual - expected) for actual, expected in zip(pointer, state['last_pointer_pixels'])) < 0.001
    env.page.mouse.move(*pointer)
    env.page.evaluate('(xy) => window.scrollTo(xy[0], xy[1])', state['scroll_xy'])
    env.page.wait_for_timeout(500)
    assert env.page.evaluate('[window.scrollX, window.scrollY]') == state['scroll_xy']
    client = env.context.new_cdp_session(env.page)
    try:
        nav = client.send('Page.getNavigationHistory')
    finally:
        client.detach()
    actual_urls = [row['url'] for row in nav['entries'][:nav['currentIndex'] + 1]]
    assert actual_urls == state['navigation_urls'], 'Actual native back stack differs from original provenance'
    obs = env._get_obs()
    raw = png(obs)
    (attempt / 'restored-live-current.png').write_bytes(raw)
    proof = {'schema': 'genuine-native-live-restore-no-agent-action-reexecution-v1',
        'time': time.time(), 'capture_source': 'current native env._get_obs()',
        'fresh_live_capture_sha256': digest(raw), 'original_current_sha256': state['original_current_image_sha256'],
        'navigation_history_bound': True, 'scroll_xy': state['scroll_xy'],
        'original_private_trajectory_sha256': state['original_private_trajectory_sha256'],
        'original_trace_sha256': state['original_trace_sha256'],
        'original_ten_actor_actions_reexecuted': False, 'restoration_navigation_count': 3,
        'restoration_pointer_moved_not_clicked': True, 'one_of_two_pending_decision_recaptures_spent': True,
        'model_GUI_agent_scorer_calls_during_restore': 0, 'pending_action_executed': False,
        'private_trajectory_only_for_official_scorer': True,
        'pixel_identity_passed': digest(raw) == state['original_current_image_sha256']}
    (attempt / 'native-restoration-receipt.json').write_bytes(canonical(proof) + b'\n')
    log.append('technical_native_live_state_restored', proof)
    require_same_live_image(raw, state['original_current_image_sha256'])
    # Use the fresh actual observation for the latest private scorer state;
    # keep every prior accepted observation/action unchanged.
    old_last = trajectory[-1]
    from browser_env.utils import DetachedPage
    info = {'page': DetachedPage(env.page.url, env.page.content()), 'fail_error': '',
            'observation_metadata': env._get_obs_metadata()}
    trajectory[-1] = {'observation': obs, 'info': info}
    assert old_last['info']['page'].url == info['page'].url
    return obs, info, trajectory


class ReplayJournal:
    def __init__(self, original):
        self.original = original

    def append(self, kind, data):
        return self.original.append('carryover_replay_' + kind, data)

    def observation(self, *args, **kwargs):
        # The immutable original contains the complete observed data. The
        # namespaced replay is not a new delivered candidate or semantic trial.
        view = args[0]
        return self.original.append('carryover_replay_observation',
            {'public': view.data(), 'audience': kwargs.get('audience', 'actor')})


def pending_decision(package, controller, actual, transcript, parser, log):
    source = package / 'carryover/checkpoint'
    full = read(source / '0044/payload.json')
    equal_view(actual, full['view'], timestamp=False)
    actual = replace(actual, observed_at=full['view']['observed_at'])
    log.append('cached_pending_decision_source_binding', {
        'fresh_capture_logged_separately': True, 'cached_source_observed_at': actual.observed_at,
        'no_archived_timestamp_claimed_fresh': True, 'pending_recaptures_already_spent': 1,
        'pending_regenerations_already_spent': 0,
        'original_candidate_event_sha256': read(package / 'carryover/state.json')['pending_candidate_event_sha256'],
        'no_new_inference_or_semantic_sample': True})
    sources = [read(source / '0042/payload.json'), full]
    replies = [read(source / '0042/response.json')['verdict'],
               (package / 'carryover/linked26-raw-output.txt').read_text(encoding='utf8')]
    pending_body = read(source / '0043/payload.json')['body']
    pending_text = read(source / '0043/response.json')['text']
    used = {'judge': 0, 'actor': 0}

    def cached_judge(system, view, candidate):
        index = used['judge']
        assert index < 2, 'Unexpected extra judge branch: do not rerun completed decision'
        expected = sources[index]
        assert system == expected['system'] and candidate == expected['candidate']
        equal_view(view, expected['view'])
        used['judge'] += 1
        return replies[index]

    def cached_actor(view, corrections):
        assert not corrections and used['actor'] == 0
        equal_view(view, full['view'])
        # This is the actual old actor body, including its original complete
        # image/history and actor-only shared boundary instructions.
        transcript.record_actual_reply(pending_body, pending_text)
        used['actor'] += 1
        return pending_text

    def unavailable():
        raise RuntimeError('Unexpected recapture during source-exact completed reply replay')

    judge, journal, limits = controller.judge, controller.log, controller.limits
    controller.judge, controller.log = cached_judge, ReplayJournal(log)
    controller.limits = replace(limits, max_recaptures=1)
    try:
        result = controller.decide(actual, cached_actor, parser, unavailable)
    finally:
        controller.judge, controller.log, controller.limits = judge, journal, limits
    assert used == {'judge': 2, 'actor': 1}
    assert controller.actor_calls == 11 and controller.verifier_calls == 34
    assert result['status'] == 'accepted' and result['candidate'] == pending_text
    assert result['recaptures'] == result['regenerations'] == 0
    log.append('cached_pending_decision_accepted_for_first_execution', {
        'candidate_sha256': digest(pending_text.encode()), 'actor_total_spent': 11,
        'judge_total_spent_including_original_OOM': 34, 'pending_live_recaptures_spent': 1,
        'new_model_calls': 0, 'pending_action_executed': False,
        'same_candidate_not_new_semantic_trial': True})
    return result
