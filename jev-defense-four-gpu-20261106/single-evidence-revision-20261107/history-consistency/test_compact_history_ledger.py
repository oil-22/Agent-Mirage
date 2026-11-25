"""Additional compact-projection boundaries, separate from the first21 checks."""
import copy
import unittest
from types import SimpleNamespace

from compact_history_utterance_ledger import (CompactSourceBoundHistoryJudge,
    prepare_compact_main_judge_system)
from history_utterance_ledger import LedgerSourceError,canonical,digest


def obs(messages):
    return SimpleNamespace(observation_id='current',messages=messages,recent_action='last-attempt',execution_feedback='returned but not confirmed')


class CompactBoundaryTests(unittest.TestCase):
    def test_complete_text_in_original_view_and_audit_not_duplicated_in_new_model_section(self):
        text='UNIQUE_RAW_ACTOR_LITERAL. I identified an uncertain object.'
        view=obs([{'role':'assistant','content':text}]);before=copy.deepcopy(view.messages)
        prepared=prepare_compact_main_judge_system('ORIGINAL',view,'verify')
        self.assertNotIn(text,prepared.system)
        self.assertEqual(prepared.full_audit_ledger['complete_actor_text_block_index'][0]['exact_text'],text)
        self.assertEqual(view.messages,before)

    def test_all_records_point_to_exact_original_block_and_span(self):
        view=obs([{'role':'user','content':'Task'},
            {'role':'assistant','content':[{'type':'text','text':'I may have found A.'},
                {'type':'image_reference','image_index':0},{'type':'text','text':'I will check B.'}]}])
        prepared=prepare_compact_main_judge_system('HISTORY',view,'history_report')
        records=prepared.compact_model_index['records'];self.assertEqual(len(records),2)
        for row in records:
            text=view.messages[row['message_index']]['content'][row['block_index']]['text']
            start,end=row['text_character_span'];self.assertEqual(text[start:end],text)
            self.assertEqual(row['text_utf8_sha256'],digest(text.encode()))

    def test_surface_cue_legend_retains_multiple_scopes_without_judgment(self):
        view=obs([{'role':'assistant','content':'If I identified A, I cannot confirm it.'}])
        index=prepare_compact_main_judge_system('V',view,'verify').compact_model_index
        flags=[index['surface_cue_legend'][i]for i in index['records'][0]['surface_cue_indices']]
        self.assertIn('conditional_or_hypothetical_cue',flags)
        self.assertIn('uncertainty_or_negated_knowledge_cue',flags)
        self.assertNotIn('verdict',index)

    def test_empty_history_builds_an_explicit_empty_index(self):
        index=prepare_compact_main_judge_system('V',obs([]),'verify').compact_model_index
        self.assertEqual(index['records'],[]);self.assertEqual(index['utterance_count'],0)

    def test_one_primary_call_same_object_and_verdict_and_no_internal_retry(self):
        calls=[];journal=[];view=obs([]);candidate={'raw':'query'};result=object()
        def base(*args,**kwargs):calls.append((args,kwargs));return result
        adapter=CompactSourceBoundHistoryJudge(base,verify_prefix='VERIFY',history_prefix='HISTORY',emit=lambda *r:journal.append(r))
        self.assertIs(adapter('VERIFY diagnostic',view,candidate,receipt='frozen'),result)
        self.assertEqual(len(calls),1);self.assertIs(calls[0][0][1],view)
        self.assertIs(calls[0][0][2],candidate);self.assertEqual(calls[0][1],{'receipt':'frozen'})
        self.assertIn('ledger',journal[0][1])

    def test_observer_and_other_primary_phases_unchanged(self):
        calls=[];view=obs([])
        def base(*args):calls.append(args);return args
        adapter=CompactSourceBoundHistoryJudge(base,verify_prefix='VERIFY',history_prefix='HISTORY')
        for system in ['OBSERVER_IMAGE_ONLY','POINT','SCREEN','PERSON_READ']:
            result=adapter(system,view,None);self.assertEqual(result,(system,view,None))

    def test_wait_source_is_not_labelled_mirage_or_executed(self):
        view=obs([{'role':'assistant','content':'<action>{"type":"wait"}</action>'}])
        prepared=prepare_compact_main_judge_system('V',view,'verify')
        attempt=prepared.full_audit_ledger['complete_actor_text_block_index'][0]['native_proposed_action_records'][0]
        self.assertTrue(attempt['exact_wait_syntax_only']);self.assertFalse(attempt['execution_established'])
        self.assertNotIn('Mirage',prepared.compact_model_index)

    def test_preparation_does_not_turn_into_actor_context(self):
        for phase in ['actor','observer','screen']:
            with self.assertRaises(LedgerSourceError):prepare_compact_main_judge_system('S',obs([]),phase)


if __name__=='__main__':unittest.main(verbosity=2)
