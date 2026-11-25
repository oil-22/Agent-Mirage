"""Freeze the exact seventeenth pending decision without replaying any action."""
import base64
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
EXPORTED = Path('D:/MultiModel/j29evidence/1794228241952080200')
SERVICE = EXPORTED / '3090/output/worker/requests'
GUI = EXPORTED / '4090/output/batch/runs/fullhistory23-T000-clean-noaux/attempt-1794227118456197872'
OLD = BASE / 'memory-scheduled-full-history-gui-20261109-29/runtime-package-linked02'
CAPACITY = BASE / 'prefill-residency-recovery-20261109-31'
read = lambda p: json.loads(Path(p).read_bytes())
digest = lambda b: hashlib.sha256(b).hexdigest()
canonical = lambda v: json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def save(p, v):
    with p.open('x', encoding='utf8') as f:
        json.dump(v, f, ensure_ascii=False, indent=2); f.write('\n')


def main():
    assert not (HERE / 'checkpoint-created.json').exists()
    for n, h in read(OLD / 'manifest.json')['files'].items():
        assert digest((OLD / n).read_bytes()) == h, n
    capacity_pointer = read(CAPACITY / 'terminal-collection-created.json')
    collection = Path(capacity_pointer['collection'])
    assert digest((collection / 'audit.json').read_bytes()) == capacity_pointer['audit_sha256']
    assert read(collection / 'audit.json')['passed']
    events = [json.loads(line) for line in (GUI / 'events.jsonl').read_bytes().splitlines()]
    accepted = [e for e in events if e['kind'] == 'accepted_actor_history_retained']
    executed = [e for e in events if e['kind'] == 'action_executed']
    candidates = [e for e in events if e['kind'] == 'candidate']
    assert len(accepted) == len(executed) == len(candidates) == 6
    prior = read(SERVICE / '0017/payload.json')['body']
    prior_reply = read(SERVICE / '0017/response.json')['text']
    history = prior['messages'][1:] + [{'role': 'assistant', 'content': prior_reply}]
    assert len(history) == 32 and digest(canonical(history)) == accepted[-1]['data']['history_after_sha256']
    old_accepted = read(OLD / 'carryover/checkpoint/accepted-actual-history.json')['accepted_source_events']
    all_accepted = old_accepted + accepted
    assert len(all_accepted) == 16
    pending = read(SERVICE / '0020/payload.json')['body']
    pending_reply = read(SERVICE / '0020/response.json')['text']
    failed = read(SERVICE / '0021/payload.json')
    assert pending['messages'][1:33] == history == failed['view']['messages'][1:33]
    assert pending_reply == candidates[-1]['data']['text'] == failed['candidate']
    assert pending_reply == '<action>{"type":"click","x":615,"y":678}</action>'
    current = base64.b64decode(failed['view']['images'][0]['raw_base64'], validate=True)
    assert current == (GUI / 'screenshots/017-delivered.png').read_bytes()
    out = HERE / ('checkpoint-' + str(time.time_ns())); out.mkdir()
    save(out / 'accepted-actual-history.json', {'system': pending['messages'][0]['content'],
        'accepted_messages': history, 'accepted_source_events': all_accepted})
    for number in ['0019', '0020', '0021']:
        dest = out / number; dest.mkdir()
        for name in ['payload.json', 'prepared.json', 'effective-generation.json', 'response.json']:
            source = SERVICE / number / name
            if source.is_file():
                (dest / name).write_bytes(source.read_bytes())
    (out / 'last-actually-delivered.png').write_bytes(current)
    requirements = {
        'schema': 'GUI29-source-exact-pending17-checkpoint-v1', 'time': time.time(),
        'original_track': 'fullhistory23-T000-clean-noaux', 'prepared_only': True, 'launch_ready': False,
        'accepted_exchanges': 16, 'accepted_messages': 32, 'executed_actions': 16,
        'accepted_history_sha256': digest(canonical(history)), 'pending_original_decision': 17,
        'pending_candidate_event_sha256': candidates[-1]['sha256'], 'pending_candidate_text': pending_reply,
        'original_actor_attempts_spent': 17, 'original_judge_attempts_spent_including_OOM': 49,
        'linked31_judge_attempt_index': 50, 'next_new_judge_attempt_index_after_linked31': 51,
        'original_current_image_sha256': digest(current),
        'pending_decision_original_recaptures_spent': 0, 'pending_decision_original_regenerations_spent': 0,
        'restoration_live_capture_consumes_original_recaptures': 1,
        'original_caps': {'actor': 70, 'judge': 140, 'auxiliary': 60, 'step': 50,
                          'recaptures_per_decision': 2, 'regenerations_per_decision': 2, 'format_retry': 1},
        'same_candidate_must_not_be_counted_twice': True,
        'pending_click_not_yet_executed': True,
        'strict_original_point_and_alignment_checks_still_required': True,
        'remaining_checks_use_new_calls_charged_to_original_cap': True,
        'restoration_requires_genuine_same_live_PNG_and_native_navigation_provenance': True,
        'interrupted_prefix_requires_technical_unknown_and_schedule_sensitivity_analysis': True,
        'no_new_model_GUI_scorer_paid_calls': True}
    save(out / 'requirements.json', requirements)
    save(out / 'seal.json', {p.relative_to(out).as_posix(): digest(p.read_bytes())
                             for p in out.rglob('*') if p.is_file()})
    save(HERE / 'checkpoint-created.json', {'checkpoint': str(out),
        'requirements_sha256': digest((out / 'requirements.json').read_bytes()),
        'seal_sha256': digest((out / 'seal.json').read_bytes()), 'launch_ready': False})
    print(json.dumps({'checkpoint': str(out), 'accepted_messages': 32, 'executed_actions': 16,
                      'pending_decision': 17, 'new_experiment_calls': 0}))


if __name__ == '__main__':
    main()
