import copy,unittest
from current_only_history_scope import check_current_only_history,check_historical_event_sources
from types import SimpleNamespace

class HistorySourceBoundary(unittest.TestCase):
    def check(self,text):return check_current_only_history({'limitations':[text]})['reject']
    def test_not_executed_is_rejected(self):self.assertTrue(self.check('The keyword is typed but Search has not been executed.'))
    def test_negative_history_rejected(self):self.assertTrue(self.check('No basketball search has been performed.'))
    def test_positive_execution_also_outside_projection(self):self.assertTrue(self.check('The search has been performed successfully.'))
    def test_click_causal_assertion_rejected(self):self.assertTrue(self.check('The click was completed.'))
    def test_never_inspected_rejected(self):self.assertTrue(self.check('The actor never inspected this page.'))
    def test_current_absence_not_history(self):self.assertFalse(self.check('No basketball search results are visible.'))
    def test_current_input_text_allowed(self):self.assertFalse(self.check('The search field contains basketball.'))
    def test_no_evidence_qualification_allowed(self):self.assertFalse(self.check('No evidence shows that a search has been performed.'))
    def test_whether_uncertainty_allowed(self):self.assertFalse(self.check('Cannot determine whether the search has been performed.'))
    def test_unknown_scope_allowed(self):self.assertFalse(self.check('It is unknown whether the query was submitted.'))
    def test_report_quote_not_automatic_reject(self):self.assertFalse(self.check('The text says "Search has not been executed".'))
    def test_future_plan_allowed(self):self.assertFalse(self.check('A search will be performed after focus is checked.'))
    def test_cue_visible_allowed(self):self.assertFalse(self.check('The City input has a distinct blue focus outline.'))
    def test_focus_cause_uncertainty_allowed(self):self.assertFalse(self.check('Cannot establish the cause of the current focus outline.'))
    def test_current_no_results_template_allowed(self):self.assertFalse(self.check('A readable no-results notice is currently visible.'))
    def test_no_output_mutation(self):
        x={'reason':'Search has not been executed.'};before=copy.deepcopy(x);r=check_current_only_history(x)
        self.assertTrue(r['reject']);self.assertEqual(x,before);self.assertFalse(r['opposite_fact_supplied'])
    def test_nested_claims_not_reinterpreted_as_current_reader(self):self.assertFalse(check_current_only_history({'claims':[{'text':'No search has been performed.'}]})['reject'])
    def test_unrecognized_is_explicitly_not_approval(self):self.assertTrue(check_current_only_history({'reason':'ambiguous words'})['unflagged_is_not_approval'])
    def hcheck(self,status='contradicted',role='current',text='No earlier search has ever been performed'):
        v=SimpleNamespace(images=[SimpleNamespace(role=role)],messages=[])
        x={'claims':[{'id':'c1','kind':'history_report','text':text,'status':status,'evidence':[{'image_index':0}]}]}
        return check_historical_event_sources(x,v)
    def test_current_input_does_not_prove_past_execution(self):self.assertTrue(self.hcheck()['reject'])
    def test_current_input_does_not_prove_never_execution(self):self.assertTrue(self.hcheck(status='supported')['reject'])
    def test_earlier_reference_is_eligible_not_approval(self):self.assertFalse(self.hcheck(role='reference')['reject'])
    def test_insufficient_history_kept(self):self.assertFalse(self.hcheck(status='insufficient')['reject'])
    def test_current_plain_field_fact_outside_guard(self):self.assertFalse(self.hcheck(text='The field currently contains text')['reject'])
    def test_plan_report_outside_event_guard(self):self.assertFalse(self.hcheck(text='I earlier stated a plan to inspect results')['reject'])
if __name__=='__main__':unittest.main()
