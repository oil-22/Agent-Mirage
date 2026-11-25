"""Check the actual primary-model messages against the frozen GUI input contract."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time

from collect import HERE, manifest_for, read, save, sha, stages
from extract_on_host import canonical, hx
from link import verify


TABS = re.compile(r'Current browser screenshot follows\. Available tab count: [1-9][0-9]*\.')
FEEDBACK = 'Previous native execution feedback (execution alone does not confirm the visible result): '


def audit(ledger):
    """Rebuild each ordered history from committed user messages and raw EOS replies."""
    messages = ledger['public_legal_messages']
    assert all(hx(canonical(v)) == k for k, v in messages.items())
    inputs = {}
    for stage in stages():
        pointer, manifest, _ = manifest_for(stage)
        root = Path(pointer['runtime'])
        template_path = root / 'actor-template.json'
        assert sha(template_path) == manifest['files']['actor-template.json']
        template = read(template_path)
        plan = read(root / 'plan.json')
        assert plan['native_full_history'] and plan['actor_budget']['max_new_tokens'] == 2048
        system = template['messages'][0]
        assert system['role'] == 'system' and isinstance(system['content'], str)
        inputs[stage] = (plan['actor_budget'], hx(canonical(system)),
                         {c['task_id']: c['intent'] for c in plan['tasks']})

    summaries = {stage: Counter() for stage in inputs}
    missing = []
    for row in ledger['rows']:
        tape = row['evidence']
        if tape is None:
            continue
        run = row['slot']['run_id']
        budget, system, intents = inputs[row['stage_id']]
        stats = summaries[row['stage_id']]
        stats['sealed_slots'] += 1
        steps = tape['steps']
        terminal = tape['terminal']
        observed = sum(s['request'] is not None for s in steps)
        assert observed <= budget['max_calls']
        assert all(1 <= s['step'] <= budget['max_steps'] for s in steps)
        if terminal.get('decisions') is not None:
            assert terminal['decisions'] <= budget['max_steps']
        if terminal.get('actor_calls') is not None:
            assert terminal['actor_calls'] == observed
        stats['controller_requests'] += observed

        history = [system]
        previous_action = None
        for step in steps:
            main = step['main']
            n = step['step']
            if main is None:
                if step['request']:
                    stats['request_without_sealed_model_body'] += 1
                    assert terminal['infrastructure_failure']
                continue
            ordered = main['messages_ordered']
            assert ordered[:-1] == history and len(ordered) == 2*n, (run, n, 'history')
            user = messages[ordered[-1]]
            assert user['role'] == 'user' and isinstance(user['content'], list)
            task, tab, *rest = user['content']
            assert task == {'type': 'text', 'text': 'Task: ' + intents[row['slot']['task_id']]}, (run, n, 'task')
            assert tab['type'] == 'text' and TABS.fullmatch(tab['text'])
            if n > 1:
                assert previous_action is not None and rest, (run, n, 'previous execution signal')
                feedback = rest.pop(0)
                assert feedback['type'] == 'text' and feedback['text'].startswith(FEEDBACK)
                payload = json.loads(feedback['text'][len(FEEDBACK):])
                assert set(payload) == {'execution_returned', 'error', 'result_state'}
                assert payload['execution_returned'] is previous_action['ok']
                assert payload['result_state'] == 'not confirmed by execution alone'
                assert feedback['text'] == FEEDBACK + json.dumps(payload)
                stats['native_execution_feedback_messages'] += 1
            img = main['current_image_sha256']
            assert rest == ([{'type': 'image', 'sha256': img}] if img is not None else []), (run, n, 'image-only tail')
            assert step['submit']['image_sha256'] == img
            stats['sealed_model_bodies'] += 1
            stats['actual_first_forwards'] += bool(step['actual_first_forward'])
            stats['natural_EOS'] += bool(main['natural_EOS'])
            if img is None:
                stats['requests_with_no_current_image_block'] += 1
                missing.append({'run_id': run, 'decision': n, 'request_id': step['request']['request_id'],
                                'required_text_and_history_preserved': True,
                                'actual_first_forward': step['actual_first_forward']})
            if main['natural_EOS']:
                assistant = {'role': 'assistant', 'content': main['reply_text']}
                history = ordered + [hx(canonical(assistant))]
            previous_action = step['executed']

    return {'stage_verification': {k: dict(v) for k,v in summaries.items()},
            'current_image_absence_cases': missing,
            'projected_messages_checked_against_frozen_task_system_and_expected_blocks': True,
            'visual_sha_and_exact_reply_bindings_checked_by_sealed_collection': True,
            'tab_count_text_format_checked_not_new_browser_measurement': True,
            'new_GUI_or_model_or_scorer_calls': 0}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('ledger', type=Path)
    args = p.parse_args()
    verify(args.ledger)
    result = audit(read(args.ledger / 'private-linked.json'))
    dst = HERE / 'legal-context-audits' / str(time.time_ns())
    dst.mkdir(parents=True, exist_ok=False)
    save(dst / 'index.json', {'ledger_seal_sha256': sha(args.ledger / 'seal.json'),
                              'auditor_sha256': sha(Path(__file__)), **result})
    save(dst / 'seal.json', {'index.json': sha(dst / 'index.json')})
    print(json.dumps({'audit': str(dst), 'seal_sha256': sha(dst / 'seal.json'),
                      'by_stage': result['stage_verification']}))


if __name__ == '__main__':
    main()
