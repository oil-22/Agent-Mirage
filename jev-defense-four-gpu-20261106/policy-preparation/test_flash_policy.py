"""CPU control-flow fixtures, not visual accuracy or model inference."""
import copy
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image

from defense.core import (Controller, Journal, Limits, PublicView, VisibleImage,
                          BudgetExhausted, ValidationError, canonical, digest)
from flash_policy import (MODEL, REVISION, POLICY, QUESTIONS, FlashAuxiliary,
                          FlashCuedController, cue_packet, CUE_RULES, from_config)


def view():
    im = io.BytesIO(); Image.new('RGB', (80, 60), 'white').save(im, format='PNG')
    return PublicView('now', [{'role': 'user', 'content': 'Full unchanged task/history'}],
                      (VisibleImage(im.getvalue(), 'current'),))


def evidence(v):
    return {'observation_id': v.observation_id, 'image_index': 0,
            'coordinate_space': 'pixels', 'box_xyxy': [0, 0, 80, 60],
            'description': 'CPU fixture, not independent visual evidence'}


def screen(v):
    return {'status': 'usable', 'visible': ['fixture'], 'limitations': [],
            'loading': 'not_observed', 'reason': 'fixture', 'evidence': [evidence(v)]}


def verdict(v, status='supported', wait=False):
    return {'claims': [], 'action': {'status': status, 'target_kind': 'button',
            'reason': 'fixture', 'evidence': [evidence(v)]},
            'pure_wait': wait, 'acknowledges_visual_deficit': False}


class Client:
    model, revision = MODEL, REVISION
    def __init__(self, fail=False):
        self.fail, self.calls = fail, 0
    def decide(self, im, key, provenance):
        self.calls += 1
        if self.fail:
            raise RuntimeError('Fixture transport failure')
        return {'model': MODEL, 'revision': REVISION, 'image_sha256': digest(im.raw),
                'answer': 'unknown',
                'probabilities': {k: float(k == 'unknown') for k in QUESTIONS[key][1]}}


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name); self.seq = 0
    def tearDown(self): self.temp.cleanup()
    def journal(self):
        self.seq += 1; return Journal(self.root / str(self.seq))
    def ctl(self, judge, client=None, cap=60, limits=None):
        return FlashCuedController(judge, self.journal(), 'post_only', limits or Limits(),
            flash_auxiliary=FlashAuxiliary(client or Client(), cap), sleeper=lambda _: None)
    def rows(self, v=None):
        v = v or view()
        return FlashAuxiliary(Client()).observe('verify', v, {'name': 'click'}, self.journal())

    def test_one_fixed_model_only(self):
        for model, revision in [('neohorse', REVISION), (MODEL, 'wrong')]:
            client = Client(); client.model, client.revision = model, revision
            with self.assertRaises(ValueError): FlashAuxiliary(client)
    def test_budget_cannot_expand(self):
        for cap in [61, True, -1]:
            with self.assertRaises(ValueError): FlashAuxiliary(Client(), cap)
    def test_only_system_augments_primary_full_input_and_verdict_unchanged(self):
        v = view(); v.messages.extend([{'role': 'assistant', 'content': 'history '*2000}]*43)
        before = canonical(v.data()); seen = []
        judge = lambda s, obs, candidate: seen.append((s, canonical(obs.data()), candidate)) or screen(obs)
        base = Controller(judge, self.journal()); expected = base.inspect('screen', v)
        original = seen[-1]; ctl = self.ctl(judge)
        self.assertEqual(ctl.inspect('screen', v), expected)
        self.assertEqual(seen[-1][1:], original[1:]); self.assertIn(CUE_RULES, seen[-1][0])
        self.assertEqual(canonical(v.data()), before); self.assertEqual(ctl.verifier_calls, base.verifier_calls)
    def test_normal_action_accepted_despite_unknown(self):
        ctl = self.ctl(lambda s,v,p: verdict(v))
        self.assertEqual(ctl.decide(view(), lambda *_:'CLICK', lambda _: {'name':'click'}, None)['status'], 'accepted')
    def test_wrong_action_strict_block_preserved(self):
        ctl = self.ctl(lambda s,v,p: verdict(v, 'contradicted'), limits=Limits(max_regenerations=0))
        self.assertEqual(ctl.decide(view(), lambda *_:'WRONG', lambda _: {'name':'click'}, None)['status'], 'blocked')
    def test_wait_and_noop_zero_extra_calls(self):
        for name in ['wait', 'noop']:
            ctl = self.ctl(lambda s,v,p: verdict(v, wait=True))
            ctl.inspect('verify', view(), name, {'name': name, 'parsed': True})
            self.assertEqual(ctl.flash_auxiliary.calls, 0)
    def test_reference_frame_excluded(self):
        original = view()
        v = replace(original, images=(VisibleImage(original.images[0].raw, 'reference'),))
        self.assertEqual(FlashAuxiliary(Client()).observe('verify', v, None, self.journal()), [])
    def test_wrong_source_revision_and_style_excluded(self):
        v = view(); rows = self.rows(v)
        edits = [('source','image_sha256'), ('source','observation_id'),
                 ('source','full_public_view_sha256'), ('result','revision')]
        for section,key in edits:
            bad = copy.deepcopy(rows[:1]); bad[0][section][key] = 'wrong'
            self.assertFalse(cue_packet(bad, v, 'verify')['observations'])
        bad = copy.deepcopy(rows[:1]); bad[0]['model']='jev_style'
        self.assertFalse(cue_packet(bad, v, 'verify')['observations'])
    def test_nan_and_duplicate_rejected(self):
        v=view(); rows=self.rows(v)
        bad=copy.deepcopy(rows[:1]); bad[0]['result']['probabilities']['unknown']=float('nan')
        self.assertFalse(cue_packet(bad,v,'verify')['observations'])
        self.assertEqual(len(cue_packet(rows[:1]*2,v,'verify')['observations']), 1)
    def test_failure_preserved_no_retry_original_check_works(self):
        client=Client(True); ctl=self.ctl(lambda s,v,p:screen(v),client)
        self.assertEqual(ctl.inspect('screen',view())['status'],'usable')
        self.assertEqual(ctl.inspect('screen',view())['status'],'usable')
        self.assertEqual(client.calls,1)
    def test_auxiliary_exhaustion_falls_back_to_original(self):
        seen=[]; ctl=self.ctl(lambda s,v,p:seen.append(s) or screen(v),cap=0)
        self.assertEqual(ctl.inspect('screen',view())['status'],'usable')
        self.assertNotIn(CUE_RULES,seen[-1]); self.assertEqual(ctl.flash_auxiliary.calls,0)
    def test_primary_budget_prevents_auxiliary(self):
        ctl=self.ctl(lambda *_:self.fail('primary called'),limits=Limits(max_verifier_calls=0))
        with self.assertRaises(BudgetExhausted):ctl.inspect('screen',view())
        self.assertEqual(ctl.flash_auxiliary.calls,0)
    def test_invalid_primary_reply_not_repaired_and_context_cleaned(self):
        ctl=self.ctl(lambda *_:{},limits=Limits(max_format_retries=0))
        with self.assertRaises(ValidationError):ctl.inspect('screen',view())
        self.assertEqual(ctl._inspection_context,[])
    def test_history_completion_point_have_no_auxiliary(self):
        for phase in ['history_report','completion','alignment','point','absence_relation']:
            self.assertFalse(cue_packet(self.rows(),view(),phase)['observations'])
    def test_original_caps_and_core_methods_unchanged(self):
        self.assertEqual((Limits().max_actor_calls,Limits().max_verifier_calls,
                          Limits().max_recaptures,Limits().max_regenerations,
                          Limits().max_format_retries),(70,140,2,2,1))
        self.assertIs(FlashCuedController.decide,Controller.decide)
        self.assertIs(FlashCuedController.accept,Controller.accept)
    def test_actual_prompt_hash_chain_and_no_ensemble(self):
        ctl=self.ctl(lambda s,v,p:screen(v)); ctl.inspect('screen',view())
        previous='0'*64; seen=False
        for line in (ctl.log.root/'events.jsonl').read_text().splitlines():
            item=json.loads(line); digest_seen=item.pop('sha256')
            self.assertEqual(item['previous'],previous); self.assertEqual(digest(canonical(item)),digest_seen)
            previous=digest_seen
            if item['kind']=='flash_cue_policy':
                self.assertFalse(item['data']['ensemble']); self.assertEqual(item['data']['auxiliary_model_count'],1)
            if item['kind']=='flash_cued_verifier_request':
                self.assertEqual(digest(item['data']['actual_system'].encode()),item['data']['actual_system_sha256']); seen=True
        self.assertTrue(seen)


if __name__=='__main__':unittest.main()
