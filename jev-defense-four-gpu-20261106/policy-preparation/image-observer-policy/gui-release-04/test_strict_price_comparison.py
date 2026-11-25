import copy,unittest
from strict_price_comparison import check_strict_price_comparison

P={'name':'scroll','payload':{'type':'scroll','direction':'up'}}
ACTUAL='I can confirm the current observation: "Success is a Choice by Rick Pitino" ($5.00) has a book cover image showing a man in a dark suit and tie. This is a strong candidate. However, I cannot yet confirm it is the cheapest item with a man in a suit, because I have not fully verified the cheaper items\x27 images ($1.00, $3.00, and the earlier $5.00 trash cans/pins). To verify the cheaper items, I need to scroll up.'
class StrictComparison(unittest.TestCase):
    def check(self,t):return check_strict_price_comparison(t,P)['reject']
    def test_actual_equal_price_group(self):self.assertTrue(self.check(ACTUAL))
    def test_uncertainty_about_minimum_not_price_order(self):self.assertTrue(self.check(ACTUAL.replace('cannot yet confirm','do not know whether')))
    def test_correct_strict_cheaper_list(self):self.assertFalse(self.check(ACTUAL.replace(', and the earlier $5.00 trash cans/pins','')))
    def test_earlier_items_does_not_mean_cheaper(self):self.assertFalse(self.check(ACTUAL.replace('cheaper items','earlier items')))
    def test_equal_or_cheaper_explicitly_allowed(self):self.assertFalse(self.check(ACTUAL.replace('cheaper items','cheaper or equally priced items')))
    def test_higher_group_conflicts_too(self):self.assertTrue(self.check(ACTUAL.replace('earlier $5.00','earlier $7.00')))
    def test_uncertain_comparator_abstains(self):self.assertFalse(self.check(ACTUAL.replace('($5.00)','(about $5.00)')))
    def test_multiple_comparator_amounts_abstain(self):self.assertFalse(self.check(ACTUAL.replace('This is a strong candidate.','This is a strong candidate. Another candidate costs $10.00.')))
    def test_no_identified_current_candidate_abstains(self):self.assertFalse(self.check('Earlier I saw $5.00 items. The cheaper items ($1.00,$5.00) are unverified.'))
    def test_whether_comparison_is_explicitly_unknown(self):self.assertFalse(self.check('The current candidate is $5.00. I cannot establish whether these are the cheaper items ($1.00,$5.00).'))
    def test_wait_excluded(self):self.assertFalse(check_strict_price_comparison(ACTUAL,{'name':'wait'})['reject'])
    def test_no_candidate_or_action_edit(self):
        p=copy.deepcopy(P);r=check_strict_price_comparison(ACTUAL,p);self.assertEqual(p,P);self.assertFalse(r['candidate_modified']);self.assertFalse(r['quoted_prices_certified'])
    def test_other_prices_no_task_answer(self):self.assertTrue(self.check(ACTUAL.replace('$5.00','$12.50').replace('$3.00','$9.25')))
    def test_action_body_not_a_price_source(self):self.assertFalse(self.check('Current candidate is $5.00. I will examine earlier items. <action>{"text":"cheaper items ($10.00)"}</action>'))

if __name__=='__main__':unittest.main()
