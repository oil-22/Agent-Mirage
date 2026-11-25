"""Behavioral scope/source failures, including adverse hedge combinations."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE / 'runtime-package/release'), str(HERE)]
from candidate_units import candidate_source_units, extraction_instructions
from scoped_absence import route_absence
from claim_origin import check_claim_origins
from appearance_absence_source import absence_clauses
import image_evidence as evidence

class SourceAndScopeTests(unittest.TestCase):
    def extra(self, candidate, action='click'):
        return [row for row in route_absence(candidate, {'name': action})['clauses'] if row['extra_absence_read_required']]

    def test_actual_qualified_sort_candidate_is_not_global_absence(self):
        candidate = ('I cannot confirm any item with a man in a suit or the cheapest such item from the current viewport. '
            'The listings are sorted by "Newly listed," not price, and only three items are visible '
            '(basketball cards $60, rocks/boulders $7, iTouch watch $65), none clearly showing a man in a suit. '
            'To find the cheapest item with a man in a suit, I should sort by price (lowest first) to systematically check items. '
            'Let me click the sort dropdown.\n\n<action>{"type":"click","x":815,"y":228}</action>')
        self.assertEqual(self.extra(candidate), [])
        self.assertEqual(absence_clauses(candidate, {'name': 'click'}), [])

    def test_hedge_does_not_cancel_distinct_categorical_assertion(self):
        for separator in ['. ', '; ', ' but ', ' however ', ' because ', ' and ']:
            with self.subTest(separator=separator):
                rows = self.extra('I cannot confirm the price' + separator + 'no man in a suit appears anywhere on these pages.')
                self.assertTrue(rows)
                self.assertTrue(rows[-1]['historical_scope'])

    def test_categorical_absence_still_checked(self):
        for sentence in ['No person is visible.', 'None of the images show a man in a suit.',
                         'There are no men in these listings.', 'A person is not shown in this image.']:
            with self.subTest(sentence=sentence):
                self.assertTrue(self.extra(sentence))

    def test_uncertainty_after_assertion_does_not_erase_it(self):
        self.assertTrue(self.extra('No man in a suit is present, although the next page may have one.'))

    def test_uncertainty_governs_negative_proposition(self):
        for text in ['I cannot confirm that no man is present.', 'There may be no man in this thumbnail.',
                     'It is unknown whether there are no people.', 'I cannot rule out a man in a suit.']:
            with self.subTest(text=text):
                self.assertFalse(self.extra(text))

    def test_bounded_readability_not_person_absence(self):
        for text in ['None clearly showing a man in a suit.', 'None of them clearly depicts a suited person.',
                     'No clear evidence of a man in a suit is readable.']:
            with self.subTest(text=text):
                self.assertFalse(self.extra(text))

    def test_bounded_report_keeps_separate_global_absence(self):
        self.assertFalse(self.extra('The only item I identified depicts a person in a suit.'))
        self.assertTrue(self.extra('The only item I identified depicts a person in a suit; there are no other suited people anywhere.'))
        self.assertTrue(self.extra('The only item I found is the only suited person anywhere.'))

    def test_only_local_numeric_count_does_not_fetch_history(self):
        rows = self.extra('Only three items are visible, and none shows a man in a suit.')
        self.assertTrue(rows)
        self.assertTrue(all(not row['historical_scope'] for row in rows))

    def test_global_exclusivity_needs_history_but_not_blind_approval(self):
        rows = self.extra('This is the only qualifying item with a man in a suit.')
        self.assertTrue(rows and rows[0]['historical_scope'])
        route = route_absence('A readable footer is visible.', {'name': 'scroll'})
        self.assertTrue(route['unflagged_is_not_approval'])
        self.assertFalse(route['semantic_correctness_established'])

    def test_native_wait_excluded_only_extra_branch(self):
        self.assertFalse(self.extra('There are no men and the task is complete.', 'wait'))
        self.assertTrue(route_absence('No man is present.', {'name': 'wait'})['main_factual_action_history_checks_unchanged'])

    def test_quote_units_preserve_every_original_character_and_offsets(self):
        for candidate in ['Go to page 2 to check more.\n\n<action>{"type":"click","x":559,"y":679}</action>',
                          '我不能确认。\n<action>{"type":"stop","answer":"没有证据"}</action>',
                          'First $1.50. Then "quoted".\r\nUnicode 👤.', '', 'Repeated. Repeated.']:
            with self.subTest(candidate=candidate):
                units = candidate_source_units(candidate)
                self.assertEqual(''.join(row['exact_text'] for row in units['source_units']), candidate)
                self.assertEqual(units['candidate_utf8_sha256'], hashlib.sha256(candidate.encode()).hexdigest())
                for row in units['source_units']:
                    self.assertEqual(candidate[row['start']:row['end']], row['exact_text'])
                self.assertIn('action.reason/evidence', extraction_instructions(units))

    def test_illegal_inferred_claim_not_rewritten_or_accepted(self):
        candidate = 'I will open the menu.\n<action>{"type":"click","x":20,"y":30}</action>'
        verdict = {'claims': [{'id': 'c1', 'text': 'the menu is open'}]}
        before = copy.deepcopy(verdict)
        checked = check_claim_origins(verdict, candidate)
        self.assertTrue(checked['reject'])
        self.assertEqual(verdict, before)
        self.assertFalse(checked['verdict_modified'])
        self.assertFalse(check_claim_origins({'claims': []}, candidate)['reject'])

    def test_quote_is_not_truth_and_duplicate_occurrences_not_resolved(self):
        result = check_claim_origins({'claims': [{'id': 'c1', 'text': 'The menu is open.'}]}, 'The menu is open. The menu is open.')
        self.assertFalse(result['reject'])
        self.assertFalse(result['semantic_truth_or_claim_completeness_established'])
        self.assertEqual(len(result['bindings'][0]['candidate_spans']), 2)

    def test_strict_aux_schema_not_relaxed_for_new_prompt(self):
        packet = {'schema_version': 'image-evidence-v2-compact', 'coordinate_space': 'normalized_1000',
                  'frame': {'kind': 'gui', 'summary': 'A readable footer', 'limitations': []},
                  'text_spans': [], 'elements': [], 'uncertain_regions': []}
        self.assertEqual(evidence.validate_evidence(packet), packet)
        bad = copy.deepcopy(packet)
        bad['elements'] = [{'id': 'e1', 'kind': 'button', 'description': 'Button', 'box_xyxy': [1,1,2,2], 'visibility': 'clear'}]
        with self.assertRaises(evidence.EvidenceContractError):
            evidence.validate_evidence(bad)
        bad = copy.deepcopy(packet)
        bad['text_spans'] = [{'id': 't'+str(i), 'text': str(i), 'box_xyxy': [1,1,2,2], 'readability': 'clear'} for i in range(7)]
        with self.assertRaises(evidence.EvidenceContractError):
            evidence.validate_evidence(bad)

    def test_original_validators_and_backend_identical(self):
        parent = HERE.parent / 'full-gui-single-evidence-20261108-01/runtime-package/release'
        for name in ['defense/schema.py', 'defense/qwen_backend.py', 'claim_origin.py', 'native_direction_consistency.py', 'evidence_observer.py']:
            self.assertEqual((parent/name).read_bytes(), (HERE/'runtime-package/release'/name).read_bytes(), name)

if __name__ == '__main__':
    unittest.main(verbosity=2)
