"""Bind both complete multimodal processor inputs; no weights or generation."""
import argparse
import base64
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import time
import traceback


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf8')


def main(package,original):
    os.environ['CUDA_VISIBLE_DEVICES']=''
    original_package=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/remaining29-full-history-gui-20261110-37')
    assert sha(original_package/'manifest.json')=='368b0a594822f5e294fcd21927aa924a18a80f23249f160857b5de7090c1c02d'
    manifest=json.loads((original_package/'manifest.json').read_bytes())
    for name in ['release/defense/qwen_backend.py','release/defense/core.py','model_runtime.py','primary-reference.json','preflight_support.py']:
        assert sha(original_package/name)==manifest['files'][name]
    reference=json.loads((package/'primary-reference.json').read_bytes())
    assert reference==json.loads((original_package/'primary-reference.json').read_bytes())
    proof_path=Path(reference['primary_dependency_receipt'])
    assert sha(proof_path)==reference['primary_dependency_receipt_sha256']
    proof=json.loads(proof_path.read_bytes());deps=Path(proof['dependency_root'])
    actual={str(p.relative_to(deps)):sha(p)for p in deps.rglob('*')if p.is_file()and'__pycache__'not in p.parts and p.suffix!='.pyc'}
    assert actual==proof['dependency_files']
    sys.path[:0]=[str(deps),str(package/'proposed-release')]
    from defense.qwen_backend import LocalQwen
    from defense.core import PublicView,VisibleImage
    from candidate_units import candidate_source_units
    from source_quote_references import extraction_boundary
    from transformers import AutoProcessor
    from PIL import Image
    import torch
    assert not torch.cuda.is_initialized()
    expected_runtime=json.loads(Path(reference['primary_expected_runtime']).read_bytes())
    model_path=Path(reference['primary_model'])
    for name,expected in expected_runtime['metadata_sha256'].items():assert sha(model_path/name)==expected
    request=original/'worker/requests/0074'
    seal=json.loads((request/'seal.json').read_bytes())
    for name in ['payload.json','native-call.json','prepared.json']:
        assert sha(request/name)==seal[name]
    payload=json.loads((request/'payload.json').read_bytes())
    actual_native=json.loads((request/'native-call.json').read_bytes())
    prepared=json.loads((request/'prepared.json').read_bytes())
    v=payload['view']
    view=PublicView(v['observation_id'],v['messages'],tuple(VisibleImage(base64.b64decode(im['raw_base64'],validate=True),im['role'])for im in v['images']),v['recent_action'],v['execution_feedback'],v['observed_at'])
    spec=importlib.util.spec_from_file_location('defense.original_backend_CPU_only',original_package/'release/defense/qwen_backend.py')
    old_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(old_module)
    captured=[]
    def capture(messages,maximum,receipt,**kwargs):
        captured.append(dict(messages=messages,max_tokens=maximum,**kwargs));return '{}'
    before=old_module.LocalQwen.__new__(old_module.LocalQwen);before.generate=capture
    before.judge(payload['system'],view,payload['candidate'])
    original_messages=captured[-1]['messages']
    assert hashlib.sha256(canonical(original_messages)).hexdigest()==actual_native['request_messages_sha256']
    assert captured[-1]['json_schema']==actual_native['verifier_grammar']['schema']
    after=LocalQwen.__new__(LocalQwen);after.generate=capture
    addition=extraction_boundary(candidate_source_units(payload['candidate']))
    after.judge(payload['system']+addition,view,payload['candidate'])
    proposed_messages=captured[-1]['messages']
    assert len(original_messages)==len(proposed_messages)==2
    assert original_messages[1:]==proposed_messages[1:]
    assert proposed_messages[0]==dict(role='system',content=original_messages[0]['content']+addition)
    assert captured[-1]['max_tokens']==4096
    processor=AutoProcessor.from_pretrained(model_path,local_files_only=True,trust_remote_code=True)
    outputs=[]
    def tensor_record(value):
        raw=value.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()
        return dict(shape=list(value.shape),dtype=str(value.dtype),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    for label,messages in [('original',original_messages),('proposed',proposed_messages)]:
        converted=[];opened=[]
        try:
            # Exact conversion used by the unchanged native generate() function.
            for message in messages:
                parts=message['content']if isinstance(message['content'],list)else[dict(type='text',text=message['content'])]
                blocks=[]
                for block in parts:
                    if block['type']=='text':blocks.append(copy.deepcopy(block))
                    elif block['type']=='image_url':
                        url=block['image_url'];url=url['url']if isinstance(url,dict)else url
                        image=Image.open(io.BytesIO(base64.b64decode(url.split(',',1)[1]))).convert('RGB')
                        opened.append(image);blocks.append(dict(type='image',image=image))
                    else:raise AssertionError('Unbound native block')
                converted.append(dict(role=message['role'],content=blocks))
            inputs=processor.apply_chat_template(converted,add_generation_prompt=True,tokenize=True,return_dict=True,return_tensors='pt',tools=None,enable_thinking=False)
            records={name:tensor_record(value)for name,value in inputs.items()}
            if label=='original':
                assert inputs['input_ids'][0].tolist()==actual_native['input_ids']
                assert set(records)==set(prepared)
                for name,row in records.items():
                    for key in ['shape','dtype','bytes','sha256']:assert row[key]==prepared[name][key],(name,key)
            outputs.append((label,inputs,records))
        finally:
            for image in opened:image.close()
    old_inputs,new_inputs=outputs[0][1],outputs[1][1]
    assert set(old_inputs)==set(new_inputs)
    for name in ['pixel_values','image_grid_thw']:
        assert name in old_inputs and torch.equal(old_inputs[name],new_inputs[name]),name
    if 'mm_token_type_ids'in old_inputs:
        assert torch.equal(old_inputs['input_ids'][old_inputs['mm_token_type_ids']==1],new_inputs['input_ids'][new_inputs['mm_token_type_ids']==1])
    old_count=int(old_inputs['input_ids'].shape[-1]);new_count=int(new_inputs['input_ids'].shape[-1])
    assert new_count>old_count
    assert not torch.cuda.is_initialized()
    with(package/'proposed-complete-messages-UNSENT.json').open('x')as stream:json.dump(proposed_messages,stream,ensure_ascii=False)
    return dict(time=time.time(),passed=True,original_complete_forward_input_reproduced=True,
        unchanged_user_public_messages_candidate_all_original_image_blocks=True,
        original_messages_sha256=hashlib.sha256(canonical(original_messages)).hexdigest(),
        proposed_messages_sha256=hashlib.sha256(canonical(proposed_messages)).hexdigest(),
        original_system_sha256=hashlib.sha256(payload['system'].encode('utf8')).hexdigest(),
        source_table_addition_sha256=hashlib.sha256(addition.encode('utf8')).hexdigest(),
        complete_image_count=len(view.images),public_history_message_count=len(view.messages),
        unchanged_complete_image_info=[im.info()for im in view.images],
        original_inputs=outputs[0][2],proposed_inputs=outputs[1][2],
        original_complete_input_tokens=old_count,proposed_complete_input_tokens=new_count,input_token_delta=new_count-old_count,
        identical_actual_pixel_values_and_image_grids=True,identical_ordered_image_token_IDs=True,
        complete_messages_prepared_UNSENT=True,no_weights_loaded_or_CUDA=True,
        CPU_input_identity_only_not_GPU_fit_semantics_or_future_context_capacity=True,
        new_model_GUI_capture_action_scorer_paid_calls=0)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--package',type=Path,required=True);parser.add_argument('--original',type=Path,required=True)
    args=parser.parse_args();root=args.package.resolve()
    try:
        value=main(root,args.original.resolve())
        with(root/'receipt.json').open('x')as stream:json.dump(value,stream,ensure_ascii=False,indent=2)
        print(json.dumps(dict(passed=True,original_tokens=value['original_complete_input_tokens'],proposed_tokens=value['proposed_complete_input_tokens'],images=value['complete_image_count'])))
    except BaseException as error:
        with(root/'failure.json').open('x')as stream:json.dump(dict(time=time.time(),type=type(error).__name__,message=str(error),traceback=traceback.format_exc(),new_model_GUI_scorer_calls=0),stream)
        traceback.print_exc();sys.exit(1)
