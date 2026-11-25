"""Native CPU-only full-history processor and strict image-index admission.

Synthetic accepted exchanges use complete sealed development fixtures; no
benchmark trajectory, official score, model weights or generation is performed.
"""
import argparse
import base64
import copy
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
ORIGINAL=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/unicode-guard-real-preflight-20261109-18')
TERMINAL=Path('/home/researcher/jev-defense-four-gpu-20261106/unicode-guard-real-preflight-20261109-18/worker')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(path,value):
    with path.open('x',encoding='utf8')as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')


def main(root):
    assert os.getuid()==1033 and os.environ.get('CUDA_VISIBLE_DEVICES')==''
    assert not root.exists();root.mkdir()
    p=Path('/proc',str(os.getpid()));tail=(p/'stat').read_text().rsplit(')',1)[1].split()
    save(root/'process.json',{'pid':os.getpid(),'uid':p.stat().st_uid,
         'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':tail[19]})
    failure=None;rows=[]
    try:
        for name,h in json.loads((HERE/'source-seal.json').read_bytes()).items():assert sha(HERE/name)==h,name
        sys.path[:0]=[str(HERE),str(ORIGINAL),str(ORIGINAL/'release')]
        from complete_actor_history import CompleteAcceptedActorHistory,HistoryBindingError
        from defense.core import PublicView,VisibleImage,canonical,digest
        from defense.qwen_backend import LocalQwen
        from defense.prompts import VERIFY
        import torch
        from transformers import AutoProcessor,GenerationConfig
        from aux_identity_support import tensor_record
        assert torch.cuda.device_count()==0
        ref=json.loads((ORIGINAL/'primary-reference.json').read_bytes())
        processor=AutoProcessor.from_pretrained(ref['primary_model'],local_files_only=True,trust_remote_code=True)
        native_generation=GenerationConfig.from_pretrained(ref['primary_model'],local_files_only=True)
        template=json.loads((ORIGINAL/'actor-template.json').read_bytes());system=template['messages'][0]['content']
        scenes=['T01-object-catalog','T03-filled-filter','T02-paged-records']
        raws={scene:(TERMINAL/'auxiliary'/scene/'original.png').read_bytes()for scene in scenes}
        packets={scene:json.loads((TERMINAL/'auxiliary'/scene/'packet.json').read_bytes())for scene in scenes}
        def block(raw):return{'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(raw).decode()}}
        def current_body(history,scene,auxiliary):
            content=[{'type':'text','text':'Task: Continue inspecting this constructed development collection.'},block(raws[scene])]
            if auxiliary:content.append({'type':'text','text':'Fallible frozen single-image reading: '+json.dumps(packets[scene],ensure_ascii=False)})
            body={k:copy.deepcopy(v)for k,v in template.items()if k!='messages'}
            body['messages']=history.current_messages(content)
            return body
        class CapturedBeforeGeneration(Exception):pass
        class CPUModel:
            device=torch.device('cpu')
            generation_config=native_generation
            def generate(self,**inputs):
                records={name:tensor_record(tensor,torch,capture['root'],name,'native_full_history_CPU_only_no_weights')
                         for name,tensor in inputs.items()if isinstance(tensor,torch.Tensor)}
                capture.update(records=records,generation_config=inputs['generation_config'].to_dict())
                raise CapturedBeforeGeneration()
        for auxiliary in [False,True]:
            history=CompleteAcceptedActorHistory(system)
            for index,scene in enumerate(scenes[:2]):
                body=current_body(history,scene,auxiliary)
                reply='I will inspect the next visible control.\n<action>{"type":"wait"}</action>'
                history.record_actual_reply(body,reply)
                history.commit_accepted({'status':'accepted','candidate':reply,'observation_id':'fixture-'+str(index)})
            body=current_body(history,scenes[2],auxiliary)
            references=history.reference_image_bytes(raws[scenes[2]])
            assert references==[raws[scene]for scene in scenes[:2]]
            images=(VisibleImage(raws[scenes[2]],'current'),)+tuple(VisibleImage(raw,'reference')for raw in references)
            view=PublicView('full-history-current',copy.deepcopy(body['messages']),images,'','',time.time())
            arm=root/('aux'if auxiliary else'noaux');arm.mkdir()
            capture={'root':arm/'actor'};capture['root'].mkdir()
            engine=LocalQwen.__new__(LocalQwen);engine.processor=processor;engine.torch=torch;engine.model=CPUModel()
            try:engine.generate(body['messages'],2048,arm/'unused-actor-receipt.json',original_body=body)
            except CapturedBeforeGeneration:pass
            else:raise AssertionError('Native actor reached actual generation unexpectedly')
            assert capture['records']['image_grid_thw']['shape']==[3,3]
            assert capture['generation_config']['max_new_tokens']==2048
            save(arm/'actor/CPU-prepared.json',{'records':capture['records'],'generation_config':capture['generation_config']})
            # The strict native judge builder must resolve every old original image.
            wire={}
            def capture_judge(messages,max_tokens,path,**kwargs):
                wire.update(messages=copy.deepcopy(messages),max_tokens=max_tokens,schema=kwargs['json_schema'])
                return 'CPU_WIRE_CAPTURE_ONLY_NOT_A_MODEL_REPLY'
            judge=LocalQwen.__new__(LocalQwen);judge.generate=capture_judge
            candidate='<action>{"type":"wait"}</action>'
            judge.judge(VERIFY,view,candidate,arm/'unused-judge-receipt.json')
            assert wire['max_tokens']==4096
            image_blocks=[b for b in wire['messages'][1]['content']if b['type']=='image_url']
            assert len(image_blocks)==3
            assert [base64.b64decode(b['image_url']['url'].split(',',1)[1])for b in image_blocks]==[i.raw for i in images]
            save(arm/'judge-wire.json',{'messages_sha256':digest(canonical(wire['messages'])),'image_SHA':[digest(i.raw)for i in images],
                 'roles':[i.role for i in images],'max_tokens':4096,'full_original_actor_body_sha256':digest(canonical(body))})
            # Explicit negative: new full actor history plus old current-only list fails.
            incomplete=PublicView(view.observation_id,copy.deepcopy(view.messages),(images[0],),'','',view.observed_at)
            try:judge.judge(VERIFY,incomplete,candidate,arm/'unused-negative-receipt.json')
            except ValueError as exc:assert str(exc)=='Message image missing from public image list'
            else:raise AssertionError('Unbound historical image accepted by native judge')
            rows.append({'auxiliary_arm':auxiliary,'actor_native_CPU_tokens':capture['records']['input_ids']['shape'][1],
                         'actor_native_CPU_image_count':3,'all_historical_image_index_bindings_valid':True,
                         'missing_history_image_list_rejected':True,'current_and_reference_roles':['current','reference','reference'],
                         'actual_GPU_or_model_generation_calls':0,
                         'old_accepted_auxiliary_text_retained_only_in_main_history':auxiliary})
        save(root/'receipt.json',{'time':time.time(),'passed':True,'checks':rows,'arms':2,
             'new_model_GPU_GUI_scorer_calls':0,'weights_loaded':False,
             'backend_sha256':sha(ORIGINAL/'release/defense/qwen_backend.py'),
             'helper_sha256':sha(HERE/'complete_actor_history.py'),
             'all_image_bytes_original':True,'source_kind':'complete constructed offline fixtures; synthetic accepted transcript, no GUI execution',
             'actual_full_history_GPU_capacity_or_efficacy_established':False})
    except BaseException:
        failure=traceback.format_exc();save(root/'failure.json',{'traceback':failure,'no_retry':True,'new_model_GPU_GUI_scorer_calls':0})
    finally:
        save(root/'terminal.json',{'time':time.time(),'status':'failure'if failure else'completed','error':failure})
        save(root/'seal.json',{q.relative_to(root).as_posix():sha(q)for q in root.rglob('*')if q.is_file()})
    return 1 if failure else 0


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(main(parser.parse_args().output))
