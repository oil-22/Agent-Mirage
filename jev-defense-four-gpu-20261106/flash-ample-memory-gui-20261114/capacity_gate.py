"""Two finite GPU capacity probes; no GUI, scorer, labels or completed-trial retry."""
import copy,hashlib,json,os,time
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
    if sha(original/'wire-request.bin')!=binding['wire_sha256']or sha(original/'seal.json')!=binding['seal_sha256']:raise RuntimeError('Failed source binding changed')
    seal=json.loads((original/'seal.json').read_bytes())
    if any(sha(original/n)!=h for n,h in seal.items()):raise RuntimeError('Original failed evidence no longer sealed')
    source=json.loads((original/'wire-request.bin').read_bytes());body=source['body'];expected=json.loads((original/'prepared.json').read_bytes())
    assert image_count(body)==15 and body['max_tokens']==2048
    probes=[('01-exact-previous-OOM-input',body,False),('02-explicit-synthetic-50-image-load',fifty_image_load(body),True)]
    results=[]
    for name,request,synthetic in probes:
        resource(True);d=root/name;d.mkdir()
        save(d/'body.json',request)
        save(d/'purpose.json',{'source_request':str(original),'source_wire_sha256':binding['wire_sha256'],'synthetic_capacity_input':synthetic,'actual_GUI_history':not synthetic,'not_formal_actor_or_semantic_trial':True,'full_images':image_count(request),'max_new_tokens':2048,'no_GUI_actions_scorer_or_paid_API':True})
        for device in range(7):native.torch.cuda.reset_peak_memory_stats(device)
        start=time.time();text=native.generate(request,d);g=json.loads((d/'actual-generation.json').read_bytes());p=json.loads((d/'prepared.json').read_bytes())
        if not synthetic:
            assert set(p)==set(expected)
            for k in expected:assert all(p[k][f]==expected[k][f]for f in ['shape','dtype','bytes','sha256']),k
        peaks=[]
        for device in range(7):
            total=native.torch.cuda.get_device_properties(device).total_memory
            peak=native.torch.cuda.max_memory_reserved(device)
            peaks.append({'physical_gpu':device,'total_bytes':total,'peak_reserved_bytes':peak,'headroom_at_reserved_peak_bytes':total-peak})
        assert g['natural_EOS']
        row={'probe':name,'synthetic_capacity_input':synthetic,'input_tokens':g['input_tokens'],'output_tokens':g['output_tokens'],'natural_EOS':True,'complete_images':image_count(request),'seconds_with_audit':time.time()-start,'memory':peaks,'original_full_input_tensor_equality':not synthetic,'semantic_label':None,'GUI_actions':0,'body_sha256':sha(d/'body.json')}
        save(d/'response.json',{'text':text,'capacity_only':True});save(d/'result.json',row)
        save(d/'seal.json',{p.name:sha(p)for p in d.iterdir()if p.is_file()})
        results.append(row)
        if min(v['headroom_at_reserved_peak_bytes']for v in peaks)<3*1024**3:raise RuntimeError('Capacity completed but less than 3GiB reserved-peak headroom; do not start GUI')
    summary={'status':'passed','probes':results,'actual_capacity_generation_calls':2,'formal_GUI_calls':0,'fifty_image_probe_is_synthetic':True,'all_future_histories_or_2048_token_each_worst_case_fit_proven':False,'main_precision':'BF16','attention':'SDPA','physical_main_gpus':list(range(7)),'Flash_physical_gpu':7,'minimum_reserved_peak_headroom_GiB':3,'time':time.time()}
    save(root/'terminal.json',summary);save(root/'seal.json',{str(p.relative_to(root)):sha(p)for p in root.rglob('*')if p.is_file()})
    return summary
