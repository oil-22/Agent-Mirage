"""Actual native vocabulary/mask checks, CPU only; never loads model weights."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
REFERENCE=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/balanced-visual-evidence-20261109-16')
sys.path[:0]=[str(HERE),str(REFERENCE),str(REFERENCE/'release')]
from unicode_length_guard import UnicodeLengthPrefixFilter


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p,value):
    with p.open('x',encoding='utf8')as f:json.dump(value,f,ensure_ascii=True,indent=2);f.write('\n')


def identity():
    p=Path('/proc',str(os.getpid()));tail=(p/'stat').read_text().rsplit(')',1)[1].split()
    return {'pid':os.getpid(),'uid':os.getuid(),'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':tail[19]}


def main(root):
    assert os.environ.get('CUDA_VISIBLE_DEVICES')=='' and os.getuid()==1033
    assert not root.exists();root.mkdir()
    save(root/'process.json',identity())
    failed=None;rows=[];new_rows=[]
    try:
        manifest=json.loads((REFERENCE/'manifest.json').read_bytes())
        assert sha(REFERENCE/'manifest.json')=='2a122aa9d76d128662cd3b68749a552004fb322070971575ebb8872b44bc7aaf'
        for name,expected in manifest['files'].items():assert sha(REFERENCE/name)==expected,name
        from preflight_support import verify_original_dependencies
        dependency=verify_original_dependencies(json.loads((REFERENCE/'primary-reference.json').read_bytes()))
        import torch
        from transformers import AutoProcessor
        from native_format_bridge import build_token_data
        from bounded_schema import SCHEMA,new_prefix_filter
        import image_evidence as contract
        assert torch.cuda.device_count()==0
        before={k:(id(v),str(getattr(v,'__file__','')))for k,v in sys.modules.items()if k=='lmformatenforcer'or k.startswith('lmformatenforcer.')}
        ref=json.loads((REFERENCE/'auxiliary-identity-reference.json').read_bytes())
        processor=AutoProcessor.from_pretrained(ref['base_model']['local_path'],local_files_only=True,trust_remote_code=False)
        data=build_token_data(processor.tokenizer);data.eos_token_id=list(ref['generation']['eos_token_id'])
        prompt=processor.tokenizer.encode('Independent CPU JSON prefix test',add_special_tokens=False)
        def status(case,steps):
            q=root/'.status.tmp'
            q.write_text(json.dumps({'time':time.time(),'case':case,'steps':steps,'completed_cases':len(rows),'new_model_calls':0}))
            q.replace(root/'status.json')
        def minimal(summary):
            return {'schema_version':'image-evidence-v2-compact','coordinate_space':'normalized_1000',
                'frame':{'kind':'gui','summary':summary,'limitations':[]},'text_spans':[],'elements':[],'uncertain_regions':[]}
        cases=[]
        for name,value,ascii_mode,accept in [
            ('ASCII-at-limit','a'*180,False,True),('ASCII-over-limit','a'*181,False,False),
            ('CJK-at-limit','图'*180,False,True),('CJK-over-limit','图'*181,False,False),
            ('emoji-at-limit','😀'*180,False,True),('emoji-over-limit','😀'*181,False,False),
            ('surrogate-escape-at-limit','😀'*180,True,True),('surrogate-escape-over-limit','😀'*181,True,False),
        ]:
            text=json.dumps(minimal(value),ensure_ascii=ascii_mode,separators=(',',':'))
            ids=processor.tokenizer.encode(text,add_special_tokens=False)
            assert processor.tokenizer.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False)==text
            cases.append((name,ids,text,accept))
        old=Path('/home/researcher/jev-defense-four-gpu-20261106/balanced-visual-evidence-20261109-16/worker/auxiliary/S02-pagination')
        old_seal=json.loads((old/'seal.json').read_bytes())
        for name in ['actual-generation.json','raw-output.txt','effective-generation.json']:assert sha(old/name)==old_seal[name]
        actual=json.loads((old/'actual-generation.json').read_bytes())
        old_ids=actual['output_ids'][:-1]
        old_text=(old/'raw-output.txt').read_text()
        assert actual['output_ids'][-1]in data.eos_token_id
        assert processor.tokenizer.decode(old_ids,skip_special_tokens=True,clean_up_tokenization_spaces=False)==old_text
        cases.append(('sealed-overlong-S02-native-token-replay',old_ids,old_text,False))
        parent=Path('/home/researcher/jev-defense-four-gpu-20261106/unicode-length-guard-20261109-17/attempt-01')
        assert sha(HERE/'unicode_length_guard.py')==sha(parent.parent/'CPU-package/unicode_length_guard.py')
        parent_seal=json.loads((parent/'seal.json').read_bytes())
        for name,expected_sha in parent_seal.items():assert sha(parent/name)==expected_sha,name
        failure=json.loads((parent/'failure.json').read_bytes())
        assert failure['traceback'].endswith('AssertionError: emoji-over-limit\n')
        rows.extend(failure['completed_cases'])
        assert [row['case'] for row in rows]==[case[0] for case in cases[:5]]
        save(root/'reused-completed-five.json',{'parent_seal_sha256':sha(parent/'seal.json'),'parent_failure_sha256':sha(parent/'failure.json'),'rows':rows,'completed_cases_not_rerun':True})
        for name,ids,text,expected in cases[5:]:
            original=new_prefix_filter(data)
            bounded=UnicodeLengthPrefixFilter(data,original,SCHEMA)
            prefix=list(prompt);rejected=None;steps=[]
            for index,token in enumerate(ids):
                status(name,index)
                tensor=torch.tensor(prefix,dtype=torch.long)
                allowed=bounded(0,tensor)
                previous=list(original(0,tensor))
                assert set(allowed)<=set(previous),'Supplemental filter expanded original auxiliary grammar'
                if token not in allowed:
                    rejected={'token_index':index,'token_id':token,'old_grammar_allowed':token in previous}
                    break
                prefix.append(token)
                steps.append({'token_index':index,'token_id':token,'selected_allowed':True,'original_allowed':True})
            inherited_valid_exclusion=bool(expected and rejected and not rejected['old_grammar_allowed'])
            assert (rejected is None)==expected or inherited_valid_exclusion,name
            if expected and not inherited_valid_exclusion:
                allowed=bounded(0,torch.tensor(prefix,dtype=torch.long))
                assert any(token in allowed for token in data.eos_token_id),name
                contract.validate_evidence(json.loads(text))
            elif name=='sealed-overlong-S02-native-token-replay':
                assert rejected and rejected['old_grammar_allowed'],name
            elif not expected:
                assert rejected is not None,name
            row={'case':name,'complete':rejected is None,'expected_complete':expected,'native_output_tokens':len(ids),
                 'allowed_prefix_tokens':len(steps),'rejected':rejected,'subset_only':True,
                 'filter_calls':bounded.calls,'filtered_choices_sum':bounded.filtered,'no_model_calls':True,
                 'text_sha256':hashlib.sha256(text.encode()).hexdigest(),
                 'inherited_original_grammar_excludes_valid_text':inherited_valid_exclusion,
                 'rejection_can_be_shared_with_original_grammar':bool(rejected and not rejected['old_grammar_allowed'])}
            save(root/(name+'.json'),dict(row,steps=steps));rows.append(row);new_rows.append(row)
        after={k:(id(v),str(getattr(v,'__file__','')))for k,v in sys.modules.items()if k=='lmformatenforcer'or k.startswith('lmformatenforcer.')}
        assert after==before
        assert sha(REFERENCE/'manifest.json')=='2a122aa9d76d128662cd3b68749a552004fb322070971575ebb8872b44bc7aaf'
        save(root/'receipt.json',{'passed':not any(row.get('inherited_original_grammar_excludes_valid_text') for row in rows),'time':time.time(),'native_cases':rows,'native_case_count':len(rows),
             'reused_completed_cases':5,'new_cases':new_rows,'new_case_count':len(new_rows),
             'test_assertion_only_repaired':True,'original_helper_source_unchanged':True,
             'original_failure_preserved':True,'all_subset_comparisons_passed':True,
             'source_sha256':sha(HERE/'unicode_length_guard.py'),'test_source_sha256':sha(__file__),
             'actual_native_tokenizer_and_EOS_used':True,'canonical_main_module_graph_unchanged':True,
             'primary_dependency_proof':dependency,'running_batch16_source_unchanged':True,
             'no_weights_loaded':True,'new_model_GPU_GUI_scorer_calls':0,
             'actual_GPU_generation_or_GUI_efficacy_established':False,'strict_final_validator_still_required':True})
        status('completed',0)
    except BaseException:
        failed={'traceback':traceback.format_exc(),'completed_cases':rows,'new_model_GPU_calls':0,'no_auto_retry':True}
        save(root/'failure.json',failed)
    finally:
        save(root/'terminal.json',{'time':time.time(),'status':'failed'if failed else'completed','error':failed,'completed_cases':len(rows),'new_cases':len(new_rows)})
        save(root/'seal.json',{p.name:sha(p)for p in root.iterdir()if p.is_file()})
    return 1 if failed else 0


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(main(parser.parse_args().output))
