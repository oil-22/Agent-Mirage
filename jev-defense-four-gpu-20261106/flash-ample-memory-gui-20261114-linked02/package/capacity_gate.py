"""Linked memory-only repair verification followed by one full 50-image load."""
import copy,json,time
from pathlib import Path

def image_count(body):
    return sum(1 for m in body['messages']if isinstance(m.get('content'),list)for x in m['content']if x.get('type')=='image_url')

def fifty_image_load(original):
    body=copy.deepcopy(original);messages=body['messages'];n=image_count(body)
    if n!=15 or len(messages)!=30 or messages[-1]['role']!='user'or messages[-2]['role']!='assistant':raise ValueError('Unexpected exact failed source history')
    pair=copy.deepcopy(messages[-2:])
    for _ in range(50-n):messages.extend(copy.deepcopy(pair))
    assert image_count(body)==50 and body['messages'][:len(original['messages'])]==original['messages']
    return body

def run(native,package,primary_root,save,sha,resource):
    root=primary_root.parent/'capacity';root.mkdir(exist_ok=False)
    binding=json.loads((package/'capacity-source.json').read_bytes());original=Path(binding['source_request'])
    assert sha(original/'wire-request.bin')==binding['wire_sha256']and sha(original/'seal.json')==binding['seal_sha256']
    for n,h in json.loads((original/'seal.json').read_bytes()).items():assert sha(original/n)==h
    body=json.loads((original/'wire-request.bin').read_bytes())['body'];expected=json.loads((original/'prepared.json').read_bytes())
    assert image_count(body)==15 and body['max_tokens']==2048
    prior=Path(binding['prior_complete15_probe']);assert sha(prior/'seal.json')==binding['prior_complete15_seal_sha256']
    for n,h in json.loads((prior/'seal.json').read_bytes()).items():assert sha(prior/n)==h
    reused=json.loads((prior/'result.json').read_bytes());assert reused['natural_EOS']and reused['input_tokens']==15367
    save(root/'reused-completed-15-image-result.json',{'source':str(prior),'seal_sha256':sha(prior/'seal.json'),'result':reused,'not_reexecuted_as_a_complete_generation':True})
    validation=root/'lifetime-validation';validation.mkdir()
    from memory_lifetime import install_validated
    proof=install_validated(native,package,validation,body,expected,save,sha,resource)
    for device in range(7):native.torch.cuda.reset_peak_memory_stats(device)
    resource(True);d=root/'50-image-source-bound-stress';d.mkdir();request=fifty_image_load(body)
    save(d/'body.json',request);save(d/'purpose.json',{'synthetic_capacity_input':True,'images':50,'real_GUI_history':False,'original_prefix_preserved':True,'inference_only':True,'formal_actor_cap_unchanged':2048,'linked_prior_50_image_OOM':binding['linked_prior_output'],'no_GUI_scorer_or_semantic_labels':True})
    began=time.time();text=native.generate(request,d);generated=json.loads((d/'actual-generation.json').read_bytes())
    assert generated['natural_EOS']
    peaks=[]
    for device in range(7):
        total=native.torch.cuda.get_device_properties(device).total_memory;peak=native.torch.cuda.max_memory_reserved(device)
        peaks.append({'physical_gpu':device,'total_bytes':total,'peak_reserved_bytes':peak,'headroom_at_reserved_peak_bytes':total-peak})
    result={'probe':'50-image-source-bound-stress','synthetic_capacity_input':True,'input_tokens':generated['input_tokens'],'output_tokens':generated['output_tokens'],'natural_EOS':True,'complete_images':50,'seconds_with_audit':time.time()-began,'memory':peaks,'semantic_label':None,'GUI_actions':0,'body_sha256':sha(d/'body.json')}
    save(d/'response.json',{'text':text,'capacity_only':True});save(d/'result.json',result);save(d/'seal.json',{p.name:sha(p)for p in d.iterdir()if p.is_file()})
    if min(v['headroom_at_reserved_peak_bytes']for v in peaks)<3*1024**3:raise RuntimeError('Less than 3GiB measured peak headroom; GUI not admitted')
    summary={'status':'passed','probes':[result],'reused_15_image_natural_EOS_result':True,'memory_lifetime_patch':proof,'actual_capacity_model_generate_calls':3,'invariance_generate_calls_at_3_steps':2,'natural_EOS_stress_calls':1,'formal_GUI_calls':0,'fifty_image_probe_is_synthetic':True,'all_future_histories_or_2048_token_each_worst_case_fit_proven':False,'main_precision':'BF16','attention':'SDPA','physical_main_gpus':list(range(7)),'Flash_physical_gpu':7,'minimum_reserved_peak_headroom_GiB':3,'time':time.time()}
    save(root/'terminal.json',summary);save(root/'seal.json',{str(p.relative_to(root)):sha(p)for p in root.rglob('*')if p.is_file()})
    return summary
