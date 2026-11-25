"""Audit original complete input bindings and replay the frozen strict Controller."""
import argparse
import ast
import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import time
from PIL import Image

HERE=Path(__file__).resolve().parent
PACKAGE=HERE/'runtime-package'
sys.path[:0]=[str(PACKAGE),str(PACKAGE/'release')]
from defense.core import Controller,Journal,Limits,ValidationError,PublicView,VisibleImage
from defense.qwen_backend import LocalQwen
import image_evidence as contract

canonical=lambda value:json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
digest=lambda raw:hashlib.sha256(raw).hexdigest()
_tree=ast.parse((PACKAGE/'worker.py').read_text(encoding='utf8'))
_functions=[node for node in _tree.body if isinstance(node,ast.FunctionDef)and node.name in ['restore','add_packet']]
assert len(_functions)==2
exec(compile(ast.Module(body=_functions,type_ignores=[]),'frozen-worker-public-view-functions','exec'),globals())


def read(path):return json.loads(Path(path).read_bytes())


def save(path,value):
    with Path(path).open('x',encoding='utf8')as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')


def main(collection):
    original=collection/'original'
    root=original/'worker'
    receipt=read(collection/'receipt.json')
    assert receipt['terminal_collection'] and receipt['new_model_GPU_GUI_scorer_paid_calls']==0
    for name,expected in read(collection/'seal.json').items():assert sha(collection/name)==expected,name
    for name,expected in receipt['exported_files'].items():assert sha(original/name)==expected,name
    assert all(row['actual'].get('absent')is True for row in receipt['actual_processes'].values())
    manifest=read(PACKAGE/'manifest.json');plan=read(PACKAGE/'controls-plan.json')
    assert sha(PACKAGE/'manifest.json')==receipt['manifest_sha256']
    for name,expected in manifest['files'].items():assert sha(PACKAGE/name)==expected,name
    terminal=read(root/'terminal.json');exit_record=read(original/'exit.json')
    assert terminal['status']=='completed' and terminal['error']is None
    assert exit_record['worker_exit_code']==exit_record['launcher_exit_code']==0
    assert {key:len(rows)for key,rows in terminal['attempted'].items()}=={'auxiliary':7,'actor':8,'judge':22}
    out=HERE/('terminal-audit-'+str(time.time_ns()));out.mkdir()
    packets={};rows=[];call_ids=set();auxiliary_rows=[];totals={'input_tokens':0,'output_tokens':0,'summed_seconds_including_instrumentation':0.0}
    CPU=read(HERE/'CPU-admission.json')['value']['proof']
    CPUaux={row['case']:row['tensors']for row in CPU['auxiliary_inputs']}
    for group in ['auxiliary','actors','judges']:
        for target in sorted((root/group).iterdir()):
            prepared=read(target/'prepared.json');forward=read(target/'first-forward.json')
            assert set(prepared)==set(forward)
            for name in prepared:
                assert all(prepared[name][k]==forward[name][k]for k in ['shape','dtype','bytes','sha256']),str(target/name)
                # Remote terminal collection hashed the original binary bytes.
                for record in [prepared[name],forward[name]]:
                    remote_name=(target/record['file']).relative_to(original).as_posix()
                    assert receipt['all_terminal_original_files'][remote_name]==record['sha256'],remote_name
            actual=read(target/'actual-generation.json');generation=read(target/'effective-generation.json')
            ids=actual['output_ids'];eos=generation['eos_token_id'];eos=[eos]if isinstance(eos,int)else eos
            assert len(ids)==actual['output_tokens']==actual['actual_forward_calls']
            assert ids[-1]in eos and actual['natural_EOS']
            assert actual['input_tokens']==prepared['input_ids']['shape'][1]
            response=read(target/'response.json');text=(target/'raw-output.txt').read_text(encoding='utf8')
            assert response['text']==text and response['natural_EOS']
            assert generation['max_new_tokens']==(4096 if group=='judges'else 2048)
            row={'group':group,'call':target.name,'input_tokens':actual['input_tokens'],'output_tokens':len(ids),
                 'natural_EOS':True,'seal_sha256':sha(target/'seal.json'),
                 'actual_IDs_pixels_grid_and_other_forward_tensors_match_prepared_and_remote_binary_SHA':True}
            totals['input_tokens']+=actual['input_tokens'];totals['output_tokens']+=len(ids)
            totals['summed_seconds_including_instrumentation']+=response['seconds_including_instrumentation']
            if group=='auxiliary':
                request=read(target/'request.json')
                source=next(r for r in plan['auxiliary']if r['id']==target.name)
                assert request==read(PACKAGE/source['path'])
                raw=contract.validate_image_only_request(request)
                assert raw==(target/'original.png').read_bytes()
                for name in prepared:
                    assert all(prepared[name][key]==CPUaux[target.name][name][key]for key in ['shape','dtype','bytes','sha256'])
                boundary=read(target/'stateless-input-boundary.json');life=read(target/'stateless-context-discarded.json')
                assert boundary['message_count']==1 and boundary['content_types']==['image','text']
                assert boundary['complete_image_sha256']==source['image_sha256']==request['image_sha256']
                assert boundary['fixed_prompt_sha256']==manifest['fixed_prompt_sha256']==request['prompt_sha256']
                assert boundary['task_history_candidate_previous_auxiliary_content_supplied']is False
                with Image.open(target/'original.png')as image:
                    assert list(image.size)==boundary['size']==[1280,720]
                    assert digest(image.convert('RGB').tobytes())==boundary['complete_RGB_sha256']
                assert life['call_id']==boundary['call_id'] and life['call_id']not in call_ids
                call_ids.add(life['call_id'])
                assert life['actual_first_forward_cache_length']==0 and life['all_observed_cache_objects_released']
                assert life['observed_cache_objects_still_alive']==0 and life['observed_cache_objects']>0
                assert life['untrackable_cache_types']==[] and life['error_type']is None
                assert life['main_model_or_main_context_referenced']is False
                mask=read(target/'actual-mask-steps.json')
                assert mask['all_actual_selected_tokens_allowed'] and [s['selected_id']for s in mask['steps']]==ids
                assert all(s['selected_allowed']for s in mask['steps'])
                assert read(target/'raw-UTF8-validation.json')['strict_native_UTF8_roundtrip']
                packet=read(target/'packet.json');valid=False;error=None
                try:
                    rebuilt=contract.actor_packet(request,text,True);assert rebuilt==packet;valid=True
                except contract.EvidenceContractError as exc:
                    error=str(exc);assert error==read(target/'contract-failure.json')['error']
                    assert packet['reading']is None and packet['automatic_allow_or_block']is False
                    assert packet['status']=='preserved_technical_or_contract_failure_no_retry'
                packets[target.name]=packet
                row.update(single_complete_image_fixed_prompt_empty_first_KV_and_released_context_verified=True,
                           native_CPU_admission_equal_actual_forward=True,format_contract_valid=valid,
                           contract_error=error,semantic_pass=None)
                auxiliary_rows.append(row)
            else:
                native=read(target/('generation.json'if group=='judges'else'native-call.json'))
                assert native['generated_ids']==ids and native['text']==text and native['generation_config']==generation
                packed=b''.join(int(token).to_bytes(8,'little',signed=True)for token in native['input_ids'])
                assert digest(packed)==prepared['input_ids']['sha256']
                assert native['environment_actions_executed']is False
            rows.append(row)

    template=read(PACKAGE/'actor-template.json');actor_rows=[]
    for source in plan['actors']:
        frozen=read(PACKAGE/source['path']);view=restore(frozen['view'])
        for condition in source['condition_order']:
            target=root/'actors'/(source['id']+'-'+condition)
            actual_view=add_packet(view,packets[source['scene']])if condition=='single_balanced_auxiliary'else view
            body={key:copy.deepcopy(value)for key,value in template.items()if key!='messages'}
            body['messages']=copy.deepcopy(actual_view.messages)
            assert read(target/'payload.json')=={'operation':'actor','body':body}
            assert read(target/'native-call.json')['request_messages_sha256']==digest(canonical(body['messages']))
            binding=read(target/'source-binding.json')
            assert binding['original_full_view_sha256']==digest(canonical(view.data()))
            assert binding['actual_full_view_sha256']==digest(canonical(actual_view.data()))
            assert binding['source_file_sha256']==source['sha256']==sha(PACKAGE/source['path'])
            actor_rows.append({'case':source['id'],'condition':condition,'full_original_messages_and_image_blocks_preserved':True,
                               'actual_wire_messages_hash_verified':True,'native_actor_reply_is_unedited':True})

    tree=ast.parse((PACKAGE/'native-parser-source.py').read_text(encoding='utf8'))
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='parse')
    namespace={'json':json,'re':re};exec(compile(ast.Module(body=[node],type_ignores=[]),'native-parser','exec'),namespace)
    parse=namespace['parse'];paired=[]
    for source in plan['judges']:
        frozen=read(PACKAGE/source['path']);candidate=frozen['candidate'];native=parse(candidate)
        proposal={'name':native['type'],'parsed':True,'executor_fallback_wait':False,'payload':native,'coordinate_space':'normalized_1000'}
        for condition in source['condition_order']:
            view=restore(frozen['view'])
            if condition=='single_balanced_auxiliary':view=add_packet(view,packets[source['scene']])
            requests=[]
            for target in sorted((root/'judges').iterdir()):
                request=read(target/'request.json')
                if request['case']==source['id']and request['condition']==condition:requests.append((target,request))
            assert 1<=len(requests)<=2;calls={'n':0}
            def replay(system,actual_view,actual_candidate):
                target,request=requests[calls['n']];calls['n']+=1
                assert actual_candidate==candidate==request['candidate'] and system==request['system']
                assert actual_view.data()==request['public']
                assert [im.raw for im in actual_view.images]==[base64.b64decode(im['raw_base64'])for im in request['images']]
                # Execute the frozen message builder without constructing/loading a model.
                stub=LocalQwen.__new__(LocalQwen)
                def capture(messages,max_tokens,path,**kwargs):
                    assert max_tokens==4096
                    assert digest(canonical(messages))==read(target/'generation.json')['request_messages_sha256']
                    return (target/'raw-output.txt').read_text(encoding='utf8')
                stub.generate=capture
                return stub.judge(system,actual_view,actual_candidate,receipt=None)
            controller=Controller(replay,Journal(out/(source['id']+'-'+condition)),'post_only',
                                  Limits(max_verifier_calls=2,max_format_retries=1),sleeper=lambda _:None)
            saved=read(root/(source['id']+'-'+condition+'-result.json'))
            try:
                verdict=controller.inspect('verify',view,candidate,proposal)
                assert saved['format_citation_contract_valid']and verdict==saved['verdict']
            except ValidationError as exc:
                assert saved['format_citation_contract_valid']is False and str(exc)==saved['error']
            assert calls['n']==len(requests)==saved['actual_judge_calls']
            paired.append({'case':source['id'],'condition':condition,'actual_calls':calls['n'],
                           'unchanged_strict_Controller_CPU_replay_equal_actual_terminal':True,
                           'actual_verifier_wire_message_hash_verified':True,'original_full_public_and_candidate_retained':True,
                           'format_citation_contract_valid':saved['format_citation_contract_valid'],
                           'original_error':saved.get('error'),'semantic_pass':None})
    assert len(rows)==37 and len(actor_rows)==8 and len(paired)==22 and len(auxiliary_rows)==7
    result={'schema':'balanced16-complete-technical-audit-v1','time':time.time(),'passed':True,
            'manifest_sha256':receipt['manifest_sha256'],'collection_receipt_sha256':sha(collection/'receipt.json'),
            'terminal_collection':str(collection),'all_original_files_verified':len(receipt['all_terminal_original_files']),
            'source_files_verified':receipt['source_files_verified'],'chains':receipt['chains'],
            'actual_attempts':37,'natural_EOS':37,'auxiliary_calls':7,'actor_calls':8,'judge_calls':22,
            'format_retries':0,'auxiliary_contract_valid':sum(row['format_contract_valid']for row in auxiliary_rows),
            'judge_conditions_format_citation_valid':sum(row['format_citation_contract_valid']for row in paired),
            'auxiliary':auxiliary_rows,'actors':actor_rows,'judges':paired,'all_calls':rows,'totals':totals,
            'four_GPU_reserved_seconds_in_launcher':exit_record['four_GPU_reserved_seconds_in_launcher'],
            'holder_reservation_outside_launcher_excluded_from_that_number':True,
            'model_seconds_include_instrumentation_not_walltime_currency_energy':True,
            'new_model_GUI_scorer_paid_calls_in_audit':0,'full_GUI_or_trajectory_reduction_established':False,
            'one_reviewer_not_blind_constructed_development_not_native_task_success':True,'goal':'active'}
    save(out/'receipt.json',result)
    save(out/'seal.json',{p.relative_to(out).as_posix():sha(p)for p in out.rglob('*')if p.is_file()})
    print(json.dumps({'audit':str(out),'receipt_sha256':sha(out/'receipt.json'),'calls':37,
                      'auxiliary_contract_valid':result['auxiliary_contract_valid'],
                      'judge_conditions_format_citation_valid':result['judge_conditions_format_citation_valid'],
                      'totals':totals},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--collection',type=Path,required=True)
    main(parser.parse_args().collection)
