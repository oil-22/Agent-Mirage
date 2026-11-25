from pathlib import Path
import copy
import json
import sys
import unittest

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE/'runtime-package/grammar-vendor'),str(HERE/'runtime-package/release'),str(HERE)]
from lmformatenforcer import JsonSchemaParser
from bounded_schema import SCHEMA,new_parser
from lmformatenforcer.consts import COMPLETE_ALPHABET
from intrinsic_count_guard import check_intrinsic_counts
import image_evidence

def sample():
    return {'schema_version':'image-evidence-v2-compact','coordinate_space':'normalized_1000',
            'frame':{'kind':'gui','summary':'Readable current interface','limitations':[]},
            'text_spans':[],'elements':[],'uncertain_regions':[]}

def grammar_accepts(value):
    parser=new_parser(COMPLETE_ALPHABET+'中文人物–—👤')
    for char in json.dumps(value,ensure_ascii=False,separators=(',',':')):
        if char not in parser.get_allowed_characters():return False
        parser=parser.add_character(char)
    return parser.can_end()

class GrammarBoundaries(unittest.TestCase):
    def test_all_frame_kinds_no_semantic_choice_forced(self):
        for kind in ['gui','blank','explicit_loading','uninterpretable','non_gui','unknown']:
            value=sample();value['frame']['kind']=kind
            self.assertTrue(grammar_accepts(value),kind)

    def test_no_missing_or_extra_fields(self):
        for kind in ['missing','extra','element_missing']:
            value=sample()
            if kind=='missing':value.pop('uncertain_regions')
            if kind=='extra':value['truth']=True
            if kind=='element_missing':value['elements']=[{'id':'e1','kind':'button','description':'Visible button','box_xyxy':[1,1,2,2],'visibility':'clear'}]
            self.assertFalse(grammar_accepts(value),kind)

    def test_six_entries_allowed_seven_forbidden(self):
        for count in [0,1,6,7]:
            value=sample();value['text_spans']=[{'id':'t'+str(i%6+1),'text':'Literal','box_xyxy':[1,1,2,2],'readability':'clear'}for i in range(count)]
            self.assertEqual(grammar_accepts(value),count<=6)

    def test_maximum_text_length_and_uncertainty_cap(self):
        for count in [1,160,161]:
            value=sample();value['text_spans']=[{'id':'t1','text':'a'*count,'box_xyxy':[1,1,2,2],'readability':'clear'}]
            self.assertEqual(grammar_accepts(value),count<=160)
        value=sample();value['uncertain_regions']=[{'box_xyxy':[1,1,2,2],'reason':'unclear'}]*3
        self.assertFalse(grammar_accepts(value))

    def test_quotes_unicode_escape_roundtrip(self):
        for text in ['6" chair','page \\ 2','中文人物','1 – 12 of 50 listings','line\nbreak']:
            value=sample();value['frame']['summary']=text
            self.assertTrue(grammar_accepts(value),text)

    def test_schema_is_not_box_or_cross_reference_truth_validator(self):
        value=sample();value['elements']=[{'id':'e1','kind':'button','description':'Unknown identity','box_xyxy':[10,10,1,1],'text_refs':['t6'],'visibility':'clear'}]
        # Structural mask does not replace stricter source/geometry checks.
        self.assertTrue(grammar_accepts(value))
        with self.assertRaises(image_evidence.EvidenceContractError):image_evidence.validate_evidence(value)

    def test_intrinsic_range_guard_withholds_without_correcting(self):
        for text,expected in [('31 - 12 of 50 listings',True),('1 - 51 of 50 listings',True),
                              ('1 - 12 of 50 listings',False),('49–50 of 50 results',False),
                              ('size 31 - 12',False),('Unknown range',False)]:
            reading=sample();reading['text_spans']=[{'id':'t1','text':text,'box_xyxy':[1,1,2,2],'readability':'clear'}]
            original=copy.deepcopy(reading);result=check_intrinsic_counts(reading)
            self.assertEqual(result['reject'],expected,text);self.assertEqual(original,reading)
            self.assertFalse(result['corrected_digits_or_action_supplied']);self.assertTrue(result['unflagged_is_not_approval'])

    def test_original_raw_validation_logic_retained(self):
        self.assertEqual(image_evidence.MAX_TEXT_SPANS,6)
        self.assertEqual(image_evidence.MAX_ELEMENTS,6)
        self.assertEqual(image_evidence.MAX_UNCERTAIN_REGIONS,2)
        prior=HERE.parent/'repair-evidence-20261109-01/runtime-package/release'
        for name in ['defense/core.py','defense/prompts.py','defense/schema.py','claim_origin.py','defense/qwen_backend.py','evidence_observer.py']:
            self.assertEqual((prior/name).read_bytes(),(HERE/'runtime-package/release'/name).read_bytes(),name)

if __name__=='__main__':unittest.main(verbosity=2)
