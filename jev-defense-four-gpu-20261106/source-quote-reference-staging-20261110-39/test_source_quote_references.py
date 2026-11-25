"""Source-bound protocol controls; mocked callbacks are not semantic passes."""
import argparse
import base64
import copy
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
from source_quote_references import source_index, bind_reference_schema, resolve_references, extraction_boundary, QuoteReferenceError
from candidate_units import candidate_source_units
from decoded_answer_source import check_with_exact_answer_source
from defense import core
from defense.schema import judge_schema
from defense.qwen_backend import LocalQwen
from defense.prompts import VERIFY, HISTORY_REPORT, SCREEN, ALIGN

spec = importlib.util.spec_from_file_location('original_reference_test_schema', args.previous / 'runtime-package/release/defense/schema.py')
old_schema = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old_schema)
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


def wire(text=candidate, ident=None, status='uncertain'):
    row = source_index(text)['rows'][0]
    return dict(claims=[dict(id='c1', kind='gui_fact', quote_id=ident or row['quote_id'], status=status,
        evidence=[], reason='No visual truth established by this source-only control.', dependent_decisions=['completion'])],
        action=dict(status='insufficient', target_kind='not_applicable', evidence=[], reason='No action approval from a source ID.'),
        acknowledges_visual_deficit=False, pure_wait=False)


class MemoryLog:
    def __init__(self):
        self.rows = []

    def append(self, kind, data):
        self.rows.append((kind, copy.deepcopy(data)))

    def observation(self, *args, **kwargs):
        raise AssertionError('No reference recapture expected in this CPU control')


class SourceReferenceBoundary(unittest.TestCase):
    def test_every_real_id_binds_raw_or_decoded_original_source(self):
        for row in source_index(candidate)['rows']:
            original = wire(ident=row['quote_id'])
            result, report = resolve_references(original, candidate)
            self.assertEqual(result['claims'][0]['text'], row['text'])
            self.assertFalse(check_with_exact_answer_source(result, candidate, native, core.check_claim_origins)['reject'])
            self.assertEqual(original, wire(ident=row['quote_id']))
            self.assertFalse(report['semantic_truth_or_extraction_completeness_established'])

    def test_original_failed_replies_stay_rejected_and_unchanged(self):
        for ident in ['0074', '0075']:
            raw = json.loads((path / ident / 'native-call.json').read_bytes())
            verdict = json.loads(raw['text'])
            before = copy.deepcopy(verdict)
            self.assertTrue(check_with_exact_answer_source(verdict, candidate, native, core.check_claim_origins)['reject'])
            with self.assertRaises(QuoteReferenceError):
                resolve_references(verdict, candidate)
            self.assertEqual(verdict, before)

    def test_unknown_missing_nonstring_or_dual_representation_rejected(self):
        values = []
        for ident in ['q9999', 'q0', 0, None, [], {}]:
            value = wire(); value['claims'][0]['quote_id'] = ident; values.append(value)
        value = wire(); del value['claims'][0]['quote_id']; values.append(value)
        value = wire(); value['claims'][0]['text'] = 'Invented premise.'; values.append(value)
        for value in values:
            before = copy.deepcopy(value)
            with self.assertRaises(QuoteReferenceError):
                resolve_references(value, candidate)
            self.assertEqual(value, before)

    def test_status_reason_evidence_dependencies_and_action_are_not_changed(self):
        for status in ['supported', 'contradicted', 'insufficient', 'uncertain']:
            value = wire(status=status)
            before = copy.deepcopy(value)
            result, report = resolve_references(value, candidate)
            self.assertEqual(value, before)
            self.assertEqual(result['action'], value['action'])
            for key in ['id', 'kind', 'status', 'evidence', 'reason', 'dependent_decisions']:
                self.assertEqual(result['claims'][0][key], value['claims'][0][key])
            self.assertTrue(report['statuses_reasons_evidence_dependencies_and_action_unchanged'])

    def test_only_claim_text_wire_representation_changes_in_schema(self):
        old = old_schema.judge_schema(view, candidate)
        new = judge_schema(view, candidate, phase='exact_source_reference')
        claim = new['properties']['claims']['items']
        ids = claim['properties'].pop('quote_id')['enum']
        claim['properties']['text'] = old['properties']['claims']['items']['properties']['text']
        claim['required'] = ['text' if x == 'quote_id' else x for x in claim['required']]
        self.assertEqual(new, old)
        self.assertEqual(ids, [r['quote_id'] for r in source_index(candidate)['rows']])

    def test_all_other_schema_phases_unchanged(self):
        for arg in [None, candidate, dict(mode='point_probe', x=1, y=2)]:
            self.assertEqual(judge_schema(view, arg), old_schema.judge_schema(view, arg))
        text_view = core.PublicView('text', [dict(role='assistant', content='I will inspect the next page.')], ())
        self.assertEqual(judge_schema(text_view, 'Earlier report?', phase='history_report'),
                         old_schema.judge_schema(text_view, 'Earlier report?', phase='history_report'))

    def test_exact_negation_qualifications_whitespace_and_unicode_retained(self):
        text = '  Café is not カフェ.\n\nIt might be blue, but I cannot confirm. '
        rows = source_index(text)['rows']
        self.assertIn('  Café is not カフェ.', [r['text'] for r in rows])
        self.assertIn('It might be blue, but I cannot confirm.', [r['text'] for r in rows])
        for row in rows:
            resolved, _ = resolve_references(wire(text, row['quote_id']), text)
            self.assertEqual(resolved['claims'][0]['text'], row['text'])

    def test_escaped_STOP_source_and_all_duplicate_occurrences_retained(self):
        text = 'Same fact.\nSame fact.\n<action>' + json.dumps(dict(type='stop', answer='No "blue" object.\nカフェ is uncertain.')) + '</action>'
        rows = source_index(text)['rows']
        same = next(r for r in rows if r['text'] == 'Same fact.')
        self.assertEqual(len(same['sources']), 2)
        decoded = [r for r in rows if any(s['lane'] == 'decoded_native_STOP_answer' for s in r['sources'])]
        self.assertTrue(decoded)
        native_payload = json.loads(text.split('<action>', 1)[1].split('</action>', 1)[0])
        for row in decoded:
            result, _ = resolve_references(wire(text, row['quote_id']), text)
            self.assertFalse(check_with_exact_answer_source(result, text, native_payload, core.check_claim_origins)['reject'])

    def test_ambiguous_native_actions_do_not_create_decoded_lane(self):
        for text in ['<action>{"type":"stop","answer":"A.","answer":"B."}</action>',
                     '<action>{"type":"stop","answer":"A."}</action><action>{"type":"wait"}</action>']:
            self.assertFalse(any(s['lane'] == 'decoded_native_STOP_answer' for r in source_index(text)['rows'] for s in r['sources']))

    def test_source_ids_do_not_make_candidate_self_proof_or_invalid_evidence_valid(self):
        examples = [dict(source='candidate', span_id='full'),
            dict(observation_id=view.observation_id, image_index=999, coordinate_space='normalized_1000', box_xyxy=[0,0,10,10], description='Invalid image.'),
            dict(observation_id=view.observation_id, image_index=0, coordinate_space='normalized_1000', box_xyxy=[0,0,1001,1000], description='Invalid region.')]
        for evidence in examples:
            value = wire(status='supported'); value['claims'][0]['evidence'] = [evidence]
            resolved, _ = resolve_references(value, candidate)
            with self.assertRaises(core.ValidationError):
                core.validate_verdict(resolved, view, candidate, proposal)

    def test_real_units_do_not_include_arbitrary_subquotes_or_joined_units(self):
        text = 'The menu is closed. I will open it. It might be loading.'
        values = [r['text'] for r in source_index(text)['rows']]
        for absent in ['menu is closed', 'The menu is closed. It might be loading.', 'It is loading.']:
            self.assertNotIn(absent, values)

    def test_extraction_prompt_keeps_original_rules_and_adds_source_data_only(self):
        from candidate_units import extraction_instructions
        system = extraction_instructions(candidate_source_units(candidate))
        self.assertIn('FINAL EXTRACTION BOUNDARY.', system)
        self.assertIn('EXACT_QUOTE_SOURCE_DATA:', system)
        self.assertIn('claims[].quote_id', system)
        self.assertFalse(source_index(candidate)['semantic_truth_or_extraction_completeness_established'])

    def controller(self, replies, cap=140):
        log, calls = MemoryLog(), []
        def judge(system, received_view, received_candidate):
            calls.append((system, core.canonical(received_view.data()), received_candidate))
            return json.dumps(replies[min(len(calls)-1, len(replies)-1)], ensure_ascii=False)
        return core.Controller(judge, log, limits=core.Limits(max_verifier_calls=cap)), log, calls

    def test_Controller_resolves_before_unchanged_validator_and_logs_raw(self):
        value = wire()
        controller, log, calls = self.controller([value])
        before = core.canonical(view.data())
        resolved = controller.inspect('verify', view, candidate, proposal)
        self.assertEqual(controller.verifier_calls, 1)
        self.assertEqual(calls[0][1], before)
        self.assertEqual(calls[0][2], candidate)
        self.assertIn('text', resolved['claims'][0])
        raw = [data for kind, data in log.rows if kind == 'verifier_raw'][0]
        self.assertEqual(json.loads(raw['response']), value)
        self.assertEqual(len([1 for kind, _ in log.rows if kind == 'candidate_quote_reference_resolved']), 1)

    def test_Controller_unknown_ID_uses_only_original_one_format_retry(self):
        invalid = wire(ident='q9999')
        controller, log, calls = self.controller([invalid, invalid])
        with self.assertRaises(core.ValidationError):
            controller.inspect('verify', view, candidate, proposal)
        self.assertEqual(controller.verifier_calls, 2)
        self.assertEqual([d['format_retry'] for k, d in log.rows if k == 'verifier_format_failure'], [0,1])
        self.assertEqual([x[2] for x in calls], [candidate, candidate])
        self.assertFalse(any(k == 'candidate_quote_reference_resolved' for k, _ in log.rows))

    def test_Controller_valid_retry_has_original_full_view_and_no_budget_reset(self):
        controller, log, calls = self.controller([wire(ident='q9999'), wire()])
        controller.inspect('verify', view, candidate, proposal)
        self.assertEqual(controller.verifier_calls, 2)
        self.assertEqual(calls[0][1:], calls[1][1:])
        self.assertIn('previous result', calls[1][0])
        self.assertTrue(all(x[0].startswith(VERIFY) for x in calls))

    def test_Controller_budget_cap_is_not_expanded_for_source_reference(self):
        controller, log, calls = self.controller([wire(ident='q9999')], cap=1)
        with self.assertRaises(core.BudgetExhausted):
            controller.inspect('verify', view, candidate, proposal)
        self.assertEqual(controller.verifier_calls, 1)
        self.assertEqual(len(calls), 1)

    def test_native_WAIT_empty_claims_preserves_exclusion_without_forced_assertions(self):
        text = '<action>{"type":"wait"}</action>'
        value = wire(text); value['claims'] = []; value['pure_wait'] = True
        value['action'] = dict(status='supported', target_kind='not_applicable', reason='Pure native WAIT source-only control.', evidence=[dict(source='candidate', span_id='full')])
        native_wait = dict(name='wait', parsed=True, executor_fallback_wait=False, payload=dict(type='wait'))
        controller, log, calls = self.controller([value])
        result = controller.inspect('verify', view, text, native_wait)
        self.assertEqual(result['claims'], [])
        self.assertTrue(core.checked_wait(native_wait))
        self.assertFalse(core.checked_wait(dict(native_wait, executor_fallback_wait=True)))
        self.assertEqual(controller.verifier_calls, 1)

    def test_backend_dispatch_only_changes_main_VERIFY_wire_schema(self):
        backend = LocalQwen.__new__(LocalQwen)
        captured = []
        backend.generate = lambda messages, maximum, receipt, **kw: captured.append((messages,maximum,kw)) or '{}'
        simple = core.PublicView('no-image', [dict(role='assistant', content='Earlier report.')], ())
        for prompt, query, phase in [(VERIFY, candidate, 'exact_source_reference'),
                                     (HISTORY_REPORT, 'Earlier report?', 'history_report'),
                                     (SCREEN, None, None), (ALIGN, candidate, None)]:
            backend.judge(prompt, simple, query)
            self.assertEqual(captured[-1][2]['json_schema'], judge_schema(simple, query, phase=phase))
            self.assertEqual(captured[-1][1],4096)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]] + remaining, verbosity=2)
