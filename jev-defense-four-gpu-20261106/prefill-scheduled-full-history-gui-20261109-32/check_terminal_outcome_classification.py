"""Synthetic CPU terminal accounting checks; not visual/WAIT semantic controls."""
import unittest

from terminal_outcome_classification import LOCAL_VERIFIER_CAP_REASONS, classify_run_termination as classify


class TerminalClassificationControls(unittest.TestCase):
    def test_exact_local_budget_catches(self):
        for reason in LOCAL_VERIFIER_CAP_REASONS:
            with self.subTest(reason=reason):
                result=classify('blocked',reason,'complete',140,140)
                self.assertTrue(result['local_verifier_budget_exhausted'])
                self.assertEqual(result['original_terminal_classification_without_repair'],'verifier_failure')
                self.assertEqual(result['technical_status'],'no_reported_infrastructure_failure')
                self.assertEqual(result['new_calls_or_retries_granted'],0)

    def test_counter_mismatch_does_not_reclassify(self):
        self.assertEqual(classify('blocked','price_history_verifier_error:verifier_call_cap','complete',139,140)
                         ['technical_status'],'verifier_failure')

    def test_transport_failure_not_reclassified_at_full_budget(self):
        self.assertEqual(classify('blocked','point_verifier_error:Verifier transport failure: HTTP500','complete',140,140)
                         ['technical_status'],'verifier_failure')

    def test_contract_failure_not_reclassified_at_full_budget(self):
        self.assertEqual(classify('blocked','candidate_verifier_error:Invalid evidence source','complete',140,140)
                         ['technical_status'],'verifier_failure')

    def test_substring_or_model_text_not_local_cap_proof(self):
        for reason in ['price_history_verifier_error:verifier_call_cap trailing',
                       'model text: price_history_verifier_error:verifier_call_cap',
                       'unknown_verifier_error:verifier_call_cap']:
            with self.subTest(reason=reason):
                self.assertFalse(classify('blocked',reason,'complete',140,140)['local_verifier_budget_exhausted'])

    def test_scoring_failure_retained_even_with_local_cap(self):
        result=classify('blocked','point_verifier_error:verifier_call_cap','failed',140,140)
        self.assertTrue(result['local_verifier_budget_exhausted'])
        self.assertEqual(result['technical_status'],'scoring_failure')

    def test_normal_stop_unchanged(self):
        self.assertFalse(classify('model_stop','','complete',12,140)['local_verifier_budget_exhausted'])

    def test_normal_WAIT_input_is_not_an_outcome_error(self):
        result=classify('step_cap','','complete',140,140)
        self.assertEqual(result['technical_status'],'no_reported_infrastructure_failure')
        self.assertFalse(result['local_verifier_budget_exhausted'])

    def test_semantic_rejection_or_regeneration_cap_unchanged(self):
        self.assertFalse(classify('blocked','regeneration_cap','complete',140,140)['local_verifier_budget_exhausted'])

    def test_nonblocked_cap_string_not_reclassified(self):
        self.assertFalse(classify('model_stop','point_verifier_error:verifier_call_cap','complete',140,140)
                         ['local_verifier_budget_exhausted'])

    def test_wrong_cap_or_bad_counter_rejected(self):
        for count,cap in [(140,141),(141,140),(-1,140),(True,140)]:
            with self.subTest(count=count,cap=cap),self.assertRaises(ValueError):
                classify('blocked','point_verifier_error:verifier_call_cap','complete',count,cap)

    def test_positive_local_budget_does_not_approve_action_or_efficacy(self):
        result=classify('blocked','point_verifier_error:verifier_call_cap','complete',140,140)
        self.assertTrue(result['original_blocked_candidate_still_not_executed'])
        self.assertTrue(result['semantic_Mirage_or_defense_efficacy_not_inferred'])


if __name__=='__main__':unittest.main(verbosity=2)
