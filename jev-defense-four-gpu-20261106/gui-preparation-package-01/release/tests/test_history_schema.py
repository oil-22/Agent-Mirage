"""Constrain relation syntax and sources without forcing semantic support."""
import json,unittest
from dataclasses import replace
import jsonschema
from test_controller import view
from defense.schema import judge_schema

class HistorySchemaTests(unittest.TestCase):
    def obs(self):
        return replace(view(),images=(),messages=[{'role':'user','content':'Task'},
            {'role':'assistant','content':'I reported page two'},
            {'role':'user','content':'Correction: still unknown'}])
    def result(self,status='supported',evidence=None):
        return {'status':status,'reason':'text relation',
            'evidence':evidence if evidence is not None else[{'message_index':1,'span_id':'full'}]}
    def test_history_support_requires_actual_actor_source(self):
        schema=judge_schema(self.obs(),'query',phase='history_report')
        jsonschema.validate(self.result(),schema)
        for source in [[{'source':'candidate','span_id':'full'}],[{'message_index':0,'span_id':'full'}],[],[{'message_index':2,'span_id':'full'}]]:
            with self.assertRaises(jsonschema.ValidationError):jsonschema.validate(self.result(evidence=source),schema)
    def test_non_support_is_available_without_evidence(self):
        for status in ['contradicted','insufficient','uncertain']:
            jsonschema.validate(self.result(status,[]),judge_schema(self.obs(),'query',phase='history_report'))
    def test_no_actor_history_cannot_support(self):
        obs=replace(self.obs(),messages=[{'role':'user','content':'Task only'}])
        schema=judge_schema(obs,'query',phase='history_report')
        jsonschema.validate(self.result('insufficient',[]),schema)
        with self.assertRaises(jsonschema.ValidationError):jsonschema.validate(self.result(),schema)
    def test_claims_and_wait_forbidden_for_text_relation(self):
        schema=judge_schema(self.obs(),'query',phase='history_report')
        for key,value in [('claims',['fabricated']),('pure_wait',True)]:
            result=self.result();result[key]=value
            with self.assertRaises(jsonschema.ValidationError):jsonschema.validate(result,schema)
    def test_images_and_unknown_phase_are_rejected(self):
        with self.assertRaises(ValueError):judge_schema(view(),'query',phase='history_report')
        with self.assertRaises(ValueError):judge_schema(self.obs(),'query',phase='unknown')

if __name__=='__main__':unittest.main()
