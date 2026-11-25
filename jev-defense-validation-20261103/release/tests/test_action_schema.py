import unittest
from defense.schema import judge_schema
from defense.core import correction_message
from test_controller import view

class ActionSchemaTests(unittest.TestCase):
    def test_supported_branch_requires_citation_without_forcing_label(self):
        choices=judge_schema(view(),'candidate')['properties']['action']['anyOf']
        yes,no=choices
        self.assertEqual(yes['properties']['status']['enum'],['supported'])
        self.assertEqual(yes['properties']['evidence']['minItems'],1)
        self.assertEqual(set(no['properties']['status']['enum']),{'contradicted','insufficient','uncertain'})
        self.assertNotIn('minItems',no['properties']['evidence'])
    def test_nonclick_alignment_keeps_text_pair_citations_available(self):
        from dataclasses import replace
        v=replace(view(),images=())
        action=judge_schema(v,'comparison pair')['properties']['action']['anyOf'][0]
        sources=action['properties']['evidence']['items']['anyOf']
        self.assertTrue(any('source'in x['properties']for x in sources))
    def test_feedback_covers_native_answer_and_preserves_uncertainty(self):
        text=correction_message([])['content']
        self.assertIn('native action JSON answer',text)
        self.assertIn('explicitly retain that uncertainty',text)

if __name__=='__main__':unittest.main()
