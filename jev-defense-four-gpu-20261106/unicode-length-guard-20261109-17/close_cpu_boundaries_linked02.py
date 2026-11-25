"""Preserve a whitespace-only test-fixture failure, reuse56 completed cases.

Only the2 remaining length cases and sealed failure replay run here. The
guard is unchanged. Original validator rejects whitespace-only strings, so
the corrected escape fixture contains one visible character plus179 newlines.
"""
import hashlib
import json
from pathlib import Path
import time
import traceback

import check_cpu_boundaries as original

HERE=Path(__file__).resolve().parent
FAILED=HERE/'CPU-boundaries-1794216006479607100'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    for name,expected in json.loads((FAILED/'seal.json').read_bytes()).items():assert sha(FAILED/name)==expected,name
    failure=json.loads((FAILED/'failure.json').read_bytes())
    assert failure['traceback'].endswith('AssertionError: escaped-newlines-at-limit\n')
    completed=failure['completed_tests']
    assert len(completed)==56
    assert sha(HERE/'unicode_length_guard.py')==sha(FAILED/'unicode_length_guard.py')
    out=HERE/('CPU-completion-linked02-'+str(time.time_ns()));out.mkdir()
    results=[];error=None
    original.save(out/'parent-failure-binding.json',{'path':str(FAILED),'seal_sha256':sha(FAILED/'seal.json'),
         'failure_sha256':sha(FAILED/'failure.json'),'56_completed_cases_reused_not_rerun':True,
         'repair_scope':'One whitespace-only fixture violated original nonblank validation. Corrected that fixture only; guard and original validator unchanged.',
         'current_guard_sha256':sha(HERE/'unicode_length_guard.py')})
    try:
        limits=original.field_limits(original.schema.SCHEMA)
        for name,value,ensure_ascii in [
            ('escaped-newlines-nonblank-at-limit','x'+'\n'*179,True),
            ('literal-mixed-at-limit','图😀\\"'*45,False),
        ]:
            reading=original.place(value,'summary')
            raw=json.dumps(reading,ensure_ascii=ensure_ascii,separators=(',',':')).encode()
            state=original.LengthState(limits)
            for byte in raw:state.feed(bytes([byte]))
            assert state.complete()and len(value)==180
            original.contract.validate_evidence(reading)
            original.LengthState(limits).feed(raw)
            results.append({'id':name,'field':'summary','decoded_characters':len(value),'accepted':True,
                            'strict_original_validator_equal':True,'every_byte_and_whole_token_chunking_agree':True})
        old=HERE.parent/'balanced-visual-evidence-20261109-16/sealed-live-collection-1794215466436948000/original/worker/auxiliary/S02-pagination'
        sealed=json.loads((old/'seal.json').read_bytes())
        for name in ['raw-output.txt','actual-generation.json','contract-failure.json']:assert sha(old/name)==sealed[name]
        raw=(old/'raw-output.txt').read_bytes();reading=json.loads(raw)
        state=original.LengthState(limits);rejected=None
        for index,byte in enumerate(raw):
            try:state.feed(bytes([byte]))
            except original.InvalidLengthPrefix as exc:
                rejected={'byte_offset':index,'error':str(exc),'decoded_characters_at_rejection':state.count};break
        assert rejected and rejected['decoded_characters_at_rejection']==181
        original.save(out/'sealed-real-failure-replay.json',{'original_output_sha256':sha(old/'raw-output.txt'),
            'original_seal_sha256':sha(old/'seal.json'),'actual_old_summary_characters':len(reading['frame']['summary']),
            'first_rejected_prefix':rejected,'new_model_calls':0,'original_reply_or_validator_edited':False})
        original.save(out/'receipt.json',{'passed':True,'time':time.time(),'completed_reused':completed,'new_cases':results,
            'total_boundaries':len(completed)+len(results),'new_boundary_executions':len(results),
            'source_sha256':sha(HERE/'unicode_length_guard.py'),'original_failure_preserved':True,
            'native_token_mask_and_actual_GPU_generation_unvalidated':True,'running_batch16_unchanged':True,
            'new_model_GPU_GUI_calls':0,'strict_final_validator_still_required':True,'defense_efficacy_established':False})
    except BaseException:
        error={'traceback':traceback.format_exc(),'new_model_calls':0,'no_auto_retry':True}
        original.save(out/'failure.json',error)
    finally:
        original.save(out/'seal.json',{p.name:sha(p)for p in out.iterdir()if p.is_file()})
    print(json.dumps({'output':str(out),'passed':error is None,'reused_boundaries':56,'new_boundaries':len(results),
                      'receipt_sha256':sha(out/'receipt.json')if error is None else None,'failure':error}))
    return 1 if error else 0


if __name__=='__main__':raise SystemExit(main())
