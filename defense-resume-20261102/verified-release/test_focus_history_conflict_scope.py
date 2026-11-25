import copy,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from focus_history_conflict_scope import focus_absence_asserted,focus_absence_conflict,plan_only_source,plan_source_check,comparative_history

class SourceBoundaries(unittest.TestCase):
    def test_negative_focus_subclaim_inside_uncertainty(self):
        self.assertTrue(focus_absence_asserted('I cannot confirm focus, since there is no visible focus cue.'))
    def test_uncertainty_alone_is_not_negative_cue(self):
        self.assertFalse(focus_absence_asserted('I am uncertain whether this field is focused.'))
    def test_border_not_necessarily_focus(self):
        self.assertFalse(focus_absence_conflict('There is no visible focus cue.',{'status':'unknown'})['reject'])
    def test_real_disagreement_withholds_no_action_rewrite(self):
        s='The image shows no visible focus cue.\n<action>{"type":"click"}</action>';r={'status':'usable','visible':['Distinct outline on an input']};before=copy.deepcopy(r)
        x=focus_absence_conflict(s,r);self.assertTrue(x['reject']);self.assertFalse(x['candidate_modified']);self.assertFalse(x['verdict_modified']);self.assertEqual(r,before)
    def test_ordinary_frame_not_forced_positive(self):
        self.assertFalse(focus_absence_conflict('No clear focus indicator.',{'status':'limited'})['reject'])
    def test_field_specific_uncertainty_not_global_absence(self):
        self.assertFalse(focus_absence_asserted('The Keyword field may not be focused; City has an outline.'))
    def test_native_action_text_not_visual_assertion(self):
        self.assertFalse(focus_absence_asserted('I will type. <action>{"type":"type","text":"no visible focus cue"}</action>'))
    def test_actual_failed_plan_source(self):
        self.assertTrue(plan_only_source('I need to examine the cheaper items at the top of the list. I\'ll scroll up to see the items to check their images. <action>{"type":"scroll","direction":"up"}</action>'))
    def test_native_click_is_attempt_not_inspection_report(self):
        self.assertTrue(plan_only_source('I will inspect the image. <action>{"type":"click"}</action>'))
    def test_actual_completed_report_remains_eligible(self):
        self.assertFalse(plan_only_source('I inspected the earlier image. I will scroll down next.'))
    def test_present_observation_is_not_past_event_certification(self):
        self.assertTrue(plan_only_source('The list is visible. I will inspect the cheaper items.'))
    def test_unknown_source_not_assumed_plan(self):
        self.assertFalse(plan_only_source('Unrecognized original source.'))
    def scope(self,text='I will inspect the item.'):
        return SimpleNamespace(messages=[{'role':'assistant','content':text}])
    def relation(self):return {'status':'supported','reason':'scripted','evidence':[{'message_index':0}]}
    def test_plan_cannot_support_completed_history(self):
        self.assertTrue(plan_source_check(self.relation(),self.scope(),'I previously inspected the item.')['reject'])
    def test_report_of_plan_allowed(self):
        self.assertFalse(plan_source_check(self.relation(),self.scope(),'I previously stated a plan to inspect the item.')['reject'])
    def test_insufficient_not_relabelled(self):
        r=self.relation();r['status']='insufficient';self.assertFalse(plan_source_check(r,self.scope(),'I previously inspected the item.')['reject'])
    def test_actual_report_source_allowed_but_not_truth_certified(self):
        self.assertFalse(plan_source_check(self.relation(),self.scope('I inspected the item.'),'I previously inspected the item.')['reject'])
    def test_image_source_not_treated_as_plan_only(self):
        r=self.relation();r['evidence'].append({'image_index':0});self.assertFalse(plan_source_check(r,self.scope(),'I previously inspected the item.')['reject'])
    def test_main_history_supported_plan_only_withheld(self):
        r={'claims':[dict(self.relation(),kind='history_report',text='I inspected the item.')]};old=copy.deepcopy(r)
        self.assertTrue(plan_source_check(r,self.scope())['reject']);self.assertEqual(r,old)
    def test_first_price_order_is_comparative(self):self.assertTrue(comparative_history('This was the first item in price order whose image matched.'))
    def test_record_of_title_not_comparative(self):self.assertFalse(comparative_history('I earlier recorded the listing title.'))

class ControllerIntegration(unittest.TestCase):
    def setUp(self):
        from defense.core import Controller,Journal,Limits
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)
        self.Controller=Controller;self.Journal=Journal;self.Limits=Limits
    def ctl(self,judge):return self.Controller(judge,self.Journal(self.path/'journal'),'post_only',self.Limits(probe_current_targets=True),sleeper=lambda _:None)
    def test_plan_only_relation_uses_original_retry_without_label_edit(self):
        from test_native_direction_development import view
        v=view();v.messages[1]={'role':'assistant','content':'I will inspect the image.'};calls=[]
        def judge(system,public,candidate):
            calls.append(system);return {'status':'supported'if len(calls)==1 else'insufficient','reason':'test relation','evidence':[{'message_index':1,'span_id':'full'}]if len(calls)==1 else[]}
        c=self.ctl(judge);pair=json.dumps({'queried_history_claim':'I previously inspected the image.'});r=c.inspect('history_report',v.__class__(v.observation_id,v.messages,()),pair)
        self.assertEqual(r['status'],'insufficient');self.assertEqual(c.verifier_calls,2)
        events=[json.loads(x)for x in(self.path/'journal/events.jsonl').read_text().splitlines()];self.assertTrue(any(e['kind']=='plan_only_history_source'and e['data']['reject']for e in events))
    def test_focus_assertion_checked_for_non_typing_action(self):
        from test_native_direction_development import view,verdict,parse
        from test_scoped_controller_integration import screen
        calls=[]
        def judge(system,v,candidate):
            calls.append('focus'if candidate is None else'verify')
            return screen(v)if candidate is None else verdict(v)
        c=self.ctl(judge);s='There is no visible focus cue. <action>{"type":"wait"}</action>'
        # A genuine WAIT remains excluded from the new conflict mechanism.
        r=c.decide(view(),lambda *_:s,parse,None)
        self.assertEqual(calls,['verify']);self.assertEqual(r['reason'],'wait_parser_verifier_disagreement')
    def test_conflict_does_not_execute_or_rewrite_click(self):
        from test_native_direction_development import view,verdict,parse
        from test_scoped_controller_integration import screen
        def judge(system,v,candidate):return screen(v)if candidate is None else verdict(v)
        c=self.ctl(judge);s='There is no visible focus cue. <action>{"type":"scroll","direction":"down"}</action>'
        # No recapture is available: independent disagreement withholds in original flow.
        r=c.decide(view(),lambda *_:s,parse,None);self.assertEqual(r['status'],'blocked')
        events=[json.loads(x)for x in(self.path/'journal/events.jsonl').read_text().splitlines()];self.assertTrue(any(e['kind']=='focus_absence_consistency'and e['data']['reject']for e in events));self.assertFalse(any(e['kind']=='action_executed'for e in events))

if __name__=='__main__':unittest.main()
