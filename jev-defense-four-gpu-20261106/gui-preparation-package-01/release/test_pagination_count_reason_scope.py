import copy
import unittest
from pagination_count_reason_scope import pagination_count_reason_check


class CountScope(unittest.TestCase):
    def row(self, text='there are 3 more pages of results I have not inspected', reason='Pages 2 and 3 and potentially more indicated by the last-page arrow remain uninspected.'):
        return {'claims': [{'kind': 'gui_fact', 'status': 'supported', 'text': text, 'reason': reason}]}

    def test_actual_failed_reply_and_immutability(self):
        row = self.row(); old = copy.deepcopy(row)
        self.assertTrue(pagination_count_reason_check(row)['reject'])
        self.assertEqual(row, old)

    def test_other_exact_counts(self):
        for text in ['There are 19 additional pages.', '7 pages remain.', 'There are 2 remaining pages.']:
            self.assertTrue(pagination_count_reason_check(self.row(text))['reject'])

    def test_lower_bound_is_not_exact(self):
        for text in ['At least 3 more pages remain.', 'There may be 3 more pages.', 'Perhaps 3 additional pages remain.']:
            self.assertFalse(pagination_count_reason_check(self.row(text))['reject'])

    def test_explicit_complete_count_source(self):
        self.assertFalse(pagination_count_reason_check(self.row(reason='Current page 1 and last page 5 are explicitly established in the cited records; four pages remain.'))['reject'])

    def test_unknown_and_unsupported_not_edited(self):
        for status in ['insufficient', 'uncertain', 'contradicted']:
            row = self.row(); row['claims'][0]['status'] = status
            self.assertFalse(pagination_count_reason_check(row)['reject'])

    def test_intent_hypothesis_not_count_truth(self):
        for kind in ['intent', 'hypothesis']:
            row = self.row(); row['claims'][0]['kind'] = kind
            self.assertFalse(pagination_count_reason_check(row)['reject'])

    def test_not_a_pagination_arithmetic_or_image_oracle(self):
        self.assertFalse(pagination_count_reason_check(self.row(reason='The numbered buttons indicate exactly three more pages.'))['reject'])
        self.assertFalse(pagination_count_reason_check(self.row('There are 50 listings.'))['reject'])

    def test_alternative_open_count(self):
        for reason, expected in [('There might be more pages beyond the shown buttons.', True), ('The total count is unknown.', False), ('Unknown total number of pages.', True)]:
            # "total count is unknown" is deliberately outside this narrow
            # grammar; leaving it unflagged is explicitly not approval.
            result = pagination_count_reason_check(self.row(reason=reason))
            self.assertEqual(result['reject'], expected)
            self.assertFalse(result['capacity_assumed'])
            self.assertFalse(result['corrected_count_supplied'])


if __name__ == '__main__':
    unittest.main()
