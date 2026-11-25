import copy,tempfile,unittest
from pathlib import Path
from test_controller import view,verdict,screen
from defense.core import *

def parse_type(text):return {'name':'wait'if text=='WAIT'else'type','parsed':True,'payload':{'type':'wait'if text=='WAIT'else'type','text':'private typed text'}}
class FocusTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def ctl(self,judge,**kw):return Controller(judge,Journal(self.root/'run'),'post_only',Limits(probe_current_targets=True,**kw),sleeper=lambda _:None)
    def test_focus_read_is_blind_to_history_candidate_and_references(self):
        obs=replace(view(),messages=[{'role':'assistant','content':'I assert it is focused'}],recent_action='old click',execution_feedback='old success')
        def judge(_,v,c):
            self.assertIsNone(c);self.assertNotIn('I assert',str(v.messages));self.assertNotIn('private typed',str(v.messages))
            self.assertEqual(v.recent_action,'');self.assertEqual(v.execution_feedback,'')
            self.assertEqual(len(v.images),1);self.assertEqual(v.images[0].raw,obs.images[0].raw)
            return screen(v)
        c=self.ctl(judge);c.remember(view('old','blue'),'old focus')
        self.assertTrue(c.check_current_focus(obs)['agrees']);self.assertEqual(c.verifier_calls,1)
    def test_missing_current_focus_is_unknown_without_model_call(self):
        c=self.ctl(lambda *_:self.fail('No image to check'))
        self.assertFalse(c.check_current_focus(PublicView('missing',[],()))['agrees']);self.assertEqual(c.verifier_calls,0)
    def test_wrong_focus_is_invalidated_even_when_main_verifier_accepts(self):
        answers=iter(['TYPE','WAIT']);corrections=[]
        def actor(v,c):corrections.append(copy.deepcopy(c));return next(answers)
        def judge(_,v,text):
            if text is None:return screen(v,'limited')
            r=verdict(v,wait=text=='WAIT');r['claims']=[];return r
        c=self.ctl(judge);r=c.decide(view(),actor,parse_type,lambda:view('fresh'))
        self.assertEqual(r['candidate'],'WAIT');self.assertTrue(any(x['claim']=='current input focus'for x in corrections[-1]))
        self.assertEqual(r['recaptures'],1);self.assertEqual(r['regenerations'],1)
    def test_visible_focus_allows_typing(self):
        c=self.ctl(lambda _,v,text:screen(v)if text is None else verdict(v))
        self.assertEqual(c.decide(view(),lambda *_:'TYPE',parse_type,None)['status'],'accepted');self.assertEqual(c.verifier_calls,2)
    def test_focus_uses_same_total_budget(self):
        c=self.ctl(lambda _,v,text:verdict(v),max_verifier_calls=1)
        r=c.decide(view(),lambda *_:'TYPE',parse_type,None)
        self.assertEqual(r['reason'],'focus_verifier_error:verifier_call_cap')

if __name__=='__main__':unittest.main()
