"""Meaningful boundary checks: never admit a spent trajectory or altered conditions."""
import copy,json,unittest
from pathlib import Path
import migration_contract as m
ROOT=Path(__file__).resolve().parents[3]
RAW=(ROOT/'gui-preparation-package-02/plan.json').read_bytes()
STATE=json.loads((ROOT/'service-stop-diagnostic-1793983538956413700/receipt.json').read_bytes())['snapshot']['state_snapshot']

class MigrationBoundaryTests(unittest.TestCase):
    def test_exact_unspent_suffix(self):
        p=m.prepare_plan(RAW,STATE);r=m.validate_plan(p,m.parent_plan(RAW))
        self.assertEqual((r['maximum_primary_calls'],r['maximum_observer_calls']),(630,120))
        self.assertFalse(r['launch_ready'])
    def test_source_hash_mismatch(self):
        with self.assertRaises(ValueError):m.prepare_plan(RAW+b' ',STATE)
    def test_cannot_hide_terminal_baseline(self):
        s=copy.deepcopy(STATE);s['runs'][next(iter(s['runs']))]['calls']['judge']=0
        with self.assertRaises(ValueError):m.prepare_plan(RAW,s)
    def test_any_spent_suffix_rejected(self):
        for run in list(STATE['runs'])[1:]:
            for role in ('actor','judge','observe'):
                with self.subTest(run=run,role=role):
                    s=copy.deepcopy(STATE);s['runs'][run]['calls'][role]=1
                    with self.assertRaises(ValueError):m.prepare_plan(RAW,s)
    def test_any_started_suffix_rejected(self):
        for run in list(STATE['runs'])[1:]:
            s=copy.deepcopy(STATE);s['runs'][run]['status']='active'
            with self.assertRaises(ValueError):m.prepare_plan(RAW,s)
    def test_baseline_requeue_rejected(self):
        p=m.prepare_plan(RAW,STATE);p['queue'].insert(0,m.parent_plan(RAW)['queue'][0])
        with self.assertRaises(ValueError):m.validate_plan(p,m.parent_plan(RAW))
    def test_order_swap_rejected(self):
        p=m.prepare_plan(RAW,STATE);p['queue'][1:]=reversed(p['queue'][1:])
        with self.assertRaises(ValueError):m.validate_plan(p,m.parent_plan(RAW))
    def test_changed_main_or_aux_condition_rejected(self):
        original=m.parent_plan(RAW)
        for field,value in [('max_steps',51),('actor_output_tokens',1024),('verifier_output_tokens',8192),
            ('max_format_retries',2),('auxiliary_calls_per_trajectory',61),('seed',1),('shared_actor_instructions_sha256','0'*64)]:
            with self.subTest(field=field):
                p=m.prepare_plan(RAW,STATE);p[field]=value
                with self.assertRaises(ValueError):m.validate_plan(p,original)

if __name__=='__main__':unittest.main()
