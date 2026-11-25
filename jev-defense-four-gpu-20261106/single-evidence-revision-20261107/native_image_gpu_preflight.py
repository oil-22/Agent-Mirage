"""New finite GPU7 image-only development, never an old service/GUI launcher.

Requires a frozen native CPU proof, source-first labels, full current weight
identity and the actual inherited four-card lease. No task/history/candidate or
label content is supplied to the model. This runner does not retry outputs.
"""
import argparse
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

BASE_REPO='Qwen/Qwen3.5-9B'
BASE_REVISION='c202236235762e1c871ad0ccb60c8ee5ba337b9a'
JEV_REVISION='7ac669b8fb476ba926491e3d1c39f9330d68dbed'
MODEL_PATH='/home/researcher/models/Qwen3.5-9B'
MODEL_CLASS='Qwen3_5ForConditionalGeneration'
EOS=[248044,248046]
OUTPUT_CAP=2048

def canonical(v):
    return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')

def digest(raw): return hashlib.sha256(raw).hexdigest()

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        while True:
            block=stream.read(16*1024*1024)
            if not block: break
            h.update(block)
    return h.hexdigest()

def write_raw(path,raw):
    with Path(path).open('xb')as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())

def write(path,value): write_raw(path,canonical(value)+b'\n')

def read(path): return json.loads(Path(path).read_bytes())

def stop_boundary(root):
    if(Path(root).parent/'stop-requested.json').exists():
        raise RuntimeError('Requested stop marker observed at a boundary; no further inference')

def load_module(name,path,expected_sha):
    if sha(path)!=expected_sha: raise ValueError('Pinned module changed: '+str(path))
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def exact_identity(pid=None):
    pid=os.getpid()if pid is None else int(pid)
    root=Path('/proc')/str(pid);stat=(root/'stat').read_text().rsplit(')',1)[1].split()
    return {'pid':pid,'ppid':int(stat[1]),'uid':root.stat().st_uid,
        'command':(root/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),
        'start_ticks':stat[19]}

class Journal:
    def __init__(self,root): self.root=root;self.seq=0;self.head='0'*64
    def append(self,kind,value):
        event={'seq':self.seq,'previous':self.head,'time_ns':time.time_ns(),'kind':kind,'data':value}
        event['sha256']=digest(canonical(event))
        with(self.root/'journal.jsonl').open('ab')as stream:
            stream.write(canonical(event)+b'\n');stream.flush();os.fsync(stream.fileno())
        self.head=event['sha256'];self.seq+=1

def verify_seal(root,expected):
    path=Path(root)/'seal.json'
    if sha(path)!=expected: raise ValueError('Frozen seal changed: '+str(path))
    seal=read(path)
    rows=seal['files']if isinstance(seal,dict)and isinstance(seal.get('files'),list)else [
        {'path':name,'sha256':value}for name,value in seal.items()]
    for row in rows:
        if sha(Path(root)/row['path'])!=row['sha256']: raise ValueError('Sealed artifact changed: '+row['path'])

def tensor_record(tensor,torch,root,name,origin):
    stable=tensor.detach().to('cpu').contiguous()
    raw=stable.view(torch.uint8).numpy().tobytes(order='C')
    write_raw(root/(name+'.tensor'),raw)
    if name in {'input_ids','image_grid_thw','generated_ids','sequence_ids'}:
        write(root/(name+'.json'),stable.tolist())
    return {'shape':list(stable.shape),'dtype':str(stable.dtype),'bytes':len(raw),
        'sha256':digest(raw),'origin':origin,'file':name+'.tensor'}

def validate_manifest(m):
    required={'schema_version','attempt_id','output_root','gpu_authorized','cpu_proof',
        'source_labels','input_package','base_model','jev_relationship','lease_path',
        'expected_holder','resource_gate','evidence_contract','prior_weight_identity','official_base_api',
        'metadata_files','weight_files','requests','generation','limits'}
    if not isinstance(m,dict)or set(m)!=required: raise ValueError('Manifest field mismatch')
    if m['schema_version']!='single-image-GPU-preflight-v1'or m['gpu_authorized']is not True:
        raise ValueError('Only a new explicitly frozen development preflight is admitted')
    if m['base_model']!={'repo':BASE_REPO,'revision':BASE_REVISION,'local_path':MODEL_PATH}:
        raise ValueError('Actual shared base identity mismatch')
    if m['jev_relationship']!={'repo':'autotrust/JEV-9B','revision':JEV_REVISION,
        'stage':'S2-shared-original-base','decision_adapter_loaded':False}:
        raise ValueError('S2 lineage mismatch; decision-head OCR cannot be claimed')
    if m['generation']!={'max_new_tokens':OUTPUT_CAP,'do_sample':False,'temperature':1.0,
        'top_p':1.0,'top_k':0,'num_beams':1,'num_return_sequences':1,'eos_token_id':EOS,
        'enable_thinking':False,'seed':0,'dtype':'bfloat16','attention_backend':'sdpa'}:
        raise ValueError('New auxiliary generation condition changed')
    if m['limits']!={'requests':4,'automatic_format_retries':0,'semantic_resampling':False,
        'primary_model_calls':0,'GUI_actions':0,'scorer':0,'paid_API':0}:
        raise ValueError('Only the four frozen first attempts are implemented')
    rows=m['requests']
    if not isinstance(rows,list)or len(rows)!=4 or [x['request_id']for x in rows]!=['S01','S07','S13','S25']:
        raise ValueError('Exact ordered four-image source list required')
    if len({row['image_sha256']for row in rows})!=4: raise ValueError('Source images must be distinct')

def current_weight_identity(m,root,journal):
    prior=m['prior_weight_identity']
    if sha(prior['path'])!=prior['sha256']: raise ValueError('Old identity receipt changed')
    old=read(prior['path'])['files'];model=Path(MODEL_PATH)
    official=m['official_base_api']
    if sha(official['path'])!=official['sha256']: raise ValueError('Pinned official base metadata changed')
    api=read(official['path'])
    if api.get('id')!=BASE_REPO or api.get('sha')!=BASE_REVISION:
        raise ValueError('Official API identity differs from the frozen base revision')
    native={item['rfilename']:item for item in api['siblings']if item['rfilename'].endswith('.safetensors')}
    metadata=[]
    for row in m['metadata_files']:
        path=model/row['filename'];before=path.stat();raw=path.read_bytes();after=path.stat()
        if (row['bytes']!=len(raw)or row['sha256']!=digest(raw)or
            before.st_mtime_ns!=after.st_mtime_ns or before.st_size!=after.st_size):
            raise ValueError('Current native metadata mismatch: '+row['filename'])
        write_raw(root/('metadata--'+row['filename']),raw);metadata.append(row)
    index=read(model/'model.safetensors.index.json')
    if set(index['weight_map'].values())!={r['filename']for r in m['weight_files']}:
        raise ValueError('Complete native shard inventory required')
    if set(native)!=set(index['weight_map'].values()): raise ValueError('Official complete shard inventory differs')
    allowed_files={r['filename']for r in m['metadata_files']}|set(native)|{'README.md'}
    if {p.name for p in model.iterdir()if p.is_file()}!=allowed_files:
        raise ValueError('Native model file set changed after CPU admission, including any extra generation/adapter defaults')
    verified=[]
    for row in m['weight_files']:
        stop_boundary(root)
        name=row['filename'];record=old['Qwen3.5-9B/'+name]
        if record['bytes']!=row['bytes']or record['sha256']!=row['sha256']:
            raise ValueError('New shard identity differs from prior full-hash receipt')
        if native[name]['lfs']['sha256']!=row['sha256']or native[name]['lfs']['size']!=row['bytes']:
            raise ValueError('Shard identity differs from the pinned official LFS identity')
        path=model/name;before=path.stat();actual=sha(path);after=path.stat()
        if(before.st_size!=after.st_size or before.st_mtime_ns!=after.st_mtime_ns or
           before.st_ino!=after.st_ino or actual!=row['sha256']or before.st_size!=row['bytes']):
            raise ValueError('Current full shard identity mismatch: '+name)
        result=dict(row,current_sha256=actual,mtime_ns=after.st_mtime_ns,inode=after.st_ino)
        verified.append(result);journal.append('current_shard_identity',result)
    result={'scope':'new load admission: prior receipt had no historical stat continuity',
        'complete_current_shards':verified,'metadata':metadata,'GPU_tensors_yet_verified':False,
        'official_pinned_base_api_sha256':official['sha256'],
        'official_LFS_current_shard_identity_verified':True,'not_old_attention_workflow_relaunch':True}
    write(root/'current-weight-identity.json',result)
    return verified

def run(m,root,journal,completed,attempted):
    if os.getuid()!=1033 or os.environ.get('CUDA_VISIBLE_DEVICES')!='7':
        raise ValueError('Only owned UID1033 physical GPU7 worker is admitted')
    if os.environ.get('HF_HUB_OFFLINE')!='1'or os.environ.get('TRANSFORMERS_OFFLINE')!='1':
        raise ValueError('Offline local model assets required')
    gate=load_module('new_resource_gate',m['resource_gate']['path'],m['resource_gate']['sha256'])
    parent=json.loads(os.environ['MIRAGE_JEV_LAUNCHER_IDENTITY'])
    actual_parent=exact_identity(os.getppid())
    if any(str(parent.get(k))!=str(actual_parent[k])for k in ['pid','uid','command','start_ticks']):
        raise ValueError('Actual parent launcher differs from the registered identity')
    def resources(empty=False):
        result=gate.assert_owned_resources(m['lease_path'],m['expected_holder'],
            allow_pids={os.getpid():exact_identity(),os.getppid():actual_parent},
            require_empty=empty,minimum_free_mib=23000)
        journal.append('actual_resource_check',result)
        return result
    stop_boundary(root);resources(True)
    contract=load_module('frozen_evidence_contract',m['evidence_contract']['path'],m['evidence_contract']['sha256'])
    verify_seal(m['cpu_proof']['root'],m['cpu_proof']['seal_sha256'])
    cpu_terminal=read(Path(m['cpu_proof']['root'])/'terminal.json')
    if cpu_terminal['status']!='completed_native_CPU_admission_no_model'or cpu_terminal['admitted_requests']!=4:
        raise ValueError('All four native CPU inputs must already be admitted')
    verify_seal(m['source_labels']['root'],m['source_labels']['seal_sha256'])
    if sha(m['input_package']['path'])!=m['input_package']['sha256']:
        raise ValueError('Frozen four-image input protocol changed')
    shards=current_weight_identity(m,root,journal)
    stop_boundary(root);resources(True)
    import torch
    import transformers
    from transformers import AutoProcessor,Qwen3_5ForConditionalGeneration
    from PIL import Image
    torch.manual_seed(0)
    processor=AutoProcessor.from_pretrained(MODEL_PATH,local_files_only=True,trust_remote_code=False)
    if [processor.tokenizer.convert_tokens_to_ids(t)for t in ['<|endoftext|>','<|im_end|>']]!=EOS:
        raise ValueError('Native tokenizer stop-token mapping changed')
    started=time.perf_counter()
    model=Qwen3_5ForConditionalGeneration.from_pretrained(MODEL_PATH,local_files_only=True,
        trust_remote_code=False,dtype=torch.bfloat16,attn_implementation='sdpa',device_map={'':0}).eval()
    torch.cuda.synchronize()
    load_seconds=time.perf_counter()-started
    resources()
    inventory=[]
    for kind,values in [('parameter',model.named_parameters()),('buffer',model.named_buffers())]:
        for name,value in values:
            if value.device.type!='cuda'or value.device.index!=0: raise ValueError('A model tensor escaped physical GPU7')
            if kind=='parameter'and value.is_floating_point()and value.dtype!=torch.bfloat16:
                raise ValueError('Model parameter BF16 precision changed')
            inventory.append({'kind':kind,'name':name,'shape':list(value.shape),'dtype':str(value.dtype),
                'device':str(value.device),'bytes':value.numel()*value.element_size()})
    if not inventory: raise ValueError('Empty actual CUDA tensor inventory')
    for row in shards:
        stat=(Path(MODEL_PATH)/row['filename']).stat()
        if stat.st_size!=row['bytes']or stat.st_mtime_ns!=row['mtime_ns']or stat.st_ino!=row['inode']:
            raise ValueError('Verified weight file changed during native load')
    runtime_sources={}
    for name,object_type in [('model',type(model)),('processor',type(processor)),('generation',type(model.generation_config))]:
        module=sys.modules[object_type.__module__];path=Path(module.__file__)
        runtime_sources[name]={'module':object_type.__module__,'path':str(path),'sha256':sha(path)}
        write_raw(root/('runtime-source--'+name+'.py'),path.read_bytes())
    write(root/'loaded.json',{'identity':exact_identity(),'torch':torch.__version__,
        'transformers':transformers.__version__,'model_class':type(model).__name__,
        'base_model':m['base_model'],'jev_relationship':m['jev_relationship'],
        'actual_cuda_tensors':inventory,'load_seconds':load_seconds,'runtime_sources':runtime_sources,
        'actual_config':model.config.to_dict(),'native_generation_defaults':model.generation_config.to_dict(),
        'actual_attention_backends':{'model':getattr(model.config,'_attn_implementation',None),
            'text':getattr(model.config.text_config,'_attn_implementation',None),
            'vision':getattr(model.config.vision_config,'_attn_implementation',None)},
        'runtime_change_from_official_vLLM':True,'vLLM_bitwise_equivalence_claimed':False})
    journal.append('one_auxiliary_loaded',{'load_seconds':load_seconds,'actual_cuda_tensors':len(inventory)})
    generation=copy.deepcopy(model.generation_config)
    for name in ['max_new_tokens','do_sample','temperature','top_p','top_k','num_beams','num_return_sequences','eos_token_id']:
        setattr(generation,name,m['generation'][name])
    generation.validate()
    write(root/'effective-generation.json',{'config':generation.to_dict(),
        'explicit_EOS_override_from_config_only_default':True,'new_auxiliary_condition':True,
        'actor_2048_judge_4096_unchanged':True})
    for i,row in enumerate(m['requests']):
        stop_boundary(root);resources()
        request_root=root/('r%03d'%i);request_root.mkdir()
        request_raw=Path(row['path']).read_bytes();write_raw(request_root/'request.original.json',request_raw)
        if digest(request_raw)!=row['sha256']: raise ValueError('Frozen input request changed')
        request=json.loads(request_raw);image_raw=contract.validate_image_only_request(request)
        if(request['model']!=BASE_REPO or request['revision']!=BASE_REVISION or
           digest(image_raw)!=row['image_sha256']): raise ValueError('Received image/model binding changed')
        write_raw(request_root/'received-original.image',image_raw)
        with Image.open(io.BytesIO(image_raw))as image:
            image.load();rgb=image.convert('RGB')
        messages=[{'role':'user','content':[{'type':'image','image':rgb},
            {'type':'text','text':contract.FIXED_PROMPT}]}]
        inputs=processor.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,
            enable_thinking=False,tools=None,return_dict=True,return_tensors='pt')
        cpu=read(Path(m['cpu_proof']['root'])/('r%03d'%i)/'admission.json')
        if cpu['request_id']!=row['request_id']or cpu['image_sha256']!=row['image_sha256']:
            raise ValueError('Native CPU proof source order changed')
        prepared={}
        for name,value in inputs.items():
            if not isinstance(value,torch.Tensor): raise ValueError('Unfrozen non-tensor native input')
            record=tensor_record(value,torch,request_root,'prepared_'+name,'regenerated_native_processor')
            expected=cpu['tensor_artifacts'][name]
            if any(record[k]!=expected[k]for k in ['shape','dtype','bytes','sha256']):
                raise ValueError('Full native GPU-stage input differs from CPU proof: '+name)
            prepared[name]=record
        if set(prepared)!=set(cpu['tensor_artifacts']): raise ValueError('Native input key set changed')
        inputs={name:value.to('cuda:0')for name,value in inputs.items()}
        forward={'count':0,'first':None}
        def hook(module,args,kwargs):
            if forward['count']==0:
                actual={}
                for name in prepared:
                    value=kwargs.get(name)
                    if not isinstance(value,torch.Tensor): raise ValueError('Actual first forward omitted frozen input: '+name)
                    record=tensor_record(value,torch,request_root,'actual_forward_'+name,'actual_model_forward_pre_hook')
                    if any(record[k]!=prepared[name][k]for k in ['shape','dtype','bytes','sha256']):
                        raise ValueError('Actual forward input mismatch: '+name)
                    actual[name]=record
                forward['first']=actual
                write(request_root/'actual-first-forward.json',actual)
            cached_ids=kwargs.get('input_ids')
            trace={'forward_index':forward['count'],
                'input_ids':cached_ids.detach().cpu().tolist()if isinstance(cached_ids,torch.Tensor)else None,
                'input_shapes':{name:list(value.shape)for name,value in kwargs.items()if isinstance(value,torch.Tensor)}}
            with(request_root/'actual-forward-calls.jsonl').open('ab')as stream:
                stream.write(canonical(trace)+b'\n');stream.flush()
            forward['count']+=1
        handle=model.register_forward_pre_hook(hook,with_kwargs=True)
        journal.append('inference_request',{'request_id':row['request_id'],'request_sha256':row['sha256'],
            'image_sha256':row['image_sha256'],'input_tokens':int(inputs['input_ids'].shape[-1]),
            'natural_EOS_required':True,'semantic_labels_supplied':False})
        attempted.append(row['request_id'])
        torch.cuda.reset_peak_memory_stats();started=time.perf_counter()
        try:
            with torch.inference_mode():
                output=model.generate(**inputs,generation_config=generation,return_dict_in_generate=True,output_scores=False)
            torch.cuda.synchronize();elapsed=time.perf_counter()-started
        except BaseException as e:
            failed={'request_id':row['request_id'],'request_sha256':row['sha256'],
                'image_sha256':row['image_sha256'],'error_type':type(e).__name__,'error':str(e),
                'generation_seconds_until_failure':time.perf_counter()-started,
                'actual_forward_calls':forward['count'],'complete_output_or_EOS':None,
                'partial_forward_trace_preserved':(request_root/'actual-forward-calls.jsonl').exists(),
                'no_automatic_retry':True}
            write(request_root/'inference-failure.json',failed);journal.append('inference_failure',failed)
            raise
        finally:
            handle.remove()
        sequence=output.sequences
        length=int(inputs['input_ids'].shape[-1])
        if sequence.shape[0]!=1 or not torch.equal(sequence[:,:length],inputs['input_ids']):
            raise ValueError('Native generation sequence prefix changed or hidden batch appeared')
        generated=sequence[:,length:]
        ids=generated[0].tolist();natural_eos=bool(ids and ids[-1]in EOS)
        tensor_record(sequence,torch,request_root,'sequence_ids','actual_native_generate')
        tensor_record(generated,torch,request_root,'generated_ids','actual_native_generate')
        raw_output=processor.tokenizer.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False)
        write_raw(request_root/'raw-output.txt',raw_output.encode('utf-8'))
        write_raw(request_root/'output-with-special-tokens.txt',processor.tokenizer.decode(ids,
            skip_special_tokens=False,clean_up_tokenization_spaces=False).encode('utf-8'))
        packet=None;error=None
        try: packet=contract.actor_packet(request,raw_output,natural_eos)
        except Exception as e: error={'type':type(e).__name__,'message':str(e)}
        if packet is not None: write(request_root/'evidence-packet.json',packet)
        if error: write(request_root/'contract-failure.json',error)
        result={'request_id':row['request_id'],'input_tokens':length,'output_tokens':len(ids),
            'image_sha256':row['image_sha256'],'request_sha256':row['sha256'],
            'natural_eos':natural_eos,'last_token_id':ids[-1]if ids else None,
            'generation_seconds':elapsed,'actual_forward_calls':forward['count'],
            'actual_first_forward_observed':forward['first']is not None,
            'raw_output_sha256':digest(raw_output.encode('utf-8')),
            'peak_allocated_bytes':torch.cuda.max_memory_allocated(),
            'peak_reserved_bytes':torch.cuda.max_memory_reserved(),
            'contract_valid':packet is not None,'contract_error':error,
            'semantic_quality_reviewed':False,'automatic_allow_or_block':False,
            'retry_performed':False,'GUI_actions':0}
        write(request_root/'result.json',result);journal.append('inference_terminal',result);completed.append(result)
        resources()
    return {'load_seconds':load_seconds,'actual_cuda_tensors':len(inventory)}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',required=True);p.add_argument('--manifest-sha256',required=True)
    p.add_argument('--output',required=True);a=p.parse_args()
    root=Path(a.output)
    if not root.is_absolute(): raise ValueError('Absolute new attempt output is required')
    root.mkdir(exist_ok=False)
    raw=Path(a.manifest).read_bytes();write_raw(root/'input-manifest.original.json',raw)
    journal=Journal(root);completed=[];attempted=[];status='failed';error=None;runtime=None
    write(root/'claim.json',{'identity':exact_identity(),'manifest_sha256':digest(raw),
        'worker_sha256':sha(__file__),'old_terminal_or_queue_relaunch':False})
    try:
        if digest(raw)!=a.manifest_sha256: raise ValueError('Submitted manifest SHA mismatch')
        m=json.loads(raw);validate_manifest(m)
        if str(root)!=m['output_root']: raise ValueError('Once-only output differs from manifest')
        runtime=run(m,root,journal,completed,attempted);status='completed_four_first_attempts'
    except BaseException as e:
        error={'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc(),
            'resource_evidence':getattr(e,'resource_evidence',None)}
        write(root/'failure.json',error);journal.append('failure_preserved',error)
    terminal={'status':status,'attempted_requests':len(attempted),'attempted_request_ids':attempted,
        'completed_requests':len(completed),'results':completed,
        'failed_incomplete_requests':len(attempted)-len(completed),
        'unattempted':4-len(attempted),'runtime':runtime,'error':error,
        'primary_actor_judge_calls':0,'GUI_actions':0,'scorer':0,'paid_API':0,
        'four_card_joint_capacity_proven':False,'Mirage_reduction_established':False,
        'no_automatic_retry':True,'lease_reservation_still_owned_by_holder':True}
    write(root/'terminal.json',terminal);journal.append('terminal',terminal)
    write(root/'seal.json',{'files':[{'path':str(f.relative_to(root)),'bytes':f.stat().st_size,
        'sha256':sha(f)}for f in sorted(root.rglob('*'))if f.is_file()],
        'journal_events':journal.seq,'journal_head':journal.head})
    print(json.dumps({'status':status,'completed':len(completed),'output':str(root)}),flush=True)
    return 0 if error is None else 1

if __name__=='__main__': raise SystemExit(main())
