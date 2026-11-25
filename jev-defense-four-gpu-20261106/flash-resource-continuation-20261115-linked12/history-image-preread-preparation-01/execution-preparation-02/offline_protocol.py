"""Finite, source-bound offline execution core; no model/GPU/browser imports.

The caller must supply actual resource admission and the audited native call.
This is not a resource launcher. No authorization is synthesized by this code.
"""
import copy
import hashlib
import json
import os
import time
from pathlib import Path

CASES = ['s%02d' % i for i in range(1, 11)]
PHASE_CAPS = {'preread': 4096, 'actor': 2048}
CONDITION = 'same-primary-history-image-preread-v1'
APPROVAL_ANSWER = '批准20次离线开发预检（推荐）'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf8')


def digest(value):
    return hashlib.sha256(value).hexdigest()


def require(value, message):
    if not value:
        raise RuntimeError(message)


def save(path, value):
    with Path(path).open('xb') as stream:
        stream.write(canonical(value))
        stream.flush()
        os.fsync(stream.fileno())


def seal(folder):
    save(folder / 'seal.json', {p.name: digest(p.read_bytes()) for p in folder.iterdir() if p.is_file()})


def validate_authorization(value, proposal_seal_sha256):
    require(value.get('authorized') is True, 'No human approval for this new condition')
    require(value.get('exact_answer') == APPROVAL_ANSWER, 'Approval is for a different scope')
    require(value.get('condition') == CONDITION, 'Different condition')
    require(value.get('proposal_seal_sha256') == proposal_seal_sha256, 'Approved proposal changed')
    require(value.get('new_primary_calls_cap') == 20 and value.get('phase_output_caps') == PHASE_CAPS,
            'Call/token budget changed')
    require(value.get('GUI_Flash_scorer_paid_calls') == value.get('automatic_retries') == 0,
            'Unapproved follow-on calls')
    require(value.get('formal_GUI_authorized') is False, 'Offline development only')
    require(value.get('source') == 'actual_human_reply' and value.get('human_reply_receipt_sha256'),
            'Real human reply receipt required; a CPU fixture is not authorization')


def run_offline(*, root, study_claim_root, authorization, proposal_seal_sha256, cases, contract,
                native_cpu_prepare, resource_admission, audited_native_call):
    """Run at most 10*(preread+actor), only with externally verified resources.

    Structural invalidity skips that case's actor; technical failures stop the
    whole attempt. Nothing retries, resumes, overwrites, or executes actions.
    """
    validate_authorization(authorization, proposal_seal_sha256)
    require([c['case_id'] for c in cases] == CASES, 'Unexpected source order or count')
    root = Path(root)
    study_claim_root = Path(study_claim_root)
    require(authorization.get('study_claim_root') == str(study_claim_root.resolve()) and
            root.resolve().parent == study_claim_root.resolve(), 'Unbound persistent study claim path')
    require(not root.exists(), 'Existing attempts are immutable')
    study_claim_root.mkdir(parents=True, exist_ok=True)
    save(study_claim_root / 'authorization-once.json', {
         'authorization_canonical_sha256': digest(canonical(authorization)),
         'proposal_seal_sha256': proposal_seal_sha256, 'one_attempt_root': str(root.resolve()),
         'maximum_new_calls_shared_by_this_authorization': 20, 'automatic_resume_or_retry': False})
    root.mkdir(exist_ok=False)
    (root / 'claims').mkdir()
    (root / 'cases').mkdir()
    save(root / 'authorization-used.json', authorization)
    save(root / 'protocol.json', {'condition': CONDITION, 'maximum_new_calls': 20,
         'phase_output_caps': PHASE_CAPS, 'baseline_replays': 0,
         'GUI_Flash_scorer_paid_calls': 0, 'automatic_retries': 0})
    attempted, completed, case_outcomes = [], [], []
    active = None
    chain = {'head': '0' * 64, 'events': 0}

    def emit(kind, data):
        value = {'seq': chain['events'], 'previous': chain['head'], 'time': time.time(),
                 'kind': kind, 'data': data}
        value['sha256'] = digest(canonical(value))
        with (root / 'journal.jsonl').open('ab') as stream:
            stream.write(canonical(value) + b'\n')
            stream.flush()
            os.fsync(stream.fileno())
        chain['events'] += 1
        chain['head'] = value['sha256']

    emit('attempt_started', {'proposal_seal_sha256': proposal_seal_sha256,
                             'authorization_canonical_sha256': digest(canonical(authorization))})

    def call(case, phase, body):
        nonlocal active
        cid = case['case_id']
        require(len(attempted) < 20 and phase in PHASE_CAPS, 'Call budget exhausted')
        require(body['max_tokens'] == PHASE_CAPS[phase] and body['temperature'] == 0,
                'Phase output budget or sampling changed')
        require(body.get('chat_template_kwargs', {}).get('enable_thinking') is False,
                'Native nonthinking condition changed')
        key = cid + '-' + phase
        require(key not in attempted, 'A phase may never be retried')
        if phase == 'actor':
            require(cid + '-preread' in completed, 'No complete preread for actor')
            require((root / 'cases' / cid / 'validated-reading.json').exists(), 'No source-valid reading')
        active = root / 'cases' / cid / phase
        active.mkdir(parents=True, exist_ok=False)
        save(active / 'body.bin', body)
        exact_body = json.loads((active / 'body.bin').read_bytes())
        expected = native_cpu_prepare(exact_body, active)
        save(active / 'native-CPU-before-inference.json', expected)
        admission = resource_admission(True)
        save(active / 'resource-before.json', admission)
        claim = {'ordinal': len(attempted) + 1, 'case_id': cid, 'phase': phase,
                 'body_file_sha256': digest((active / 'body.bin').read_bytes()),
                 'source_body_canonical_sha256': case['binding']['source_body_canonical_sha256'],
                 'CPU_preparation_sha256': digest((active / 'native-CPU-before-inference.json').read_bytes()),
                 'max_output_tokens': PHASE_CAPS[phase], 'technical_failure_consumes_this_claim': True}
        # A disk claim is written before entering the native call, even on failure.
        save(root / 'claims' / (key + '.json'), claim)
        attempted.append(key)
        emit('call_claimed', claim)
        result = audited_native_call(exact_body, active, expected, copy.deepcopy(case['original_effective_generation']),
                                     PHASE_CAPS[phase])
        save(active / 'native-returned.json', result)
        emit('native_returned', {'case_id': cid, 'phase': phase,
                                'raw_return_sha256': digest((active / 'native-returned.json').read_bytes())})
        require(result['natural_EOS'] is True and isinstance(result['text'], str), 'Incomplete native reply')
        require(result['model_generate_calls'] == 1 and result['first_forward_seen'] is True,
                'Unexpected native generation/forward accounting')
        save(active / 'resource-after.json', resource_admission(True))
        save(active / 'response.json', result)
        seal(active)
        emit('reply_sealed', {'case_id': cid, 'phase': phase, 'seal_sha256': digest((active / 'seal.json').read_bytes())})
        completed.append(key)
        active = None
        return result['text']

    failure = None
    try:
        for case in cases:
            cid, original, binding = case['case_id'], case['original_body'], case['binding']
            require(digest(canonical(original)) == binding['source_body_canonical_sha256'],
                    'Original complete body changed')
            projected, actual_binding = contract.project_source(original)
            require(actual_binding == binding and projected == case['preread_body'],
                    'Frozen preread input changed')
            reading = call(case, 'preread', projected)
            try:
                parsed = contract.validate_reading(reading, binding)
            except (ValueError, TypeError, KeyError) as exc:
                save(root / 'cases' / cid / 'invalid-reading.json',
                     {'error': str(exc), 'actor_called': False, 'not_a_semantic_zero': True,
                      'raw_reply_unchanged': True, 'no_retry': True})
                case_outcomes.append({'case_id': cid, 'status': 'reading_contract_invalid', 'actor_called': False})
                emit('reading_contract_invalid', {'case_id': cid, 'actor_called': False})
                continue
            save(root / 'cases' / cid / 'validated-reading.json',
                 {'reading_raw_UTF8_sha256': digest(reading.encode('utf8')), 'parsed': parsed,
                  'source_IDs_valid_only_not_visual_truth': True})
            emit('reading_source_structure_valid', {'case_id': cid, 'not_a_semantic_verdict': True,
                 'reading_validation_sha256': digest((root / 'cases' / cid / 'validated-reading.json').read_bytes())})
            actor_body = contract.attach_reading(original, reading, binding)
            call(case, 'actor', actor_body)
            case_outcomes.append({'case_id': cid, 'status': 'two_complete_replies',
                                  'actions_proposed_only': True, 'semantic_success': None})
    except BaseException as exc:
        failure = {'type': type(exc).__name__, 'message': str(exc), 'no_automatic_retry': True,
                   'infrastructure_or_contract_failure_not_semantic_zero': True}
        save(root / 'failure.json', failure)
        emit('preserved_failure', failure)
        if active is not None and not (active / 'seal.json').exists():
            save(active / 'failure.json', failure)
            seal(active)
    finally:
        terminal = {'status': 'completed' if failure is None else 'preserved_failure',
                    'attempted': attempted, 'completed': completed, 'case_outcomes': case_outcomes,
                    'maximum_calls': 20, 'extra_retries': 0, 'new_GUI_Flash_scorer_paid_calls': 0,
                    'all_replies_are_offline_not_executed': True, 'semantic_success': None,
                    'formal_GUI_release': False, 'failure': failure}
        emit('terminal', terminal)
        terminal['journal_chain'] = copy.deepcopy(chain)
        save(root / 'terminal.json', terminal)
    return terminal
