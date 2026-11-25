"""Probe isolation/control-flow tests. Vision accuracy is checked by real replay."""
import copy,tempfile,unittest
from pathlib import Path
from test_controller import view,verdict,citation
from defense.core import *

def parse(text):
    return {'name':'wait'if text=='WAIT'else'click','parsed':True,'executor_fallback_wait':False,
        'coordinate_space':'normalized_1000','payload':{'type':'click','x':500,'y':500}}
def point(v,kind='input'):
    return {'kind':kind,'visible_text':'actual current element','reason':'current-only fixture',
        'evidence':[]if kind=='unknown'else[citation(v)]}
class PointTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def controller(self,judge,**kwargs):
        return Controller(judge,Journal(self.root/'run'),'post_only',Limits(probe_current_targets=True,**kwargs),sleeper=lambda _:None)
    def test_probe_is_blind_to_old_history_references_and_intended_target(self):
        obs=replace(view(),messages=[{'role':'assistant','content':'Old statement: page four button is here'}],
            recent_action='old click',execution_feedback='old feedback')
        actor_context=[]
        def actor(v,correction):actor_context.append(copy.deepcopy(v.messages));return 'CLICK'
        def judge(_,v,candidate):
            if isinstance(candidate,dict):
                self.assertNotIn('Old statement',str(v.messages));self.assertNotIn('four',str(v.messages))
                self.assertEqual(v.recent_action,'');self.assertEqual(v.execution_feedback,'')
                self.assertEqual([im.role for im in v.images],['current','reference']);self.assertEqual(v.images[0].raw,obs.images[0].raw)
                self.assertEqual(set(candidate),{'mode','coordinate_space','pixel_point','original_size'})
                self.assertEqual(candidate['coordinate_space'],'pixels')
                self.assertEqual(candidate['pixel_point'],[s/2 for s in obs.images[0].info()['size']])
                self.assertEqual(v.images[1].info()['size'],obs.images[0].info()['size'])
                return point(v)
            self.assertEqual(v.messages[:len(obs.messages)],obs.messages);return verdict(v)
        c=self.controller(judge);c.remember(view('old','blue'),'Old picture includes page four button')
        self.assertEqual(c.decide(obs,actor,parse,None)['status'],'accepted')
        self.assertEqual(actor_context,[obs.messages]);self.assertEqual(c.verifier_calls,2)
    def test_wrong_current_kind_invalidates_action_and_regenerates_without_erasing_it(self):
        answers=iter(['CLICK','WAIT']);seen=[]
        def actor(v,c):seen.append(c);return next(answers)
        def judge(_,v,candidate):
            if isinstance(candidate,dict):return point(v,'content')
            r=verdict(v,wait=candidate=='WAIT');r['claims']=[]
            r['action']['target_kind']='button'if candidate=='CLICK'else'not_applicable'
            return r
        c=self.controller(judge);r=c.decide(view(),actor,parse,None)
        self.assertEqual(r['candidate'],'WAIT');self.assertTrue(seen[1]);self.assertIn('content',seen[1][0]['reason'])
        es=[json.loads(x)for x in (self.root/'run/events.jsonl').read_text().splitlines()]
        self.assertEqual([e['data']['text']for e in es if e['kind']=='candidate'],['CLICK','WAIT'])
    def test_unknown_probe_requires_new_evidence(self):
        def judge(_,v,c):return point(v,'unknown')if isinstance(c,dict)else verdict(v)
        r=self.controller(judge).decide(view(),lambda *_:'CLICK',parse,None)
        self.assertEqual(r['reason'],'live_recapture_unavailable');self.assertIsNone(r['semantic_mirage'])
    def test_probe_cannot_cite_reference_or_wrong_region(self):
        v=view();q={'x':500,'y':500};r=point(v);r['evidence'][0]['box_xyxy']=[0,0,10,10]
        with self.assertRaises(ValidationError):validate_point(r,v,q)
        v=replace(v,images=(VisibleImage(v.images[0].raw,'reference'),));r=point(v)
        with self.assertRaises(ValidationError):validate_point(r,v,q)
    def test_locator_is_derived_only_from_current_and_cannot_be_evidence(self):
        obs=view()
        def judge(_,v,q):
            self.assertEqual(v.images[0].raw,obs.images[0].raw)
            self.assertNotEqual(v.images[1].raw,obs.images[0].raw)
            self.assertEqual(q['original_size'],v.images[0].info()['size'])
            r=point(v);r['evidence'][0]['image_index']=1
            return r
        c=self.controller(judge,max_format_retries=0)
        with self.assertRaisesRegex(ValidationError,'current image'):
            c.check_current_point(obs,parse('CLICK'),'input')
    def test_real_wait_does_not_make_point_call(self):
        def judge(_,v,c):
            self.assertIsInstance(c,str);r=verdict(v,wait=True);r['claims']=[];return r
        c=self.controller(judge);r=c.decide(view(),lambda *_:'WAIT',parse,None)
        self.assertEqual(r['status'],'accepted');self.assertEqual(c.verifier_calls,1)
    def test_probe_calls_share_total_verifier_budget(self):
        c=self.controller(lambda _,v,c:verdict(v),max_verifier_calls=1)
        r=c.decide(view(),lambda *_:'CLICK',parse,None)
        self.assertEqual(r['reason'],'point_verifier_error:verifier_call_cap');self.assertEqual(c.verifier_calls,1)

if __name__=='__main__':unittest.main()
