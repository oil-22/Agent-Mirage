"""Finite NEW source-bound repair controls; no actor, GUI, scorer, or API."""
from pathlib import Path
import argparse
import ast
import base64
import fcntl
import io
import json
import os
import re
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE/'release')]
from model_runtime import load_runtime,save,sha,canonical,digest
from resource_gate import assert_owned_resources,identity,same_identity
from defense.core import Controller,Journal,Limits,PublicView,VisibleImage,ValidationError
from native_direction_consistency import check_direction
from scoped_absence import route_absence
import image_evidence as contract

LEASE=Path('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json')

def main(a):
    assert sha(a.manifest)==a.manifest_sha256
    package=a.manifest.parent;manifest=json.loads(a.manifest.read_bytes())
    for n,h in manifest['files'].items():assert sha(package/n)==h,n
    plan=json.loads((package/'controls-plan.json').read_bytes())
    assert plan['limits']=={'auxiliary':6,'judge':16,'actor':0,'GUI':0,'scorer':0,'paid_API':0,'format_retries_per_judge':1}
    assert [r['id']for r in plan['auxiliary']]==['A01','A02','A03','A04','A05','A06']
    assert [r['id']for r in plan['judges']]==['R01','R02','R03','R04','R05','R06','R07','R08']
    assert os.getuid()==1033 and os.environ['CUDA_VISIBLE_DEVICES']=='4,5,6,7'
    assert not a.output.exists();a.output.mkdir()
    root=a.output;me=identity(os.getpid());save(root/'process.json',me)
    launcher=json.loads(os.environ['MIRAGE_JEV_LAUNCHER_IDENTITY'])
    assert same_identity(identity(os.getppid()),launcher)
    journal=Journal(root/'journal');started=time.time();error=None;runtime=None
    attempts={'auxiliary':[],'judge':[]};complete={'auxiliary':[],'judge':[]};results=[]
    def resource(empty=False):
        assert not (root.parent/'stop-requested.json').exists(),'Stop own attempt before another request'
        proof=assert_owned_resources(LEASE,manifest['expected_holder'],{me['pid']:me,launcher['pid']:launcher},empty)
        journal.append('actual_resource_check',proof);return proof
    def status(phase,**more):
        p=root/'.status.tmp';p.write_bytes(canonical({'phase':phase,'time':time.time(),'attempted':attempts,'completed':complete,**more}));p.replace(root/'status.json')
    try:
        resource(True)
        mutex=Path(json.loads(LEASE.read_bytes())['inference_lock']).open('a');fcntl.flock(mutex,fcntl.LOCK_EX|fcntl.LOCK_NB)
        status('loading')
        runtime=load_runtime(package,root,journal,resource,manifest,me)
        engine=runtime['engine'];torch=runtime['torch'];support=runtime['support'];audit=runtime['audited_generation']
        aux_model=runtime['auxiliary_model'];aux_processor=runtime['auxiliary_processor'];generation=runtime['generation']
        from PIL import Image
        aux_root=root/'auxiliary';aux_root.mkdir()
        for row in plan['auxiliary']:
            resource();target=aux_root/row['id'];target.mkdir()
            p=package/row['path'];assert sha(p)==row['sha256']
            request=json.loads(p.read_bytes());raw=contract.validate_image_only_request(request)
            save(target/'request.json',request);(target/'original.png').write_bytes(raw)
            messages=[{'role':'user','content':[{'type':'image','image':Image.open(io.BytesIO(raw)).convert('RGB')},{'type':'text','text':contract.FIXED_PROMPT}]}]
            attempts['auxiliary'].append(row['id']);status('auxiliary_generating',case=row['id'])
            support.reset_memory(torch);start=time.perf_counter();torch.manual_seed(0)
            journal.append('auxiliary_request',{'case':row['id'],'request_sha256':sha(target/'request.json')})
            with audit(aux_model,aux_processor,target):
                inputs=aux_processor.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=False,tools=None,return_dict=True,return_tensors='pt')
                with torch.inference_mode():output=aux_model.generate(**inputs.to('cuda:3'),generation_config=generation,return_dict_in_generate=True,output_scores=False)
            actual=json.loads((target/'actual-generation.json').read_bytes())
            text=aux_processor.tokenizer.decode(actual['output_ids'],skip_special_tokens=True,clean_up_tokenization_spaces=False)
            (target/'raw-output.txt').write_text(text,encoding='utf8')
            response={'request_sha256':digest(contract.canonical(request)),'image_sha256':request['image_sha256'],
                      'model':request['model'],'revision':request['revision'],'raw_output':text,'natural_eos':actual['natural_EOS']}
            save(target/'response.json',response)
            result={'id':row['id'],'natural_EOS':actual['natural_EOS'],'semantic_pass':None,
                    'seconds_including_instrumentation':time.perf_counter()-start}
            try:
                packet=contract.actor_packet(request,text,actual['natural_EOS']);save(target/'packet.json',packet)
                result['format_contract_valid']=True
            except contract.EvidenceContractError as exc:
                result.update(format_contract_valid=False,error=str(exc),no_retry=True)
                save(target/'contract-failure.json',result)
            complete['auxiliary'].append(result);resource()
            save(target/'seal.json',{p.name:sha(p)for p in target.iterdir()if p.is_file()})
            journal.append('auxiliary_reply_sealed',{'case':row['id'],'seal_sha256':sha(target/'seal.json'),'natural_EOS':actual['natural_EOS']})
            del inputs,output;torch.cuda.empty_cache()
        # Execute only the original parser function AST, never its browser imports/main.
        source=package/'native-parser-source.py';tree=ast.parse(source.read_text())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='parse')
        namespace={'json':json,'re':re};exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),namespace)
        parse=namespace['parse'];judge_root=root/'judges';judge_root.mkdir();current={'id':None}
        def judge(system,view,candidate):
            resource();assert len(attempts['judge'])<16,'Frozen total judge cap'
            rid='%02d'%(len(attempts['judge'])+1);target=judge_root/rid;target.mkdir()
            save(target/'request.json',{'case':current['id'],'system':system,'public':view.data(),
                'images':[{'raw_base64':base64.b64encode(im.raw).decode(),'role':im.role}for im in view.images],
                'candidate':candidate,'strict_native_judge_output_cap':4096})
            attempts['judge'].append({'case':current['id'],'call':rid});status('main_judge_generating',case=current['id'],request=rid)
            journal.append('main_request',{'case':current['id'],'request':rid,'request_sha256':sha(target/'request.json')})
            support.reset_memory(torch);start=time.perf_counter()
            with audit(engine.model,engine.processor,target):
                text=engine.judge(system,view,candidate,receipt=target/'generation.json')
            actual=json.loads((target/'actual-generation.json').read_bytes())
            (target/'raw-output.txt').write_text(text,encoding='utf8')
            save(target/'response.json',{'case':current['id'],'text':text,'natural_EOS':actual['natural_EOS'],'seconds_including_instrumentation':time.perf_counter()-start})
            resource();save(target/'seal.json',{p.name:sha(p)for p in target.iterdir()if p.is_file()})
            complete['judge'].append({'case':current['id'],'call':rid,'natural_EOS':actual['natural_EOS']})
            journal.append('main_reply_sealed',{'case':current['id'],'request':rid,'seal_sha256':sha(target/'seal.json'),'natural_EOS':actual['natural_EOS']})
            assert actual['natural_EOS'],'Original4096 nonEOS preserved; no retry beyond output cap'
            return text
        for row in plan['judges']:
            resource();p=package/row['path'];assert sha(p)==row['sha256']
            frozen=json.loads(p.read_bytes());v=frozen['view'];candidate=frozen['candidate'];current['id']=row['id']
            view=PublicView(v['observation_id'],v['messages'],tuple(VisibleImage(base64.b64decode(im['raw_base64']),im['role'])for im in v['images']),v['recent_action'],v['execution_feedback'],v['observed_at'])
            payload=parse(candidate);assert payload['type']in {'click','type','scroll','wait','stop'}
            proposal={'name':payload['type'],'parsed':True,'executor_fallback_wait':False,'payload':payload,'coordinate_space':'normalized_1000'}
            direction=check_direction(candidate,proposal);routing=route_absence(candidate,proposal)
            journal.observation(view,audience='new_constructed_source_bound_main_control')
            ctl=Controller(judge,journal,'post_only',Limits(max_verifier_calls=2,max_format_retries=1),sleeper=lambda _:None)
            before=len(attempts['judge'])
            try:
                verdict=ctl.inspect('verify',view,candidate,proposal)
                result={'id':row['id'],'format_citation_contract_valid':True,'verdict':verdict,'semantic_pass':None}
            except ValidationError as exc:
                result={'id':row['id'],'format_citation_contract_valid':False,'error':str(exc),'semantic_pass':None}
            result.update(actual_judge_calls=len(attempts['judge'])-before,native_direction=direction,extra_absence_routing=routing,
                          GUI_action_executed=False,actor_feedback_tested=False)
            save(root/(row['id']+'-result.json'),result);results.append(result)
            journal.append('new_control_terminal',result);torch.cuda.empty_cache()
        status('completed')
        save(root/'summary.json',{'status':'completed','controls':results,'auxiliary':complete['auxiliary'],
            'actual_auxiliary_calls':len(attempts['auxiliary']),'actual_judge_calls':len(attempts['judge']),
            'both_models_resident':True,'actor_GUI_scorer_paid_calls':0,'old_terminal_controls_reexecuted':False,
            'known_nonblind_development_sources':True,'semantic_efficacy_or_GUI_release_established':False})
    except BaseException as exc:
        error={'type':type(exc).__name__,'traceback':traceback.format_exc(),'resource_evidence':getattr(exc,'resource_evidence',None),'no_automatic_retry':True}
        save(root/'failure.json',error);journal.append('technical_failure_preserved',error);status('technical_failure')
    finally:
        journal.append('worker_terminal',{'status':'technical_failure'if error else'completed'})
        save(root/'terminal.json',{'status':'technical_failure'if error else'completed','attempted':attempts,'completed':complete,'error':error,'started':started,'ended':time.time(),'actor_GUI_scorer_paid_calls':0})
        save(root/'worker-manifest.json',{str(p.relative_to(root)):sha(p)for p in sorted(root.rglob('*'))if p.is_file()})
    return 1 if error else 0

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--manifest-sha256',required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    try:code=main(args)
    except BaseException:
        target=HERE/'pre-admission-failures'/str(time.time_ns());target.mkdir(parents=True)
        save(target/'failure.json',{'traceback':traceback.format_exc(),'no_automatic_retry':True});code=1
    raise SystemExit(code)
