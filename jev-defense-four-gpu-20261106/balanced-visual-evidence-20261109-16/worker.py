"""Finite paired development with one stateless image-only auxiliary.

Never starts a task browser, actor loop, scorer, paid API, or old queue.  A
packet is a fallible alternate reading, not a source of ground-truth boxes.
"""
import argparse
import ast
import base64
import copy
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE),str(HERE/'release')]
from model_runtime import load_runtime,save,sha,canonical,digest
from resource_gate import assert_owned_resources,identity,same_identity
from defense.core import Controller,Journal,Limits,PublicView,VisibleImage,ValidationError
import bounded_auxiliary
import image_evidence as contract

LEASE = Path('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json')
LIMITS = {'auxiliary':7,'actor':8,'judge':44,'format_retries_per_judge_control':1,
          'GUI':0,'scorer':0,'paid_API':0,'auxiliary_retries':0,'actor_retries':0}


def restore(frozen):
    return PublicView(frozen['observation_id'],copy.deepcopy(frozen['messages']),
                      tuple(VisibleImage(base64.b64decode(im['raw_base64']),im['role']) for im in frozen['images']),
                      frozen['recent_action'],frozen['execution_feedback'],frozen['observed_at'])


def add_packet(view,packet):
    original = canonical(view.data())
    result = copy.deepcopy(view)
    message = result.messages[-1]
    assert message['role']=='user' and isinstance(message['content'],list)
    images=[block for block in message['content'] if block.get('type')=='image_url']
    assert len(images)==1 and len(view.images)==1 and view.images[0].role=='current'
    assert digest(view.images[0].raw)==packet['image_sha256']
    message['content'].append({'type':'text','text':contract.ACTOR_BOUNDARY+json.dumps(packet,ensure_ascii=False,separators=(',',':'))})
    assert result.messages[:-1]==view.messages[:-1]
    assert result.messages[-1]['content'][:-1]==view.messages[-1]['content']
    assert canonical(view.data())==original
    return result


def main(a):
    assert sha(a.manifest)==a.manifest_sha256
    manifest=json.loads(a.manifest.read_bytes());package=a.manifest.parent
    for name,expected in manifest['files'].items():assert sha(package/name)==expected,name
    plan=json.loads((package/'controls-plan.json').read_bytes())
    assert plan['limits']==manifest['limits']==LIMITS
    assert len(plan['auxiliary'])==7 and len(plan['actors'])==4 and len(plan['judges'])==11
    assert sha(package/'fixed-prompt.txt')==manifest['fixed_prompt_sha256']
    assert (package/'fixed-prompt.txt').read_text()==contract.FIXED_PROMPT
    assert os.getuid()==1033 and os.environ['CUDA_VISIBLE_DEVICES']=='4,5,6,7'
    assert not a.output.exists();a.output.mkdir()
    root=a.output;me=identity(os.getpid());launcher=json.loads(os.environ['MIRAGE_JEV_LAUNCHER_IDENTITY'])
    assert same_identity(identity(os.getppid()),launcher)
    save(root/'process.json',me);journal=Journal(root/'journal')
    attempts={'auxiliary':[],'actor':[],'judge':[]};completed={'auxiliary':[],'actor':[],'judge':[]}
    started=time.time();error=None;packets={};results=[]

    def resource(empty=False):
        assert not (root.parent/'stop-requested.json').exists()
        proof=assert_owned_resources(LEASE,manifest['expected_holder'],{me['pid']:me,launcher['pid']:launcher},empty)
        journal.append('actual_resource_check',proof)
        return proof

    def status(phase,**extra):
        p=root/'.status.tmp'
        p.write_bytes(canonical({'phase':phase,'time':time.time(),'attempted':attempts,'completed':completed,**extra}))
        p.replace(root/'status.json')

    def frozen(row):
        p=package/row['path'];assert sha(p)==row['sha256']
        return json.loads(p.read_bytes())

    def seal(target,kind,data):
        save(target/'seal.json',{p.name:sha(p) for p in target.iterdir() if p.is_file()})
        journal.append(kind,dict(data,seal_sha256=sha(target/'seal.json')))

    try:
        resource(True)
        mutex=Path(json.loads(LEASE.read_bytes())['inference_lock']).open('a')
        fcntl.flock(mutex,fcntl.LOCK_EX|fcntl.LOCK_NB)
        status('loading')
        rt=load_runtime(package,root,journal,resource,manifest,me)
        engine,torch,audit=rt['engine'],rt['torch'],rt['audited_generation']
        support=rt['support'];model=rt['auxiliary_model'];processor=rt['auxiliary_processor'];generation=rt['generation']
        data=bounded_auxiliary.prepare(processor,generation,root,package)
        call_ids=set()
        for row in plan['auxiliary']:
            assert len(attempts['auxiliary'])<LIMITS['auxiliary']
            request=frozen(row);raw=contract.validate_image_only_request(request)
            assert digest(raw)==row['image_sha256']
            target=root/'auxiliary'/row['id'];target.mkdir(parents=True)
            save(target/'request.json',request);(target/'original.png').write_bytes(raw)
            resource();attempts['auxiliary'].append(row['id']);status('auxiliary_generating',case=row['id'])
            journal.append('new_auxiliary_request',{'case':row['id'],'request_sha256':sha(target/'request.json'),
                          'only_one_complete_image_and_fixed_prompt':True})
            support.reset_memory(torch);began=time.perf_counter()
            text,actual,utf8=bounded_auxiliary.generate(model,processor,generation,torch,audit,data,raw,target)
            life=json.loads((target/'stateless-context-discarded.json').read_bytes())
            assert life['actual_first_forward_cache_length']==0 and life['all_observed_cache_objects_released']
            assert life['call_id']not in call_ids;call_ids.add(life['call_id'])
            save(target/'response.json',{'text':text,'natural_EOS':actual['natural_EOS'],
                                         'seconds_including_instrumentation':time.perf_counter()-began})
            result={'case':row['id'],'natural_EOS':actual['natural_EOS'],'semantic_pass':None,'format_contract_valid':False}
            try:
                if not utf8:raise contract.EvidenceContractError('Native strict UTF8 roundtrip failed')
                packet=contract.actor_packet(request,text,actual['natural_EOS'])
                result['format_contract_valid']=True
            except contract.EvidenceContractError as exc:
                save(target/'contract-failure.json',{'error':str(exc),'no_retry':True})
                packet={'policy':contract.POLICY,'status':'preserved_technical_or_contract_failure_no_retry',
                        'image_sha256':request['image_sha256'],'reading':None,'automatic_allow_or_block':False,
                        'semantic_correctness_established':False,'inventory_is_exhaustive':False,'auxiliary_model_count':1}
            save(target/'packet.json',packet);packets[row['id']]=packet;completed['auxiliary'].append(result)
            resource();seal(target,'auxiliary_reply_sealed',{'case':row['id']});torch.cuda.empty_cache()

        template=json.loads((package/'actor-template.json').read_bytes())
        for row in plan['actors']:
            source=frozen(row);view=restore(source['view'])
            for condition in row['condition_order']:
                resource();assert len(attempts['actor'])<LIMITS['actor']
                actual_view=add_packet(view,packets[row['scene']]) if condition=='single_balanced_auxiliary' else view
                body={k:copy.deepcopy(v) for k,v in template.items() if k!='messages'}
                body['messages']=copy.deepcopy(actual_view.messages)
                target=root/'actors'/(row['id']+'-'+condition);target.mkdir(parents=True)
                save(target/'payload.json',{'operation':'actor','body':body})
                save(target/'source-binding.json',{'case':row['id'],'condition':condition,
                     'original_full_view_sha256':digest(canonical(view.data())),
                     'actual_full_view_sha256':digest(canonical(actual_view.data())),
                     'source_file_sha256':row['sha256'],'current_image_sha256':digest(view.images[0].raw),
                     'original_history_and_image_blocks_unchanged':True,
                     'auxiliary_packet_sha256':digest(canonical(packets[row['scene']])) if condition!='no_auxiliary' else None})
                attempts['actor'].append({'case':row['id'],'condition':condition});status('actor_generating',case=row['id'],condition=condition)
                journal.observation(actual_view,audience='constructed_actor_pair')
                journal.append('actual_actor_request',{'case':row['id'],'condition':condition,'payload_sha256':sha(target/'payload.json')})
                support.reset_memory(torch);began=time.perf_counter()
                with audit(engine.model,engine.processor,target):
                    reply=engine.generate(body['messages'],2048,target/'native-call.json',original_body=body)
                actual=json.loads((target/'actual-generation.json').read_bytes())
                (target/'raw-output.txt').write_text(reply,encoding='utf8')
                save(target/'response.json',{'text':reply,'natural_EOS':actual['natural_EOS'],
                                             'seconds_including_instrumentation':time.perf_counter()-began})
                completed['actor'].append({'case':row['id'],'condition':condition,'natural_EOS':actual['natural_EOS']})
                assert actual['natural_EOS'];resource();seal(target,'actor_reply_sealed',{'case':row['id'],'condition':condition})
                torch.cuda.empty_cache()

        tree=ast.parse((package/'native-parser-source.py').read_text())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='parse')
        namespace={'json':json,'re':re}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'native-parser-source.py','exec'),namespace)
        parse=namespace['parse']
        current={'case':None,'condition':None,'calls':0}

        def judge(system,view,candidate):
            resource();assert len(attempts['judge'])<LIMITS['judge'] and current['calls']<2
            current['calls']+=1
            number='%02d'%(len(attempts['judge'])+1)
            target=root/'judges'/number;target.mkdir(parents=True)
            request={'case':current['case'],'condition':current['condition'],'system':system,
                     'public':view.data(),'images':[{'raw_base64':base64.b64encode(im.raw).decode(),'role':im.role} for im in view.images],
                     'candidate':candidate,'strict_native_output_cap':4096}
            save(target/'request.json',request)
            attempts['judge'].append({'case':current['case'],'condition':current['condition'],'request':number})
            status('judge_generating',case=current['case'],condition=current['condition'],request=number)
            journal.append('actual_judge_request',{'case':current['case'],'condition':current['condition'],'request':number,'request_sha256':sha(target/'request.json')})
            support.reset_memory(torch);began=time.perf_counter()
            with audit(engine.model,engine.processor,target):
                text=engine.judge(system,view,candidate,receipt=target/'generation.json')
            actual=json.loads((target/'actual-generation.json').read_bytes())
            (target/'raw-output.txt').write_text(text,encoding='utf8')
            save(target/'response.json',{'text':text,'natural_EOS':actual['natural_EOS'],
                                         'seconds_including_instrumentation':time.perf_counter()-began})
            completed['judge'].append({'case':current['case'],'condition':current['condition'],'request':number,'natural_EOS':actual['natural_EOS']})
            resource();seal(target,'judge_reply_sealed',{'request':number})
            assert actual['natural_EOS'],'Original4096 nonEOS terminal preserved without extension'
            return text

        for row in plan['judges']:
            source=frozen(row);view=restore(source['view']);candidate=source['candidate']
            native=parse(candidate)
            proposal={'name':native['type'],'parsed':True,'executor_fallback_wait':False,
                      'payload':native,'coordinate_space':'normalized_1000'}
            for condition in row['condition_order']:
                actual_view=add_packet(view,packets[row['scene']]) if condition=='single_balanced_auxiliary' else view
                current.update(case=row['id'],condition=condition,calls=0)
                journal.observation(actual_view,audience='constructed_main_judge_pair')
                controller=Controller(judge,journal,'post_only',Limits(max_verifier_calls=2,max_format_retries=1),sleeper=lambda _:None)
                before=len(attempts['judge'])
                try:
                    verdict=controller.inspect('verify',actual_view,candidate,proposal)
                    result={'case':row['id'],'condition':condition,'format_citation_contract_valid':True,
                            'verdict':verdict,'semantic_pass':None}
                except ValidationError as exc:
                    result={'case':row['id'],'condition':condition,'format_citation_contract_valid':False,
                            'error':str(exc),'semantic_pass':None}
                result.update(actual_judge_calls=len(attempts['judge'])-before,GUI_action_executed=False,
                              actor_feedback_or_full_GUI_tested=False,
                              same_complete_source_image_sha256=digest(view.images[0].raw),
                              original_public_messages_and_candidate_retained=True)
                save(root/(row['id']+'-'+condition+'-result.json'),result)
                results.append(result);journal.append('paired_judge_control_terminal',result)
                torch.cuda.empty_cache()
        status('completed')
        save(root/'summary.json',{'status':'completed','paired_judge_controls':results,'completed':completed,
             'actual_counts':{k:len(v) for k,v in attempts.items()},'new_GUI_scorer_paid_calls':0,
             'old_completed_controls_reexecuted':False,'trajectory_Mirage_reduction_or_GUI_release_established':False})
    except BaseException as exc:
        error={'type':type(exc).__name__,'traceback':traceback.format_exc(),
               'resource_evidence':getattr(exc,'resource_evidence',None),'no_automatic_retry':True}
        save(root/'failure.json',error);journal.append('failure_preserved',error);status('failure')
    finally:
        journal.append('worker_terminal',{'status':'failure' if error else 'completed'})
        save(root/'terminal.json',{'status':'failure' if error else 'completed','attempted':attempts,'completed':completed,
             'error':error,'started':started,'ended':time.time(),'new_GUI_scorer_paid_calls':0})
        save(root/'worker-manifest.json',{p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file()})
    return 1 if error else 0


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args()
    try:
        code=main(a)
    except BaseException:
        p=HERE/'pre-admission-failures'/str(time.time_ns());p.mkdir(parents=True)
        save(p/'failure.json',{'traceback':traceback.format_exc(),'no_automatic_retry':True});code=1
    raise SystemExit(code)
