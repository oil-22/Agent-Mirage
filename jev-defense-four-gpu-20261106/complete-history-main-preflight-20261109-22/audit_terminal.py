"""Audit full native inputs and strict Controller replay for completed22calls."""
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

HERE=Path(__file__).resolve().parent
PACKAGE=HERE/'runtime-package'
sys.path[:0]=[str(PACKAGE),str(PACKAGE/'release')]
from defense.core import Controller,Journal,Limits,ValidationError,PublicView,VisibleImage
from defense.qwen_backend import LocalQwen
import image_evidence as contract

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
canonical=lambda v:json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
digest=lambda b:hashlib.sha256(b).hexdigest()
functions=[n for n in ast.parse((PACKAGE/'worker.py').read_text(encoding='utf8')).body if isinstance(n,ast.FunctionDef)and n.name in ['restore','add_packet']]
assert len(functions)==2
exec(compile(ast.Module(body=functions,type_ignores=[]),'frozen-main22-view-functions','exec'),globals())


def save(path,value):
    with path.open('x',encoding='utf8')as stream:json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')


def main(collection):
    original=collection/'original';root=original/'worker';receipt=read(collection/'receipt.json')
    assert receipt['terminal_collection']
    for name,h in read(collection/'seal.json').items():assert sha(collection/name)==h,name
    for name,h in receipt['exported_files'].items():assert sha(original/name)==h,name
    assert all(item['actual'].get('absent')is True for item in receipt['actual_processes'].values())
    manifest=read(PACKAGE/'manifest.json');plan=read(PACKAGE/'controls-plan.json')
    assert sha(PACKAGE/'manifest.json')==receipt['manifest_sha256']
    for name,h in manifest['files'].items():assert sha(PACKAGE/name)==h,name
    terminal=read(root/'terminal.json');exit_record=read(original/'exit.json')
    assert terminal['status']=='completed'and terminal['error']is None
    assert exit_record['worker_exit_code']==exit_record['launcher_exit_code']==0
    assert terminal['attempted']['auxiliary']==terminal['completed']['auxiliary']==[]
    assert len(terminal['attempted']['actor'])==4 and 12<=len(terminal['attempted']['judge'])<=24
    cpu=read(HERE/'CPU-admission.json')['value']['proof']
    CPUactor={(row['case'],row['condition']):row for row in cpu['actor_inputs']}
    packets={}
    for row in plan['stage_readings']:
        source=PACKAGE/row['directory'];request=read(source/'request.json')
        raw=contract.validate_image_only_request(request)
        assert digest(raw)==row['image_sha256']and sha(source/'raw-output.txt')==row['source_raw_output_sha256']
        packet=contract.actor_packet(request,(source/'raw-output.txt').read_text(encoding='utf8'),True)
        assert packet==read(source/'packet.json');packets[row['id']]=packet
    totals={'input_tokens':0,'output_tokens':0,'summed_seconds_including_instrumentation':0.0};calls=[]
    for group in ['actors','judges']:
        for target in sorted((root/group).iterdir()):
            for name,h in read(target/'seal.json').items():
                assert receipt['all_terminal_original_files'][(target/name).relative_to(original).as_posix()]==h,name
            prepared=read(target/'prepared.json');forward=read(target/'first-forward.json')
            assert set(prepared)==set(forward)
            for name in prepared:
                assert all(prepared[name][k]==forward[name][k]for k in ['shape','dtype','bytes','sha256'])
                for record in [prepared[name],forward[name]]:
                    filename=(target/record['file']).relative_to(original).as_posix()
                    assert receipt['all_terminal_original_files'][filename]==record['sha256']
            actual=read(target/'actual-generation.json');generation=read(target/'effective-generation.json')
            ids=actual['output_ids'];eos=generation['eos_token_id'];eos=[eos]if isinstance(eos,int)else eos
            assert actual['natural_EOS']and ids[-1]in eos
            assert len(ids)==actual['output_tokens']==actual['actual_forward_calls']
            assert actual['input_tokens']==prepared['input_ids']['shape'][1]
            assert generation['max_new_tokens']==(2048 if group=='actors'else 4096)
            sequence=read(target/'sequence_ids.json');assert len(sequence)==1;sequence=sequence[0]
            assert sequence[actual['input_tokens']:]==ids
            packed=b''.join(int(token).to_bytes(8,'little',signed=True)for token in sequence[:actual['input_tokens']])
            assert digest(packed)==prepared['input_ids']['sha256']
            text=(target/'raw-output.txt').read_text(encoding='utf8');response=read(target/'response.json')
            assert response['text']==text and response['natural_EOS']
            native=read(target/('native-call.json'if group=='actors'else'generation.json'))
            assert native['generated_ids']==ids and native['text']==text and native['generation_config']==generation
            assert native['environment_actions_executed']is False
            totals['input_tokens']+=actual['input_tokens'];totals['output_tokens']+=len(ids)
            totals['summed_seconds_including_instrumentation']+=response['seconds_including_instrumentation']
            calls.append({'group':group,'call':target.name,'input_tokens':actual['input_tokens'],'output_tokens':len(ids),
                          'natural_EOS':True,'prepared_first_forward_and_original_binary_SHA_equal':True,
                          'raw_output_sha256':sha(target/'raw-output.txt'),'seal_sha256':sha(target/'seal.json')})
    template=read(PACKAGE/'actor-template.json');actors=[]
    for row in plan['actors']:
        source=read(PACKAGE/row['path']);view=restore(source['view'])
        for condition in row['condition_order']:
            target=root/'actors'/(row['id']+'-'+condition)
            actual_view=add_packet(view,packets[row['scene']])if condition=='single_balanced_auxiliary'else view
            body={key:copy.deepcopy(value)for key,value in template.items()if key!='messages'}
            body['messages']=copy.deepcopy(actual_view.messages)
            assert read(target/'payload.json')=={'operation':'actor','body':body}
            assert read(target/'native-call.json')['request_messages_sha256']==digest(canonical(body['messages']))
            expected=CPUactor[(row['id'],condition)]
            assert expected['body_sha256']==digest(canonical(body))
            prepared=read(target/'prepared.json');assert set(prepared)==set(expected['tensors'])
            for name in prepared:
                assert all(prepared[name][k]==expected['tensors'][name][k]for k in ['shape','dtype','bytes','sha256'])
            binding=read(target/'source-binding.json')
            assert binding['original_full_view_sha256']==digest(canonical(view.data()))
            assert binding['actual_full_view_sha256']==digest(canonical(actual_view.data()))
            assert binding['source_file_sha256']==row['sha256']==sha(PACKAGE/row['path'])
            assert sum(b.get('type')=='image_url'for m in body['messages']if isinstance(m['content'],list)for b in m['content'])==3
            actors.append({'case':row['id'],'condition':condition,'full_original_messages_and_three_full_images_preserved':True,
                           'native_CPU_tensors_equal_actual_GPU_first_forward':True,'actual_wire_hash_verified':True})
    out=HERE/('terminal-audit-'+str(time.time_ns()));out.mkdir()
    tree=ast.parse((PACKAGE/'native-parser-source.py').read_text(encoding='utf8'))
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='parse')
    namespace={'json':json,'re':re};exec(compile(ast.Module(body=[node],type_ignores=[]),'native-parser','exec'),namespace)
    parse=namespace['parse'];conditions=[]
    for row in plan['judges']:
        source=read(PACKAGE/row['path']);candidate=source['candidate'];native=parse(candidate)
        proposal={'name':native['type'],'parsed':True,'executor_fallback_wait':False,'payload':native,'coordinate_space':'normalized_1000'}
        for condition in row['condition_order']:
            view=restore(source['view'])
            if condition=='single_balanced_auxiliary':view=add_packet(view,packets[row['scene']])
            requests=[]
            for target in sorted((root/'judges').iterdir()):
                request=read(target/'request.json')
                if request['case']==row['id']and request['condition']==condition:requests.append((target,request))
            assert 1<=len(requests)<=2;counter={'n':0}
            def replay(system,actual_view,actual_candidate):
                target,request=requests[counter['n']];counter['n']+=1
                assert request['system']==system and request['candidate']==actual_candidate==candidate
                assert actual_view.data()==request['public']
                assert [im.raw for im in actual_view.images]==[base64.b64decode(im['raw_base64'])for im in request['images']]
                stub=LocalQwen.__new__(LocalQwen)
                def capture(messages,max_tokens,path,**kwargs):
                    assert max_tokens==4096
                    assert digest(canonical(messages))==read(target/'generation.json')['request_messages_sha256']
                    return(target/'raw-output.txt').read_text(encoding='utf8')
                stub.generate=capture
                return stub.judge(system,actual_view,actual_candidate)
            controller=Controller(replay,Journal(out/(row['id']+'-'+condition)),'post_only',Limits(max_verifier_calls=2,max_format_retries=1),sleeper=lambda _:None)
            saved=read(root/(row['id']+'-'+condition+'-result.json'))
            try:
                verdict=controller.inspect('verify',view,candidate,proposal)
                assert saved['format_citation_contract_valid']and verdict==saved['verdict']
            except ValidationError as exc:
                assert saved['format_citation_contract_valid']is False and saved['error']==str(exc)
            assert counter['n']==len(requests)==saved['actual_judge_calls']
            conditions.append({'case':row['id'],'condition':condition,'actual_calls':counter['n'],
                 'format_citation_contract_valid':saved['format_citation_contract_valid'],
                 'strict_Controller_CPU_replay_and_actual_wire_hash_equal':True,'semantic_pass':None})
    result={'schema':'complete-history-main22-technical-audit-v1','time':time.time(),'passed':True,
          'collection_receipt_sha256':sha(collection/'receipt.json'),'manifest_sha256':receipt['manifest_sha256'],
          'all_original_files_verified':len(receipt['all_terminal_original_files']),'chains':receipt['chains'],
          'actual_main_model_calls':len(calls),'natural_EOS':len(calls),'actor_calls':4,
          'judge_calls':len(calls)-4,'judge_conditions':12,'format_retries':len(calls)-16,
          'fresh_auxiliary_calls':0,'frozen_readings_stage_inputs_only':True,
          'judge_conditions_format_citation_valid':sum(r['format_citation_contract_valid']for r in conditions),
          'actors':actors,'conditions':conditions,'all_calls':calls,'totals':totals,
          'four_GPU_reserved_seconds_in_launcher':exit_record['four_GPU_reserved_seconds_in_launcher'],
          'holder_reservation_outside_launcher_excluded':True,
          'all_images_histories_precision_and_caps_unchanged':True,'new_GUI_scorer_paid_calls':0,
          'all_future_history_capacity_or_full_GUI_or_trajectory_reduction_established':False,'goal':'active'}
    save(out/'receipt.json',result);save(out/'seal.json',{q.relative_to(out).as_posix():sha(q)for q in out.rglob('*')if q.is_file()})
    print(json.dumps({'audit':str(out),'receipt_sha256':sha(out/'receipt.json'),'main_calls':len(calls),
          'format_citation_valid_conditions':result['judge_conditions_format_citation_valid'],'totals':totals},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--collection',type=Path,required=True)
    main(parser.parse_args().collection)
