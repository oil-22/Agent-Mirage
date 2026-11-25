"""Synthetic CPU transport/counter boundaries, not real model/GUI controls."""
import base64
import copy
import json
import unittest

from logical_terminal_checks import (canonical, check_terminal_counters, digest,
    events_from_bytes, run_end_binding, unreviewed_candidates)


def journal(entries):
    events, previous = [], '0' * 64
    for kind, data in entries:
        row = dict(seq=len(events), previous=previous, time=1.0, kind=kind, data=data)
        row['sha256'] = digest(canonical(row))
        previous = row['sha256']
        events.append(row)
    return b''.join(canonical(row) + b'\n' for row in events)


def end_events():
    body = dict(trajectory_id='original-run', request_id='a' * 32, status='completed',
                terminal_receipt_sha256='b' * 64)
    reply = dict(request_id=body['request_id'], external_wire_sha256=digest(canonical(body)), accepted=True)
    raw = canonical(reply)
    return events_from_bytes(journal([
        ('online_run_end_request', dict(path='/end',body=body,wire_sha256=digest(canonical(body)))),
        ('online_run_end_raw_response',dict(http_status=200, raw_base64=base64.b64encode(raw).decode(),raw_sha256=digest(raw))),
        ('online_run_end_response',dict(body=reply))]))[0]


def terminal():
    plan = dict(run_id='original-run', observer_enabled=False)
    carry = dict(original_track='original-run')
    value = dict(run=plan, observer_enabled=False, step_cap=50, diagnostic_only=False, decisions=37,
        environment_actions=36, actor_calls=38, verifier_calls=140, auxiliary_calls=0, auxiliary_cap=60,
        technical_continuation_of_original23=True, original_prefix_actions_carried=16,
        original_prefix_actor_calls_carried=17, original_prefix_judge_calls_carried_including_OOM_and26_and31=50,
        scoring_status='complete', official_reward=0.0)
    return value, plan, carry


class LogicalTerminalControls(unittest.TestCase):
    def test_original_chain(self):
        rows, proof = events_from_bytes(journal([('candidate', {'text':'original'})]))
        self.assertEqual(proof['events'],1)
        self.assertEqual(proof['head'],rows[0]['sha256'])

    def test_tampered_chain(self):
        raw=journal([('candidate', {'text':'original'})]).replace(b'original',b'changed')
        with self.assertRaises(ValueError): events_from_bytes(raw)

    def test_incomplete_terminal_line_rejected(self):
        with self.assertRaises(ValueError): events_from_bytes(journal([('candidate', {})])+b'{')

    def test_live_service_prefix_retains_partial_line_disclosure(self):
        _,proof=events_from_bytes(journal([('model_request', {})])+b'{',live_prefix=True)
        self.assertEqual(proof['events'],1)
        self.assertTrue(proof['incomplete_last_line'])

    def test_source_gate_uses_full_original_event_hashes(self):
        rows,_=events_from_bytes(journal([('candidate', {}),('carryover_replay_candidate',{})]))
        self.assertEqual(unreviewed_candidates(rows,set()),[rows[0]['sha256']])
        self.assertEqual(unreviewed_candidates(rows,{rows[0]['sha256']}),[])
        with self.assertRaises(ValueError): unreviewed_candidates(rows,{rows[0]['sha256'][:20]})

    def test_end_acknowledgement_binds_original_terminal(self):
        proof=run_end_binding(end_events(),'original-run','b'*64)
        self.assertEqual(proof['body']['status'],'completed')

    def test_end_wrong_trajectory_or_terminal_rejected(self):
        for run,sha in [('foreign-run','b'*64),('original-run','c'*64)]:
            with self.subTest(run=run,sha=sha), self.assertRaises(ValueError):
                run_end_binding(end_events(),run,sha)

    def test_end_unacknowledged_is_pending_not_completed(self):
        self.assertIsNone(run_end_binding(end_events()[:-1],'original-run','b'*64))

    def test_end_original_wire_bytes_required(self):
        rows=end_events();rows[1]['data']['raw_base64']=base64.b64encode(b'{}').decode()
        with self.assertRaises(ValueError): run_end_binding(rows,'original-run','b'*64)

    def test_original_counters_include_carried_technical_calls(self):
        v,p,c=terminal()
        self.assertTrue(check_terminal_counters(v,p,c)['original_technical_prefix_expenditure_retained'])
        v['original_prefix_judge_calls_carried_including_OOM_and26_and31']=48
        with self.assertRaises(ValueError): check_terminal_counters(v,p,c)

    def test_budget_or_noaux_changes_rejected(self):
        for field,value in [('actor_calls',71),('verifier_calls',141),('auxiliary_calls',1),('step_cap',49)]:
            v,p,c=terminal();v[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError): check_terminal_counters(v,p,c)

    def test_scoring_failure_never_model_zero(self):
        v,p,c=terminal();v.update(scoring_status='failed',official_reward=None)
        check_terminal_counters(v,p,c)
        v['official_reward']=0
        with self.assertRaises(ValueError): check_terminal_counters(v,p,c)


if __name__=='__main__': unittest.main(verbosity=2)
