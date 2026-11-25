"""Independent, fixed cohort for full native GUI trajectories."""
import copy
import hashlib
import json
from pathlib import Path

CONDITIONS = ('clean_control', 'silent_drop', 'blank_replace', 'stale_replace', 'buttons_only')
SAMPLE_COUNT = 10
STUDY = 'jev-paper-paired-native-gui-v1'
ORDER_SALT = '20261122:mirage:paired-v1'


def queue_for(task_ids):
    if len(task_ids) != SAMPLE_COUNT or len(set(task_ids)) != SAMPLE_COUNT:
        raise ValueError('Exactly ten distinct, predeclared native task IDs are required')
    queue = []
    for t, task_id in enumerate(task_ids):
        order = sorted(CONDITIONS, key=lambda key: hashlib.sha256(f'{ORDER_SALT}/{task_id}/{key}'.encode()).digest())
        if t == 0:
            order.remove('clean_control')
            order.insert(0, 'clean_control')
        for condition in order:
            pair = f'paperpair-T{task_id:03d}-{condition}'
            on_first = (t + CONDITIONS.index(condition)) % 2 == 1
            for on in (on_first, not on_first):
                arm = 'on' if on else 'off'
                queue.append(dict(run_id=f'{pair}-{arm}', pair_id=pair, task_id=task_id,
                                  condition=condition, gate_enabled=on, arm=arm))
    return queue


def load_plan(root):
    root = Path(root)
    m = json.loads((root / 'manifest.json').read_bytes())
    plan = json.loads((root / 'plan.json').read_bytes())
    assert m['study'] == plan['version'] == STUDY
    assert m['action_envelope_compatibility'] == plan['action_envelope_compatibility']
    assert m['trajectories'] == len(plan['queue'])
    assert m['plan_sha256'] == hashlib.sha256((root / 'plan.json').read_bytes()).hexdigest()
    parent_file = root / 'parent-full-plan.json'
    parent = json.loads(parent_file.read_bytes())
    cut = json.loads((root/'action-envelope-cutover.json').read_bytes())
    assert cut['parent_plan_sha256'] == hashlib.sha256(parent_file.read_bytes()).hexdigest()
    assert cut['prefix_count'] == 22
    split = m['preserved_prefix_count']
    assert split == 61
    assert type(split) is int and 0 < split < SAMPLE_COUNT * len(CONDITIONS) * 2 and parent['queue'][split-1]['pair_id'] == parent['queue'][split]['pair_id']
    assert parent['queue'] == queue_for([row['task_id'] for row in parent['tasks']])
    assert plan['queue'] == parent['queue'][split:] and plan['tasks'] == parent['tasks']
    assert {k:v for k,v in plan.items() if k not in ('queue','action_envelope_compatibility')} == {k:v for k,v in parent.items() if k!='queue'}
    return m, plan


def missing_image_request(actor, frame):
    """Use the archived native omission convention, with no new alert text."""
    if frame.png is not None:
        return actor(frame)
    body = {k: copy.deepcopy(v) for k, v in actor.template.items() if k != 'messages'}
    body['messages'] = [copy.deepcopy(actor.template['messages'][0])] + copy.deepcopy(actor.history)
    body['messages'].append({'role': 'user', 'content': copy.deepcopy(actor.text_blocks)})
    original = copy.deepcopy(body)
    reply = actor.call(body)
    if body != original:
        raise ValueError('Actor transport mutated the complete native request/history')
    actor.pending = {'body': original, 'reply': reply, 'frame_sha256': None}
    return reply
