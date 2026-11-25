"""Auxiliary-only structural decoding with actual selected-token provenance."""
import io
import json
from pathlib import Path
from PIL import Image
from model_runtime import save,sha,canonical,digest
from native_format_bridge import build_token_data
from bounded_schema import SCHEMA,schema_sha256,new_prefix_filter
import image_evidence as contract

def prepare(processor,generation,root,package):
    from auxiliary_grammar_import import load_auxiliary_grammar
    api,import_proof=load_auxiliary_grammar()
    save(root/'auxiliary-grammar-actual-imports.json',import_proof)
    data=build_token_data(processor.tokenizer)
    data.eos_token_id=list(generation.eos_token_id)
    save(root/'grammar-policy.json',{'schema':SCHEMA,'schema_sha256':schema_sha256(),
        'bridge_sha256':sha(package/'native_format_bridge.py'),'decoder':'native ByteLevel raw bytes',
        'eos_token_ids':data.eos_token_id,'mask_changes_decoding':True,'main_generation_unchanged':True,
        'max_new_tokens':generation.max_new_tokens,'no_truth_or_task_hints':True,'strict_final_validator_required':True})
    return data

def generate(model,processor,generation,torch,audit,data,raw,target):
    messages=[{'role':'user','content':[{'type':'image','image':Image.open(io.BytesIO(raw)).convert('RGB')},
                                      {'type':'text','text':contract.FIXED_PROMPT}]}]
    prefix=new_prefix_filter(data);checks=[]
    def mask(batch,ids):
        current=ids.tolist();allowed=prefix(batch,ids)
        checks.append({'prefix_length':len(current),'prefix_sha256':digest(canonical(current)),
            'allowed_count':len(allowed),'allowed_sha256':digest(canonical(allowed)),'allowed':allowed})
        return allowed
    try:
        torch.manual_seed(0)
        with audit(model,processor,target):
            inputs=processor.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=False,
                tools=None,return_dict=True,return_tensors='pt')
            with torch.inference_mode():
                output=model.generate(**inputs.to('cuda:3'),generation_config=generation,return_dict_in_generate=True,
                    output_scores=False,prefix_allowed_tokens_fn=mask)
        actual=json.loads((target/'actual-generation.json').read_bytes());ids=actual['output_ids']
        assert len(ids)==len(checks)
        prompt_ids=inputs['input_ids'][0].detach().cpu().tolist();verified=[]
        for index,(token,check)in enumerate(zip(ids,checks)):
            assert check['prefix_length']==len(prompt_ids)+index
            assert check['prefix_sha256']==digest(canonical(prompt_ids+ids[:index]))
            assert token in check['allowed'],'Actual selected token outside structural mask'
            verified.append({k:v for k,v in check.items()if k!='allowed'}|{'selected_id':token,'selected_allowed':True})
        save(target/'actual-mask-steps.json',{'steps':verified,'all_actual_selected_tokens_allowed':True,
            'native_stops':data.eos_token_id,'schema_sha256':schema_sha256(),'no_unmasked_probability_claim':True})
        text=processor.tokenizer.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False)
        raw_bytes=b''.join(data.native_raw_token_bytes[t]for t in ids if t not in data.eos_token_id)
        (target/'generated-raw-utf8.bin').write_bytes(raw_bytes)
        (target/'raw-output.txt').write_text(text,encoding='utf8')
        utf8_roundtrip=False
        try:utf8_roundtrip=raw_bytes.decode('utf8',errors='strict')==text
        except UnicodeDecodeError:pass
        save(target/'raw-UTF8-validation.json',{'strict_native_UTF8_roundtrip':utf8_roundtrip,
            'native_output_unchanged':True,'on_failure':'entire evidence packet unavailable, no replacement chars accepted'})
        return text,actual,utf8_roundtrip
    except BaseException:
        save(target/'failed-mask-steps.json',{'steps':[{k:v for k,v in c.items()if k!='allowed'}for c in checks],
            'no_automatic_retry':True});raise
