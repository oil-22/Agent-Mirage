"""Read-only logical-terminal provenance checks; never creates semantic labels."""
import base64
import hashlib
import json


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf8')


def events_from_bytes(raw, *, live_prefix=False):
    incomplete = bool(raw and not raw.endswith(b'\n'))
    require(live_prefix or not incomplete, 'A terminal GUI journal cannot have an uncommitted final line')
    committed = raw[:raw.rfind(b'\n') + 1] if incomplete else raw
    previous, events = '0' * 64, []
    for line in committed.splitlines():
        event = json.loads(line)
        signature = event.pop('sha256')
        require(event['seq'] == len(events) and event['previous'] == previous,
                'Journal sequence or previous digest mismatch')
        require(digest(canonical(event)) == signature, 'Journal event digest mismatch')
        event['sha256'] = signature
        events.append(event)
        previous = signature
    return events, dict(events=len(events), head=previous, complete_prefix_bytes=len(committed),
        complete_prefix_sha256=digest(committed), incomplete_last_line=incomplete)


def unreviewed_candidates(events, reviewed_event_hashes):
    require(all(isinstance(value, str) and len(value) == 64 for value in reviewed_event_hashes),
            'Original candidate-event hashes required, not shortened IDs or text hashes')
    return [event['sha256'] for event in events if event['kind'] == 'candidate'
            and event['sha256'] not in reviewed_event_hashes]


def run_end_binding(events, run_id, terminal_sha):
    request = response_raw = response = None
    for event in events:
        if event['kind'] == 'online_run_end_request':
            request, response_raw, response = event, None, None
        elif event['kind'] == 'online_run_end_raw_response':
            response_raw = event
        elif event['kind'] == 'online_run_end_response':
            response = event
    if response is None:
        return None
    require(request is not None and response_raw is not None, 'Run-end response lacks original request/raw response')
    data, original = request['data'], response_raw['data']
    body, reply = data['body'], response['data']['body']
    raw = base64.b64decode(original['raw_base64'], validate=True)
    require(data['path'] == '/end' and body['trajectory_id'] == run_id, 'Run end belongs to another trajectory')
    require(body['terminal_receipt_sha256'] == terminal_sha, 'Run end is bound to a different terminal')
    require(digest(canonical(body)) == data['wire_sha256'] == reply['external_wire_sha256'], 'Run-end request wire mismatch')
    require(original['http_status'] == 200 and digest(raw) == original['raw_sha256'] and json.loads(raw) == reply,
            'Run-end original HTTP response mismatch')
    require(reply['request_id'] == body['request_id'] and reply['accepted'] is True, 'Run end not actually acknowledged')
    require(body['status'] in ['completed', 'technical_failure', 'stopped'], 'Unrecognized original run-end status')
    return dict(body=body, request_event_sha256=request['sha256'],
        response_event_sha256=response['sha256'], raw_response_event_sha256=response_raw['sha256'])


def check_terminal_counters(value, planned, carryover):
    require(value['run'] == planned and value['observer_enabled'] is planned['observer_enabled'],
            'Terminal frozen task/condition/arm differs')
    require(value['step_cap'] == 50 and value['diagnostic_only'] is False, 'Not the original full GUI setting')
    for field, maximum in [('decisions', 50), ('environment_actions', 50), ('actor_calls', 70),
                           ('verifier_calls', 140), ('auxiliary_calls', 60)]:
        require(type(value[field]) is int and 0 <= value[field] <= maximum, 'Original budget changed: ' + field)
    require(value['auxiliary_cap'] == 60, 'Auxiliary budget changed')
    require(planned['observer_enabled'] or value['auxiliary_calls'] == 0, 'Noaux arm performed auxiliary inference')
    linked = planned['run_id'] == carryover['original_track']
    require(value['technical_continuation_of_original23'] is linked, 'Original continuation identity lost')
    for field, expected in [('original_prefix_actions_carried', 16), ('original_prefix_actor_calls_carried', 17),
                            ('original_prefix_judge_calls_carried_including_OOM_and26_and31', 50)]:
        require(value[field] == (expected if linked else 0), 'Original technical attempt expenditure lost: ' + field)
    if value['scoring_status'] == 'complete':
        require(value['official_reward'] in [0.0, 1.0] and type(value['official_reward']) in [int, float],
                'Official scoring result is not original binary reward')
    else:
        require(value['official_reward'] is None, 'Unavailable scoring cannot become model zero')
    return dict(original_native_budgets_retained=True, original_technical_prefix_expenditure_retained=linked,
        semantic_Mirage_not_inferred_from_terminal_or_official_reward=True)
