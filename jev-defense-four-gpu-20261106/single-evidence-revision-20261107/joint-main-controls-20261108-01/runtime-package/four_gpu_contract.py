"""Pure admission rules for the new owned four-GPU preflight (no torch import)."""
import hashlib
import json
import math

PRIMARY = 'primary'
FLASH = 'pplx_flash'
FLASH_REVISION = '9ff7cf9838e59df461c276b7699d56b244d2af58'
PHYSICAL_GPUS = (4, 5, 6, 7)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':')).encode('utf8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def request_fingerprint(body):
    # Transport IDs may differ; every content byte remains bound (including image).
    return digest(canonical({k: v for k, v in body.items() if k != 'request_id'}))


def identity_matches(actual, expected):
    return all(str(actual.get(k)) == str(expected.get(k))
               for k in ('pid', 'uid', 'command', 'start_ticks'))


def validate_layout(layout):
    if layout['physical_gpus'] != list(PHYSICAL_GPUS):
        raise ValueError('Only user-authorized physical GPUs4-7 are allowed')
    limits = layout['primary_max_memory_gib']
    if (len(limits) != 4 or any(type(x) is not int or not 1 <= x <= 20 for x in limits)
            or sum(limits) < 56 or limits[3] > 10):
        raise ValueError('Unreviewed asymmetric primary parameter allocation')
    if layout['flash_physical_gpu'] != 7 or layout['primary_dtype'] != 'bfloat16':
        raise ValueError('Unreviewed flash GPU or main precision')
    if layout['primary_attention'] != 'sdpa' or layout['flash_fast'] is not False:
        raise ValueError('Original main SDPA and native reference Flash are required')
    if layout['flash_revision'] != FLASH_REVISION:
        raise ValueError('Unpinned Flash revision')
    return {i: str(x) + 'GiB' for i, x in enumerate(limits)}


def primary_device_map():
    result = {'model.visual': 0, 'model.language_model.embed_tokens': 0,
              'model.language_model.norm': 3, 'model.language_model.rotary_emb': 3,
              'lm_head': 3}
    for layer in range(64):
        device = 0 if layer < 14 else 1 if layer < 36 else 2 if layer < 58 else 3
        result['model.language_model.layers.' + str(layer)] = device
    return result


def validate_admission(plan):
    if plan['mode'] not in {'preflight', 'capacity_preflight', 'image_observer_preflight', 'resident_only'} or plan.get('GUI_actions', 0) != 0:
        raise ValueError('This worker only admits frozen no-GUI preflights')
    rows = plan['requests']
    if plan['mode'] == 'resident_only':
        if plan['max_new_calls'] != 0 or type(plan['max_new_calls']) is not int or rows != []:
            raise ValueError('Resident-only peers cannot admit any new model request')
        return {}
    if type(plan['max_new_calls']) is not int or not 1 <= plan['max_new_calls'] <= len(rows):
        raise ValueError('Invalid finite preflight budget')
    indexed = {}
    for row in rows:
        value = row['fingerprint']
        if (not isinstance(value, str) or len(value) != 64
                or any(c not in '0123456789abcdef' for c in value) or value in indexed):
            raise ValueError('Invalid or duplicate frozen input fingerprint')
        wire = row.get('wire_sha256')
        if (not isinstance(wire, str) or len(wire) != 64
                or any(c not in '0123456789abcdef' for c in wire)):
            raise ValueError('Frozen raw wire SHA is required to preserve native option order')
        indexed[value] = row
    return indexed


def validate_frozen_wire(raw, body, allowed):
    key = request_fingerprint(body)
    if key not in allowed or digest(raw) != allowed[key]['wire_sha256']:
        raise ValueError('Request content/order differs from the frozen full wire body')
    return key


def validate_resource_group(lease, registrations, actual_identities, compute):
    """No same-user-but-unrelated process is admitted; stale PIDs cannot suffice."""
    cards = {int(g['index']): g['uuid'] for g in lease['gpu']}
    if sorted(cards) != list(PHYSICAL_GPUS):
        raise ValueError('Lease does not cover exactly physical GPUs4-7')
    expected = {}
    roles = set()
    for registration in registrations:
        pid = registration['identity']['pid']
        if registration['role'] not in {'primary', FLASH} or pid in expected or registration['role'] in roles:
            raise ValueError('Unexpected/duplicate worker registration')
        if registration['identity']['uid'] != 1033:
            raise ValueError('Worker UID mismatch')
        actual = actual_identities.get(pid)
        if actual is None or not identity_matches(actual, registration['identity']):
            raise ValueError('Worker identity is stale or command differs')
        expected[pid] = registration['role']
        roles.add(registration['role'])
    owned_uuids = set(cards.values())
    for row in compute:
        if row['uuid'] not in owned_uuids:
            continue
        if row['pid'] not in expected:
            raise ValueError('Unrelated compute process entered task GPU')
        if expected[row['pid']] == FLASH and row['uuid'] != cards[7]:
            raise ValueError('Flash process escaped its one authorized device')
    return {'exclusive_task_group': True, 'actual_allowed_pids': sorted(expected),
            'physical_gpu_uuids': cards}


def validate_actor(body):
    if (set(body) != {'operation', 'body'} or body['operation'] != 'actor'
            or body['body'].get('max_tokens') != 2048
            or body['body'].get('temperature') != 0
            or body['body'].get('chat_template_kwargs') != {'enable_thinking': False}):
        raise ValueError('Actor original2048/nonthinking/greedy contract mismatch')


def validate_decision(body):
    if (not isinstance(body['state'], (str, dict, list)) or not isinstance(body['question'], str)
            or not isinstance(body['options'], dict) or not 2 <= len(body['options']) <= 255):
        raise ValueError('Expected one native choice question')
    if any(not isinstance(k, str) or not isinstance(v, (str, type(None)))
           for k, v in body['options'].items()):
        raise ValueError('Invalid option names/descriptions')


def validate_observation(body, contract):
    expected_keys = {'request_id', 'image_base64', 'image_sha256', 'state', 'questions', 'provenance'}
    if set(body) != expected_keys:
        raise ValueError('Image-only observer cannot receive task/history/candidate/extra keys')
    if (body['state'] != contract['state'] or body['questions'] != contract['questions']
            or list(body['questions']) != list(contract['questions']) or len(body['questions']) != 3):
        raise ValueError('Observer instructions/questions must be the fixed ordered neutral contract')
    provenance = body['provenance']
    if (set(provenance) != {'observation_id', 'image_sha256'}
            or provenance['image_sha256'] != body['image_sha256']
            or not isinstance(provenance['observation_id'], str)):
        raise ValueError('Observer provenance contains extra context or wrong image identity')
    for question in body['questions'].values():
        if set(question) != {'type', 'instructions', 'criteria'} or question['type'] != 'choice':
            raise ValueError('Observer requires exactly three native choice questions')
        validate_decision({'state': body['state'], 'question': question['instructions'],
                           'options': question['criteria']})


def validate_probabilities(probabilities, options, answer):
    if (set(probabilities) != set(options) or answer not in probabilities
            or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1
                   for v in probabilities.values())
            or abs(sum(probabilities.values()) - 1) > 1e-5
            or probabilities[answer] < max(probabilities.values())):
        raise ValueError('Native choice result violates probability contract')

