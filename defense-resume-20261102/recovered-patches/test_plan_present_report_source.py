"""Eligibility of actual reports, independent of whether their visual claims are true."""
import json,unittest
from types import SimpleNamespace
from focus_history_conflict_scope import plan_only_source,plan_source_check

class PresentReports(unittest.TestCase):
    def relation(self,source,query):
        view=SimpleNamespace(messages=[{'role':'assistant','content':source}])
        value={'status':'supported','reason':'archived/scripted relation','evidence':[{'message_index':0}]}
        return plan_source_check(value,view,query)
    def test_present_content_report_does_not_become_plan_only(self):
        source='I need to find the matching item. The first image shows cards at a flea market. I will scroll next.'
        self.assertFalse(plan_only_source(source))
        self.assertFalse(self.relation(source,'The earlier assistant reported that the first image showed cards.')['reject'])
    def test_present_content_report_with_native_attempt(self):
        self.assertFalse(plan_only_source('The image depicts a book. I will scroll. <action>{"type":"scroll","direction":"down"}</action>'))
    def test_future_content_reading_remains_plan(self):
        source='I will inspect what the image shows. I need to check what it contains.'
        self.assertTrue(plan_only_source(source))
        self.assertTrue(self.relation(source,'I previously inspected the image.')['reject'])
    def test_native_action_text_does_not_supply_report(self):
        source='I will inspect. <action>{"type":"type","text":"The image shows a book."}</action>'
        self.assertTrue(plan_only_source(source))
    def test_display_or_content_report_eligible_but_not_certified_true(self):
        for content in ['The screen displays a title.','The frame contains a card.']:
            with self.subTest(content=content):self.assertFalse(plan_only_source(content+' I will inspect next.'))
    def test_generic_page_presence_does_not_supply_completed_inspection(self):
        self.assertTrue(plan_only_source('The list is visible. I will inspect the item images.'))

if __name__=='__main__':unittest.main()
