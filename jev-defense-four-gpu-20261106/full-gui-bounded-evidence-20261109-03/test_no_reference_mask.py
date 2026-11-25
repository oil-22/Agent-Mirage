"""Targeted condition tests; do not repeat prior nine native tokenizer tests."""
import copy
import json
import sys
import time
from pathlib import Path
from prepare import HERE,RUNTIME,sha,save
sys.path[:0]=[str(RUNTIME),str(RUNTIME/'release'),str(RUNTIME/'grammar-vendor')]
from bounded_schema import SCHEMA,new_parser,schema_sha256
from lmformatenforcer.consts import COMPLETE_ALPHABET
import image_evidence

def accepts(v):
    p=new_parser(COMPLETE_ALPHABET+'中文')
    for char in json.dumps(v,ensure_ascii=False,separators=(',',':')):
        if char not in p.get_allowed_characters():return False
        p=p.add_character(char)
    return p.can_end()

def main():
    base={'schema_version':'image-evidence-v2-compact','coordinate_space':'normalized_1000',
        'frame':{'kind':'gui','summary':'Independent literals and regions','limitations':[]},
        'text_spans':[{'id':'t1','text':'Visible literal','box_xyxy':[5,5,10,10],'readability':'clear'}],
        'elements':[{'id':'e1','kind':'button','description':'Visible control','box_xyxy':[50,50,100,100],
            'text_refs':[],'visibility':'clear'}],'uncertain_regions':[]}
    assert accepts(base);image_evidence.validate_evidence(base)
    for refs in [['t1'],['t6'],['t1','t1']]:
        value=copy.deepcopy(base);value['elements'][0]['text_refs']=refs;assert not accepts(value)
    assert SCHEMA['properties']['elements']['items']['properties']['text_refs']['maxItems']==0
    # All original structural limits/validator remain. Empty refs are already legal.
    assert SCHEMA['properties']['text_spans']['maxItems']==6
    assert SCHEMA['properties']['elements']['maxItems']==6
    assert image_evidence.MAX_TEXT_SPANS==image_evidence.MAX_ELEMENTS==6
    assert image_evidence.MAX_UNCERTAIN_REGIONS==2
    save(HERE/'no-reference-mask-CPU-result.json',{'passed':True,'targeted_cases':4,
        'native_tokenizer_tests_not_reexecuted':True,'schema_sha256':schema_sha256(),
        'original_validator_accepts_empty_refs':True,'models_GUI_CUDA_calls':0,
        'real_new_generation_not_yet_tested':True,'generated_untouched_output_required':True})
    print(json.dumps({'passed':True,'targeted_cases':4,'new_model_GUI_calls':0}))

if __name__=='__main__':main()
