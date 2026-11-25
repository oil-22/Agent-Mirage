"""Safety boundaries for the staged arithmetic check, no model-quality assertions."""
import unittest
from pagination_derivation_guard import check_relation,inspect_supported_claim


class Boundaries(unittest.TestCase):
    def test_correct_third_page(self):self.assertEqual(check_relation(3,25,36,50,12)['status'],'arithmetically_consistent')
    def test_observed_wrong_fourth_page(self):self.assertEqual(check_relation(4,25,36,50,12)['status'],'internally_inconsistent')
    def test_correct_fourth_page(self):self.assertEqual(check_relation(4,37,48,50,12)['status'],'arithmetically_consistent')
    def test_partial_final_page(self):self.assertEqual(check_relation(5,49,50,50,12)['status'],'arithmetically_consistent')
    def test_never_infer_capacity_from_partial_span(self):self.assertEqual(check_relation(25,49,50,50,None)['status'],'not_checkable')
    def test_first_small_page(self):self.assertEqual(check_relation(1,1,2,2,12)['status'],'arithmetically_consistent')
    def test_span_too_wide(self):self.assertEqual(check_relation(1,1,13,50,12)['status'],'internally_inconsistent')
    def test_invalid_boolean(self):self.assertEqual(check_relation(True,1,12,50,12)['status'],'invalid_relation')
    def test_zero_capacity(self):self.assertEqual(check_relation(1,1,12,50,0)['status'],'invalid_relation')
    def test_range_over_total(self):self.assertEqual(check_relation(4,37,60,50,12)['status'],'invalid_relation')
    def test_reversed_range(self):self.assertEqual(check_relation(4,48,37,50,12)['status'],'invalid_relation')
    def test_without_page(self):self.assertEqual(check_relation(None,25,36,50,12)['status'],'not_checkable')
    def test_short_nonfinal_page_not_assumed_valid(self):self.assertEqual(check_relation(3,25,30,50,12)['status'],'internally_inconsistent')
    def claim(self):return {'id':'c1','kind':'gui_fact','text':"I'm on page 4",'status':'supported','reason':'Fourth page of a 12-per-page result set','evidence':[{'observation_id':'o','image_index':0,'box_xyxy':[300,200,450,250],'description':"Header reads '25 - 36 of 50 listings'."}]}
    def test_source_bound_wrong_derivation(self):self.assertTrue(inspect_supported_claim(self.claim(),'o')['withhold_supported_feedback'])
    def test_wrong_observation_not_used(self):self.assertEqual(inspect_supported_claim(self.claim(),'new')['status'],'not_checkable')
    def test_missing_capacity_not_invented(self):
        c=self.claim();c['reason']='The current page is fourth';self.assertEqual(inspect_supported_claim(c,'o')['status'],'not_checkable')
    def test_uncertain_claim_never_promoted(self):
        c=self.claim();c['status']='insufficient';self.assertFalse(inspect_supported_claim(c,'o')['withhold_supported_feedback'])
    def test_historical_quote_not_current_range(self):
        c=self.claim();c['evidence']=[{'source':'candidate','span_id':'full','resolved_quote':'25-36 of50'}];self.assertEqual(inspect_supported_claim(c,'o')['status'],'not_checkable')
    def test_does_not_edit_input(self):
        import copy
        c=self.claim();before=copy.deepcopy(c);r=inspect_supported_claim(c,'o');self.assertEqual(c,before);self.assertNotIn('correct_page',r)
    def test_ambiguous_capacity_abstains(self):
        c=self.claim();c['reason']+=' or 10-per-page';self.assertEqual(inspect_supported_claim(c,'o')['status'],'not_checkable')
    def test_negative_page_claim_not_misparsed(self):
        c=self.claim();c['text']="I'm not on page 4";self.assertEqual(inspect_supported_claim(c,'o')['status'],'not_checkable')
    def test_plan_not_promoted_to_current_page(self):
        c=self.claim();c['text']='Let me check page 4';self.assertEqual(inspect_supported_claim(c,'o')['status'],'not_checkable')


if __name__=='__main__':unittest.main()
