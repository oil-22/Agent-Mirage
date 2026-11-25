"""CPU protocol and original native-call invariance tests; no model imports."""
import ast
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

from online_contract import initial_state,validate_plan,begin,finish,admit
from online_gate import validate_capacity
from online_service import save

HERE=Path(__file__).resolve().parent
PLAN=Path(os.environ['TEST_ORIGINAL_THREE_PLAN'])
ORIGINAL=Path(os.environ['TEST_ORIGINAL_ONLINE_SOURCE'])
CAPACITY=Path(os.environ['TEST_ACTUAL_CAPACITY_RECEIPT'])


class TestOnlineThree(unittest.TestCase):
    def setUp(self):self.plan=json.loads(PLAN.read_bytes())
    def test_caps_exact(self):
        runs=validate_plan(self.plan);self.assertEqual([r['caps']['observe']for r in runs.values()],[60,0,60])
        self.assertEqual(sum(r['caps']['actor']+r['caps']['judge']for r in runs.values()),630)
    def test_completed_old_clean_rejected(self):
        p=copy.deepcopy(self.plan);p['queue'][0]['observer_enabled']=False
        with self.assertRaises(ValueError):validate_plan(p)
    def test_extra_old_queue_rejected(self):
        p=copy.deepcopy(self.plan);p['queue']+=p['queue'][:1]
        with self.assertRaises(ValueError):validate_plan(p)
    def test_order_rejected(self):
        p=copy.deepcopy(self.plan);p['queue'].reverse()
        with self.assertRaises(ValueError):validate_plan(p)
    def test_run_id_alias_rejected(self):
        p=copy.deepcopy(self.plan);p['queue'][1]['run_id']+='-retry'
        with self.assertRaises(ValueError):validate_plan(p)
    def test_observer_integer_rejected(self):
        p=copy.deepcopy(self.plan);p['queue'][0]['observer_enabled']=1
        with self.assertRaises(ValueError):validate_plan(p)
    def test_finish_after_exact_three(self):
        state=initial_state(self.plan)
        for row in self.plan['queue']:begin(state,self.plan,row['run_id']);finish(state,row['run_id'],'completed')
        self.assertEqual(state['phase'],'complete');self.assertEqual(state['next_run_index'],3)
        with self.assertRaises(ValueError):begin(state,self.plan,self.plan['queue'][0]['run_id'])
    def test_failure_no_remaining_budget_requeue(self):
        state=initial_state(self.plan);key=self.plan['queue'][0]['run_id'];begin(state,self.plan,key);finish(state,key,'technical_failure')
        with self.assertRaises(ValueError):begin(state,self.plan,self.plan['queue'][1]['run_id'])
    def envelope(self,key,index):return dict(trajectory_id=key,decision_index=1,attempt_index=index,request_id='new_opaque_request_01',payload={'operation':'judge'})
    def test_finite_judge_cap(self):
        state=initial_state(self.plan);key=self.plan['queue'][0]['run_id'];begin(state,self.plan,key)
        for i in range(1,141):admit(state,self.plan,self.envelope(key,i),'primary')
        with self.assertRaises(ValueError):admit(state,self.plan,self.envelope(key,141),'primary')
    def test_no_observer_calls_for_control(self):
        state=initial_state(self.plan);keys=[x['run_id']for x in self.plan['queue']]
        begin(state,self.plan,keys[0]);finish(state,keys[0],'completed');begin(state,self.plan,keys[1])
        with self.assertRaises(ValueError):admit(state,self.plan,self.envelope(keys[1],1),'pplx_flash')
    def test_original_budgets_not_relaxed(self):
        for key,value in [('max_steps',51),('actor_output_tokens',2049),('verifier_output_tokens',4097),('max_format_retries',2)]:
            p=copy.deepcopy(self.plan);p[key]=value
            with self.assertRaises(ValueError):validate_plan(p)
    def test_actual_capacity_admitted(self):validate_capacity(json.loads(CAPACITY.read_bytes()))
    def test_old_capacity_not_admitted(self):
        p=json.loads(CAPACITY.read_bytes());p['input_tokens']=15720;p['original_images']=4
        with self.assertRaises(RuntimeError):validate_capacity(p)
    def test_wrong_layout_or_allocator_not_admitted(self):
        for key,value in [('new_device_map_14_22_22_6_actual',False),('primary_process_allocator_actual','')]:
            p=json.loads(CAPACITY.read_bytes());p[key]=value
            with self.assertRaises(RuntimeError):validate_capacity(p)
    def test_native_model_call_AST_unchanged(self):
        def calls(path):
            tree=ast.parse(path.read_text(encoding='utf8'))
            return [ast.dump(n,include_attributes=False)for n in ast.walk(tree)if isinstance(n,ast.Call)
                    and ast.unparse(n.func)in {'engine.generate','engine.judge','engine.decide','PublicView','VisibleImage','audited_forward','load_primary','load_flash'}]
        self.assertEqual(calls(ORIGINAL/'online_service.py'),calls(HERE/'online_service.py'))
    def test_mutable_state_atomic_original_unchanged(self):
        def definition(path,name):return ast.dump(next(n for n in ast.parse(path.read_text(encoding='utf8')).body if isinstance(n,ast.FunctionDef)and n.name==name),include_attributes=False)
        self.assertEqual(definition(ORIGINAL/'online_service.py','state_save'),definition(HERE/'online_service.py','state_save'))
    def test_safe_marker_stop_contains_zombie_handling(self):
        text=(HERE/'marker_stop_helpers.py').read_text(encoding='utf8')
        self.assertIn("state == 'Z'",text);self.assertIn('exit_code_not_inferred',text)
        self.assertNotIn('os.kill(child[\'process\'].pid, signal.SIGUSR1)',text)
    @unittest.skipIf(os.name=='nt','Linux-only actual hardlink/directory fsync tested remotely')
    def test_immutable_atomic_no_clobber(self):
        with tempfile.TemporaryDirectory()as d:
            path=Path(d)/'evidence.json';save(path,{'complete':True});raw=path.read_bytes()
            with self.assertRaises(FileExistsError):save(path,{'complete':False})
            self.assertEqual(path.read_bytes(),raw);self.assertEqual([p.name for p in Path(d).iterdir()],['evidence.json'])
    def test_sources_compile(self):
        for path in HERE.glob('*.py'):compile(path.read_text(encoding='utf8'),str(path),'exec')


if __name__=='__main__':unittest.main()
