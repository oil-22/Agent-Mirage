"""Freeze exact public carryover state; this never replays a model or GUI action."""
import base64
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ORIGINAL = Path(r'D:\MultiModel\j23evidence/1794223604796828100')
SERVICE = ORIGINAL / '3090/output/worker/requests'
GUI = ORIGINAL / '4090/output/batch/runs/fullhistory23-T000-clean-noaux/attempt-1794221958077864899'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
canonical = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
read = lambda path: json.loads(Path(path).read_bytes())


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2); stream.write('\n')


def main():
    assert not (HERE / 'checkpoint-created.json').exists()
    events = [json.loads(line) for line in (GUI / 'events.jsonl').read_bytes().splitlines()]
    accepted = [v for v in events if v['kind'] == 'accepted_actor_history_retained']
    executed = [v for v in events if v['kind'] == 'action_executed']
    candidates = [v for v in events if v['kind'] == 'candidate']
    assert len(accepted) == len(executed) == 10 and len(candidates) == 11
    prior = read(SERVICE / '0040/payload.json')['body']
    prior_reply = read(SERVICE / '0040/response.json')['text']
    history = prior['messages'][1:] + [{'role': 'assistant', 'content': prior_reply}]
    assert len(history) == 20
    assert sha(canonical(history)) == accepted[-1]['data']['history_after_sha256']
    pending = read(SERVICE / '0043/payload.json')['body']
    pending_reply = read(SERVICE / '0043/response.json')['text']
    failed = read(SERVICE / '0044/payload.json')
    assert pending['messages'][1:21] == history == failed['view']['messages'][1:21]
    assert pending_reply == candidates[-1]['data']['text'] == failed['candidate']
    current = base64.b64decode(failed['view']['images'][0]['raw_base64'], validate=True)
    assert current == (GUI / 'screenshots/011-delivered.png').read_bytes()
    out = HERE / ('checkpoint-' + str(time.time_ns())); out.mkdir()
    save(out / 'accepted-actual-history.json', {'system': pending['messages'][0]['content'],
                                             'accepted_messages': history, 'accepted_source_events': accepted})
    for number in ['0042', '0043', '0044']:
        directory = out / number; directory.mkdir()
        for name in ['payload.json', 'prepared.json', 'effective-generation.json', 'response.json']:
            path = SERVICE / number / name
            if path.is_file():
                (directory / name).write_bytes(path.read_bytes())
    (out / 'last-actually-delivered.png').write_bytes(current)
    requirements = {
        'schema': 'GUI23-public-checkpoint-for-new-linked-technical-continuation-v1',
        'time': time.time(), 'prepared_only': True, 'launch_ready': False,
        'original_track': 'fullhistory23-T000-clean-noaux',
        'pending_candidate_event_sha256': candidates[-1]['sha256'],
        'pending_candidate_text': pending_reply, 'same_candidate_must_not_be_counted_twice': True,
        'accepted_exchanges': 10, 'accepted_messages': 20, 'executed_actions': 10,
        'accepted_history_sha256': sha(canonical(history)),
        'last_execution_event': executed[-1], 'pending_original_decision': 11,
        'original_actor_attempts_spent': 11, 'original_judge_attempts_spent_including_OOM': 33,
        'linked26_judge_attempt_index': 34, 'linked26_reply_must_be_sealed_before_admission': True,
        'next_new_judge_attempt_index_after_linked26': 35,
        'remaining_caps': {'actor': 70, 'judge': 140, 'step': 50, 'auxiliary': 60},
        'pending_decision_original_recaptures_spent': 0, 'pending_decision_original_regenerations_spent': 0,
        'live_restoration_requirement': 'New native browser context must capture and bind the genuine current page. First establish recoverable original URL/scroll/form state from execution provenance, never pass hidden page/scorer data to models. Do not substitute archived pixels for a live frame. Reusing the pending exact verifier reply requires a fresh actual capture with identical original supplied pixels and exact source bindings; any mismatch must stop that continuation path before native execution.',
        'original_current_image_sha256': sha(current),
        'model_replay_requirement': 'Only replay the already completed readiness0042 and actor0043 and the once-completed linked26 original0044 reply through the unchanged Controller, explicitly as cached carryover rather than new inference. Preserve failed0044 as a spent judge call. Any additional Controller call starts at original judge35; never regenerate the completed three replies or reset full-track counts.',
        'native_action_requirement': 'The original first10native actions must not execute again. The pending11th scroll has never executed and may execute only following actual live-state binding and the unchanged original Controller verdict pipeline. Preserve complete original accepted history/images and current per-decision recovery budget.',
        'analysis_requirement': 'Keep original technical terminal/official0 immutable. Tag placement change and infrastructure interruption. Do not silently pool this disrupted prefix as a homogeneous matched completed trajectory; include unknown/technical-failure sensitivity bounds. Both future arms need the identical new weight schedule.',
        'auxiliary_requirement': 'One current full supplied image plus fixed generic v6; empty fresh per-call KV and release. Weight RAM storage never permits CPU model inference. No task/history/candidate/previous auxiliary input.',
        'no_new_model_GUI_scorer_paid_calls': True,
    }
    save(out / 'requirements.json', requirements)
    save(out / 'seal.json', {p.relative_to(out).as_posix(): sha(p.read_bytes()) for p in out.rglob('*') if p.is_file()})
    save(HERE / 'checkpoint-created.json', {'checkpoint': str(out), 'requirements_sha256': sha((out / 'requirements.json').read_bytes()),
                                          'seal_sha256': sha((out / 'seal.json').read_bytes()), 'launch_ready': False})
    print(json.dumps({'checkpoint': str(out), 'accepted_messages': 20, 'accepted_exchanges': 10,
                      'pending_decision': 11, 'launch_ready': False, 'new_experiment_calls': 0}))


if __name__ == '__main__':
    main()
