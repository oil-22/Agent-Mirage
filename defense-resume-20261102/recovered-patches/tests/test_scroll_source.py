import copy
import unittest
from scroll_source import with_native_action_feedback

class ScrollSourceTests(unittest.TestCase):
    def test_selects_scroll_rejection_not_earlier_focus_or_future_attempt(self):
        public={'observation_id':'009-obs011','messages':[], 'recent_action':{},'execution_feedback':'','observed_at':1}
        text='I will scroll up. <action>{"type":"scroll","direction":"down"}</action>'
        corrections=[{'claim':'proposed_action','reason':'text and JSON conflict'}]
        events=[{'seq':1,'kind':'actor_request','data':{'public':{**public,'observation_id':'002-obs003'},'corrections':[{'claim':'proposed_action','reason':'focus'}]}},
                {'seq':2,'kind':'candidate','data':{'text':'click field'}},
                {'seq':3,'kind':'actor_request','data':{'public':public,'corrections':[]}},
                {'seq':4,'kind':'candidate','data':{'text':text}},
                {'seq':5,'kind':'verdict','data':{'verdict':{'action':{'status':'contradicted'}}}},
                {'seq':6,'kind':'actor_request','data':{'public':{**public,'observation_id':'009-obs012'},'corrections':corrections}},
                {'seq':7,'kind':'candidate','data':{'text':'future result'}}]
        original=copy.deepcopy(events)
        parse=lambda t:{'name':'scroll','payload':{'type':'scroll','direction':'down'}}
        req,patches,seq=with_native_action_feedback(events,parse)
        self.assertEqual((req['seq'],seq),(6,4))
        self.assertEqual(patches[0]['source_observation'],'009-obs011')
        self.assertEqual(patches[0]['rejected_candidate_text'],text)
        self.assertEqual(events,original)

    def test_no_matching_rejected_proposal_fails_closed(self):
        with self.assertRaises(AssertionError):with_native_action_feedback([],lambda t:{})
