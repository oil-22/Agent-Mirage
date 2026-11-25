"""New selector integration controls; derived CPU data, never model trials."""
import copy
import io
import json
from pathlib import Path
import time

from check_mixed_exchange_audit import fixture
from mixed_audit_selection import collect_GUI_prefix, select_completed_requests
from mixed_journal_map import canonical
from orchestrate import HERE, save, sha


def main():
    pointer = HERE / 'mixed-audit-selection-controls-created.json'
    assert not pointer.exists()
    checks = []
    def passed(name):
        checks.append(name)
    def rejects(name, call):
        try:
            call()
        except (ValueError, KeyError, TypeError, IndexError):
            passed(name)
        else:
            raise AssertionError('Invalid selector binding accepted: ' + name)

    evidence = dict(request='9000', operation='evidence', trajectory_id='runA', decision=7,
                    original_track_attempt_index=2, primary_prefill_session=None)
    actor = dict(request='9001', operation='actor', trajectory_id='runA', decision=7,
                 original_track_attempt_index=8, primary_prefill_session=17)
    mapping = dict(sealed_requests=[evidence, actor])
    value = select_completed_requests(mapping, ['9001'])
    assert [row['request'] for row in value] == ['9000', '9001']
    assert value[1]['primary_prefill_session'] == 17 and value[1]['preceding_auxiliary_request'] == '9000'
    passed('mixed_global_ID_never_substitutes_primary_session_and_actor_includes_own_auxiliary')
    assert [r['request'] for r in select_completed_requests(mapping, ['9000'])] == ['9000', '9001']
    passed('auxiliary_selection_requires_its_following_completed_actor')
    rejects('auxiliary_without_completed_actor_remains_pending', lambda: select_completed_requests(
        dict(sealed_requests=[evidence]), ['9000']))
    different = copy.deepcopy(mapping)
    different['sealed_requests'][1]['decision'] = 8
    rejects('next_decision_actor_cannot_certify_this_insertion', lambda: select_completed_requests(different, ['9000']))
    different['sealed_requests'][1]['trajectory_id'] = 'runB'
    rejects('next_run_actor_cannot_certify_this_insertion', lambda: select_completed_requests(different, ['9001']))
    regenerated = copy.deepcopy(actor)
    regenerated.update(request='9002', original_track_attempt_index=9, primary_prefill_session=18)
    value = select_completed_requests(dict(sealed_requests=[evidence, actor, regenerated]), ['9002'])
    assert len(value) == 1 and value[0]['preceding_auxiliary_request'] is None
    assert value[0]['prior_evidence_calls_in_this_track'] == 2
    passed('same_decision_later_candidate_does_not_reuse_prior_candidates_auxiliary')
    rejects('duplicate_request_selection_rejected', lambda: select_completed_requests(mapping, ['9001', '9001']))
    rejects('unsealed_request_selection_rejected', lambda: select_completed_requests(mapping, ['9002']))

    # Read one existing control as source data, never regenerate it. Existing
    # primitive checks are not rerun or recounted as new visual observations.
    old = fixture(enabled=True)
    a, h = old['actor'], old['http']
    events = [a['context_event'], a['observer_request_event'], h['request_event'], h['raw_response_event'],
              h['response_event'], a['observer_raw_reply_event'], a['packet_event'], a['insertion_event'], a['actor_request_event']]
    actor_id = a['actor_request_event']['data']['body']['request_id']
    events += [dict(kind='actual_actor_wire_raw_response', data={'raw_base64': ''}),
               dict(kind='actual_actor_wire_response', data={'body': {'request_id': actor_id}})]

    def encode(values, tail=b''):
        result = []
        previous = '0' * 64
        for index, event in enumerate(values):
            core = {k: copy.deepcopy(v) for k, v in event.items() if k not in ['sha256', 'seq', 'previous']}
            core.update(seq=index, previous=previous)
            signature = __import__('hashlib').sha256(canonical(core)).hexdigest()
            result.append(canonical(dict(core, sha256=signature)) + b'\n')
            previous = signature
        return b''.join(result) + tail
    raw = encode(events)
    selected = collect_GUI_prefix(io.BytesIO(raw), {actor_id})
    assert set(selected['http'][actor_id]) == {'request', 'raw_response', 'response'}
    assert selected['actor_windows'][actor_id][0]['data']['public']['observation_id'] == 'fixture-obs1'
    passed('whole_original_GUI_prefix_selects_own_actor_context_and_three_HTTP_events')
    second = copy.deepcopy(events)
    second[0]['data']['public']['observation_id'] = 'fixture-obs2'
    for event in second:
        if event['kind'].endswith('_request') and event['kind'].startswith('actual_'):
            event['data']['body']['request_id'] = '3' * 32 if 'evidence' in event['kind'] else '4' * 32
        if event['kind'].endswith('_response') and not event['kind'].endswith('_raw_response'):
            event['data']['body']['request_id'] = '3' * 32 if 'evidence' in event['kind'] else '4' * 32
    selected = collect_GUI_prefix(io.BytesIO(encode(events + second)), {actor_id, '4' * 32})
    assert selected['actor_windows'][actor_id][0]['data']['public']['observation_id'] == 'fixture-obs1'
    assert selected['actor_windows']['4' * 32][0]['data']['public']['observation_id'] == 'fixture-obs2'
    passed('two_candidates_do_not_share_or_replace_their_original_actor_window')
    partial = collect_GUI_prefix(io.BytesIO(encode(events, b'{"pending":')), {actor_id})
    assert partial['prefix']['events'] == len(events) and partial['prefix']['incomplete_tail_bytes'] == 11
    passed('live_incomplete_last_line_is_explicitly_preserved_not_declared_terminal')
    altered = raw.replace(b'fixture-obs1', b'fixture-obs9', 1)
    rejects('changed_original_event_data_fails_prefix_SHA', lambda: collect_GUI_prefix(io.BytesIO(altered), {actor_id}))
    lines = raw.splitlines(keepends=True)
    broken = json.loads(lines[1]); broken['seq'] = 20
    rejects('changed_sequence_fails_full_prefix', lambda: collect_GUI_prefix(
        io.BytesIO(lines[0] + canonical(broken) + b'\n' + b''.join(lines[2:])), {actor_id}))
    rejects('response_without_original_request_rejected', lambda: collect_GUI_prefix(
        io.BytesIO(encode(events[-2:])), {actor_id}))
    duplicate = copy.deepcopy(events)
    rejects('duplicate_request_ID_in_same_prefix_rejected', lambda: collect_GUI_prefix(
        io.BytesIO(encode(events + duplicate)), {actor_id}))
    out = HERE / ('mixed-audit-selection-controls-' + str(time.time_ns()))
    out.mkdir()
    save(out / 'CPU-results.json', dict(passed=True, count=len(checks), checks=checks,
        synthetic_derived_selection_controls_not_new_model_GUI_or_semantic_controls=True))
    for name in ['mixed_audit_selection.py', 'mixed_audit_service.py', 'mixed_audit_GUI.py',
                 'audit_mixed_receipts_once.py', Path(__file__).name]:
        (out / name).write_bytes((HERE / name).read_bytes())
    save(out / 'receipt.json', dict(time=time.time(), passed=True, CPU_selection_checks=len(checks),
         actual_enabled_auxiliary_inference_observed=False, runtime_modified=False,
         new_model_GUI_scorer_calls=0, semantic_correctness_or_defense_efficacy_established=False))
    save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    result = dict(root=str(out), receipt_sha256=sha(out / 'receipt.json'), seal_sha256=sha(out / 'seal.json'))
    save(pointer, result)
    print(json.dumps(dict(result, passed=True, CPU_selection_checks=len(checks), new_model_GUI_calls=0)))


if __name__ == '__main__':
    main()
