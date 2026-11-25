"""Source binding and unchanged acceptance/budget guarantees for action feedback."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from test_controller import view, verdict
from defense.core import (Controller, Journal, Limits, canonical, digest,
                          pending_action_patch, correction_message)


class NativeActionFeedbackTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def ctl(self,judge,arm='joint',limits=None):
        return Controller(judge,Journal(self.root/'run'),arm,limits,sleeper=lambda _:None)
    def events(self):return [json.loads(line)for line in(self.root/'run/events.jsonl').read_text().splitlines()]
    def test_feedback_binds_raw_candidate_and_parsed_action_without_mutation(self):
        candidate='I will scroll back up.\n<action>{"type":"scroll","direction":"down"}</action>'
        proposal={'name':'scroll','parsed':True,'payload':{'type':'scroll','direction':'down'}}
        original=copy.deepcopy(proposal)
        patch=pending_action_patch(candidate,proposal,view(),'contradicted','checker-only alleged GUI fact')
        self.assertEqual(patch['rejected_candidate_text'],candidate)
        self.assertEqual(patch['rejected_candidate_sha256'],digest(candidate.encode()))
        self.assertEqual(patch['rejected_native_proposal'],original)
        self.assertEqual(patch['execution_status'],'rejected_not_executed')
        self.assertTrue(patch['reason_is_checker_feedback_not_observation'])
        self.assertEqual(patch['reason'],'checker-only alleged GUI fact')
        patch['rejected_native_proposal']['payload']['direction']='up'
        self.assertEqual(proposal,original)

    def test_feedback_documents_both_directions_and_wait_without_commanding_one(self):
        text=correction_message([])['content']
        self.assertIn('Both native scroll direction values "up" and "down" are valid',text)
        self.assertIn('does not instruct you to scroll',text)
        self.assertIn('A genuine wait remains valid',text)

    def test_new_native_output_is_returned_verbatim_and_old_payload_not_rewritten(self):
        bad='I will scroll up.\n<action>{"type":"scroll","direction":"down"}</action>'
        good='I will inspect earlier content.\n<action>{"type":"scroll","direction":"up"}</action>'
        generated=iter([bad,good]);seen=[]
        def parse(text):
            payload=json.loads(text.split('<action>')[1].split('</action>')[0])
            return {'name':payload['type'],'parsed':True,'payload':payload}
        def actor(public,patches):seen.append((public,patches));return next(generated)
        def judge(_,public,text):
            value=verdict(public,'supported'if text==good else'contradicted')
            value['claims']=[]
            return value
        controller=self.ctl(judge,'post_only')
        result=controller.decide(view(),actor,parse,lambda:view('fresh'))
        self.assertEqual(result['candidate'],good)
        self.assertEqual(result['proposal']['payload']['direction'],'up')
        self.assertEqual(result['regenerations'],1)
        self.assertEqual(seen[0][0].messages,view().messages)
        patch=next(x for x in seen[1][1]if x['claim']=='proposed_action')
        self.assertEqual(patch['rejected_native_proposal']['payload']['direction'],'down')
        self.assertTrue(all(e['data']['text']==text for e,text in zip(
            [e for e in self.events()if e['kind']=='candidate'],[bad,good])))

    def test_unfixed_conflict_still_exhausts_original_two_regenerations(self):
        text='I will scroll up.\n<action>{"type":"scroll","direction":"down"}</action>'
        def judge(_,public,candidate):
            value=verdict(public,'contradicted');value['claims']=[];return value
        c=self.ctl(judge,'post_only',Limits())
        parse=lambda _: {'name':'scroll','parsed':True,'payload':{'type':'scroll','direction':'down'}}
        captures=iter([view('fresh1'),view('fresh2')])
        result=c.decide(view(),lambda *_:text,parse,lambda:next(captures))
        self.assertEqual(result['reason'],'regeneration_cap')
        self.assertEqual(result['regenerations'],2)
        self.assertEqual(c.actor_calls,3)
        self.assertFalse(any(e['kind']=='decision_accepted'for e in self.events()))


if __name__=='__main__':unittest.main()
