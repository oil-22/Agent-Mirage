"""CPU source boundaries and unchanged primary call control; not semantic efficacy."""
import copy
import json
import unittest
from types import SimpleNamespace

from history_utterance_ledger import (LedgerSourceError, SourceBoundHistoryJudge,
    build_ledger, canonical, digest, prepare_main_judge_system)


def view(messages, **kwargs):
    return SimpleNamespace(observation_id='test-current', messages=messages, recent_action='', execution_feedback='', **kwargs)


class LedgerBoundaryTests(unittest.TestCase):
    def test_original_public_indices_include_system_and_user_turns(self):
        value=view([{'role':'system','content':'S'},{'role':'user','content':'Task'},
                    {'role':'assistant','content':'I identified item A.'}])
        ledger=build_ledger(value)
        self.assertEqual(ledger['complete_actor_text_block_index'][0]['message_index'],2)
        self.assertEqual(ledger['original_message_count'],3)

    def test_utf8_whitespace_punctuation_and_full_raw_text_are_exact(self):
        text='我发现物品α。\r\n  Maybe it matches.\n\n<action>{"type":"wait"}</action>  '
        value=view([{'role':'assistant','content':text}]);before=copy.deepcopy(value.messages)
        record=build_ledger(value)['complete_actor_text_block_index'][0]
        self.assertEqual(record['exact_text'],text)
        self.assertEqual(record['text_utf8_sha256'],digest(text.encode()))
        cursor=0
        for line in record['line_units']:
            start,end=line['character_span'];self.assertEqual(start,cursor)
            self.assertEqual(digest(text[start:end].encode()),line['text_utf8_sha256']);cursor=end
        self.assertEqual(cursor,len(text));self.assertEqual(value.messages,before)

    def test_multimodal_assistant_text_blocks_are_not_silently_omitted(self):
        value=view([{'role':'assistant','content':[{'type':'text','text':'First'},
            {'type':'image_reference','image_index':0},{'type':'text','text':'Second'}]}])
        rows=build_ledger(value)['complete_actor_text_block_index']
        self.assertEqual([r['block_index']for r in rows],[0,2])
        self.assertEqual([r['exact_text']for r in rows],['First','Second'])

    def test_unknown_assistant_content_fails_instead_of_losing_text(self):
        with self.assertRaises(LedgerSourceError):
            build_ledger(view([{'role':'assistant','content':[{'type':'mystery','text':'retain me'}]}]))

    def test_user_correction_quote_is_not_a_new_actor_identification(self):
        value=view([{'role':'user','content':'Correction retained: I found item B.'},
                    {'role':'assistant','content':'I cannot confirm item B.'}])
        rows=build_ledger(value)['complete_actor_text_block_index']
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['message_index'],1)
        self.assertFalse(rows[0]['visual_truth_established'])

    def test_plan_is_preserved_with_intent_cue_not_completed_inspection(self):
        row=build_ledger(view([{'role':'assistant','content':"I'll check the remaining items."}]))['complete_actor_text_block_index'][0]
        self.assertTrue(row['surface_cues_only']['future_or_intent_cue'])
        self.assertEqual(row['semantic_classification'],'not_automatically_inferred')
        self.assertFalse(row['execution_established'])

    def test_conditional_identification_stays_conditional_not_a_certified_finding(self):
        row=build_ledger(view([{'role':'assistant','content':'If the cover shows a uniform, I would identify item B.'}]))['complete_actor_text_block_index'][0]
        self.assertTrue(row['surface_cues_only']['conditional_or_hypothetical_cue'])
        self.assertFalse(row['visual_truth_established'])

    def test_uncertain_and_negated_recognition_not_upgraded(self):
        row=build_ledger(view([{'role':'assistant','content':'I cannot confirm that I identified item B.'}]))['complete_actor_text_block_index'][0]
        self.assertTrue(row['surface_cues_only']['uncertainty_or_negated_knowledge_cue'])
        self.assertTrue(row['surface_cues_only']['self_report_cue'])
        self.assertEqual(row['semantic_classification'],'not_automatically_inferred')

    def test_retraction_does_not_delete_or_relabel_earlier_raw_utterance(self):
        messages=[{'role':'assistant','content':'I identified item B.'},
                  {'role':'assistant','content':'I retract that identification; I was mistaken.'}]
        rows=build_ledger(view(messages))['complete_actor_text_block_index']
        self.assertEqual(len(rows),2);self.assertEqual(rows[0]['exact_text'],messages[0]['content'])
        self.assertTrue(rows[1]['surface_cues_only']['withdrawal_or_correction_cue'])
        self.assertFalse(any(row['visual_truth_established']for row in rows))

    def test_later_only_one_report_does_not_filter_out_other_prior_report(self):
        messages=[{'role':'assistant','content':'I found item A.'},
                  {'role':'assistant','content':'Item B image shows a person wearing a jacket.'},
                  {'role':'assistant','content':'The only item I identified was A.'}]
        ledger=build_ledger(view(messages))
        self.assertEqual([r['exact_text']for r in ledger['complete_actor_text_block_index']],
                         [m['content']for m in messages])
        self.assertTrue(ledger['assistant_text_not_retrieved_or_ranked'])
        self.assertIsNone(ledger['automatic_verdict_or_action'])

    def test_native_action_is_attempt_not_execution_even_after_report_of_success(self):
        value=view([{'role':'assistant','content':'The click succeeded. <action>{"type":"click","x":20,"y":40}</action>'}])
        row=build_ledger(value)['complete_actor_text_block_index'][0]
        attempt=row['native_proposed_action_records'][0]
        self.assertEqual(attempt['payload_for_source_index_only']['type'],'click')
        self.assertFalse(attempt['execution_established']);self.assertFalse(attempt['native_parser_validated'])

    def test_wait_is_syntax_only_and_does_not_create_a_mirage_label(self):
        row=build_ledger(view([{'role':'assistant','content':'Waiting. <action>{"type":"wait"}</action>'}]))['complete_actor_text_block_index'][0]
        self.assertTrue(row['native_proposed_action_records'][0]['exact_wait_syntax_only'])
        self.assertNotIn('semantic_Mirage',row)
        self.assertFalse(row['native_proposed_action_records'][0]['execution_established'])

    def test_invalid_or_duplicate_action_json_is_not_repaired(self):
        text='<action>{"type":"wait","type":"click"}</action> <action>not-json</action>'
        row=build_ledger(view([{'role':'assistant','content':text}]))['complete_actor_text_block_index'][0]
        self.assertEqual(row['exact_text'],text)
        self.assertTrue(all(not a['json_object_without_duplicate_keys']for a in row['native_proposed_action_records']))

    def test_latest_execution_feedback_is_separate_and_not_guessed_for_all_history(self):
        value=view([{'role':'assistant','content':'I will open a detail.'}])
        value.recent_action='{"type":"click","x":20,"y":40}'
        value.execution_feedback='execution returned, state not confirmed'
        ledger=build_ledger(value)
        feedback=ledger['separate_latest_action_and_feedback_channels']['execution_feedback']
        self.assertEqual(feedback['exact_text'],value.execution_feedback)
        self.assertFalse(feedback['visual_confirmation']);self.assertFalse(feedback['all_past_outcomes_inferred'])

    def test_content_change_changes_hash_even_when_same_index_and_grammar(self):
        a=build_ledger(view([{'role':'assistant','content':'I identified A.'}]))
        b=build_ledger(view([{'role':'assistant','content':'I identified B.'}]))
        self.assertNotEqual(a['original_messages_canonical_sha256'],b['original_messages_canonical_sha256'])
        self.assertNotEqual(a['complete_actor_text_block_index'][0]['source_id'],b['complete_actor_text_block_index'][0]['source_id'])

    def test_index_shift_is_visible_even_when_text_sha_stays_equal(self):
        a=build_ledger(view([{'role':'assistant','content':'Report'}]))
        b=build_ledger(view([{'role':'user','content':'Instruction'},{'role':'assistant','content':'Report'}]))
        x=a['complete_actor_text_block_index'][0];y=b['complete_actor_text_block_index'][0]
        self.assertEqual(x['text_utf8_sha256'],y['text_utf8_sha256'])
        self.assertNotEqual(x['source_id'],y['source_id'])

    def test_primary_adapter_is_one_call_same_candidate_view_and_return_value(self):
        original=view([{'role':'assistant','content':'I found A.'}]);candidate='Current candidate';seen=[];result={'unchanged':'raw verdict'}
        def base(system,v,c,**kwargs):
            seen.append((system,v,c,kwargs));return result
        events=[]
        adapter=SourceBoundHistoryJudge(base,verify_prefix='VERIFY-original',history_prefix='HISTORY-original',emit=lambda *x:events.append(x))
        self.assertIs(adapter('VERIFY-original\nexisting retry instruction',original,candidate,receipt='same-path'),result)
        self.assertEqual(len(seen),1);self.assertIs(seen[0][1],original);self.assertIs(seen[0][2],candidate)
        self.assertEqual(seen[0][3],{'receipt':'same-path'});self.assertTrue(seen[0][0].startswith('VERIFY-original\nexisting retry instruction'))
        self.assertEqual(len(events),1)

    def test_image_observer_screen_and_point_calls_are_exact_pass_through(self):
        original=view([]);seen=[]
        def base(*args):seen.append(args);return 'raw'
        adapter=SourceBoundHistoryJudge(base,verify_prefix='VERIFY',history_prefix='HISTORY')
        for system in ['IMAGE_ONLY_AUX','SCREEN','POINT']:
            self.assertEqual(adapter(system,original,None),'raw');self.assertEqual(seen[-1],(system,original,None))

    def test_format_retry_ownership_remains_outside_adapter(self):
        calls=[]
        def base(*args):calls.append(args);raise RuntimeError('original failure')
        adapter=SourceBoundHistoryJudge(base,verify_prefix='VERIFY',history_prefix='HISTORY')
        with self.assertRaisesRegex(RuntimeError,'original failure'):adapter('VERIFY',view([]),'candidate')
        self.assertEqual(len(calls),1)

    def test_original_view_and_messages_remain_byte_equal(self):
        original=view([{'role':'assistant','content':[{'type':'text','text':'I saw A.'},{'type':'image_reference','image_index':0}]}])
        before=canonical(original.messages)
        prepared=prepare_main_judge_system('HISTORY',original,'history_report')
        self.assertEqual(canonical(original.messages),before)
        self.assertGreater(prepared.added_utf8_bytes,0)
        self.assertEqual(prepared.ledger_sha256,digest(canonical(prepared.ledger)))

    def test_scope_cannot_augment_actor_or_auxiliary(self):
        for phase in ['actor','observer','point','screen']:
            with self.assertRaises(LedgerSourceError):prepare_main_judge_system('S',view([]),phase)


if __name__=='__main__':
    unittest.main(verbosity=2)
