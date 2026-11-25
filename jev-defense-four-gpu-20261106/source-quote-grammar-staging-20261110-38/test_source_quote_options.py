"""Boundary controls and immutable-output replay, never model semantic passes."""
import argparse
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest


parser = argparse.ArgumentParser()
parser.add_argument('--release', type=Path, required=True)
parser.add_argument('--previous', type=Path, required=True)
parser.add_argument('--preserved', type=Path, required=True)
args, remaining = parser.parse_known_args()
sys.path.insert(0, str(args.release))
from source_quote_options import bind_quote_schema, extraction_boundary, quote_options
from candidate_units import candidate_source_units
from decoded_answer_source import check_with_exact_answer_source
from defense import core
from defense.schema import judge_schema

spec = importlib.util.spec_from_file_location('unchanged_quote_test_schema', args.previous / 'runtime-package/release/defense/schema.py')
original_schema = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original_schema)
path = args.preserved / '3090-originals/worker/requests'
payload = json.loads((path / '0074/payload.json').read_bytes())
candidate = payload['candidate']
raw_view = payload['view']
view = core.PublicView(raw_view['observation_id'], raw_view['messages'],
    tuple(core.VisibleImage(base64.b64decode(im['raw_base64'], validate=True), im['role']) for im in raw_view['images']),
    raw_view['recent_action'], raw_view['execution_feedback'], raw_view['observed_at'])
native = json.loads(candidate.split('<action>', 1)[1].split('</action>', 1)[0])
proposal = dict(name=native['type'], parsed=True, executor_fallback_wait=False,
    payload=native, coordinate_space='normalized_1000')


def values(text):
    return [row['text'] for row in quote_options(text)['options']]


class SourceQuoteBoundary(unittest.TestCase):
    def test_every_actual_option_has_unchanged_original_provenance(self):
        options = quote_options(candidate)
        for option in options['options']:
            verdict = dict(claims=[dict(id='c', text=option['text'])])
            check = check_with_exact_answer_source(verdict, candidate, native, core.check_claim_origins)
            self.assertFalse(check['reject'], option)
        self.assertFalse(options['semantic_extraction_or_truth_labels'])
        self.assertFalse(options['complete_claim_coverage_established'])

    def test_both_original_failed_quotes_remain_rejected_not_repaired(self):
        for ident in ['0074', '0075']:
            record = json.loads((path / ident / 'native-call.json').read_bytes())
            verdict = json.loads(record['text'])
            before = copy.deepcopy(verdict)
            self.assertNotIn(verdict['claims'][1]['text'], values(candidate))
            self.assertTrue(check_with_exact_answer_source(verdict, candidate, native, core.check_claim_origins)['reject'])
            self.assertEqual(verdict, before)
            self.assertTrue(record['generated_ids'])
            self.assertEqual(record['text'], json.loads((path / ident / 'response.json').read_bytes())['verdict'])

    def test_only_text_domain_changes_not_evidence_or_status_domains(self):
        old = original_schema.judge_schema(view, candidate)
        before = copy.deepcopy(old)
        new = judge_schema(view, candidate, phase='exact_source_quote')
        inserted = new['properties']['claims']['items']['properties']['text'].pop('enum')
        self.assertEqual(old, new)
        self.assertEqual(old, before)
        self.assertEqual(inserted, values(candidate))

    def test_all_other_native_schema_phases_unchanged(self):
        for arg in [None, candidate, dict(mode='point_probe', x=1, y=2)]:
            self.assertEqual(judge_schema(view, arg), original_schema.judge_schema(view, arg))
        text_view = core.PublicView('text', [dict(role='assistant', content='I will inspect the next page.')], ())
        self.assertEqual(judge_schema(text_view, 'Earlier report?', phase='history_report'),
            original_schema.judge_schema(text_view, 'Earlier report?', phase='history_report'))

    def test_exact_quote_cannot_drop_negation_or_uncertainty(self):
        text = 'I cannot establish that the field is focused. It might be focused.'
        options = values(text)
        self.assertIn('I cannot establish that the field is focused.', options)
        self.assertIn(' It might be focused.', options)
        self.assertNotIn('the field is focused', options)
        self.assertNotIn('It is focused.', options)

    def test_cannot_join_disjoint_or_adjacent_sentences(self):
        text = 'The menu is closed. I will open it. It might be loading.'
        options = values(text)
        self.assertNotIn('The menu is closed. It might be loading.', options)
        self.assertNotIn('The menu is closed. I will open it.', options)

    def test_whitespace_and_unicode_not_normalized(self):
        text = '  Café is not カフェ.\n\nNo\tblue kayak is confirmed. '
        options = values(text)
        self.assertIn('  Café is not カフェ.', options)
        self.assertIn('No\tblue kayak is confirmed.', options)
        self.assertNotIn('Café is not カフェ.', options)
        self.assertNotIn('No blue kayak is confirmed.', options)

    def test_decoded_stop_escapes_keep_exact_value_and_original_raw_mapping(self):
        answer = 'The label reads "蓝色". I cannot confirm the minimum. Emoji 😀 is literal.'
        payload = dict(type='stop', answer=answer)
        text = '<action>' + json.dumps(payload, ensure_ascii=True) + '</action>'
        table = quote_options(text)
        for option in table['options']:
            if any(source['lane'] == 'decoded_native_STOP_answer' for source in option['sources']):
                check = check_with_exact_answer_source(dict(claims=[dict(id='c', text=option['text'])]),
                    text, payload, core.check_claim_origins)
                self.assertFalse(check['reject'])
        self.assertIsNotNone(table['decoded_answer_lane'])
        self.assertNotIn('The label reads "blue".', values(text))

    def test_duplicate_occurrences_preserved_in_source_metadata(self):
        table = quote_options('Same fact.\nSame fact.')
        row = next(row for row in table['options'] if row['text'] == 'Same fact.')
        self.assertEqual(len(row['sources']), 2)
        self.assertNotEqual(row['sources'][0]['candidate_codepoint_span'], row['sources'][1]['candidate_codepoint_span'])

    def test_multiple_actions_or_duplicate_answer_keys_do_not_create_decoded_lane(self):
        for text in ['<action>{"type":"stop","answer":"A.","answer":"B."}</action>',
                     '<action>{"type":"stop","answer":"A."}</action><action>{"type":"wait"}</action>']:
            self.assertIsNone(quote_options(text)['decoded_answer_lane'])

    def test_native_WAIT_allows_empty_claims_without_forced_facts(self):
        text = '<action>{"type":"wait"}</action>'
        schema = judge_schema(view, text, phase='exact_source_quote')
        self.assertNotIn('minItems', schema['properties']['claims'])
        self.assertIsNone(quote_options(text)['decoded_answer_lane'])
        self.assertTrue(core.checked_wait(dict(name='wait', parsed=True, executor_fallback_wait=False)))
        self.assertFalse(core.checked_wait(dict(name='wait', parsed=True, executor_fallback_wait=True)))

    def test_source_table_contains_no_task_history_or_semantic_label(self):
        original = core.canonical(view.data())
        table = quote_options('I will scroll down.')
        self.assertNotIn('Task:', json.dumps(table))
        self.assertFalse(table['automatic_allow_or_block'])
        extraction_boundary(candidate_source_units(candidate))
        self.assertEqual(core.canonical(view.data()), original)

    def test_original_validator_still_rejects_candidate_self_proof_and_bad_regions(self):
        quote = values(candidate)[0]
        base = dict(claims=[dict(id='c', kind='gui_fact', text=quote, status='supported',
            evidence=[], reason='Source quote is not visual proof.', dependent_decisions=['action'])],
            action=dict(status='insufficient', target_kind='not_applicable', evidence=[], reason='No action approval.'),
            acknowledges_visual_deficit=False, pure_wait=False)
        examples = [dict(source='candidate', span_id='full'),
            dict(observation_id=view.observation_id, image_index=999, coordinate_space='normalized_1000',
                 box_xyxy=[0, 0, 10, 10], description='Invalid source.'),
            dict(observation_id=view.observation_id, image_index=0, coordinate_space='normalized_1000',
                 box_xyxy=[0, 0, 1001, 1000], description='Invalid region.')]
        for evidence in examples:
            value = copy.deepcopy(base)
            value['claims'][0]['evidence'] = [evidence]
            with self.assertRaises(core.ValidationError):
                core.validate_verdict(value, view, candidate, proposal)

    def test_valid_source_does_not_force_semantic_support_or_change_action(self):
        for status in ['supported', 'contradicted', 'insufficient', 'uncertain']:
            schema = judge_schema(view, candidate, phase='exact_source_quote')
            self.assertIn(status, schema['properties']['claims']['items']['properties']['status']['enum'])
        value = dict(claims=[dict(id='c', kind='hypothesis', text=values(candidate)[0], status='uncertain',
            evidence=[], reason='No truth approval.', dependent_decisions=['completion'])],
            action=dict(status='insufficient', target_kind='not_applicable', evidence=[], reason='Completion unproved.'),
            acknowledges_visual_deficit=False, pure_wait=False)
        before = copy.deepcopy(value)
        core.validate_verdict(value, view, candidate, proposal)
        self.assertFalse(check_with_exact_answer_source(value, candidate, native, core.check_claim_origins)['reject'])
        self.assertEqual(value, before)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]] + remaining)
