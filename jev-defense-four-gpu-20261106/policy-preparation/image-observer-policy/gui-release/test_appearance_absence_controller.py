"""Budget/fail-closed integration, not mocked semantic efficacy."""
import json,tempfile,unittest
from pathlib import Path
from defense.core import Controller,Journal,Limits
from test_native_direction_development import view,verdict,candidate,parse
from test_scoped_controller_integration import screen
class AbsenceController(unittest.TestCase):
 def setup_controller(self,root,relation='insufficient',cap=140):
  seen=[]
  def judge(system,v,c):
   if system.startswith('Read ONLY the single original screenshot'):
    seen.append('raw');self.assertNotIn('No man',json.dumps(v.data()));return screen(v)
   if system.startswith('Audit only the exact original candidate'):
    seen.append('relation');self.assertEqual(v.images,());return {'claims':[],'action':{'status':relation,'target_kind':'not_applicable','reason':'source relation','evidence':[{'source':'candidate','span_id':'full'}]},'pure_wait':False,'acknowledges_visual_deficit':False}
   seen.append('main');self.assertEqual(v.messages,view().messages);return verdict(v)
  c=Controller(judge,Journal(root/'journal'),'post_only',Limits(probe_history_reports=True,max_verifier_calls=cap),sleeper=lambda _:None);return c,seen
 def test_missing_source_cannot_accept(self):
  with tempfile.TemporaryDirectory()as t:
   c,seen=self.setup_controller(Path(t));r=c.decide(view(),lambda *_:candidate('No man in a suit here.'),parse,None)
   self.assertEqual(r['status'],'blocked');self.assertEqual(seen,['main','raw','relation']);self.assertEqual(c.verifier_calls,3)
 def test_fully_supported_relation_does_not_rewrite_candidate(self):
  with tempfile.TemporaryDirectory()as t:
   c,seen=self.setup_controller(Path(t),'supported');text=candidate('No man in a suit here.');r=c.decide(view(),lambda *_:text,parse,None)
   self.assertEqual(r['status'],'accepted');self.assertEqual(r['candidate'],text);self.assertEqual(seen,['main','raw','relation'])
 def test_original_total_budget_still_stops_before_third_inference(self):
  with tempfile.TemporaryDirectory()as t:
   c,seen=self.setup_controller(Path(t),cap=2);r=c.decide(view(),lambda *_:candidate('No man in a suit here.'),parse,None)
   self.assertEqual(r['status'],'blocked');self.assertEqual(c.verifier_calls,2);self.assertEqual(seen,['main','raw'])
 def test_qualified_selfreport_no_extra_calls(self):
  with tempfile.TemporaryDirectory()as t:
   c,seen=self.setup_controller(Path(t));r=c.decide(view(),lambda *_:candidate('The only item I identified with a man in a suit was this book.'),parse,None)
   self.assertEqual(r['status'],'accepted');self.assertEqual(seen,['main'])
if __name__=='__main__':unittest.main()
