"""Behavior at the acceptance boundary, immutable blind-read scope and retry budget."""
import copy,io,json,tempfile,unittest
from pathlib import Path
from PIL import Image
from defense.core import Controller,Journal,Limits,PublicView,VisibleImage
from price_history_binding import check_price_history

def image():
    b=io.BytesIO();Image.new('RGB',(1280,720),'white').save(b,format='PNG');return VisibleImage(b.getvalue())
def cite():return {'observation_id':'test-live','image_index':0,'coordinate_space':'pixels','box_xyxy':[1,1,20,20],'description':'test evidence'}
def screen():return {'status':'usable','visible':['Synthetic readable test record: object A at $5.00'],'limitations':[],'loading':'not_observed','evidence':[cite()],'reason':'synthetic unit record, no real semantic evidence'}
def main_verdict():return {'claims':[],'action':{'status':'supported','target_kind':'not_applicable','reason':'native back test','evidence':[cite()]},'pure_wait':False,'acknowledges_visual_deficit':False}
def relation(status):return {'claims':[],'action':{'status':status,'target_kind':'not_applicable','reason':'synthetic relation','evidence':[{'source':'candidate','span_id':'full'}]},'pure_wait':False,'acknowledges_visual_deficit':False}

class Behavior(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.view=PublicView('test-live',[{'role':'user','content':'Task: Find cheapest item'},{'role':'assistant','content':'SENTINEL actor history must not enter blind reader'}],(image(),))
    def controller(self,replies):
        self.requests=[]
        def judge(system,view,candidate):
            self.requests.append((system,view.data(),candidate));return json.dumps(replies.pop(0))
        return Controller(judge,Journal(Path(self.tmp.name)/'journal'),'joint',Limits(probe_history_reports=True),sleeper=lambda _:None)
    def test_false_pair_cannot_reach_accept(self):
        c=self.controller([screen(),main_verdict(),screen(),relation('contradicted')])
        text='I saw object A for $1.00.\n<action>{"type":"back"}</action>'
        p={'name':'back','payload':{'type':'back'},'parsed':True,'executor_fallback_wait':False}
        result=c.decide(self.view,lambda v,x:text,lambda t:p,None)
        self.assertEqual(result['status'],'blocked');self.assertEqual(c.actor_calls,1);self.assertEqual(c.verifier_calls,4)
        events=[json.loads(x)for x in(c.log.root/'events.jsonl').read_text().splitlines()]
        self.assertFalse(any(e['kind'] in {'decision_accepted','action_executed'}for e in events))
        self.assertTrue(any(e['kind']=='price_history_binding'and not e['data']['agrees']for e in events))
    def test_correct_pair_preserves_native_action(self):
        c=self.controller([screen(),main_verdict(),screen(),relation('supported')])
        text='I saw object A for $5.00.\n<action>{"type":"back"}</action>';p={'name':'back','payload':{'type':'back'},'parsed':True,'executor_fallback_wait':False};old=copy.deepcopy(p)
        result=c.decide(self.view,lambda v,x:text,lambda t:p,None)
        self.assertEqual(result['status'],'accepted');self.assertEqual(result['candidate'],text);self.assertEqual(result['proposal'],old)
    def test_blind_read_frozen_before_candidate_and_reused(self):
        c=self.controller([screen(),relation('contradicted'),relation('supported')]);original=copy.deepcopy(self.view.data())
        a=check_price_history(c,self.view,'I saw object A for $1.00.')
        b=check_price_history(c,self.view,'I saw object A for $5.00.')
        self.assertIsNone(self.requests[0][2]);self.assertNotIn('SENTINEL',json.dumps(self.requests[0][1]))
        self.assertEqual(self.requests[1][1]['images'],[]);self.assertEqual(a['frozen_sha256'],b['frozen_sha256'])
        self.assertEqual(len(self.requests),3);self.assertEqual(self.view.data(),original)

if __name__=='__main__':unittest.main()
