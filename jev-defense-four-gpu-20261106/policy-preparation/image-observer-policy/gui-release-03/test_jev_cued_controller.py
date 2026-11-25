"""Behavioral protocol checks with scripted primary replies; not model accuracy."""
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image

from defense.core import (Controller, Journal, Limits, PublicView, VisibleImage,
                          ValidationError, BudgetExhausted, canonical, digest)
from jev_auxiliary import JevAuxiliary, QUESTIONS, REVISIONS
from jev_cued_controller import JevCuedController, cue_packet, CUE_RULES


def view(name='now', reference=False):
    raw = io.BytesIO()
    Image.new('RGB', (80, 60), 'white').save(raw, format='PNG')
    return PublicView(name, [{'role': 'user', 'content': 'Full unchanged task/history'}],
                      (VisibleImage(raw.getvalue(), 'reference' if reference else 'current'),))


def evidence(v):
    return {'observation_id': v.observation_id, 'image_index': 0,
            'coordinate_space': 'pixels', 'box_xyxy': [0, 0, 80, 60],
            'description': 'Scripted fixture; not semantic evidence'}


def screen(v):
    return {'status': 'usable', 'visible': ['fixture'], 'limitations': [],
            'loading': 'not_observed', 'reason': 'fixture', 'evidence': [evidence(v)]}


def verdict(v, status='supported', wait=False):
    return {'claims': [], 'action': {'status': status, 'target_kind': 'button',
            'reason': 'fixture', 'evidence': [evidence(v)]},
            'pure_wait': wait, 'acknowledges_visual_deficit': False}


class Client:
    def __init__(self, model='jev_style', choices=None, fail=False):
        self.model = model
        self.choices = choices or {}
        self.fail = fail
        self.calls = 0

    def decide(self, im, key, provenance):
        self.calls += 1
        if self.fail:
            raise RuntimeError('test transport failure')
        answer = self.choices.get(key, 'unknown')
        return {'model': self.model, 'revision': REVISIONS[self.model],
                'image_sha256': digest(im.raw), 'answer': answer,
                'probabilities': {k: float(k == answer) for k in QUESTIONS[key][1]}}


class CuedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.seq = 0

    def tearDown(self):
        self.temp.cleanup()

    def ctl(self, judge, clients=None, limits=None, arm='post_only', cap=60):
        self.seq += 1
        return JevCuedController(judge, Journal(self.root / str(self.seq)), arm,
                                 limits or Limits(), jev_auxiliary=JevAuxiliary(
                                     clients or [Client()], cap), sleeper=lambda _: None)

    def rows(self, v=None):
        v = v or view()
        self.seq += 1
        return JevAuxiliary([Client()]).observe('verify', v, {'name': 'click'},
                                                Journal(self.root / str(self.seq)))

    def test_valid_cues_change_only_system_not_full_input_or_verdict(self):
        v = view()
        v.messages.extend({'role': 'assistant', 'content': 'history ' * 1000} for _ in range(43))
        before = canonical(v.data())
        seen = []
        def judge(s, obs, c):
            seen.append((s, canonical(obs.data()), c))
            return screen(obs)
        base = Controller(judge, Journal(self.root / 'base'))
        expected = base.inspect('screen', v)
        original = seen[-1]
        c = self.ctl(judge)
        self.assertEqual(c.inspect('screen', v), expected)
        self.assertTrue(seen[-1][0].startswith(original[0]))
        self.assertIn(CUE_RULES, seen[-1][0])
        self.assertEqual(seen[-1][1:], original[1:])
        self.assertEqual(c.verifier_calls, base.verifier_calls)
        self.assertEqual(canonical(v.data()), before)

    def test_normal_action_not_blocked_by_negative_auxiliary(self):
        clients = [Client(choices={'readability': 'blank', 'keyword_focus': 'absent',
                                   'suit_presence': 'none_visible'})]
        c = self.ctl(lambda s, v, p: verdict(v), clients)
        out = c.decide(view(), lambda *_: 'CLICK', lambda _: {'name': 'click'}, None)
        self.assertEqual(out['status'], 'accepted')
        self.assertEqual(out['candidate'], 'CLICK')

    def test_wrong_action_not_released_by_auxiliary_agreement(self):
        clients = [Client(m, {'readability': 'coherent', 'keyword_focus': 'present',
                             'suit_presence': 'visible'}) for m in REVISIONS]
        c = self.ctl(lambda s, v, p: verdict(v, 'contradicted'), clients,
                     Limits(max_regenerations=0))
        out = c.decide(view(), lambda *_: 'WRONG', lambda _: {'name': 'click'}, None)
        self.assertEqual(out['status'], 'blocked')
        self.assertEqual(out['reason'], 'regeneration_cap')

    def test_native_wait_candidate_has_zero_auxiliary_calls(self):
        c = self.ctl(lambda s, v, p: verdict(v, wait=True))
        p = {'name': 'wait', 'parsed': True, 'executor_fallback_wait': False}
        out = c.decide(view(), lambda *_: 'WAIT', lambda _: p, None)
        self.assertEqual(out['status'], 'accepted')
        self.assertEqual(c.jev_auxiliary.calls, 0)

    def test_fallback_wait_not_treated_as_native_wait(self):
        p = {'name': 'wait', 'parsed': False, 'executor_fallback_wait': True}
        # Historical shadow collector skips this name; policy never calls it a
        # successful native-WAIT control. Original strict parser check remains.
        self.assertNotEqual(cue_packet([], view(), 'verify', p).get('reason'),
                            'excluded_phase_or_native_wait')

    def test_native_noop_has_zero_auxiliary_calls(self):
        c = self.ctl(lambda s, v, p: verdict(v, wait=True))
        c.inspect('verify', view(), 'NOOP', {'name': 'noop', 'parsed': True})
        self.assertEqual(c.jev_auxiliary.calls, 0)

    def test_failed_auxiliary_falls_back_to_original_strict_judge(self):
        seen = []
        c = self.ctl(lambda s, v, p: seen.append(s) or screen(v), [Client(fail=True)])
        self.assertEqual(c.inspect('screen', view())['status'], 'usable')
        self.assertNotIn(CUE_RULES, seen[-1])
        c.inspect('screen', view())
        self.assertEqual(c.jev_auxiliary.calls, 1)

    def test_exhaustion_neither_auto_accepts_nor_auto_rejects(self):
        c = self.ctl(lambda s, v, p: screen(v), cap=0)
        self.assertEqual(c.inspect('screen', view())['status'], 'usable')
        self.assertEqual(c.jev_auxiliary.calls, 0)

    def test_primary_budget_exhaustion_prevents_auxiliary_calls(self):
        c = self.ctl(lambda *_: self.fail('primary called'), limits=Limits(max_verifier_calls=0))
        with self.assertRaises(BudgetExhausted):
            c.inspect('screen', view())
        self.assertEqual(c.jev_auxiliary.calls, 0)

    def test_strict_invalid_reply_is_not_fixed_by_cues(self):
        c = self.ctl(lambda *_: {}, limits=Limits(max_format_retries=0))
        with self.assertRaises(ValidationError):
            c.inspect('screen', view())
        self.assertEqual(c.verifier_calls, 1)

    def test_original_format_retry_limit_and_cached_auxiliary(self):
        n = 0
        def judge(s, v, p):
            nonlocal n
            n += 1
            return {} if n == 1 else screen(v)
        c = self.ctl(judge)
        c.inspect('screen', view())
        self.assertEqual(c.verifier_calls, 2)
        self.assertEqual(c.jev_auxiliary.calls, 1)

    def test_reference_frame_is_never_current_cue(self):
        v = view(reference=True)
        rows = self.rows(view())
        self.assertFalse(cue_packet(rows, v, 'verify')['observations'])

    def test_wrong_image_revision_observation_and_public_are_excluded(self):
        v = view()
        rows = self.rows(v)
        edits = [('source', 'image_sha256'), ('source', 'observation_id'),
                 ('source', 'full_public_view_sha256'), ('result', 'revision')]
        for section, key in edits:
            with self.subTest(key=key):
                bad = copy.deepcopy(rows[:1]);bad[0][section][key] = 'wrong'
                self.assertFalse(cue_packet(bad, v, 'verify')['observations'])

    def test_unbound_probabilities_rejected(self):
        v = view();rows = self.rows(v)
        for badp in [{'unknown': 1}, {k: float('nan') for k in QUESTIONS['readability'][1]}]:
            bad = copy.deepcopy(rows[:1]);bad[0]['result']['probabilities'] = badp
            self.assertFalse(cue_packet(bad, v, 'verify')['observations'])

    def test_duplicate_prediction_cannot_form_two_votes(self):
        v = view();rows = self.rows(v)
        packet = cue_packet(rows[:1] * 2, v, 'verify')
        self.assertEqual(len(packet['observations']), 1)
        self.assertEqual(len(packet['excluded']), 1)
        self.assertFalse(packet['agreement_is_truth'])

    def test_readability_not_sent_as_focus_evidence(self):
        v = view();rows = self.rows(v)
        packet = cue_packet(rows, v, 'focus')
        self.assertEqual([r['query'] for r in packet['observations']], ['keyword_focus'])

    def test_point_history_and_completion_have_no_cues(self):
        for phase in ['point', 'history_report', 'completion', 'alignment', 'absence_relation']:
            self.assertFalse(cue_packet(self.rows(), view(), phase)['observations'])

    def test_shared_none_visible_never_yields_absence_certificate(self):
        v = view();self.seq += 1
        clients = [Client(m, {'suit_presence': 'none_visible'}) for m in REVISIONS]
        rows = JevAuxiliary(clients).observe('person_read', v, None, Journal(self.root / str(self.seq)))
        packet = cue_packet(rows, v, 'person_read')
        self.assertEqual(len(packet['observations']), 2)
        self.assertFalse(packet['automatic_allow_or_block'])
        self.assertIn('proves neither local', CUE_RULES)

    def test_actual_augmented_request_is_in_hash_chain(self):
        c = self.ctl(lambda s, v, p: screen(v))
        c.inspect('screen', view())
        previous = '0' * 64;seen = False
        for line in (c.log.root / 'events.jsonl').read_text().splitlines():
            e = json.loads(line);h = e.pop('sha256')
            self.assertEqual(e['previous'], previous)
            self.assertEqual(digest(canonical(e)), h);previous = h
            if e['kind'] == 'jev_cued_verifier_request':
                seen = True
                self.assertEqual(digest(e['data']['actual_system'].encode()), e['data']['actual_system_sha256'])
                self.assertEqual(e['data']['additional_main_calls'], 0)
        self.assertTrue(seen)

    def test_failure_cleans_nested_inspection_context(self):
        c = self.ctl(lambda *_: {}, limits=Limits(max_format_retries=0))
        with self.assertRaises(ValidationError):c.inspect('screen', view())
        self.assertEqual(c._inspection_context, [])

    def test_advisory_use_is_not_mislabeled_as_shadow_only(self):
        c = self.ctl(lambda s, v, p: screen(v))
        c.inspect('screen', view())
        events = [json.loads(s) for s in (c.log.root / 'events.jsonl').read_text().splitlines()]
        row = next(e['data'] for e in events if e['kind'] == 'jev_auxiliary')
        self.assertEqual(row['policy'], 'jev-cued-judge-v1')
        self.assertFalse(row['directly_used_to_allow_or_block'])
        packet = next(e['data'] for e in events if e['kind'] == 'jev_cue_policy')
        self.assertTrue(packet['actually_in_primary_prompt'])

    def test_source_schema_and_recovery_caps_are_unchanged(self):
        self.assertEqual((Limits().max_actor_calls, Limits().max_verifier_calls,
                          Limits().max_recaptures, Limits().max_regenerations,
                          Limits().max_format_retries), (70, 140, 2, 2, 1))
        self.assertIs(JevCuedController.decide, Controller.decide)
        self.assertIs(JevCuedController.accept, Controller.accept)


if __name__ == '__main__':
    unittest.main()
