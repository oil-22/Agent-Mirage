import copy,unittest
from types import SimpleNamespace
from price_history_binding import needs_price_history,task_text

class Routing(unittest.TestCase):
    def test_actual_misbinding(self):
        self.assertTrue(needs_price_history('The cheaper $1.00/$3.00 items I saw showed cards, boxes, trash cans, pins, binders, and cartridges.',{'name':'back'}))
    def test_correct_historical_price(self):self.assertTrue(needs_price_history('I saw the trash can at $5.00.',{'name':'scroll'}))
    def test_money_after_number(self):self.assertTrue(needs_price_history('I observed the book at 5 dollars.',{'name':'stop'}))
    def test_pure_wait_excluded(self):self.assertFalse(needs_price_history('I saw the book at $5.',{'name':'wait'}))
    def test_future_inspection_not_historical(self):self.assertFalse(needs_price_history('I will inspect the $1 and $3 items.',{'name':'scroll'}))
    def test_current_only_not_historical(self):self.assertFalse(needs_price_history('The current book is $5.',{'name':'click'}))
    def test_no_price_not_targeted(self):self.assertFalse(needs_price_history('I saw a book.',{'name':'back'}))
    def test_never_treat_text_as_true(self):
        candidate='I saw a secret object for $3.';old=copy.deepcopy(candidate);self.assertTrue(needs_price_history(candidate,{'name':'back'}));self.assertEqual(candidate,old)
    def test_task_from_legal_user_text(self):
        v=SimpleNamespace(messages=[{'role':'assistant','content':'Task: hidden invented claim'},{'role':'user','content':[{'type':'text','text':'Task: Find cheapest\nPrevious observation request. original'}]}])
        self.assertEqual(task_text(v),'Find cheapest')
    def test_absent_task_abstains(self):self.assertIsNone(task_text(SimpleNamespace(messages=[])))

if __name__=='__main__':unittest.main()
