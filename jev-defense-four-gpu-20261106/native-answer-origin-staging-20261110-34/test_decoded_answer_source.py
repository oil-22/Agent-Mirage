"""Representation/source boundaries only; these are not model semantic controls."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

from decoded_answer_source import answer_source, check_with_exact_answer_source


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent / 'remaining-full-history-gui-20261110-33/runtime-package'
ORIGINAL = PACKAGE / 'release/claim_origin.py'
manifest = json.loads((PACKAGE / 'manifest.json').read_bytes())
assert hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() == manifest['files']['release/claim_origin.py']
spec = importlib.util.spec_from_file_location('original_literal_checker_for_source_tests', ORIGINAL)
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)


def case(answer, kind='stop', ensure_ascii=True):
    payload = dict(type=kind, answer=answer)
    candidate = 'A bounded observation.\n<action>' + json.dumps(payload, ensure_ascii=ensure_ascii) + '</action>'
    return candidate, payload


def check(candidate, payload, quote):
    verdict = dict(claims=[dict(id='c1', text=quote, status='insufficient')],
                   action=dict(status='insufficient'), pure_wait=False)
    before = copy.deepcopy(verdict)
    result = check_with_exact_answer_source(verdict, candidate, payload, old.check_claim_origins)
    assert verdict == before and result['original_verdict'] == before
    return result


class ExactAnswerSourceBoundaries(unittest.TestCase):
    def test_plain_original_match_is_unchanged(self):
        c, p = case('The visible price is 185.')
        r = check(c, p, 'The visible price is 185.')
        self.assertFalse(r['reject'])
        self.assertEqual(r['bindings'], r['original_byte_checker_result']['bindings'])
        self.assertEqual(r['decoded_answer_bindings'], [])

    def test_quoted_answer_maps_to_exact_raw_span(self):
        q = 'The item is "Kayak".'
        c, p = case(q)
        r = check(c, p, q)
        self.assertTrue(r['original_byte_checker_result']['reject'])
        self.assertFalse(r['reject'])
        span = r['decoded_answer_bindings'][0]['occurrences'][0]['raw_candidate_span']
        self.assertEqual(json.loads('"' + c[span[0]:span[1]] + '"'), q)

    def test_backslash_is_decoded_once(self):
        q = 'Literal path "C:\\data\\x".'
        c, p = case(q)
        self.assertFalse(check(c, p, q)['reject'])
        self.assertTrue(check(c, p, q.replace('\\data', '\\other'))['reject'])

    def test_unicode_escape_and_non_ascii_characters(self):
        q = 'Item "蓝色皮划艇".'
        for ascii_only in [True, False]:
            c, p = case(q, ensure_ascii=ascii_only)
            self.assertFalse(check(c, p, q)['reject'])

    def test_surrogate_pair_maps_one_character_to_twelve_source_characters(self):
        c, p = case('Item "kayak😀".')
        source = answer_source(c, p)
        at = source['value'].index('😀')
        a, b = source['character_spans'][at]
        self.assertEqual(b - a, 12)
        self.assertEqual(c[a:b], '\\ud83d\\ude00')
        self.assertFalse(check(c, p, p['answer'])['reject'])

    def test_newlines_and_control_escapes_preserved(self):
        q = 'Item "A".\nNext\tline.\b\f\r'
        c, p = case(q)
        self.assertFalse(check(c, p, q)['reject'])
        self.assertTrue(check(c, p, q.replace('\n', ' '))['reject'])

    def test_escaped_slash(self):
        c = '<action>{"type":"stop","answer":"Item \\"A\\/B\\"."}</action>'
        p = json.loads(c[8:-9])
        self.assertFalse(check(c, p, p['answer'])['reject'])

    def test_escaped_answer_key(self):
        c = '<action>{"type":"stop","\\u0061nswer":"Item \\"A\\"."}</action>'
        p = json.loads(c[8:-9])
        self.assertFalse(check(c, p, p['answer'])['reject'])

    def test_changed_number_rejected(self):
        c, p = case('The "price" is 185.')
        self.assertTrue(check(c, p, 'The "price" is 5.')['reject'])

    def test_dropped_negation_rejected(self):
        c, p = case('The "item" is not blue.')
        self.assertTrue(check(c, p, 'The "item" is blue.')['reject'])

    def test_strengthened_uncertainty_rejected(self):
        c, p = case('The "item" may be blue.')
        self.assertTrue(check(c, p, 'The "item" is blue.')['reject'])

    def test_cross_source_concatenation_rejected(self):
        c, p = case('The "price" is 185.')
        self.assertTrue(check(c, p, 'A bounded observation. The "price" is 185.')['reject'])

    def test_no_whitespace_or_unicode_normalization(self):
        c, p = case('The "item"  is bluе.')  # final e is Cyrillic
        self.assertTrue(check(c, p, 'The "item" is blue.')['reject'])

    def test_non_stop_answer_is_not_an_added_source(self):
        c, p = case('The "item" is blue.', kind='wait')
        self.assertTrue(check(c, p, p['answer'])['reject'])

    def test_native_payload_mismatch_rejected(self):
        c, p = case('The "item" is blue.')
        self.assertTrue(check(c, dict(p, answer='Other'), p['answer'])['reject'])

    def test_duplicate_top_level_keys_rejected_for_new_lane(self):
        c = '<action>{"type":"stop","answer":"first","answer":"Item \\"A\\"."}</action>'
        p = json.loads(c[8:-9])
        self.assertTrue(check(c, p, p['answer'])['reject'])

    def test_multiple_action_blocks_rejected_for_new_lane(self):
        c, p = case('The "item" is blue.')
        self.assertTrue(check(c + '<action>{"type":"wait"}</action>', p, p['answer'])['reject'])

    def test_nested_non_answer_text_not_promoted(self):
        p = dict(type='stop', answer='Other', metadata=dict(answer='The "item" is blue.'))
        c = '<action>' + json.dumps(p) + '</action>'
        self.assertTrue(check(c, p, p['metadata']['answer'])['reject'])

    def test_repeated_decoded_occurrences_all_retained(self):
        q = 'The "item".'
        c, p = case(q + ' ' + q)
        r = check(c, p, q)
        self.assertFalse(r['reject'])
        self.assertEqual(len(r['decoded_answer_bindings'][0]['occurrences']), 2)
        self.assertFalse(r['decoded_answer_bindings'][0]['unique_occurrence'])

    def test_empty_claim_rejected(self):
        c, p = case('Item "A".')
        self.assertTrue(check(c, p, '')['reject'])

    def test_pure_native_wait_with_no_claims_unchanged(self):
        c, p = '<action>{"type":"wait"}</action>', dict(type='wait')
        v = dict(claims=[], pure_wait=True, action=dict(status='supported'))
        r = check_with_exact_answer_source(v, c, p, old.check_claim_origins)
        self.assertFalse(r['reject'])
        self.assertEqual(r['original_verdict'], v)
        self.assertEqual(r['decoded_answer_bindings'], [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
