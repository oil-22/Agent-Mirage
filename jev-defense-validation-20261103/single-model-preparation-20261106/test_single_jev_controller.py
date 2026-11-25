"""CPU contract fixtures only; these tests cannot establish semantic accuracy."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'release'))
from defense.core import (Controller, Journal, Limits, BudgetExhausted,
                          ValidationError, canonical, digest)
from jev_auxiliary import JevAuxiliary
from test_jev_cued_controller import Client, view, screen, verdict
from single_jev_controller import (SingleJevAuxiliary, SingleJevController,
                                   CUE_RULES, POLICY, MODEL, REVISION,
                                   cue_packet, from_config)


class SingleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.n = 0

    def tearDown(self):
        self.tmp.cleanup()

    def ctl(self, judge, client=None, cap=60, limits=None):
        self.n += 1
        return SingleJevController(judge, Journal(self.root / str(self.n)),
            'post_only', limits or Limits(), sleeper=lambda _: None,
            jev_auxiliary=SingleJevAuxiliary([client or Client(MODEL)], cap))

    def rows(self, v, model=MODEL):
        self.n += 1
        return JevAuxiliary([Client(model)]).observe('verify', v, None,
                                                    Journal(self.root / str(self.n)))

    def test_constructor_rejects_style_two_clients_and_expanded_budget(self):
        for clients in [[], [Client('jev_style')], [Client(MODEL), Client(MODEL)],
                        [Client(MODEL), Client('jev_style')]]:
            with self.assertRaises(ValueError):
                SingleJevAuxiliary(clients)
        for cap in [61, -1, True]:
            with self.assertRaises(ValueError):
                SingleJevAuxiliary([Client(MODEL)], cap)

    def test_factory_pins_one_model_revision_budget(self):
        base = json.loads((ROOT / 'integration-config.staged.json').read_bytes())
        for edit in [dict(services=[{'model': 'jev_style', 'url': 'http://127.0.0.1:18221'}]),
                     dict(services=base['services'] * 2), dict(selected_revision='wrong'),
                     dict(max_auxiliary_calls=61), dict(policy='jev-cued-judge-v1')]:
            self.n += 1
            path = self.root / (str(self.n) + '.json')
            path.write_text(json.dumps(dict(base, **edit)))
            with self.assertRaises(ValueError):
                from_config(path, lambda *_: {}, Journal(self.root / ('j' + str(self.n))))
        c = from_config(ROOT / 'integration-config.staged.json', lambda *_: {},
                        Journal(self.root / 'valid'))
        self.assertEqual([x.model for x in c.jev_auxiliary.clients], [MODEL])
        self.assertEqual(c.jev_auxiliary.calls, 0)

    def test_style_predictions_never_reach_prompt_packet(self):
        v = view()
        out = cue_packet(self.rows(v) + self.rows(v, 'jev_style'), v, 'verify')
        self.assertEqual({x['model'] for x in out['observations']}, {MODEL})
        self.assertEqual(len(out['excluded']), 3)
        self.assertTrue(all(x['reason'] == 'single_model_policy_excludes_model'
                            for x in out['excluded']))
        self.assertFalse(out['ensemble'])
        self.assertFalse(out['agreement_assessed'])

    def test_identity_and_current_frame_binding_remain_strict(self):
        v = view()
        row = self.rows(v)[:1]
        for section, key in [('source', 'image_sha256'), ('source', 'observation_id'),
                             ('source', 'full_public_view_sha256'), ('result', 'revision')]:
            bad = copy.deepcopy(row)
            bad[0][section][key] = 'wrong'
            self.assertFalse(cue_packet(bad, v, 'verify')['observations'])
        self.assertFalse(cue_packet(row, view(reference=True), 'verify')['observations'])

    def test_normal_action_not_blocked_by_negative_single_prediction(self):
        c = self.ctl(lambda s, v, p: verdict(v),
                     Client(MODEL, {'readability': 'blank', 'suit_presence': 'none_visible'}))
        out = c.decide(view(), lambda *_: 'CLICK', lambda _: {'name': 'click'}, None)
        self.assertEqual(out['status'], 'accepted')
        self.assertEqual(out['candidate'], 'CLICK')

    def test_wrong_action_not_released_by_positive_single_prediction(self):
        c = self.ctl(lambda s, v, p: verdict(v, 'contradicted'),
                     Client(MODEL, {'suit_presence': 'visible'}),
                     limits=Limits(max_regenerations=0))
        out = c.decide(view(), lambda *_: 'WRONG', lambda _: {'name': 'click'}, None)
        self.assertEqual(out['status'], 'blocked')

    def test_native_wait_and_noop_make_zero_auxiliary_calls(self):
        for name in ['wait', 'noop']:
            c = self.ctl(lambda s, v, p: verdict(v, wait=True))
            c.inspect('verify', view(), name, {'name': name, 'parsed': True,
                                              'executor_fallback_wait': False})
            self.assertEqual(c.jev_auxiliary.calls, 0)

    def test_auxiliary_failure_uses_original_system_without_retry(self):
        seen = []
        c = self.ctl(lambda s, v, p: seen.append(s) or screen(v), Client(MODEL, fail=True))
        c.inspect('screen', view())
        c.inspect('screen', view())
        self.assertEqual(c.jev_auxiliary.calls, 1)
        self.assertTrue(all(CUE_RULES not in s for s in seen))
        self.assertEqual(c.verifier_calls, 2)

    def test_auxiliary_cap_and_primary_cap_fallback(self):
        c = self.ctl(lambda s, v, p: screen(v), cap=0)
        self.assertEqual(c.inspect('screen', view())['status'], 'usable')
        self.assertEqual(c.jev_auxiliary.calls, 0)
        c = self.ctl(lambda *_: self.fail('primary called'),
                     limits=Limits(max_verifier_calls=0))
        with self.assertRaises(BudgetExhausted):
            c.inspect('screen', view())
        self.assertEqual(c.jev_auxiliary.calls, 0)

    def test_full_public_candidate_and_main_call_count_unchanged(self):
        v = view()
        v.messages.extend([{'role': 'assistant', 'content': 'legal history ' * 1000}] * 43)
        before = canonical(v.data())
        seen = []
        c = self.ctl(lambda s, v, p: seen.append((s, canonical(v.data()), p)) or screen(v))
        c.inspect('screen', v)
        self.assertEqual(canonical(v.data()), before)
        self.assertEqual(seen[0][1], before)
        self.assertIn(CUE_RULES, seen[0][0])
        self.assertEqual(c.verifier_calls, 1)
        self.assertEqual(c.jev_auxiliary.calls, 1)

    def test_strict_validator_original_retry_and_cache(self):
        n = 0
        def judge(s, v, p):
            nonlocal n
            n += 1
            return {} if n == 1 else screen(v)
        c = self.ctl(judge)
        c.inspect('screen', view())
        self.assertEqual(c.verifier_calls, 2)
        self.assertEqual(c.jev_auxiliary.calls, 1)
        c = self.ctl(lambda *_: {}, limits=Limits(max_format_retries=0))
        with self.assertRaises(ValidationError):
            c.inspect('screen', view())

    def test_journal_has_no_one_model_agreement_claim_and_chain_verifies(self):
        c = self.ctl(lambda s, v, p: screen(v))
        c.inspect('screen', view())
        previous = '0' * 64
        events = []
        for line in (c.log.root / 'events.jsonl').read_text().splitlines():
            event = json.loads(line)
            h = event.pop('sha256')
            self.assertEqual(event['previous'], previous)
            self.assertEqual(digest(canonical(event)), h)
            previous = h
            events.append(event)
        self.assertFalse(any(e['kind'] == 'jev_auxiliary_comparison' for e in events))
        summary = next(e['data'] for e in events
                       if e['kind'] == 'jev_single_model_observation_summary')
        self.assertFalse(summary['ensemble'])
        self.assertFalse(summary['agreement_assessed'])
        packet = next(e['data'] for e in events if e['kind'] == 'jev_cue_policy')
        self.assertEqual(packet['policy'], POLICY)
        request = next(e['data'] for e in events if e['kind'] == 'jev_cued_verifier_request')
        self.assertEqual(digest(request['actual_system'].encode()), request['actual_system_sha256'])
        self.assertFalse(request['direct_verdict_override'])

    def test_native_controller_decide_accept_and_original_limits_unchanged(self):
        self.assertIs(SingleJevController.decide, Controller.decide)
        self.assertIs(SingleJevController.accept, Controller.accept)
        self.assertEqual((Limits().max_actor_calls, Limits().max_verifier_calls,
                          Limits().max_recaptures, Limits().max_regenerations,
                          Limits().max_format_retries), (70, 140, 2, 2, 1))


if __name__ == '__main__':
    unittest.main()
