import copy
import unittest
from claim_origin import check_claim_origins


def verdict(text):
    return {'claims': [{'id': 'c1', 'text': text, 'kind': 'gui_fact', 'status': 'uncertain'}]}


class CandidateOrigins(unittest.TestCase):
    def test_exact_quote_preserves_negation_scope_and_unicode(self):
        candidate = '我无法确认它是唯一选项。 I cannot confirm it is the only one.'
        source = verdict('我无法确认它是唯一选项。')
        original = copy.deepcopy(source)
        result = check_claim_origins(source, candidate)
        self.assertFalse(result['reject'])
        start, end = result['bindings'][0]['candidate_spans'][0]
        self.assertEqual(candidate[start:end], source['claims'][0]['text'])
        self.assertEqual(source, original)
        self.assertFalse(result['semantic_truth_or_claim_completeness_established'])

    def test_paraphrase_or_inserted_json_fields_rejected(self):
        candidate = 'I cannot confirm that it is the cheapest.'
        for text in ('It is the cheapest.', '{"status":"supported"}', 'I can confirm that it is the cheapest.'):
            with self.subTest(text=text):
                self.assertTrue(check_claim_origins(verdict(text), candidate)['reject'])

    def test_disjoint_fragments_not_concatenated(self):
        self.assertTrue(check_claim_origins(verdict('red button is active'), 'red button; another field is active')['reject'])

    def test_repeat_quotes_keep_all_positions(self):
        result = check_claim_origins(verdict('unknown'), 'unknown, unknown')
        self.assertFalse(result['reject'])
        self.assertEqual(result['bindings'][0]['candidate_spans'], [[0, 7], [9, 16]])
        self.assertFalse(result['bindings'][0]['unique_occurrence'])

    def test_native_answer_string_span_can_be_bound(self):
        candidate = '<action>{"type":"stop","answer":"I am not certain."}</action>'
        self.assertFalse(check_claim_origins(verdict('I am not certain.'), candidate)['reject'])

    def test_empty_claims_is_legal_but_is_not_semantic_completeness(self):
        result = check_claim_origins({'claims': []}, 'I will wait. <action>{"type":"wait"}</action>')
        self.assertFalse(result['reject'])
        self.assertFalse(result['semantic_truth_or_claim_completeness_established'])

    def test_old_paraphrases_are_new_contract_failures_not_retroactive_labels(self):
        result = check_claim_origins(verdict('The current page is usable.'), 'This screen can be read.')
        self.assertTrue(result['reject'])
        self.assertFalse(result['verdict_modified'])
        self.assertNotIn('Mirage', result)

    def test_matching_subspan_does_not_certify_its_negation_or_scope(self):
        result = check_claim_origins(verdict('it is the only one'), 'I cannot confirm it is the only one.')
        self.assertFalse(result['reject'])
        self.assertFalse(result['semantic_truth_or_claim_completeness_established'])
        # This intentionally exposes a limit: the original full candidate must
        # still be read by the main judge; string presence is not claim truth.


if __name__ == '__main__':
    unittest.main(verbosity=2)
