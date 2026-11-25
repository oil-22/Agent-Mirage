"""Six new image-only constrained outputs; no semantic retries or GUI calls."""
from pathlib import Path
import argparse
import fcntl
import io
import json
import os
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE/'release'),str(HERE/'grammar-vendor')]
from model_runtime import load_runtime,save,sha,canonical,digest
from resource_gate import assert_owned_resources,identity,same_identity
from defense.core import Journal
from native_format_bridge import build_token_data
from bounded_schema import SCHEMA,schema_sha256,new_prefix_filter
import image_evidence as contract

LEASE=Path('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json')

def main(a):
    assert sha(a.manifest)==a.manifest_sha256
    package=a.manifest.parent;manifest=json.loads(a.manifest.read_bytes())
    for name,h in manifest['files'].items():assert sha(package/name)==h,name
    plan=json.loads((package/'controls-plan.json').read_bytes())
    assert plan['limits']=={'auxiliary':6,'judge':0,'actor':0,'GUI':0,'scorer':0,'paid_API':0,'format_retries':0}
    assert [r['id']for r in plan['auxiliary']]==['B01','B02','B03','B04','B05','B06']
    assert os.getuid()==1033 and os.environ['CUDA_VISIBLE_DEVICES']=='4,5,6,7'
    assert not a.output.exists();a.output.mkdir()
    root=a.output;me=identity(os.getpid());save(root/'process.json',me)
    launcher=json.loads(os.environ['MIRAGE_JEV_LAUNCHER_IDENTITY'])
    assert same_identity(identity(os.getppid()),launcher)
    journal=Journal(root/'journal');started=time.time();error=None;runtime=None
    attempted=[];completed=[]
    def resource(empty=False):
        assert not(root.parent/'stop-requested.json').exists(),'Stop own attempt before another request'
        proof=assert_owned_resources(LEASE,manifest['expected_holder'],{me['pid']:me,launcher['pid']:launcher},empty)
        journal.append('actual_resource_check',proof);return proof
    def status(phase,**more):
        p=root/'.status.tmp';p.write_bytes(canonical({'phase':phase,'time':time.time(),'attempted':attempted,'completed':completed,**more}));p.replace(root/'status.json')
    try:
        resource(True)
        mutex=Path(json.loads(LEASE.read_bytes())['inference_lock']).open('a');fcntl.flock(mutex,fcntl.LOCK_EX|fcntl.LOCK_NB)
        status('loading')
        runtime=load_runtime(package,root,journal,resource,manifest,me)
        torch=runtime['torch'];support=runtime['support'];audit=runtime['audited_generation']
        model=runtime['auxiliary_model'];processor=runtime['auxiliary_processor'];generation=runtime['generation']
        tokenizer=processor.tokenizer;data=build_token_data(tokenizer)
        # Retain BOTH native generation stopping tokens. Neither is permitted
        # before the structural parser reaches a complete JSON object.
        data.eos_token_id=list(generation.eos_token_id)
        save(root/'grammar-policy.json',{'schema':SCHEMA,'schema_sha256':schema_sha256(),
            'bridge_sha256':sha(package/'native_format_bridge.py'),'decoder':'native ByteLevel raw bytes',
            'eos_token_ids':data.eos_token_id,'mask_changes_decoding':True,'main_generation_unchanged':True,
            'max_new_tokens':generation.max_new_tokens,'no_truth_or_task_hints':True,
            'strict_final_validator_required':True,'native_tokenizer_vocab':len(tokenizer)})
        from PIL import Image
        out=root/'auxiliary';out.mkdir()
        for row in plan['auxiliary']:
            resource();target=out/row['id'];target.mkdir()
            p=package/row['path'];assert sha(p)==row['sha256']
            request=json.loads(p.read_bytes());raw=contract.validate_image_only_request(request)
            save(target/'request.json',request);(target/'original.png').write_bytes(raw)
            messages=[{'role':'user','content':[{'type':'image','image':Image.open(io.BytesIO(raw)).convert('RGB')},{'type':'text','text':contract.FIXED_PROMPT}]}]
            prefix=new_prefix_filter(data);checks=[];prompt_length=None
            def mask(batch,ids):
                nonlocal prompt_length
                current=ids.tolist()
                if prompt_length is None:prompt_length=len(current)
                allowed=prefix(batch,ids)
                checks.append({'prefix_length':len(current),'prefix_sha256':digest(canonical(current)),
                    'allowed_count':len(allowed),'allowed_sha256':digest(canonical(allowed)),
                    'allowed':allowed})
                return allowed
            attempted.append(row['id']);status('auxiliary_generating',case=row['id'])
            support.reset_memory(torch);start=time.perf_counter();torch.manual_seed(0)
            journal.append('auxiliary_request',{'case':row['id'],'request_sha256':sha(target/'request.json'),
                'schema_sha256':schema_sha256(),'structural_mask_enabled':True})
            try:
                with audit(model,processor,target):
                    inputs=processor.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=False,tools=None,return_dict=True,return_tensors='pt')
                    with torch.inference_mode():
                        output=model.generate(**inputs.to('cuda:3'),generation_config=generation,return_dict_in_generate=True,
                            output_scores=False,prefix_allowed_tokens_fn=mask)
                actual=json.loads((target/'actual-generation.json').read_bytes())
                ids=actual['output_ids'];assert len(ids)==len(checks)
                prompt_ids=inputs['input_ids'][0].detach().cpu().tolist()
                verified=[]
                for index,(token,check)in enumerate(zip(ids,checks)):
                    assert check['prefix_length']==len(prompt_ids)+index
                    assert check['prefix_sha256']==digest(canonical(prompt_ids+ids[:index]))
                    assert token in check['allowed'],'Native generation selected a token outside mask'
                    verified.append({k:v for k,v in check.items()if k!='allowed'}|{'selected_id':token,'selected_allowed':True})
                save(target/'actual-mask-steps.json',{'steps':verified,'all_actual_selected_tokens_allowed':True,
                    'native_stops':data.eos_token_id,'schema_sha256':schema_sha256(),'no_unmasked_probability_claim':True})
                text=tokenizer.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False)
                raw_bytes=b''.join(data.native_raw_token_bytes[t]for t in ids if t not in data.eos_token_id)
                (target/'generated-raw-utf8.bin').write_bytes(raw_bytes)
                (target/'raw-output.txt').write_text(text,encoding='utf8')
                utf8_roundtrip=False
                try:utf8_roundtrip=raw_bytes.decode('utf8',errors='strict')==text
                except UnicodeDecodeError:pass
                response={'request_sha256':digest(contract.canonical(request)),'image_sha256':request['image_sha256'],
                    'model':request['model'],'revision':request['revision'],'raw_output':text,'natural_eos':actual['natural_EOS'],
                    'strict_native_UTF8_roundtrip':utf8_roundtrip,'structural_mask':True}
                save(target/'response.json',response)
                result={'id':row['id'],'natural_EOS':actual['natural_EOS'],'semantic_pass':None,
                    'strict_native_UTF8_roundtrip':utf8_roundtrip,'input_tokens':actual['input_tokens'],'output_tokens':actual['output_tokens'],
                    'seconds_including_instrumentation':time.perf_counter()-start,'format_retries':0}
                try:
                    if not utf8_roundtrip:raise contract.EvidenceContractError('Actual generated native bytes fail strict UTF8 roundtrip')
                    packet=contract.actor_packet(request,text,actual['natural_EOS']);save(target/'packet.json',packet)
                    result['format_contract_valid']=True
                except contract.EvidenceContractError as exc:
                    result.update(format_contract_valid=False,error=str(exc),no_retry=True);save(target/'contract-failure.json',result)
                completed.append(result);resource()
                save(target/'seal.json',{p.name:sha(p)for p in target.iterdir()if p.is_file()})
                journal.append('auxiliary_reply_sealed',{'case':row['id'],'seal_sha256':sha(target/'seal.json'),'result':result})
                del inputs,output;torch.cuda.empty_cache()
            except BaseException:
                save(target/'failed-mask-steps.json',{'steps':[{k:v for k,v in c.items()if k!='allowed'}for c in checks],
                    'no_automatic_retry':True});raise
        status('completed')
        save(root/'summary.json',{'status':'completed','auxiliary':completed,'actual_auxiliary_calls':len(attempted),
            'both_models_resident':True,'actor_judge_GUI_scorer_paid_calls':0,'old_terminal_controls_reexecuted':False,
            'known_nonblind_development_sources':True,'semantic_efficacy_or_GUI_release_established':False})
    except BaseException as exc:
        error={'type':type(exc).__name__,'traceback':traceback.format_exc(),'resource_evidence':getattr(exc,'resource_evidence',None),'no_automatic_retry':True}
        save(root/'failure.json',error);journal.append('technical_failure_preserved',error);status('technical_failure')
    finally:
        journal.append('worker_terminal',{'status':'technical_failure'if error else'completed'})
        save(root/'terminal.json',{'status':'technical_failure'if error else'completed','attempted':attempted,'completed':completed,
            'error':error,'started':started,'ended':time.time(),'actor_judge_GUI_scorer_paid_calls':0})
        save(root/'worker-manifest.json',{str(p.relative_to(root)):sha(p)for p in sorted(root.rglob('*'))if p.is_file()})
    return 1 if error else 0

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--manifest-sha256',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    try:code=main(a)
    except BaseException:
        target=HERE/'pre-admission-failures'/str(time.time_ns());target.mkdir(parents=True)
        save(target/'failure.json',{'traceback':traceback.format_exc(),'no_automatic_retry':True});code=1
    raise SystemExit(code)
