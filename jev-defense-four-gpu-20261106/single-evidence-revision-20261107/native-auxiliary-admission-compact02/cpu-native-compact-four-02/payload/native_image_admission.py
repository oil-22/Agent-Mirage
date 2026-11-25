"""STAGED native CPU admission only. No model loading, CUDA or GUI implementation.

This file has not been run. Its only executable mode prepares processor inputs on CPU;
it does not perform CPU inference or change the user's GPU deployment choice.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import socket
import sys
import time
import traceback

VERSION='native-image-admission-compact-20261107-02'
BASE_REPO='Qwen/Qwen3.5-9B'
BASE_REVISION='c202236235762e1c871ad0ccb60c8ee5ba337b9a'
JEV_REPO='autotrust/JEV-9B'
JEV_REVISION='7ac669b8fb476ba926491e3d1c39f9330d68dbed'
MODEL_PATH='/home/researcher/models/Qwen3.5-9B'
MODEL_CLASS='Qwen3_5ForConditionalGeneration'
CONTRACT_SHA256='081caa2595440dd1f813efaa4f960a78cd095b8448353d65a11f464593140676'
MAX_NEW_TOKENS=2048
REQUIRED_METADATA={'config.json','model.safetensors.index.json',
    'preprocessor_config.json','tokenizer_config.json','chat_template.jinja','tokenizer.json'}
OPTIONAL_NATIVE_METADATA={'processor_config.json','video_preprocessor_config.json',
    'special_tokens_map.json','added_tokens.json','vocab.json','merges.txt',
    'tokenizer.model','spiece.model','sentencepiece.bpe.model'}
FORBIDDEN_WEIGHT_SUFFIXES={'.safetensors','.bin','.pt','.pth','.ckpt','.gguf'}


class AdmissionError(ValueError):pass


def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf8')


def digest(raw):return hashlib.sha256(raw).hexdigest()


def strict_json(raw):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise AdmissionError('Duplicate JSON key')
            result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=unique,
        parse_constant=lambda _:(_ for _ in ()).throw(AdmissionError('Non-finite JSON')))


def exact_keys(value,keys,where):
    if not isinstance(value,dict)or set(value)!=set(keys):
        raise AdmissionError('Unknown or missing fields: '+where)


def write_bytes_once(path,raw):
    with path.open('xb')as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())


def write_json_once(path,value):write_bytes_once(path,canonical(value)+b'\n')


def process_identity():
    status=Path('/proc/self/status');cmdline=Path('/proc/self/cmdline')
    return {'pid':os.getpid(),'ppid':os.getppid(),
        'uid':os.getuid()if hasattr(os,'getuid')else None,
        'gid':os.getgid()if hasattr(os,'getgid')else None,
        'host':socket.gethostname(),'executable':sys.executable,'python':sys.version,
        'argv':sys.argv,'cwd':os.getcwd(),
        'proc_status':status.read_text()if status.is_file()else None,
        'proc_cmdline_base64':base64.b64encode(cmdline.read_bytes()).decode('ascii')if cmdline.is_file()else None,
        'selected_environment':{key:os.environ.get(key)for key in
            ['CUDA_VISIBLE_DEVICES','HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE']}}


class Journal:
    def __init__(self,root):self.root=root;self.seq=0;self.previous='0'*64
    def append(self,kind,data):
        event={'seq':self.seq,'previous':self.previous,'time_ns':time.time_ns(),'kind':kind,'data':data}
        event['sha256']=digest(canonical(event))
        with(self.root/'journal.jsonl').open('ab')as stream:
            stream.write(canonical(event)+b'\n');stream.flush();os.fsync(stream.fileno())
        self.previous=event['sha256'];self.seq+=1


def validate_manifest(value):
    exact_keys(value,{'schema_version','attempt_id','mode','output_root','cpu_admission_authorized',
        'gpu_inference_authorized','base_model','jev_relationship','evidence_contract',
        'metadata_files','prior_weight_identity','weight_file_stats','requests','expected_request_count',
        'native_input_policy','future_aux_generation'},'input manifest')
    if(value['schema_version']!='native-image-admission-v1'or value['mode']!='cpu_admission_only'
       or value['cpu_admission_authorized']is not True or value['gpu_inference_authorized']is not False):
        raise AdmissionError('Only explicitly frozen native CPU admission is implemented')
    if not isinstance(value['attempt_id'],str)or not value['attempt_id']or any(x in value['attempt_id']for x in '/\\'):
        raise AdmissionError('A unique simple attempt ID is required')
    if value['base_model']!={'repo':BASE_REPO,'revision':BASE_REVISION,'local_path':MODEL_PATH}:
        raise AdmissionError('Fixed native base model/revision/path mismatch')
    if value['jev_relationship']!={'repo':JEV_REPO,'revision':JEV_REVISION,
        'stage':'S2-shared-original-base','decision_adapter_loaded':False}:
        raise AdmissionError('JEV S2 lineage must be explicit; no decision adapter can be represented as loaded')
    exact_keys(value['evidence_contract'],{'source_path','sha256'},'evidence contract')
    if value['evidence_contract']['sha256']!=CONTRACT_SHA256:
        raise AdmissionError('Evidence contract revision is not the frozen CPU-audited source')
    exact_keys(value['prior_weight_identity'],{'receipt_path','receipt_sha256'},'prior identity link')
    if value['native_input_policy']!={'enable_thinking':False,'truncate':False,
        'image_count':1,'processor_overrides':{},'task_history_candidate_supplied':False}:
        raise AdmissionError('Native fixed single-image input contract mismatch')
    if value['future_aux_generation']!={'max_new_tokens':2048,'do_sample':False,
        'temperature':1.0,'top_p':1.0,'top_k':0,'dtype':'bfloat16','attention_backend':'sdpa',
        'model_class':MODEL_CLASS,'eos_stop_rule_status':'UNDECIDED_before_GPU_inference',
        'inference_performed_in_this_mode':False}:
        raise AdmissionError('Auxiliary greedy2048 plan mismatch; no actor or judge budget is edited')
    requests=value['requests']
    if not isinstance(requests,list)or not requests or type(value['expected_request_count'])is not int or len(requests)!=value['expected_request_count']:
        raise AdmissionError('Exact ordered nonempty CPU request list required')
    seen=set()
    for row in requests:
        exact_keys(row,{'request_id','path','sha256'},'request binding')
        rid=row['request_id']
        if not isinstance(rid,str)or not rid or rid in seen or any(char not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-'for char in rid):
            raise AdmissionError('Unique filesystem-safe request ID required')
        seen.add(rid)
    metadata=value['metadata_files']
    if not isinstance(metadata,list)or not metadata:raise AdmissionError('Pinned native metadata missing')
    names=[]
    for row in metadata:
        exact_keys(row,{'filename','bytes','sha256'},'metadata binding')
        name=row['filename']
        if not isinstance(name,str)or Path(name).name!=name or name not in REQUIRED_METADATA|OPTIONAL_NATIVE_METADATA:
            raise AdmissionError('Only explicit local small metadata files may be hashed')
        if type(row['bytes'])is not int or not 0<row['bytes']<=40000000:
            raise AdmissionError('Unexpected metadata size')
        names.append(name)
    if len(names)!=len(set(names))or not REQUIRED_METADATA<=set(names):
        raise AdmissionError('Incomplete or duplicated native processor metadata inventory')
    if not isinstance(value['weight_file_stats'],list)or not value['weight_file_stats']:
        raise AdmissionError('Prior identity-bound weight stat inventory required')
    for row in value['weight_file_stats']:
        exact_keys(row,{'filename','bytes','mtime_ns'},'weight stat binding')
        if not isinstance(row['filename'],str)or Path(row['filename']).name!=row['filename']or not row['filename'].endswith('.safetensors'):
            raise AdmissionError('Only native local shard stat names are allowed')
        if type(row['bytes'])is not int or row['bytes']<=0 or type(row['mtime_ns'])is not int:
            raise AdmissionError('Explicit positive shard size and exact stat time required')
    return value


def metadata_gate(manifest,root,journal):
    model=Path(MODEL_PATH)
    if(model/'generation_config.json').exists():
        raise AdmissionError('Official fixed revision has no generation_config.json; an extra local file needs independent review')
    present={name for name in REQUIRED_METADATA|OPTIONAL_NATIVE_METADATA if(model/name).is_file()}
    if present!=set(row['filename']for row in manifest['metadata_files']):
        raise AdmissionError('Every present native processor metadata file must be identity-bound; no unbound optional defaults')
    rows=[]
    for row in manifest['metadata_files']:
        path=model/row['filename'];before=path.stat();raw=path.read_bytes();after=path.stat()
        if(before.st_size!=after.st_size or before.st_mtime_ns!=after.st_mtime_ns
           or len(raw)!=row['bytes']or digest(raw)!=row['sha256']):
            raise AdmissionError('Native metadata changed or identity mismatch: '+row['filename'])
        write_bytes_once(root/('metadata--'+row['filename']),raw)
        rows.append({'filename':row['filename'],'bytes':len(raw),'sha256':digest(raw)})
    config=strict_json((model/'config.json').read_bytes())
    if config.get('architectures')!=[MODEL_CLASS]or config.get('model_type')!='qwen3_5':
        raise AdmissionError('Only native Qwen3_5ForConditionalGeneration metadata accepted')
    if config.get('text_config',{}).get('num_hidden_layers')!=32 or config['text_config'].get('num_attention_heads')!=16:
        raise AdmissionError('Unexpected native9B architecture')
    prior=manifest['prior_weight_identity'];raw=Path(prior['receipt_path']).read_bytes()
    if digest(raw)!=prior['receipt_sha256']:raise AdmissionError('Prior full-weight identity receipt link changed')
    write_bytes_once(root/'prior-weight-identity.original.json',raw)
    index=strict_json((model/'model.safetensors.index.json').read_bytes())
    shards=set(index['weight_map'].values());bound=manifest['weight_file_stats']
    if shards!=set(row['filename']for row in bound)or len(shards)!=len(bound):
        raise AdmissionError('Shard stat inventory does not match native index')
    for row in bound:
        stat=(model/row['filename']).stat()
        if stat.st_size!=row['bytes']or stat.st_mtime_ns!=row['mtime_ns']:
            raise AdmissionError('Current shard stat changed since the NEW frozen manifest')
    record={'metadata':rows,'weight_stats':bound,'prior_receipt_sha256':prior['receipt_sha256'],
        'weight_bytes_opened_or_rehashed':False,'current_GPU_tensors_verified':False,
        'old_fullhash_receipt_link_plus_stat_matching_NEW_manifest_only':True,
        'stat_continuity_since_old_fullhash_established':False}
    write_json_once(root/'metadata-gate.json',record);journal.append('metadata_gate_passed',record)
    return config


def contract_from_pinned_source(path):
    source=Path(path);raw=source.read_bytes()
    if digest(raw)!=CONTRACT_SHA256:raise AdmissionError('Pinned evidence contract source SHA mismatch')
    spec=importlib.util.spec_from_file_location('frozen_image_evidence_contract',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def save_tensor(root,name,tensor,torch):
    if tensor.device.type!='cpu':raise AdmissionError('CPU admission received a non-CPU tensor')
    stable=tensor.detach().contiguous()
    raw=stable.view(torch.uint8).numpy().tobytes(order='C')
    write_bytes_once(root/(name+'.tensor'),raw)
    record={'shape':list(stable.shape),'dtype':str(stable.dtype),'device':str(stable.device),
        'numel':stable.numel(),'bytes':len(raw),'sha256':digest(raw),
        'byteorder':sys.byteorder,'layout':'contiguous_native_dtype','file':name+'.tensor',
        'origin':'native_AutoProcessor_CPU_preparation_not_model_forward'}
    if name in {'input_ids','attention_mask','image_grid_thw','mm_token_type_ids'}:
        write_json_once(root/(name+'.json'),stable.tolist())
    return record


def bound_request(binding,request_root,contract):
    request_raw=Path(binding['path']).read_bytes()
    write_bytes_once(request_root/'request.original.json',request_raw)
    if digest(request_raw)!=binding['sha256']:raise AdmissionError('Frozen request bytes changed')
    request=strict_json(request_raw);image_raw=contract.validate_image_only_request(request)
    if request['model']!=BASE_REPO or request['revision']!=BASE_REVISION:
        raise AdmissionError('Request model identity must name the actual shared base without an adapter')
    write_bytes_once(request_root/'received-original.image',image_raw)
    return request,image_raw


def cpu_admit(manifest,root,journal,config,rows):
    # All gates above run before importing torch/transformers. No CUDA API is invoked.
    if os.environ.get('CUDA_VISIBLE_DEVICES')!='':
        raise AdmissionError('Explicit CUDA_VISIBLE_DEVICES empty is required for CPU admission')
    if os.environ.get('HF_HUB_OFFLINE')!='1'or os.environ.get('TRANSFORMERS_OFFLINE')!='1':
        raise AdmissionError('Offline native CPU admission requires both Hugging Face offline flags')
    import torch
    import safetensors
    import safetensors.torch
    def deny_weights(*args,**kwargs):
        raise AdmissionError('Any weight/tensor-loading API is forbidden during CPU admission')
    # Native processor/config need no tensor checkpoints. Deny their accidental use.
    torch.load=deny_weights
    safetensors.safe_open=deny_weights
    safetensors.torch.load_file=deny_weights
    safetensors.torch.load=deny_weights
    import transformers
    from transformers import AutoProcessor,AutoConfig,GenerationConfig
    from PIL import Image
    contract=contract_from_pinned_source(manifest['evidence_contract']['source_path'])
    processor=AutoProcessor.from_pretrained(MODEL_PATH,local_files_only=True,trust_remote_code=False)
    native_config=AutoConfig.from_pretrained(MODEL_PATH,local_files_only=True,trust_remote_code=False)
    original_generation=GenerationConfig.from_model_config(native_config)
    effective=copy.deepcopy(original_generation)
    effective.max_new_tokens=MAX_NEW_TOKENS;effective.do_sample=False
    effective.temperature=1.0;effective.top_p=1.0;effective.top_k=0
    effective.validate()
    runtime={'torch':torch.__version__,'transformers':transformers.__version__,
        'processor_class':type(processor).__name__,'tokenizer_class':type(processor.tokenizer).__name__,
        'processor_native_description':processor.to_dict()if hasattr(processor,'to_dict')else None,
        'original_native_generation_config':original_generation.to_dict(),
        'native_generation_defaults_derivation':{
            'generation_config_file_present':False,
            'method':'GenerationConfig.from_model_config(AutoConfig.from_pretrained(local native config))',
            'source_config_sha256':digest((Path(MODEL_PATH)/'config.json').read_bytes()),
            'text_config_eos_token_id':config['text_config'].get('eos_token_id'),
            'derived_generation_eos_token_id':original_generation.eos_token_id,
            'tokenizer_eos_token':processor.tokenizer.eos_token,
            'tokenizer_eos_token_id':processor.tokenizer.eos_token_id,
            'endoftext_id':processor.tokenizer.convert_tokens_to_ids('<|endoftext|>'),
            'im_end_id':processor.tokenizer.convert_tokens_to_ids('<|im_end|>'),
            'old_attention_eos_override_not_applied':True,
            'auxiliary_GPU_stop_rule_decision_pending':True},
        'prospective_greedy_config_with_NATIVE_unresolved_stop_rule':effective.to_dict(),
        'all_other_native_generation_defaults_preserved':True,
        'future_native_model_class':MODEL_CLASS,'future_model_dtype':'bfloat16','future_attention_backend':'sdpa',
        'model_loaded':False,'generation_performed':False,'actual_forward_inputs_observed':False,
        'actual_CUDA_tensor_inventory':None,'actual_generated_ids':None,'actual_EOS':None,
        'GPU_capacity_or_memory_fit_established':False}
    write_json_once(root/'native-processor-and-generation.json',runtime)
    journal.append('native_processor_loaded_without_model',runtime)
    for index,binding in enumerate(manifest['requests']):
        request_root=root/('r%03d'%index);request_root.mkdir(exist_ok=False)
        request,image_raw=bound_request(binding,request_root,contract)
        with Image.open(io.BytesIO(image_raw))as image:
            image.load();original_mode=image.mode;original_size=list(image.size);rgb=image.convert('RGB')
        # Exactly one user turn, one received original image and the FIXED_PROMPT.
        messages=[{'role':'user','content':[{'type':'image','image':rgb},
            {'type':'text','text':contract.FIXED_PROMPT}]}]
        source={'messages':[{'role':'user','content':[{'type':'image_source',
            'sha256':digest(image_raw),'size':original_size},
            {'type':'text','text':contract.FIXED_PROMPT}]}],
            'request_id':binding['request_id'],'original_image_mode':original_mode,
            'RGB_conversion_and_native_internal_smart_resize_no_external_resize_override':True,
            'enable_thinking':False,'tools':None,'truncation':False,
            'task_history_candidate_targets_or_expected_labels_supplied':False}
        write_json_once(request_root/'native-input-source.json',source)
        rendered=processor.apply_chat_template(messages,tokenize=False,
            add_generation_prompt=True,enable_thinking=False,tools=None)
        write_bytes_once(request_root/'rendered-native-template.txt',rendered.encode('utf8'))
        inputs=processor.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,
            enable_thinking=False,tools=None,return_dict=True,return_tensors='pt')
        required={'input_ids','pixel_values','image_grid_thw'}
        if not required<=set(inputs):raise AdmissionError('Native multimodal tensors missing')
        if list(inputs['input_ids'].shape[:1])!=[1]or list(inputs['image_grid_thw'].shape)!=[1,3]:
            raise AdmissionError('One single-image batch must be prepared without splitting/dropping')
        tensors={};other={}
        for name,value in inputs.items():
            if not isinstance(name,str)or not name.replace('_','').isalnum():raise AdmissionError('Unexpected native input key')
            if isinstance(value,torch.Tensor):tensors[name]=save_tensor(request_root,name,value,torch)
            else:canonical(value);other[name]=value
        if other:write_json_once(request_root/'non-tensor-native-inputs.json',other)
        tokens=int(inputs['input_ids'].shape[-1]);context=int(config['text_config']['max_position_embeddings'])
        if tokens+MAX_NEW_TOKENS>context:
            raise AdmissionError('Full native input plus frozen2048 output exceeds model context; no truncation allowed')
        row={'index':index,'request_id':binding['request_id'],'request_sha256':binding['sha256'],
            'image_sha256':digest(image_raw),'prompt_sha256':request['prompt_sha256'],
            'original_size':original_size,'input_tokens':tokens,'future_aux_output_cap':2048,
            'native_internal_smart_resize_retained':True,
            'native_context_capacity':context,'complete_input_fits_configured_context':True,
            'tensor_artifacts':tensors,'non_tensor_input_keys':list(other),
            'native_processor_inputs_only_not_actual_model_forward':True,
            'model_calls':0,'GPU_inference':False,'memory_fit_established':False}
        write_json_once(request_root/'admission.json',row);journal.append('native_CPU_input_admitted',row)
        rows.append(row)
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',required=True,choices=['cpu-admission'])
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    raw=Path(args.manifest).read_bytes()
    root=Path(args.output)
    if not root.is_absolute():
        raise AdmissionError('Explicit absolute once-only output root required')
    root.mkdir(parents=False,exist_ok=False) # Atomic once-only claim; never resume or remove.
    write_bytes_once(root/'input-manifest.original.json',raw)
    worker_source=Path(__file__).read_bytes()
    write_bytes_once(root/'worker-source.py',worker_source)
    write_json_once(root/'claim.json',{'manifest_sha256':digest(raw),
        'worker_sha256':digest(worker_source),'identity':process_identity(),
        'mode':'cpu-admission-only','weight_loading_allowed':False,'model_calls_allowed':0})
    journal=Journal(root);journal.append('once_only_CPU_admission_claimed',{'manifest_sha256':digest(raw)})
    status='failed';error=None;rows=[];manifest={}
    try:
        manifest=validate_manifest(strict_json(raw))
        if str(root)!=manifest['output_root']:
            raise AdmissionError('Once-only output root must match the frozen manifest')
        config=metadata_gate(manifest,root,journal)
        cpu_admit(manifest,root,journal,config,rows)
        status='completed_native_CPU_admission_no_model'
    except BaseException as exception:
        error={'type':type(exception).__name__,'message':str(exception),'traceback':traceback.format_exc()}
        write_json_once(root/'failure.json',error);journal.append('failure_preserved',error)
    finally:
        terminal={'status':status,'attempt_id':manifest.get('attempt_id'),'admitted_requests':len(rows),
            'expected_requests':manifest.get('expected_request_count'),'model_calls':0,'GPU_allocations':0,
            'GUI_actions':0,'generated_output_or_EOS':None,'actual_forward_inputs_or_CUDA_inventory':None,
            'CPU_inference_performed':False,'GPU_deployment_plan_changed':False,
            'GPU_launch_ready':False,'semantic_correctness_established':False,
            'journal_events_before_terminal':journal.seq,'journal_head_before_terminal':journal.previous,
            'error':error}
        write_json_once(root/'terminal.json',terminal);journal.append('terminal',terminal)
        files=[{'path':path.relative_to(root).as_posix(),'bytes':path.stat().st_size,
            'sha256':digest(path.read_bytes())}for path in sorted(root.rglob('*'))if path.is_file()]
        write_json_once(root/'seal.json',{'files':files,'journal_events':journal.seq,
            'journal_head':journal.previous,'worker_version':VERSION,'terminal_status':status})
    print(json.dumps({'output':str(root),'status':status,'admitted':len(rows),'model_calls':0},ensure_ascii=False))
    return 0 if error is None else 1


if __name__=='__main__':
    raise SystemExit(main())
