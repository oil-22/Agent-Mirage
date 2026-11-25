"""New source audit uses the existing one-format-retry boundary, no actor rewrite."""
import copy,io,json,tempfile,unittest
from pathlib import Path
from PIL import Image
from defense.core import Controller,Journal,Limits,PublicView,VisibleImage,ValidationError

class CompletionRetry(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        b=io.BytesIO();Image.new('RGB',(1280,720),'white').save(b,format='PNG')
        self.view=PublicView('test',[{'role':'user','content':'Task: Find an item'}],(VisibleImage(b.getvalue()),))
    def read(self,text):return {'status':'usable','visible':[text],'limitations':[],'loading':'not_observed','evidence':[{'observation_id':'test','image_index':0,'coordinate_space':'pixels','box_xyxy':[1,1,20,20],'description':'Synthetic test only'}],'reason':'Synthetic'}
    def relation(self,status):return {'claims':[],'action':{'status':status,'target_kind':'not_applicable','reason':'Synthetic binding','evidence':[{'source':'candidate','span_id':'full'}]},'pure_wait':False,'acknowledges_visual_deficit':False}
    def controller(self,replies):
        self.requests=[]
        def judge(system,v,candidate):self.requests.append((system,copy.deepcopy(v.data()),candidate));return json.dumps(replies.pop(0))
        return Controller(judge,Journal(Path(self.tmp.name)/'journal'),'joint',Limits(),sleeper=lambda _:None)
    def test_correction_on_original_single_retry(self):
        bad=self.read('Image0 item A at $7.00');raw=self.read('Item A price unknown');good=self.read('Image0 item A price unknown, no price established')
        old=copy.deepcopy(bad);v=self.view.data();c=self.controller([bad,raw,self.relation('insufficient'),good]);out=c.inspect('completion',self.view)
        self.assertEqual(out['visible'],good['visible']);self.assertEqual(bad,old);self.assertEqual(self.view.data(),v);self.assertEqual(c.verifier_calls,4)
        requests=[r for r in self.requests if r[1]==v];self.assertEqual(len(requests),2);self.assertIn('No corrected price',requests[-1][0]);self.assertEqual(c.actor_calls,0)
    def test_persistent_conflict_exhausts_original_retry(self):
        bad=self.read('Image0 item A at $7.00');c=self.controller([bad,self.read('Item A price unknown'),self.relation('insufficient'),bad,self.relation('insufficient')])
        with self.assertRaises(ValidationError):c.inspect('completion',self.view)
        self.assertEqual(c.verifier_calls,5);events=[json.loads(x)for x in(c.log.root/'events.jsonl').read_text(encoding='utf-8').splitlines()]
        failures=[e for e in events if e['kind']=='verifier_format_failure'];self.assertEqual([e['data']['format_retry']for e in failures],[0,1]);self.assertFalse(any(e['kind']=='decision_accepted'for e in events))

if __name__=='__main__':unittest.main()
