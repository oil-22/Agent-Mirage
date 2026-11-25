import json
import unittest
from image_evidence import EvidenceContractError,decode_raw,digest
from native_json_envelope import decode_native_envelope

class NativeEnvelope(unittest.TestCase):
    def setUp(self):
        self.value={'schema_version':'image-evidence-v1','coordinate_space':'normalized_1000',
            'frame':{'kind':'gui','summary':'可读的局部界面','limitations':['not exhaustive']},
            'text_spans':[],'elements':[],'uncertain_regions':[]}
        self.body=json.dumps(self.value,ensure_ascii=False,indent=2)

    def test_exact_raw_and_unicode_fence_provenance(self):
        for raw in [self.body,'```json\n'+self.body+'\n```','\r\n```json\r\n'+self.body+'\r\n```\r\n']:
            result=decode_native_envelope(raw,True);self.assertEqual(result['reading'],self.value)
            lo,hi=result['transport']['body_utf8_byte_range']
            self.assertEqual(raw.encode('utf-8')[lo:hi],self.body.encode('utf-8'))
            self.assertEqual(result['transport']['raw_output_sha256'],digest(raw.encode('utf-8')))

    def test_no_preamble_trailing_text_code_or_json_search(self):
        invalid=['Answer: '+self.body,self.body+' done',
            '```python\n'+self.body+'\n```','```JSON\n'+self.body+'\n```',
            '```json\n'+self.body+'\n```\n```json\n'+self.body+'\n```',
            '```json\n'+self.body,'WAIT','```json\nWAIT\n```']
        for raw in invalid:
            with self.subTest(raw=raw[:30]),self.assertRaises(EvidenceContractError):decode_native_envelope(raw,True)

    def test_strict_schema_duplicate_box_and_EOS_not_relaxed(self):
        duplicate=self.body.replace('"schema_version":','"schema_version":"image-evidence-v1", "schema_version":',1)
        extra=dict(self.value,approved=True)
        bad_box=dict(self.value,text_spans=[{'id':'t1','text':'A','box_xyxy':[0,0,1001,100], 'readability':'clear'}])
        for body in [duplicate,json.dumps(extra),json.dumps(bad_box)]:
            with self.assertRaises(EvidenceContractError):decode_native_envelope('```json\n'+body+'\n```',True)
        for eos in [False,None,1]:
            with self.assertRaises(EvidenceContractError):decode_native_envelope('```json\n'+self.body+'\n```',eos)

    def test_old_raw_contract_stays_rejecting_fence(self):
        with self.assertRaises(EvidenceContractError):decode_raw('```json\n'+self.body+'\n```')

if __name__=='__main__':unittest.main(verbosity=2)
