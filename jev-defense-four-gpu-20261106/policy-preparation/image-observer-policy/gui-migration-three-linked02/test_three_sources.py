"""CPU-only boundaries for the new exact-three queue and outer admission."""
import copy,hashlib,importlib.util,json,sys,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE/'release'))
import migration_contract as m
import gui_once as g
import observer_launch_contract as launch
PLAN=json.loads((HERE/'plan.json').read_bytes())
STATE=json.loads((ROOT/'service-stop-diagnostic-1793983538956413700/receipt.json').read_bytes())['snapshot']['state_snapshot']
RUNS=[r['run_id']for r in PLAN['queue']]

class ThreeSourceTests(unittest.TestCase):
    def test_exact_three_suffix(self):self.assertEqual(m.validate_three_plan(PLAN),PLAN['queue'])
    def test_cannot_requeue_baseline(self):
        p=copy.deepcopy(PLAN);p['queue'].insert(0,m.original_plan()['queue'][0])
        with self.assertRaises(RuntimeError):m.validate_three_plan(p)
    def test_wrong_queue_order_rejected(self):
        p=copy.deepcopy(PLAN);p['queue'][1:]=reversed(p['queue'][1:])
        with self.assertRaises(RuntimeError):m.validate_three_plan(p)
    def test_typed_budget_mutation_rejected(self):
        for field,value in [('max_format_retries',True),('max_steps',50.0),('actor_output_tokens',2048.0),('auxiliary_calls_per_trajectory',61)]:
            p=copy.deepcopy(PLAN);p[field]=value
            with self.assertRaises(RuntimeError):m.validate_three_plan(p)
    def test_seed_or_prompt_mutation_rejected(self):
        for field,value in [('seed',1),('shared_actor_instructions_sha256','0'*64),('observer_native_contract_sha256','1'*64)]:
            p=copy.deepcopy(PLAN);p[field]=value
            with self.assertRaises(RuntimeError):m.validate_three_plan(p)
    def test_original_failure_counts_retained(self):m.validate_original_state(STATE)
    def test_any_migrated_start_or_call_rejected(self):
        for run in RUNS:
            for field in ('actor','judge','observe'):
                s=copy.deepcopy(STATE);s['runs'][run]['calls'][field]=1
                with self.assertRaises(RuntimeError):m.validate_original_state(s)
            s=copy.deepcopy(STATE);s['runs'][run]['status']='active'
            with self.assertRaises(RuntimeError):m.validate_original_state(s)
    def test_boolean_zero_not_accepted_as_native_int(self):
        s=copy.deepcopy(STATE);s['runs'][RUNS[0]]['calls']['actor']=False
        with self.assertRaises(RuntimeError):m.validate_original_state(s)
    def owner(self):
        return {**{k:True for k in g.OWN_FIELDS},'collected_time':100,
            'three_unstarted_run_ids':RUNS,'physical_gpu_uuids':{str(i):'uuid'+str(i)for i in range(4,8)},
            'actual_allowed_pids':[11,12],'source_evidence':[{'path':'synthetic','sha256':'0'*64}]}
    def test_ownership_requires_exact_three_ids(self):
        with patch.object(g,'bound',return_value={}):g.ownership(self.owner(),101)
        for bad in [RUNS[:2],list(reversed(RUNS)),RUNS+[m.original_plan()['queue'][0]['run_id']]]:
            value=self.owner();value['three_unstarted_run_ids']=bad
            with self.assertRaises(RuntimeError):g.ownership(value,101)
    def test_freshness_stays120seconds(self):
        with patch.object(g,'bound',return_value={}):g.ownership(self.owner(),220)
        for now in (220.01,99):
            with self.assertRaises(RuntimeError):g.ownership(self.owner(),now)
    def test_real_root_collector_AST_health_Popen_guard(self):
        path=ROOT/'transport-preparation/ownership-proof-collector-three-01/collect_ownership_transport.py'
        spec=importlib.util.spec_from_file_location('root_collector_actual',path)
        collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(collector)
        wrapper=HERE/'gui_once.py'
        result=collector.validate_wrapper_fresh_guards(wrapper,hashlib.sha256(wrapper.read_bytes()).hexdigest())
        self.assertTrue(result['both_health_endpoints_rechecked_before_child_spawn'])
    def health(self,role):
        owner=self.owner()
        return {'role':role,'stage':'online_ready','phase':'ready_gui','exclusive_task_group':True,
            'actual_allowed_pids':owner['actual_allowed_pids'],'physical_gpu_uuids':owner['physical_gpu_uuids'],
            'state':{'phase':'ready','active':None,'next_run_index':0,'runs':{run:{'status':'not_started','last_decision_index':0,
                'calls':{'actor':0,'judge':0,'observe':0}}for run in RUNS}}}
    def test_actual_health_resources_and_three_zero_states(self):
        g.validate_health(self.health('primary'),self.health('pplx_flash'),self.owner(),PLAN)
        for mutate in ('spent','active','wrong_peer','wrong_role','reorder'):
            primary=self.health('primary')
            if mutate=='spent':primary['state']['runs'][RUNS[0]]['calls']['judge']=1
            if mutate=='active':primary['state']['active']=RUNS[0]
            if mutate=='wrong_peer':primary['actual_allowed_pids']=[13,14]
            if mutate=='wrong_role':primary['role']='pplx_flash'
            if mutate=='reorder':primary['state']['runs']=dict(reversed(list(primary['state']['runs'].items())))
            with self.assertRaises(RuntimeError):g.validate_health(primary,self.health('pplx_flash'),self.owner(),PLAN)
    def test_old_token_path_not_used(self):
        self.assertEqual(g.TOKEN,'/data/researcher/jev-defense-four-gpu-20261106/transport-online-three-01/private.token')
        self.assertNotIn('transport-online-01',g.TOKEN)
    def test_closed_readiness_before_any_task_access(self):
        with tempfile.TemporaryDirectory()as tmp:
            p=Path(tmp)/'closed.json';p.write_text(json.dumps({'policy':'single-flash-image-observer-actor-v1','launch_ready':False}))
            with self.assertRaisesRegex(RuntimeError,'prerequisites incomplete'):
                launch.validate_launch_inputs(SimpleNamespace(readiness=p))
    def test_capacity_is_new_21470_audit_not_old15720(self):
        self.assertEqual(g.CAPACITY_SHA,'fc5919611dc79e478684cbffc226cd98e40285b645f856029c694ad0173be366')
        self.assertNotEqual(g.CAPACITY_SHA,'5a89138010f8cf005cbcd03bc2a4b249af0e253178666388fb17652bb0571fb8')
    def test_native_environment_all14_preserved(self):
        from native_environment import NATIVE_ENV
        self.assertEqual(len(NATIVE_ENV),14);self.assertEqual(NATIVE_ENV['DATASET'],'visualwebarena')
    def test_exclusive_claim_cannot_be_reused(self):
        with tempfile.TemporaryDirectory()as tmp:
            path=Path(tmp)/'claim.json';g.save(path,{'once':True})
            with self.assertRaises(FileExistsError):g.save(path,{'once':False})

if __name__=='__main__':unittest.main()
