"""Read-only experiment audit; freeze a separate deployment completion receipt."""
import base64,hashlib,json,math,os,pathlib,statistics,time,urllib.request
import numpy as np
B=pathlib.Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
canonical=lambda v:json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def verify_seal(root,name):
    entries=json.loads((root/name).read_bytes())
    for n,h in entries.items():assert sha(root/n)==h,(root,n)
    return {'files':len(entries),'seal_sha256':sha(root/name)}
def chain(path):
    previous='0'*64;count=0
    for line in path.read_text().splitlines():
        event=json.loads(line);h=event.pop('sha256')
        assert event['seq']==count and event['previous']==previous and hashlib.sha256(canonical(event)).hexdigest()==h,path
        previous=h;count+=1
    return {'file':str(path),'events':count,'head':previous}
old=verify_seal(B/'services/style-01','postexit-seal.json')
runs={}
for name in ('preflight-style-01','preflight-paired-01'):
    root=B/name;runs[name]={'terminal':verify_seal(root,'terminal-sha256.json'),'event_chains':[chain(p) for p in root.rglob('events.jsonl')]}
paired=json.loads((B/'preflight-paired-01/summary.json').read_bytes())
assert paired['new_model_calls']==18 and len(paired['rows'])==36
assert sum(r['status']=='exact_input_reuse' for r in paired['rows'])==18
assert sum(r['status']=='measured' for r in paired['rows'])==18
responses={};bindings=[]
for model,name in [('jev_style','style-01'),('neohorse','neo-01')]:
    collected=[]
    for d in sorted((B/'services'/name/'runtime/requests').iterdir()):
        verify_seal(d,'seal.json');req=json.loads((d/'request.json').read_bytes());out=json.loads((d/'response.json').read_bytes());native=json.loads((d/'native-result.json').read_bytes())
        assert out['native_result']==native and out['model']==model and out['request_sha256']==sha(d/'request.json')
        assert out['image_sha256']==sha(d/'original.image')==req['image_sha256']
        assert base64.b64decode(req['image_base64'])==(d/'original.image').read_bytes()
        assert out['forward_trace_sha256']==sha(d/'forward-trace.json')
        traces=json.loads((d/'forward-trace.json').read_bytes());assert len(traces)==1
        trace=traces[0]
        for field in ('input_ids','image_grid_thw'):
            record=trace[field];tensor=np.asarray(record['values'],dtype=np.int64)
            assert list(tensor.shape)==record['shape'] and hashlib.sha256(tensor.tobytes()).hexdigest()==record['sha256']
        assert trace['input_ids']['shape']==[1,native['input_tokens']]
        assert math.prod(trace['image_grid_thw']['values'][0])//4==native['image_tokens']==880
        assert trace['pixel_values']['shape']==[3520,1536]
        assert out['generation_tokens']==0
        collected.append(out);bindings.append({'model':model,'request_id':out['request_id'],'receipt':str(d),'request_sha256':out['request_sha256'],'response_sha256':sha(d/'response.json'),'image_sha256':out['image_sha256'],'forward_trace_sha256':out['forward_trace_sha256']})
    assert len(collected)==19
    times=[r['seconds_including_audit'] for r in collected]
    responses[model]={'actual_calls':len(collected),'input_tokens':sum(r['native_result']['input_tokens'] for r in collected),'prefill_decision_only':True,'summed_inference_and_audit_seconds':sum(times),'median_seconds_including_audit':statistics.median(times),'min_seconds_including_audit':min(times),'max_seconds_including_audit':max(times),'max_peak_allocated_bytes':max(r['peak_allocated_bytes'] for r in collected),'max_peak_reserved_bytes':max(r['peak_reserved_bytes'] for r in collected)}
live=[]
for model,name,port in [('neohorse','neo-01',18222),('jev_style','style-02',18221)]:
    root=B/'services'/name;launch=json.loads((root/'launch.json').read_bytes());proc=pathlib.Path('/proc')/str(launch['pid'])
    assert proc.stat().st_uid==1033
    assert proc.joinpath('cmdline').read_bytes().replace(b'\0',b' ').decode().strip()==' '.join(launch['command'])
    assert proc.joinpath('stat').read_text().split()[21]==json.loads((root/'runtime/process.json').read_bytes())['start_ticks']
    locks=[]
    for fd in (proc/'fdinfo').iterdir():
        info=fd.read_text()
        if 'lock:' in info:locks.append({'fd':fd.name,'info':info,'path':os.readlink(proc/'fd'/fd.name)})
    assert {x['path'] for x in locks}=={x['path'] for x in launch['locks']}
    with urllib.request.urlopen('http://127.0.0.1:'+str(port)+'/health',timeout=15) as response:health=json.load(response)
    assert health['exclusive_gpu'] and health['pid']==launch['pid'] and health['uid']==1033 and health['model']==model
    assert sha(root/'serve_local.py')==launch['script_sha256']
    live.append({'model':model,'attempt':name,'pid':launch['pid'],'uid':1033,'physical_gpu':launch['physical_gpu'],'url':'http://127.0.0.1:'+str(port),'command':launch['command'],'locks':locks,'health':health,'loaded_audit_sha256':sha(root/'runtime/loaded.json'),'runtime_source_sha256':sha(root/'serve_local.py'),'elapsed_reserved_gpu_seconds_at_audit':time.time()-launch['time'],'this_instance_replies':len(list((root/'runtime/requests').iterdir()))})
result={'time':time.time(),'status':'deployment_and_shadow_integration_complete','deployment_complete':True,'formal_defense_efficacy_proven':False,'active_services':live,'model_metrics':responses,'total_real_model_calls':38,'style_18_reused_not_rerun':True,'original_style_postexit':old,'experiment_runs':runs,'actual_forward_request_bindings':bindings,'controller_contract':paired['integration'],'main_27B_actor_GUI_scorer_paid_API_calls':0,'scope':'Nonblind selected single-task visual development controls; original main judge is contract fixture; no causal or general accuracy claim','runtime_conditions':'Native BF16 backbones with original FP32 exceptions/heads; separate one3090-card services; no quantization or extra cropping; native processor 1280x704 from original1280x720','source_sha256':{n:sha(B/n) for n in ['serve_local.py','launch_services.py','jev_auxiliary.py','integration-config.json','run_real_preflight.py','preflight-plan.json','test_integration.py']}}
target=B/'finalizations'/str(time.time_ns());target.mkdir(parents=True,exist_ok=False)
for name,value in [('completion.json',result),('paired-summary.json',paired)]:
    with(target/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2)
with(target/'seal.json').open('x') as f:json.dump({p.name:sha(p) for p in target.iterdir() if p.is_file() and p.name!='seal.json'},f,indent=2)
pointer={'root':str(target),'completion_sha256':sha(target/'completion.json'),'seal_sha256':sha(target/'seal.json')}
(B/'completion-current.json').write_text(json.dumps(pointer,indent=2))
print(json.dumps({'pointer':pointer,'model_metrics':responses,'active_services':[{'model':r['model'],'physical_gpu':r['physical_gpu'],'pid':r['pid'],'exclusive':r['health']['exclusive_gpu']}for r in live]}))
