import copy,json,tempfile,unittest
from pathlib import Path
from dataclasses import replace
from scene_only_readiness import scene_projection,SCENE_READINESS
from defense.core import Controller,Journal,Limits,ValidationError
from test_native_direction_development import view,verdict,candidate,parse
from test_scoped_controller_integration import screen

class SceneSourceIsolation(unittest.TestCase):
 def test_no_task_action_feedback_or_candidate_leak(self):
  v=replace(view(),messages=[{'role':'user','content':'Task: SECRET_TASK'},{'role':'assistant','content':'SECRET_CANDIDATE'}],recent_action='SECRET_ACTION',execution_feedback='SECRET_EXECUTION')
  before=copy.deepcopy(v.data());p=scene_projection(v)
  for x in ['SECRET_TASK','SECRET_CANDIDATE','SECRET_ACTION','SECRET_EXECUTION']:self.assertNotIn(x,json.dumps(p.data()))
  self.assertEqual(v.data(),before);self.assertEqual(p.images[0].raw,v.images[0].raw)
 def test_prompt_has_no_task_or_image_answer(self):
  for x in ['basketball','Keyword','1556aff','Rick','5.00']:self.assertNotIn(x,SCENE_READINESS)
 def test_guard_and_original_retry_remain(self):
  with tempfile.TemporaryDirectory()as t:
   def judge(_,v,c):x=screen(v);x['reason']='Search has not been performed.';return x
   c=Controller(judge,Journal(Path(t)/'journal'),'joint',Limits(probe_observation_readiness=True),sleeper=lambda _:None)
   with self.assertRaises(ValidationError):c.inspect('screen',view())
   self.assertEqual(c.verifier_calls,2)
 def test_actor_main_and_real_frame_unchanged(self):
  with tempfile.TemporaryDirectory()as t:
   v=view();old=copy.deepcopy(v.data());seen=[]
   def judge(system,p,c):
    if system.startswith(SCENE_READINESS):
     self.assertEqual(p.recent_action,'');self.assertEqual(p.execution_feedback,'');self.assertEqual(p.images[0].raw,v.images[0].raw);seen.append('scene');return screen(p)
    self.assertEqual(p.messages,v.messages);seen.append('main');return verdict(p)
   def actor(p,_):self.assertEqual(p.data(),old);seen.append('actor');return candidate('I will scroll down.')
   c=Controller(judge,Journal(Path(t)/'journal'),'joint',Limits(probe_observation_readiness=True),sleeper=lambda _:None)
   self.assertEqual(c.decide(v,actor,parse,None)['status'],'accepted');self.assertEqual(seen,['scene','actor','main']);self.assertEqual(v.data(),old)
 def test_blank_not_forced_usable(self):
  with tempfile.TemporaryDirectory()as t:
   c=Controller(lambda _,v,c:screen(v,'limited'),Journal(Path(t)/'journal'),'joint',Limits(probe_observation_readiness=True),sleeper=lambda _:None)
   self.assertEqual(c.decide(view(),lambda *_:self.fail('limited reached actor'),parse,None)['reason'],'observation_not_confirmed')

if __name__=='__main__':unittest.main()
