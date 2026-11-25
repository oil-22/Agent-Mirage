import unittest
from price_history_frame_binding import price_history_clauses

class Scope(unittest.TestCase):
    def test_actual_grouping_is_retained_exact(self):
        clause='The cheaper $1.00/$3.00 items I saw showed cards, boxes, trash cans, pins, binders, and cartridges.'
        self.assertEqual(price_history_clauses('This book is $5.00. '+clause+' I cannot confirm the global minimum.'),[clause])
    def test_decimal_is_not_sentence_split(self):self.assertEqual(price_history_clauses('I saw a pin at $3.00.'),['I saw a pin at $3.00.'])
    def test_no_rewrite_of_original_clause(self):
        s='Earlier I saw two books at $5.00 and $7.00.';self.assertEqual(price_history_clauses(s),[s])
    def test_no_price_in_past_clause_abstains(self):self.assertEqual(price_history_clauses('I saw books. I will check $3.00 listings.'),[])
    def test_answer_span_is_not_dropped(self):
        s='<action>{"type":"stop","answer":"I saw a pin at $3.00"}</action>';self.assertEqual(price_history_clauses(s),[s])

if __name__=='__main__':unittest.main()
