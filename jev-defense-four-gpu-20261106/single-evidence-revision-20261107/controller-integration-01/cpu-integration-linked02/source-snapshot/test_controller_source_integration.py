"""Scripted CPU checks of new control flow; no semantic or model-success claims."""
from __future__ import annotations

import ast
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
RELEASE = HERE / 'release'
PARENT = HERE.parents[1] / 'policy-preparation/image-observer-policy/gui-migration-three-linked02/release'
sys.path.insert(0, str(RELEASE))
from PIL import Image
from defense import core
from defense.core import (BudgetExhausted, Controller, Journal, Limits, PublicView,
    ValidationError, VisibleImage, checked_wait, validate_verdict)
from defense.prompts import HISTORY_REPORT, SCREEN, VERIFY
from claim_origin import EXACT_CLAIM_INSTRUCTIONS
from history_utterance_ledger import SCOPE, build_ledger
from compact_history_utterance_ledger import compact_source_index

ATTEMPT_ROOT = None
CANDIDATE = 'A visible panel is shown. <action>{"type":"scroll","direction":"down"}</action>'
PROPOSAL = {'name':'scroll','payload':{'type':'scroll','direction':'down'},
            'parsed':True,'executor_fallback_wait':False}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fixture():
    stream = io.BytesIO()
    Image.new('RGB', (80, 60), 'blue').save(stream, format='PNG')
    return PublicView('o1', [
        {'role':'user','content':'Task: inspect the current display'},
        {'role':'assistant','content':'I will inspect the display. <action>{"type":"wait"}</action>'},
        {'role':'user','content':[
            {'type':'text','text':'Execution returned; no visual success is certified.'}]},
        {'role':'assistant','content':'I identified a visible panel.'}],
        (VisibleImage(stream.getvalue()),), recent_action='native scroll attempt',
        execution_feedback='returned; current visual state still needs evidence')


def evidence(view):
    return {'observation_id':view.observation_id,'image_index':0,
        'coordinate_space':'pixels','box_xyxy':[0,0,80,60],
        'description':'synthetic CPU fixture panel'}


def verdict(view, text='A visible panel is shown.', status='supported'):
    return {'claims':[{'id':'c1','kind':'gui_fact','text':text,'status':status,
        'evidence':[evidence(view)] if status in {'supported','contradicted'} else [],
        'reason':'scripted fixture; no semantic inference','dependent_decisions':['action']}],
        'action':{'status':'supported','target_kind':'content',
            'reason':'scripted fixture','evidence':[evidence(view)]},
        'acknowledges_visual_deficit':False,'pure_wait':False}


def events(path):
    return [json.loads(line) for line in (path / 'events.jsonl').read_text(encoding='utf8').splitlines()]


def ast_dump(node):
    return ast.dump(node, include_attributes=False)


class SourceIntegrationTests(unittest.TestCase):
    def setUp(self):
        # Keep native Windows image-artifact paths below MAX_PATH without changing
        # the Controller journal or its original artifact naming behavior.
        self.run_root = ATTEMPT_ROOT / 'j' / self._testMethodName.split('_')[1]
        self.view = fixture()

    def ctl(self, callback, **limits):
        return Controller(callback, Journal(self.run_root), 'post_only', Limits(**limits), sleeper=lambda _:None)

    def rows(self, kind):
        return [event['data'] for event in events(self.run_root) if event['kind'] == kind]

    def test_01_unchanged_native_validator_asts(self):
        old = ast.parse((PARENT/'defense/core.py').read_text(encoding='utf8'))
        new = ast.parse((RELEASE/'defense/core.py').read_text(encoding='utf8'))
        old_funcs = {node.name:node for node in old.body if isinstance(node, ast.FunctionDef)}
        new_funcs = {node.name:node for node in new.body if isinstance(node, ast.FunctionDef)}
        self.assertEqual(set(old_funcs), set(new_funcs))
        for name in old_funcs:
            self.assertEqual(ast_dump(old_funcs[name]), ast_dump(new_funcs[name]), name)
        self.assertEqual(len([name for name in old_funcs if name.startswith('validate_')]), 6)

    def test_02_limits_and_all_other_controller_methods_asts_unchanged(self):
        old = ast.parse((PARENT/'defense/core.py').read_text(encoding='utf8'))
        new = ast.parse((RELEASE/'defense/core.py').read_text(encoding='utf8'))
        classes = lambda tree:{node.name:node for node in tree.body if isinstance(node, ast.ClassDef)}
        before, after = classes(old), classes(new)
        self.assertEqual(set(before), set(after))
        for name in before:
            if name != 'Controller':
                self.assertEqual(ast_dump(before[name]), ast_dump(after[name]), name)
        methods = lambda node:{part.name:part for part in node.body if isinstance(part, ast.FunctionDef)}
        before, after = methods(before['Controller']), methods(after['Controller'])
        self.assertEqual(set(before), set(after))
        for name in before:
            if name != 'inspect':
                self.assertEqual(ast_dump(before[name]), ast_dump(after[name]), name)
        self.assertNotEqual(ast_dump(before['inspect']), ast_dump(after['inspect']))
        self.assertEqual(Limits().max_format_retries, 1)
        self.assertEqual(Limits().max_verifier_calls, 140)
        self.assertEqual(Limits().max_actor_calls, 70)
        self.assertEqual((Limits().max_recaptures, Limits().max_regenerations), (2, 2))

    def test_03_byte_identity_all_copies_except_core(self):
        receipt = json.loads((HERE/'source-build-receipt.json').read_text(encoding='utf8'))
        self.assertEqual(receipt['modified_parent_files'], ['defense/core.py'])
        for item in receipt['files']:
            target = RELEASE/item['relative_path']
            self.assertEqual(sha(target.read_bytes()), item['release_sha256'])
            self.assertEqual(sha(Path(item['source']).read_bytes()), item['source_sha256'])
            if item['relative_path'] != 'defense/core.py':
                self.assertEqual(target.read_bytes(), Path(item['source']).read_bytes())

    def test_04_exact_claim_one_callback_and_public_unchanged(self):
        original = copy.deepcopy(self.view.data())
        seen = []
        def callback(system, view, candidate):
            seen.append((system,view,candidate))
            return verdict(view)
        controller = self.ctl(callback)
        self.assertEqual(controller.inspect('verify',self.view,CANDIDATE,PROPOSAL)['claims'][0]['status'],'supported')
        self.assertEqual(controller.verifier_calls,1)
        self.assertEqual(len(seen),1)
        self.assertEqual(self.view.data(),original)
        self.assertIs(seen[0][1],self.view)
        self.assertEqual(seen[0][2],CANDIDATE)
        self.assertEqual(self.rows('verifier_request')[0]['proposal'],PROPOSAL)

    def test_05_actual_system_equals_journal_before_callback(self):
        def callback(system, view, candidate):
            row = self.rows('verifier_request')[-1]
            self.assertEqual(row['system'],system)
            self.assertEqual(row['candidate'],candidate)
            self.assertEqual(row['public'],view.data())
            self.assertTrue(system.startswith(VERIFY))
            self.assertIn(EXACT_CLAIM_INSTRUCTIONS,system)
            self.assertIn(SCOPE,system)
            return verdict(view)
        controller=self.ctl(callback)
        controller.inspect('verify',self.view,CANDIDATE,PROPOSAL)
        prepared=self.rows('history_utterance_ledger_prepared')
        self.assertEqual(len(prepared),1)
        self.assertEqual(prepared[0]['augmented_system_utf8_sha256'],sha(self.rows('verifier_request')[0]['system'].encode('utf8')))

    def test_06_full_audit_ledger_compact_index_and_original_indices_match(self):
        controller=self.ctl(lambda _,view,__ : verdict(view))
        controller.inspect('verify',self.view,CANDIDATE,PROPOSAL)
        row=self.rows('history_utterance_ledger_prepared')[0]
        full=build_ledger(self.view); compact=compact_source_index(full)
        self.assertEqual(row['ledger'],full)
        self.assertEqual(row['compact_model_index'],compact)
        self.assertEqual([record['message_index'] for record in compact['records']],[1,3])
        self.assertEqual(row['full_ledger_sha256'],sha(core.canonical(full)))
        self.assertEqual(row['compact_model_index_sha256'],sha(core.canonical(compact)))
        self.assertTrue(row['source_metadata_not_a_verdict'])

    def test_07_invented_extraction_original_validator_pass_new_origin_rejects(self):
        bad=verdict(self.view,'The panel is absent.')
        validate_verdict(copy.deepcopy(bad),self.view,CANDIDATE,PROPOSAL)
        controller=self.ctl(lambda *_:copy.deepcopy(bad))
        with self.assertRaisesRegex(ValidationError,'Exact candidate extraction provenance invalid'):
            controller.inspect('verify',self.view,CANDIDATE,PROPOSAL)
        self.assertEqual(controller.verifier_calls,2)
        self.assertEqual([item['format_retry'] for item in self.rows('verifier_request')],[0,1])
        self.assertEqual(len(self.rows('verifier_raw')),2)
        self.assertEqual(len(self.rows('candidate_claim_origin_check')),2)
        self.assertEqual(len(self.rows('verifier_format_failure')),2)

    def test_08_bad_then_exact_uses_same_public_candidate_and_one_retry(self):
        answers=iter(['Synthetic premise not stated.','A visible panel is shown.'])
        calls=[]
        def callback(system,view,candidate):
            calls.append((system,view.data(),candidate))
            self.assertEqual(system,self.rows('verifier_request')[-1]['system'])
            return verdict(view,next(answers))
        controller=self.ctl(callback)
        result=controller.inspect('verify',self.view,CANDIDATE,PROPOSAL)
        self.assertEqual(result['claims'][0]['text'],'A visible panel is shown.')
        self.assertEqual(controller.verifier_calls,2)
        self.assertEqual(calls[0][1:],calls[1][1:])
        self.assertTrue(calls[1][0].startswith(calls[0][0]))
        self.assertEqual(len(self.rows('history_utterance_ledger_prepared')),1)
        self.assertEqual([row['reject'] for row in self.rows('candidate_claim_origin_check')],[True,False])

    def test_09_origin_does_not_relax_original_citations(self):
        bad=verdict(self.view)
        bad['claims'][0]['evidence']=[{'source':'candidate','span_id':'full'}]
        controller=self.ctl(lambda *_:copy.deepcopy(bad))
        with self.assertRaisesRegex(ValidationError,'Candidate cannot prove its own factual claim'):
            controller.inspect('verify',self.view,CANDIDATE,PROPOSAL)
        self.assertEqual(controller.verifier_calls,2)
        self.assertEqual(self.rows('candidate_claim_origin_check'),[])

    def test_10_original_140_cap_blocks_hidden_third_or_overflow_call(self):
        actual=[]
        def callback(*_):
            actual.append(True)
            return verdict(self.view,'Synthetic premise not stated.')
        controller=self.ctl(callback);controller.verifier_calls=139
        with self.assertRaisesRegex(BudgetExhausted,'verifier_call_cap'):
            controller.inspect('verify',self.view,CANDIDATE,PROPOSAL)
        self.assertEqual(controller.verifier_calls,140)
        self.assertEqual(len(actual),1)
        self.assertEqual(len(self.rows('verifier_raw')),1)

    def test_11_zero_remaining_budget_never_calls_backend(self):
        controller=self.ctl(lambda *_:self.fail('backend called past original cap'))
        controller.verifier_calls=140
        with self.assertRaises(BudgetExhausted):
            controller.inspect('verify',self.view,CANDIDATE,PROPOSAL)
        self.assertEqual(self.rows('verifier_request'),[])

    def test_12_no_retry_setting_is_respected(self):
        controller=self.ctl(lambda *_:verdict(self.view,'Synthetic premise not stated.'),max_format_retries=0)
        with self.assertRaises(ValidationError):
            controller.inspect('verify',self.view,CANDIDATE,PROPOSAL)
        self.assertEqual(controller.verifier_calls,1)

    def test_13_history_relation_only_gets_index_not_candidate_contract(self):
        text_view=core.replace(self.view,images=())
        pair=json.dumps({'actual_candidate':'I identified a visible panel.',
            'queried_history_claim':'I identified a visible panel.','query_is_not_an_observed_fact':True})
        def callback(system,view,candidate):
            self.assertTrue(system.startswith(HISTORY_REPORT))
            self.assertIn(SCOPE,system)
            self.assertNotIn(EXACT_CLAIM_INSTRUCTIONS,system)
            self.assertEqual(candidate,pair)
            self.assertEqual(system,self.rows('verifier_request')[-1]['system'])
            return {'status':'supported','reason':'bounded prior textual report',
                'evidence':[{'message_index':3,'span_id':'full'}]}
        controller=self.ctl(callback)
        self.assertEqual(controller.inspect('history_report',text_view,pair)['status'],'supported')
        self.assertEqual(controller.verifier_calls,1)
        self.assertEqual(self.rows('candidate_claim_origin_check'),[])

    def test_14_history_relation_cannot_claim_support_from_plan_only(self):
        text_view=core.replace(self.view,images=())
        pair=json.dumps({'actual_candidate':'I inspected the display.',
            'queried_history_claim':'I inspected the display.','query_is_not_an_observed_fact':True})
        controller=self.ctl(lambda *_:{'status':'supported','reason':'scripted plan-only source',
            'evidence':[{'message_index':1,'span_id':'full'}]})
        with self.assertRaisesRegex(ValidationError,'Plan-only source cannot establish'):
            controller.inspect('history_report',text_view,pair)
        self.assertEqual(controller.verifier_calls,2)
        self.assertEqual(self.rows('candidate_claim_origin_check'),[])

    def test_15_pure_native_wait_keeps_exclusion_and_actor_public(self):
        wait='<action>{"type":"wait"}</action>'
        parsed={'name':'wait','payload':{'type':'wait'},'parsed':True,'executor_fallback_wait':False}
        actor_calls=[]
        def actor(view,corrections):
            actor_calls.append((view.data(),corrections))
            return wait
        def callback(system,view,candidate):
            self.assertEqual(candidate,wait)
            return {'claims':[],'action':{'status':'supported','target_kind':'not_applicable',
                'reason':'native wait only; no definite loading assertion',
                'evidence':[{'source':'candidate','span_id':'full'}]},
                'acknowledges_visual_deficit':False,'pure_wait':True}
        controller=self.ctl(callback)
        result=controller.decide(self.view,actor,lambda text:copy.deepcopy(parsed),None)
        self.assertEqual(result['status'],'accepted')
        self.assertTrue(result['execution_pending'])
        self.assertEqual((controller.actor_calls,controller.verifier_calls),(1,1))
        self.assertEqual(actor_calls,[(self.view.data(),[])])
        self.assertTrue(self.rows('verdict')[0]['pure_wait_excluded'])
        self.assertTrue(checked_wait(parsed))
        self.assertFalse(checked_wait(dict(parsed,executor_fallback_wait=True)))
        self.assertEqual(self.rows('action_executed'),[])

    def test_16_normal_scroll_accepts_without_actor_or_auxiliary_context_changes(self):
        received=[]
        def actor(view,corrections):
            received.append((view.data(),corrections))
            return CANDIDATE
        controller=self.ctl(lambda _,view,__ :verdict(view))
        result=controller.decide(self.view,actor,lambda _:copy.deepcopy(PROPOSAL),None)
        self.assertEqual(result['status'],'accepted')
        self.assertEqual(received,[(self.view.data(),[])])
        self.assertEqual((controller.actor_calls,controller.verifier_calls),(1,1))
        self.assertFalse(self.rows('verdict')[0]['pure_wait_excluded'])
        self.assertEqual(self.rows('action_executed'),[])

    def test_17_uncertain_claim_not_rewritten_to_supported(self):
        controller=self.ctl(lambda _,view,__ :verdict(view,status='uncertain'))
        result=controller.inspect('verify',self.view,CANDIDATE,PROPOSAL)
        self.assertEqual(result['claims'][0]['status'],'uncertain')
        self.assertEqual(result['claims'][0]['evidence'],[])
        self.assertFalse(self.rows('candidate_claim_origin_check')[0]['semantic_truth_or_claim_completeness_established'])

    def test_18_screen_phase_system_and_view_unchanged(self):
        def callback(system,view,candidate):
            self.assertTrue(system.startswith(SCREEN))
            self.assertNotIn(EXACT_CLAIM_INSTRUCTIONS,system)
            self.assertNotIn(SCOPE,system)
            self.assertIs(view,self.view)
            return {'status':'usable','visible':['panel'],'limitations':[],
                'loading':'not_observed','evidence':[evidence(view)],'reason':'scripted fixture'}
        controller=self.ctl(callback)
        self.assertEqual(controller.inspect('screen',self.view)['status'],'usable')
        self.assertEqual(self.rows('history_utterance_ledger_prepared'),[])
        self.assertEqual(self.rows('candidate_claim_origin_check'),[])

    def test_19_journal_chain_verifies_including_new_audit_artifacts(self):
        controller=self.ctl(lambda _,view,__ :verdict(view))
        controller.inspect('verify',self.view,CANDIDATE,PROPOSAL)
        previous='0'*64
        for seq,event in enumerate(events(self.run_root)):
            supplied=event.pop('sha256')
            self.assertEqual(event['seq'],seq)
            self.assertEqual(event['previous'],previous)
            self.assertEqual(sha(core.canonical(event)),supplied)
            previous=supplied

    def test_20_release_contains_no_live_transport_backend_or_launcher(self):
        files=[path.relative_to(RELEASE).as_posix() for path in RELEASE.rglob('*.py')]
        for name in files:
            self.assertFalse(any(fragment in Path(name).name for fragment in
                ['run_','launch','remote','transport','backend','observer','auxiliary']),name)
        self.assertEqual(set(path.suffix for path in RELEASE.rglob('*') if path.is_file()),{'.py'})
        self.assertNotIn('torch',sys.modules)

    def test_21_origin_failure_stops_decide_without_rewriting_actor(self):
        candidates=[]
        def actor(view,corrections):
            candidates.append(CANDIDATE)
            self.assertEqual(corrections,[])
            return CANDIDATE
        controller=self.ctl(lambda _,view,__ :verdict(view,'Synthetic premise not stated.'))
        result=controller.decide(self.view,actor,lambda _:copy.deepcopy(PROPOSAL),None)
        self.assertEqual(result['status'],'blocked')
        self.assertTrue(result['reason'].startswith('candidate_verifier_error:Exact candidate extraction provenance invalid'))
        self.assertEqual((controller.actor_calls,controller.verifier_calls),(1,2))
        self.assertEqual(candidates,[CANDIDATE])
        self.assertEqual((result['regenerations'],result['recaptures']),(0,0))
        self.assertEqual(self.rows('action_executed'),[])


def run_attempt():
    global ATTEMPT_ROOT
    if len(sys.argv)!=2:
        raise SystemExit('Supply a NEW attempt directory name inside this package')
    attempt_name=sys.argv[1]
    if Path(attempt_name).name!=attempt_name:
        raise SystemExit('Attempt must be a simple directory name')
    ATTEMPT_ROOT=HERE/attempt_name
    ATTEMPT_ROOT.mkdir(exist_ok=False)
    # Snapshot every tested byte before running, including failed attempts.
    snapshot=ATTEMPT_ROOT/'source-snapshot'; snapshot.mkdir()
    for path in [*RELEASE.rglob('*.py'),Path(__file__),HERE/'build_isolated_release.py',HERE/'source-build-receipt.json']:
        relative=Path('release')/path.relative_to(RELEASE) if path.is_relative_to(RELEASE) else Path(path.name)
        target=snapshot/relative;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(path.read_bytes())
    log=io.StringIO()
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SourceIntegrationTests))
    (ATTEMPT_ROOT/'tests.log').write_text(log.getvalue(),encoding='utf8')
    receipt={'kind':'scripted_cpu_source_integration_only','tests_run':result.testsRun,
        'failures':len(result.failures),'errors':len(result.errors),'successful':result.wasSuccessful(),
        'failure_details':[{'test':str(test),'traceback':trace} for test,trace in result.failures+result.errors],
        'release':str(RELEASE),'parent_release':str(PARENT),
        'linked_previous_attempt':str(HERE/'cpu-integration-attempt-01') if attempt_name!='cpu-integration-attempt-01' else None,
        'model_calls':0,'gpu_allocations':0,'gui_actions':0,'paid_api_calls':0,
        'semantic_effectiveness_established':False,'launch_ready':False}
    (ATTEMPT_ROOT/'result.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    files=[{'path':path.relative_to(ATTEMPT_ROOT).as_posix(),'bytes':path.stat().st_size,
        'sha256':sha(path.read_bytes())} for path in sorted(ATTEMPT_ROOT.rglob('*')) if path.is_file()]
    seal={'files':files,'source_and_failed_test_outputs_preserved':True}
    (ATTEMPT_ROOT/'seal.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'attempt':str(ATTEMPT_ROOT),'tests':result.testsRun,
        'successful':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors)},ensure_ascii=False))
    if not result.wasSuccessful():
        print(log.getvalue())
        raise SystemExit(1)


if __name__=='__main__':
    run_attempt()
