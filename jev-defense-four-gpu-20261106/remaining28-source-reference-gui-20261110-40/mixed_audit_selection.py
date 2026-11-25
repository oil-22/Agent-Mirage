"""Read-only selection across mixed requests and complete GUI journal prefixes."""
import hashlib
import json
import re

from mixed_journal_map import canonical, require


def select_completed_requests(mapping, requested):
    rows = mapping['sealed_requests']
    indexed = {row['request']: (i, row) for i, row in enumerate(rows)}
    require(bool(requested) and len(requested) == len(set(requested)), 'Unique completed request IDs required')
    wanted = set(requested)
    for ident in requested:
        require(re.fullmatch(r'\d{4,}', ident) is not None and ident in indexed,
                'Requested reply is not sealed: ' + ident)
        pos, row = indexed[ident]
        if row['operation'] == 'evidence':
            require(pos + 1 < len(rows), 'Following actor is not sealed; evidence insertion remains pending')
            actor = rows[pos + 1]
            require(actor['operation'] == 'actor' and actor['trajectory_id'] == row['trajectory_id']
                    and actor['decision'] == row['decision'], 'Auxiliary is not followed by its own actor')
            wanted.add(actor['request'])
        elif row['operation'] == 'actor' and pos:
            prior = rows[pos - 1]
            if prior['operation'] == 'evidence':
                require(prior['trajectory_id'] == row['trajectory_id'] and prior['decision'] == row['decision'],
                        'Actor follows auxiliary from another decision/run')
                wanted.add(prior['request'])
    selected = []
    for ident in sorted(wanted, key=int):
        pos, row = indexed[ident]
        result = dict(row)
        result['preceding_auxiliary_request'] = None
        result['prior_evidence_calls_in_this_track'] = max(
            [0] + [r['original_track_attempt_index'] for r in rows[:pos]
                   if r['trajectory_id'] == row['trajectory_id'] and r['operation'] == 'evidence'])
        if row['operation'] == 'actor' and pos and rows[pos - 1]['operation'] == 'evidence':
            result['preceding_auxiliary_request'] = rows[pos - 1]['request']
        selected.append(result)
    return selected


def collect_GUI_prefix(stream, wanted_request_ids):
    """Verify every complete original event before selecting its HTTP/window."""
    previous, count, complete_bytes = '0' * 64, 0, 0
    prefix_sha = hashlib.sha256()
    partial = b''
    http, windows, in_flight, current = {}, {}, {}, []
    observer_kinds = {'neutral_evidence_request', 'neutral_evidence_raw_reply',
                      'neutral_evidence_failure', 'neutral_evidence_packet',
                      'neutral_evidence_actor_insertion'}
    for raw in stream:
        if not raw.endswith(b'\n'):
            partial = raw
            break
        event = json.loads(raw)
        core = dict(event)
        signature = core.pop('sha256')
        require(event['seq'] == count and event['previous'] == previous
                and hashlib.sha256(canonical(core)).hexdigest() == signature,
                'Broken original GUI event prefix')
        count += 1
        complete_bytes += len(raw)
        prefix_sha.update(raw)
        previous = signature
        kind, data = event['kind'], event['data']
        if kind == 'actor_request':
            current = [event]
        elif current and (kind in observer_kinds or kind.startswith('actual_evidence_wire_')):
            current.append(event)
        for operation in ['actor', 'judge', 'evidence']:
            prefix = 'actual_' + operation + '_wire_'
            if not kind.startswith(prefix):
                continue
            suffix = kind[len(prefix):]
            require(suffix in ['request', 'raw_response', 'response'], 'Unknown actual HTTP event')
            if suffix == 'request':
                require(operation not in in_flight, 'Interleaved HTTP exchange')
                ident = data['body']['request_id']
                in_flight[operation] = ident
                if ident in wanted_request_ids:
                    require(ident not in http, 'Duplicate selected HTTP request')
                    http[ident] = {'request': event}
                    if operation == 'actor':
                        require(bool(current), 'Actor context absent from original GUI prefix')
                        windows[ident] = list(current)
            else:
                require(operation in in_flight, 'HTTP response without original request')
                ident = in_flight[operation]
                if ident in wanted_request_ids:
                    require(suffix not in http[ident], 'Repeated selected HTTP response')
                    http[ident][suffix] = event
                if suffix == 'response':
                    require(data['body']['request_id'] == ident, 'Different response request ID')
                    del in_flight[operation]
    return dict(http=http, actor_windows=windows,
                prefix=dict(events=count, head=previous, complete_prefix_bytes=complete_bytes,
                            complete_prefix_sha256=prefix_sha.hexdigest(),
                            incomplete_tail_bytes=len(partial),
                            incomplete_tail_sha256=hashlib.sha256(partial).hexdigest() if partial else None))
