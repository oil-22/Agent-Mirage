"""Finite online admission for a new exact-three GUI group; CPU only."""
import hashlib
import json


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_plan(plan):
    expected = [
        {'dataset': 'vwa', 'run_id': 'image-observer-v1--classifieds_112--clean--joint--observer',
         'condition': 'clean', 'arm': 'joint', 'observer_enabled': True},
        {'dataset': 'vwa', 'run_id': 'image-observer-v1--classifieds_112--stale_replace--joint--no-observer',
         'condition': 'stale_replace', 'arm': 'joint', 'observer_enabled': False},
        {'dataset': 'vwa', 'run_id': 'image-observer-v1--classifieds_112--stale_replace--joint--observer',
         'condition': 'stale_replace', 'arm': 'joint', 'observer_enabled': True}]
    queue = plan['queue']
    if (queue != expected or any(type(r['observer_enabled']) is not bool for r in queue)):
        raise ValueError('Only the exact last three unstarted original trajectories are allowed')
    if (plan['max_steps'] != 50 or plan['actor_output_tokens'] != 2048 or
            plan['verifier_output_tokens'] != 4096 or plan['max_format_retries'] != 1 or
            plan['auxiliary_calls_per_trajectory'] != 60 or
            plan['limits'] != {'max_recaptures_per_decision': 2,
                'max_regenerations_per_decision': 2, 'max_actor_calls': 70,
                'max_verifier_calls': 140, 'wait_seconds': [0.5, 1.0]}):
        raise ValueError('Original step/output/recovery caps and finite observer cap must remain')
    return {r['run_id']: {**r, 'caps': {'actor': 70, 'judge': 140,
            'observe': 60 if r['observer_enabled'] else 0}} for r in queue}


def initial_state(plan):
    runs = validate_plan(plan)
    return {'phase': 'ready', 'active': None, 'next_run_index': 0,
            'runs': {key: {'status': 'not_started', 'last_decision_index': 0,
                           'calls': {'actor': 0, 'judge': 0, 'observe': 0}}
                     for key in runs}}


def begin(state, plan, trajectory_id):
    if state['phase'] != 'ready' or state['active'] is not None:
        raise ValueError('A terminal failure or active trajectory prevents a new start')
    order = [r['run_id'] for r in plan['queue']]
    if state['next_run_index'] >= len(order) or trajectory_id != order[state['next_run_index']]:
        raise ValueError('Trajectory must follow the once-only reviewed run order')
    row = state['runs'][trajectory_id]
    if row['status'] != 'not_started':
        raise ValueError('A started/terminal trajectory cannot restart')
    row['status'] = 'active'
    state['active'] = trajectory_id


def finish(state, trajectory_id, status):
    if state['active'] != trajectory_id or status not in {'completed', 'technical_failure', 'stopped'}:
        raise ValueError('Invalid active trajectory terminal transition')
    state['runs'][trajectory_id]['status'] = status
    state['active'] = None
    state['next_run_index'] += 1
    if status != 'completed':
        state['phase'] = 'terminal_failure'
    elif state['next_run_index'] == 3:
        state['phase'] = 'complete'


def admit(state, plan, envelope, role):
    if set(envelope) != {'trajectory_id', 'decision_index', 'attempt_index', 'request_id', 'payload'}:
        raise ValueError('Online transport must contain exactly the five reviewed fields')
    trajectory = envelope['trajectory_id']
    if state['phase'] != 'ready' or state['active'] != trajectory:
        raise ValueError('Request is outside the active once-only trajectory')
    runs = validate_plan(plan)
    operation = 'observe' if role == 'pplx_flash' else envelope['payload'].get('operation')
    if operation not in ({'observe'} if role == 'pplx_flash' else {'actor', 'judge'}):
        raise ValueError('Unreviewed model operation')
    if (not isinstance(envelope['request_id'], str) or not 16 <= len(envelope['request_id']) <= 128 or
            any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in envelope['request_id'])):
        raise ValueError('Request ID must be a new opaque identifier, never task context')
    decision = envelope['decision_index']
    attempt = envelope['attempt_index']
    row = state['runs'][trajectory]
    if (type(decision) is not int or not 1 <= decision <= 50 or decision < row['last_decision_index'] or
            type(attempt) is not int or attempt != row['calls'][operation] + 1 or
            attempt > runs[trajectory]['caps'][operation]):
        raise ValueError('Decision order, per-operation sequence or finite trajectory cap exceeded')
    row['last_decision_index'] = decision
    row['calls'][operation] += 1
    return operation

