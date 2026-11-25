import copy,unittest
from minimum_price_reason_scope import minimum_reason_check

TASK='Search for basketball and navigate to the cheapest item that has a man in a suit in its image.'
ACTUAL='Ascending order and cheaper prefix are covered, but the full set of equal-price ($5.00) candidates is not fully inspected; a cheaper-suit item cannot be ruled out among unviewed $5.00 listings'
def verdict(reason=ACTUAL,status='insufficient',text='This book is the cheapest matching item.'):
    return {'claims':[{'kind':'gui_fact','text':text,'status':status,'reason':reason,'evidence':[]}],'action':{'status':'insufficient','reason':'original untouched'}}
class Boundaries(unittest.TestCase):
    def test_actual_online_reason_quarantined(self):self.assertTrue(minimum_reason_check(verdict(),TASK)['reject'])
    def test_no_status_or_action_rewrite(self):
        value=verdict();old=copy.deepcopy(value);r=minimum_reason_check(value,TASK);self.assertEqual(value,old);self.assertFalse(r['minimum_certified']);self.assertFalse(r['replacement_action_supplied'])
    def test_unestablished_order_remains_unresolved(self):
        self.assertFalse(minimum_reason_check(verdict('Ascending order is not confirmed and equal-price candidates are not fully inspected.'),TASK)['reject'])
    def test_uncovered_cheaper_prefix_is_valid_missing_premise(self):
        self.assertFalse(minimum_reason_check(verdict('Ascending order and cheaper prefix are not covered; equal-price candidates are not fully inspected.'),TASK)['reject'])
    def test_qualified_incomplete_prefix_not_confused_with_covered(self):
        self.assertFalse(minimum_reason_check(verdict('Ascending order and cheaper prefix are only partly covered; equal-price candidates are not fully inspected.'),TASK)['reject'])
    def test_specific_unreadable_cheaper_row_not_quarantined(self):
        self.assertFalse(minimum_reason_check(verdict('The cheaper prefix has an unreadable three-dollar card image; its clothing is unresolved.'),TASK)['reject'])
    def test_supported_minimum_not_relabelled(self):self.assertFalse(minimum_reason_check(verdict(status='supported'),TASK)['reject'])
    def test_nonminimum_claim_not_targeted(self):self.assertFalse(minimum_reason_check(verdict(text='The current item title is readable.'),TASK)['reject'])
    def test_unique_goal_requires_separate_scope(self):self.assertFalse(minimum_reason_check(verdict(),TASK+' Establish uniqueness.')['reject'])
    def test_all_matches_goal_not_minimum_only(self):self.assertFalse(minimum_reason_check(verdict(),TASK+' Return all matches.')['reject'])
    def test_nonminimum_task_not_targeted(self):self.assertFalse(minimum_reason_check(verdict(),'Find every matching item.')['reject'])
    def test_missing_task_abstains(self):self.assertFalse(minimum_reason_check(verdict(),None)['reject'])
    def test_simple_equal_price_observation_not_rejected(self):
        self.assertFalse(minimum_reason_check(verdict('Ascending order and cheaper prefix are covered. Equal-price candidates are visible; the current detail is unreadable.'),TASK)['reject'])
    def test_negative_cue_reason_not_affected(self):self.assertFalse(minimum_reason_check(verdict('The input has no visible focus cue.'),TASK)['reject'])

if __name__=='__main__':unittest.main()
