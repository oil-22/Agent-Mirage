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
    assert len(messages) == 32 and digest(canonical(messages)) == state['accepted_history_sha256']
    transcript.messages = copy.deepcopy(messages)
    transcript.accepted = [copy.deepcopy(row['data']) for row in history['accepted_source_events']]
    assert len(transcript.accepted) == 16
    controller.valid_state = copy.deepcopy(state['controller_valid_state'])
    controller.reference_bank = []
    for index, record in enumerate(transcript.accepted):
        controller.reference_bank.append({'observation_id': record['accepted_observation_id'],
            'image': VisibleImage(image_bytes(messages[index * 2]), 'current'),
            'candidate': messages[index * 2 + 1]['content']})
    assert len(controller.reference_bank) == 16
    # Cached readiness48 and the completed linked50 reply are replayed as
    # sources only. The original zero-token OOM49 remains charged.
    controller.actor_calls = 16
    controller.verifier_calls = 48
    view = read(package / 'carryover/checkpoint/0021/payload.json')['view']
    return {'sequence': 16, 'previous': json.loads(view['recent_action']),
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
    assert len(original) == 34
    assert original[-1]['action_type'] == ActionTypes.STOP and original[-1]['answer'] == 'Defense blocked'
    assert original[-2]['info']['page'].url == state['navigation_urls'][-1]
    trajectory = copy.deepcopy(original[:-1])
    assert len(trajectory) == 33 and sum('action_type' in value for value in trajectory) == 16
    # env.reset has already genuinely opened the original initial page. Rebuild
    # its six navigation entries, including back history, without repeating
    # any of the sixteen native actor actions. Restoration is separately logged.
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
        'original_sixteen_actor_actions_reexecuted': False, 'restoration_navigation_count': 4,
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


class PrefixReplayJournal:
    def __init__(self, original):
        self.original = original
        self.judge_requests = 0
        self.live = False

    def append(self, kind, data):
        if kind == 'verifier_request':
            self.judge_requests += 1
            if self.judge_requests > 2:
                self.live = True
        return self.original.append(kind if self.live else 'carryover_replay_' + kind, data)

    def observation(self, view, *args, **kwargs):
        if self.live:
            return self.original.observation(view, *args, **kwargs)
        return self.original.append('carryover_replay_observation',
            {'public': view.data(), 'audience': kwargs.get('audience', 'actor')})


def pending_decision(package, controller, actual, transcript, parser, log, live_actor, live_recapture):
    source = package / 'carryover/checkpoint'
    full = read(source / '0021/payload.json')
    equal_view(actual, full['view'], timestamp=False)
    actual = replace(actual, observed_at=full['view']['observed_at'])
    state = read(package / 'carryover/state.json')
    log.append('cached_pending_decision_source_binding', {
        'fresh_capture_logged_separately': True, 'cached_source_observed_at': actual.observed_at,
        'no_archived_timestamp_claimed_fresh': True, 'pending_recaptures_already_spent': 1,
        'pending_regenerations_already_spent': 0,
        'original_candidate_event_sha256': state['pending_candidate_event_sha256'],
        'no_new_inference_or_semantic_sample_for_cached_prefix': True,
        'original_point_alignment_and_recovery_checks_retained': True})
    sources = [read(source / '0019/payload.json'), full]
    replies = [read(source / '0019/response.json')['verdict'],
               (package / 'carryover/linked31-raw-output.txt').read_text(encoding='utf8')]
    pending_body = read(source / '0020/payload.json')['body']
    pending_text = read(source / '0020/response.json')['text']
    used = {'judge': 0, 'actor': 0}
    original_judge = controller.judge

    def prefix_judge(system, view, candidate):
        index = used['judge']
        if index < 2:
            expected = sources[index]
            assert system == expected['system'] and candidate == expected['candidate']
            equal_view(view, expected['view'])
            used['judge'] += 1
            return replies[index]
        return original_judge(system, view, candidate)

    def prefix_actor(view, corrections):
        if used['actor'] == 0:
            assert not corrections
            equal_view(view, full['view'])
            transcript.record_actual_reply(pending_body, pending_text)
            used['actor'] += 1
            return pending_text
        return live_actor(view, corrections)

    judge, journal, limits = controller.judge, controller.log, controller.limits
    assert limits.max_recaptures == 2
    assert len(limits.wait_seconds) >= 2
    controller.judge, controller.log = prefix_judge, PrefixReplayJournal(log)
    controller.limits = replace(limits, max_recaptures=1, wait_seconds=tuple(limits.wait_seconds[1:]))
    try:
        result = controller.decide(actual, prefix_actor, parser, live_recapture)
    finally:
        controller.judge, controller.log, controller.limits = judge, journal, limits
    assert used == {'judge': 2, 'actor': 1}
    assert controller.actor_calls >= 17 and controller.verifier_calls >= 50
    assert 0 <= result['recaptures'] <= 1 and 0 <= result['regenerations'] <= 2
    log.append('pending17_original_pipeline_returned', {
        'cached_candidate_sha256': digest(pending_text.encode()), 'status': result['status'],
        'actor_total_spent': controller.actor_calls, 'judge_total_spent': controller.verifier_calls,
        'new_actual_judge_calls': controller.verifier_calls - 50,
        'new_actual_actor_calls': controller.actor_calls - 17,
        'restoration_recapture_spent': 1, 'additional_recaptures': result['recaptures'],
        'pending_action_executed': False, 'original_16_actions_not_reexecuted': True,
        'cached_candidate_count_once': True, 'regenerated_candidates_are_new_samples': True})
    return result
