"""Finite Unicode/escape boundary tests and a sealed failure replay, CPU only."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
REFERENCE=BASE/'balanced-visual-evidence-20261109-16/runtime-package'
sys.path.insert(0,str(REFERENCE/'release'))
from unicode_length_guard import LengthState,InvalidLengthPrefix,field_limits
spec=importlib.util.spec_from_file_location('bounded_schema_cpu17',REFERENCE/'bounded_schema.py')
schema=importlib.util.module_from_spec(spec);spec.loader.exec_module(schema)
import image_evidence as contract
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p,value):
    with p.open('x',encoding='utf8')as f:json.dump(value,f,ensure_ascii=True,indent=2);f.write('\n')


def minimal():
    return {'schema_version':'image-evidence-v2-compact','coordinate_space':'normalized_1000',
            'frame':{'kind':'gui','summary':'Visible interface','limitations':[]},
            'text_spans':[],'elements':[],'uncertain_regions':[]}


def place(value,field):
    reading=minimal()
    if field=='summary':reading['frame']['summary']=value
    elif field=='limitations':reading['frame']['limitations']=[value]
    elif field=='text':reading['text_spans']=[{'id':'t1','text':value,'box_xyxy':[1,1,2,2],'readability':'clear'}]
    elif field=='description':reading['elements']=[{'id':'e1','kind':'image','description':value,'box_xyxy':[1,1,2,2],'text_refs':[],'visibility':'clear'}]
    elif field=='reason':reading['uncertain_regions']=[{'box_xyxy':[1,1,2,2],'reason':value}]
    else:raise AssertionError(field)
    return reading


def main():
    out=HERE/('CPU-boundaries-'+str(time.time_ns()));out.mkdir()
    for p in [HERE/'unicode_length_guard.py',Path(__file__)]:
        (out/p.name).write_bytes(p.read_bytes())
    canonical_before={k:id(v)for k,v in sys.modules.items()if k=='lmformatenforcer'or k.startswith('lmformatenforcer.')}
    results=[];failure=None
    try:
        limits=field_limits(schema.SCHEMA)
        assert limits=={'summary':180,'limitations':160,'text':160,'description':120,'reason':120}
        specs=[]
        for key,maximum in limits.items():
            for alphabet,unit in [('ASCII','a'),('CJK','图'),('emoji','😀'),('escaped_quote','"'),('backslash','\\')]:
                for offset in [0,1]:
                    value=unit*(maximum+offset)
                    specs.append((key+'-'+alphabet+'-'+str(offset),key,value,False,offset==0))
        specs.extend([
            ('surrogate-pairs-at-limit','summary','😀'*180,True,True),
            ('surrogate-pairs-over-limit','summary','😀'*181,True,False),
            ('mixed-surrogate-and-ASCII-at-limit','summary','😀'+'a'*179,True,True),
            ('mixed-surrogate-and-ASCII-over-limit','summary','😀'+'a'*180,True,False),
            ('combining-codepoints-at-limit','summary','e\u0301'*90,False,True),
            ('combining-codepoints-over-limit','summary','e\u0301'*90+'x',False,False),
            ('escaped-newlines-at-limit','summary','\n'*180,True,True),
            ('literal-mixed-at-limit','summary','图😀\\"'*45,False,True),
        ])
        for name,key,value,ensure_ascii,expected in specs:
            reading=place(value,key)
            raw=json.dumps(reading,ensure_ascii=ensure_ascii,separators=(',',':')).encode()
            # Every byte is a separate chunk. This exercises all partial UTF8
            # and escape/surrogate token boundaries without a tokenizer model.
            state=LengthState(limits);accepted=True;error=None;rejected_offset=None
            for index,byte in enumerate(raw):
                try:state.feed(bytes([byte]))
                except InvalidLengthPrefix as exc:
                    accepted=False;error=str(exc);rejected_offset=index;break
            assert accepted==expected,name
            if accepted:assert state.complete(),name
            strict=True
            try:contract.validate_evidence(reading)
            except contract.EvidenceContractError:strict=False
            assert strict==expected,name
            # Chunking invariance: one token may contain many JSON characters.
            other=LengthState(limits);whole=True
            try:other.feed(raw)
            except InvalidLengthPrefix:whole=False
            assert whole==accepted,name
            results.append({'id':name,'field':key,'decoded_characters':len(value),'utf8_JSON_bytes':len(raw),
                            'accepted':accepted,'strict_original_validator_equal':True,
                            'every_byte_and_whole_token_chunking_agree':True,
                            'rejected_byte_offset':rejected_offset,'error':error})
        # This is an existing sealed raw failure, not another model attempt.
        old=BASE/'balanced-visual-evidence-20261109-16/sealed-live-collection-1794215466436948000/original/worker/auxiliary/S02-pagination'
        seal=json.loads((old/'seal.json').read_bytes())
        for name in ['raw-output.txt','actual-generation.json','contract-failure.json']:
            assert sha(old/name)==seal[name]
        raw=(old/'raw-output.txt').read_bytes();reading=json.loads(raw)
        assert len(reading['frame']['summary'])>180
        state=LengthState(limits);rejected=None
        for index,byte in enumerate(raw):
            try:state.feed(bytes([byte]))
            except InvalidLengthPrefix as exc:
                rejected={'byte_offset':index,'error':str(exc),'decoded_characters_at_rejection':state.count};break
        assert rejected is not None and rejected['decoded_characters_at_rejection']==181
        save(out/'sealed-real-failure-replay.json',{'raw_output_sha256':sha(old/'raw-output.txt'),
             'original_seal_sha256':sha(old/'seal.json'),'actual_old_summary_characters':len(reading['frame']['summary']),
             'new_guard_would_reject_before_old_overlong_summary_completed':rejected,
             'new_model_calls':0,'original_output_or_validator_modified':False,'not_a_new_semantic_pass':True})
        assert canonical_before=={k:id(v)for k,v in sys.modules.items()if k=='lmformatenforcer'or k.startswith('lmformatenforcer.')}
        save(out/'receipt.json',{'passed':True,'time':time.time(),'tests':results,'boundary_count':len(results),
             'source_sha256':sha(HERE/'unicode_length_guard.py'),'old_failure_replayed_without_inference':True,
             'primary_grammar_module_graph_unchanged':True,'new_model_GPU_GUI_calls':0,
             'native_vocabulary_prefix_mask_and_actual_GPU_generation_unvalidated':True,
             'running_batch16_unchanged':True,'strict_final_validator_still_required':True,
             'not_output_clipping_relaxation_or_efficacy':True})
    except BaseException:
        failure={'traceback':traceback.format_exc(),'completed_tests':results,'new_model_calls':0,'no_auto_retry':True}
        save(out/'failure.json',failure)
    finally:
        save(out/'seal.json',{p.name:sha(p)for p in out.iterdir()if p.is_file()})
    print(json.dumps({'output':str(out),'passed':failure is None,'boundaries_passed':len(results),
                      'receipt_sha256':sha(out/'receipt.json')if failure is None else None,'failure':failure},ensure_ascii=True))
    return 1 if failure else 0


if __name__=='__main__':raise SystemExit(main())
