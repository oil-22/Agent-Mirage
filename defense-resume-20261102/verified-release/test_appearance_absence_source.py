"""Routing/source/budget boundaries only; mocks never assert model semantic accuracy."""
import copy,json,tempfile,unittest
from pathlib import Path
from dataclasses import replace
from appearance_absence_source import absence_clauses,check_appearance_absence,PERSON_READ,ABSENCE_RELATION
from test_native_direction_development import view
from test_scoped_controller_integration import screen

class AbsenceSourceBoundaries(unittest.TestCase):
 def test_wait_always_excluded(self):self.assertEqual(absence_clauses('No man in a suit here.',{'name':'wait'}),[])
 def test_known_local_negative_trigger(self):self.assertEqual(absence_clauses('No man in a suit on this part of page 2.',{'name':'scroll'}),['No man in a suit on this part of page 2.'])
 def test_uncertainty_not_strengthened(self):self.assertEqual(absence_clauses('I cannot confirm that no man in a suit is shown.',{'name':'scroll'}),[])
 def test_identified_is_not_global_uniqueness(self):self.assertEqual(absence_clauses('The only item I identified with a man in a suit was this book.',{'name':'click'}),[])
 def test_neither_negative_is_in_scope(self):self.assertTrue(absence_clauses('Neither item shows a man in a suit.',{'name':'click'}))
 def test_native_answer_not_dropped(self):self.assertTrue(absence_clauses('<action>{"type":"stop","answer":"No man in a suit appeared."}</action>',{'name':'stop'}))
 def test_prompts_have_no_source_answer(self):
  for s in [PERSON_READ,ABSENCE_RELATION]:
   for word in ['Victor','green suit','Rick Pitino','3e254','basketball']:self.assertNotIn(word,s)
 def test_raw_source_is_blind_and_cached_no_rewrite(self):
  original=replace(view(),messages=[{'role':'user','content':'SECRET_TASK'},{'role':'assistant','content':'SECRET_PRIOR'}],recent_action='SECRET_CLICK',execution_feedback='SECRET_FEEDBACK');before=copy.deepcopy(original.data())
  class Log:
   def append(self,*args):pass
   def observation(self,*args,**kw):pass
  class C:
   reference_bank=[];log=Log();calls=[]
   def inspect(self,phase,v,c=None):
    self.calls.append(phase)
    if phase=='person_read':
     data=json.dumps(v.data())
     for x in ['SECRET_TASK','SECRET_PRIOR','SECRET_CLICK','SECRET_FEEDBACK','No man']:assert x not in data
     assert c is None and v.images[0].raw==original.images[0].raw
     return screen(v)
    assert not v.images and c
    return {'claims':[],'action':{'status':'insufficient','target_kind':'not_applicable','reason':'unresolved scope','evidence':[]},'pure_wait':False,'acknowledges_visual_deficit':False}
  c=C();proposal={'name':'scroll'};candidate='No man in a suit here.'
  for _ in range(2):self.assertIsNotNone(check_appearance_absence(c,original,candidate,proposal)['reason'])
  self.assertEqual(c.calls,['person_read','absence_relation','absence_relation']);self.assertEqual(original.data(),before)
 def test_no_trigger_makes_no_inference(self):
  class C:
   class Log:
    def append(self,*args):pass
   log=Log()
   def inspect(self,*args):raise AssertionError('Unexpected inference')
  self.assertFalse(check_appearance_absence(C(),view(),'I will inspect more.',{'name':'scroll'})['triggered'])

if __name__=='__main__':unittest.main()
