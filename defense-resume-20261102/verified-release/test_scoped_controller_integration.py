import copy,json,tempfile,unittest
from pathlib import Path
from defense.core import Controller,Journal,Limits,ValidationError
from scoped_observability import SCOPED_READINESS
from test_native_direction_development import view,verdict,candidate,parse

def screen(v,status='usable'):
    return {'status':status,'visible':['scripted control only'],'limitations':[],'loading':'uncertain',
            'evidence':[{'observation_id':v.observation_id,'image_index':0,'coordinate_space':'pixels','box_xyxy':[0,0,80,60],'description':'scripted source'}], 'reason':'scripted control only'}
class Integration(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def ctl(self,judge,arm='joint'):
        return Controller(judge,Journal(self.root/'run'),arm,Limits(probe_observation_readiness=True),sleeper=lambda _:None)
    def test_limited_still_blocks_without_actor(self):
        c=self.ctl(lambda _,v,__ :screen(v,'limited'))
        r=c.decide(view(),lambda *_:self.fail('limited frame reached actor'),parse,None)
        self.assertEqual(r['reason'],'observation_not_confirmed');self.assertEqual(c.actor_calls,0)
    def test_existing_one_format_retry_handles_invalid_source(self):
        seen=[]
        def judge(_,v,__):
            x=verdict(v);seen.append(1)
            if len(seen)==1:x['action']['reason']='The button is visible in reference image 9.'
            return x
        c=self.ctl(judge);c.inspect('verify',view(),candidate('I will scroll down.'),parse(candidate('I will scroll down.')))
        self.assertEqual(c.verifier_calls,2)
    def test_persistent_source_error_remains_rejected(self):
        def judge(_,v,__):
            x=verdict(v);x['action']['reason']='Image 8 shows the button.';return x
        c=self.ctl(judge)
        with self.assertRaises(ValidationError):c.inspect('verify',view(),candidate('I will scroll down.'),parse(candidate('I will scroll down.')))
        self.assertEqual(c.verifier_calls,2)
    def test_projection_and_full_actor_context_unchanged(self):
        v=view();old=copy.deepcopy(v.messages);seen=[]
        def judge(system,p,c):
            if system.startswith(SCOPED_READINESS):
                self.assertIsNone(c);self.assertNotIn('complete old history',json.dumps(p.messages));self.assertEqual(p.images[0].raw,v.images[0].raw);return screen(p)
            self.assertEqual(p.messages,old);seen.append('judge');return verdict(p)
        def actor(p,_):self.assertEqual(p.messages,old);seen.append('actor');return candidate('I will scroll down.')
        self.assertEqual(self.ctl(judge).decide(v,actor,parse,None)['status'],'accepted');self.assertEqual(v.messages,old);self.assertEqual(seen,['actor','judge'])
    def test_recapture_stays_at_two(self):
        count=[];c=self.ctl(lambda _,v,__ :screen(v,'unknown'))
        def capture():count.append(1);return view('fresh'+str(len(count)))
        r=c.decide(view(),lambda *_:self.fail('unknown frame reached actor'),parse,capture)
        self.assertEqual(r['reason'],'observation_not_confirmed');self.assertEqual(len(count),2)

if __name__=='__main__':unittest.main()
