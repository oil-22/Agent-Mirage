"""Original failed input CPU binding and source-bound placement proposal; no GPU work."""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import traceback

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
    with path.open('x')as handle:json.dump(value,handle,indent=2)
def map_for(counts):
    result={'model.visual':0,'model.language_model.embed_tokens':0,
        'model.language_model.norm':3,'model.language_model.rotary_emb':3,'lm_head':3}
    start=0
    for device,count in enumerate(counts):
        for layer in range(start,start+count):result['model.language_model.layers.'+str(layer)]=device
        start+=count
    assert start==64
    return result
def state_placement(records,device_map):
    result={str(i):{'bytes':0,'tensors':0}for i in range(4)}
    for row in records:
        matches=[name for name in device_map if row['name']==name or row['name'].startswith(name+'.')]
        assert matches,'Unbound native state key '+row['name']
        prefix=max(matches,key=len);device=str(device_map[prefix])
        result[device]['bytes']+=row['bytes'];result[device]['tensors']+=1
    return result

def main(a):
    assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
    root=a.root;root.mkdir(parents=True,exist_ok=False)
    try:
        config=json.loads((a.preservation/'service-group/runtime-config.json').read_bytes())
        failed=a.preservation/'service-group/primary/requests/bd7ed2f4753b00594cb626a4cad3b740c0f95d91128547da69404254a2559841'
        assert sha(a.preservation/'receipt.json')=='d78feb1d58d452c5218663bd41afe155e35825efddff0300ef0f5ff2c9c7e976'
        assert sha(failed/'seal.json')=='2524d02f7c18dd662794122701648e92c7b5729b9ae7c386b13c23ffbe4dcec7'
        for name,expected in json.loads((failed/'seal.json').read_bytes()).items():assert sha(failed/name)==expected
        assert sha(Path(config['primary_release'])/'defense/qwen_backend.py')==config['primary_backend_sha256']
        wire=json.loads((failed/'request.json').read_bytes());body=wire['payload']
        spec=importlib.util.spec_from_file_location('capacity_original_helpers',a.helper)
        helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
        import torch
        assert not torch.cuda.is_initialized()
        inputs,processor,cfg,construction=helper.reconstruct_native_inputs(config,body,torch)
        sys.path.insert(0,config['preflight_source_root'])
        from preflight_service import tensor_record
        cpu={key:tensor_record(torch,value,key in{'input_ids','image_grid_thw','video_grid_thw'})
             for key,value in inputs.items()if isinstance(value,torch.Tensor)}
        trace=json.loads((failed/'forward-trace.json').read_bytes())
        assert len(trace)==1
        actual=trace[0]['tensors']
        for key in('input_ids','pixel_values','image_grid_thw'):assert actual[key]==cpu[key],key
        save(root/'CPU-native-tensor-records.json',cpu)
        save(root/'actual-failed-forward-trace.json',trace)
        save(root/'original-native-generation-config.reconstructed.json',cfg)
        import defense.qwen_backend as backend
        from defense.core import PublicView,VisibleImage
        view_data=body['view'];images=tuple(VisibleImage(base64.b64decode(row['raw_base64']),row['role'])
                                                for row in view_data['images'])
        view=PublicView(view_data['observation_id'],view_data['messages'],images,
            view_data.get('recent_action',''),view_data.get('execution_feedback',''),view_data['observed_at'])
        captured={}
        class Capture:
            def generate(self,messages,max_tokens,receipt,seed=42,original_body=None,json_schema=None):
                captured.update(messages=messages,max_tokens=max_tokens,seed=seed,
                    original_body=original_body,json_schema=json_schema)
                return 'CPU construction only; no generate or model'
        backend.LocalQwen.judge(Capture(),body['system'],view,body.get('candidate'),None)
        assert captured['max_tokens']==4096 and captured['seed']==42 and captured['original_body']is None
        save(root/'original-judge-call-schema-and-messages.reconstructed.json',captured)
        native=json.loads(Path(config['primary_native_layout_receipt']).read_bytes())
        meta_root=Path(native['meta_root'])
        assert sha(meta_root/'receipt.json')==native['meta_receipt_sha256']
        for name,expected in json.loads((meta_root/'seal.json').read_bytes()).items():assert sha(meta_root/name)==expected
        records=json.loads((meta_root/'meta-state.json').read_bytes())
        assert len(records)==1184
        original=map_for([18,20,20,6]);candidate=map_for([14,22,22,6])
        old=state_placement(records,original);new=state_placement(records,candidate)
        metadata=json.loads((Path(config['primary_model'])/'config.json').read_bytes())
        types=metadata['text_config']['layer_types']
        assert len(types)==64 and types.count('full_attention')==16 and types.count('linear_attention')==48
        distribution={}
        for label,counts in [('original',[18,20,20,6]),('candidate',[14,22,22,6])]:
            start=0;rows={}
            for device,count in enumerate(counts):
                values=types[start:start+count]
                rows[str(device)]={'physical_GPU':device+4,'layer_start':start,'layer_end':start+count-1,
                    'decoder_layers':count,'full_attention_layers':values.count('full_attention'),
                    'linear_attention_layers':values.count('linear_attention')};start+=count
            distribution[label]=rows
        before=json.loads((a.preservation/'service-group/primary/loaded.json').read_bytes())
        failure=json.loads((failed/'failure.json').read_bytes())
        snapshots={str(row['logical_device']):row for row in failure['per_device_memory']}
        deltas={str(i):new[str(i)]['bytes']-old[str(i)]['bytes']for i in range(4)}
        for i in range(4):
            # Only a parameter subtraction illustration, not a measured activation/KV bound.
            distribution['candidate'][str(i)].update(native_state_bytes=new[str(i)]['bytes'],
                parameter_delta_bytes=deltas[str(i)],
                illustrative_old_failed_allocated_plus_parameter_delta_bytes=snapshots[str(i)]['allocated_bytes']+deltas[str(i)],
                original_loaded_extra_nonpersistent_buffer_bytes=before['tensor_bytes_by_device']['cuda:'+str(i)]-old[str(i)]['bytes'])
        assert deltas['0']<0 and deltas['1']>0 and deltas['2']>0 and deltas['3']==0
        assert all(new[str(i)]['bytes']<([20,20,20,8][i]*1024**3)for i in range(4))
        save(root/'candidate-device-map.json',candidate)
        save(root/'native-state-placement-comparison.json',{'source_meta_root':str(meta_root),
            'source_meta_receipt_sha256':sha(meta_root/'receipt.json'),'source_meta_state_sha256':sha(meta_root/'meta-state.json'),
            'records':len(records),'original':old,'candidate':new,'parameter_delta_bytes':deltas,
            'layer_types_and_distribution':distribution,'not_runtime_peak_prediction':True})
        save(root/'allocator-vs-placement-assessment.json',{
            'observed_failure':'prefill native linear attention contiguous cast alloc504MiB on logical0/physical4',
            'observed_error_fragmentation_recommendation_is_not_proof_of_fix':True,
            'observed_GPU0_free_bytes':snapshots['0']['free_bytes'],
            'observed_GPU0_allocated_bytes':snapshots['0']['allocated_bytes'],
            'observed_GPU0_reserved_minus_allocated_bytes':snapshots['0']['reserved_bytes']-snapshots['0']['allocated_bytes'],
            'allocator_only':'expandable_segments may reduce reserved fragmentation; no guarantee with high live allocations',
            'placement_change':'14/22/22/6 moves decoder14..17 off physical4; moves36..37 from5 to6',
            'proposed_single_attempt':'one changed-layout process with process-local expandable_segments:True plus exact original failed judge input once',
            'why_one':'deterministic parameter headroom first, optional allocator for fragmentation in same single attempt; no allocator-only extra model trial',
            'output_numerical_equivalence_guaranteed':False,'algorithm_precision_inputs_outputs_changed':False,
            'device_map_change_can_change_numerics_or_reply':True,'actual_KV_prefill_capacity_unverified':True})
        assert not torch.cuda.is_initialized()
        receipt={'status':'passed','scope':'CPU exact failed-input reconstruction and parameter-only candidate layout',
            'failed_external_wire_sha256':sha(failed/'request.json'),
            'failed_payload_sha256':sha(failed/'payload.json'),'failed_forwardtrace_sha256':sha(failed/'forward-trace.json'),
            'preservation_receipt_sha256':sha(a.preservation/'receipt.json'),
            'input_tokens':inputs['input_ids'].shape[-1],'image_count':len(images),
            'native_CPU_IDs_pixels_grid_exact_actual_failed_prefill':True,
            'original_judge_method_and_generate_input_AST_unchanged':True,
            'construction':construction,'schema_sha256':hashlib.sha256(helper.json.dumps(captured['json_schema'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'schema_and_config_are_source_bound_CPU_reconstruction_not_runtime_generation_receipt':True,
            'seed':42,'verifier_output_tokens':4096,'BF16_SDPA_full_images_full_history_unchanged':True,
            'candidate_layer_counts':[14,22,22,6],'original_layer_counts':[18,20,20,6],
            'candidate_parameter_deltas_bytes':deltas,'native_meta_state_count':1184,
            'allocator_only_not_proven':'high live allocation plus possible fragmentation; error recommendation not validation',
            'proposed_capacity_replay_primary_judge_calls':1,'proposed_helper_resident_calls':0,
            'old72completed_replies_preserved_not_repeated':True,'no_automatic_GUI_release_after_capacity':True,
            'requires_old_group_marker_only_stop_then_root_reviewed_new_once_only_launcher':True,
            'GPU_allocations':0,'model_calls':0,'GUI_calls':0,'full_weight_rehashes':0,'live_changes':0}
        save(root/'receipt.json',receipt)
        save(root/'seal.json',{str(p.relative_to(root)):sha(p)for p in root.rglob('*')if p.is_file()})
        print(json.dumps({'receipt':str(root/'receipt.json'),'receipt_sha256':sha(root/'receipt.json'),
            'seal_sha256':sha(root/'seal.json'),'input_tokens':receipt['input_tokens'],'images':len(images),
            'candidate_parameter_deltas_bytes':deltas,'native_CPU_input_exact':True,'model_GPU_calls':0}))
    except BaseException:
        save(root/'failure.json',{'error':traceback.format_exc(),'model_GPU_calls':0})
        save(root/'seal.json',{str(p.relative_to(root)):sha(p)for p in root.rglob('*')if p.is_file()})
        raise

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--preservation',type=Path,required=True);parser.add_argument('--helper',type=Path,required=True)
    main(parser.parse_args())
