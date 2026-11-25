"""Audit all sealed actual inputs/forwards, without model loading or GPU calls."""
import base64,hashlib,io,json,math,os,struct,time
from pathlib import Path
from PIL import Image
import torch

exec(LIB_CODE,globals())
B=Path('/home/researcher/jev-defense-four-gpu-20261106')
G=B/'online-three-service-group-1793985778592347799'
O=B/('three-complete-service-request-audit-'+str(time.time_ns()))
O.mkdir(mode=0o700,exist_ok=False)
S=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,obj):
    with p.open('x',encoding='utf8')as f:json.dump(obj,f,ensure_ascii=False,indent=2)

def tensor_hash(value):
    # Stored int64 forward values are checked against the original raw tensor hash.
    values=value['values'];flat=[]
    def walk(v):
        if isinstance(v,list):
            for item in v:walk(item)
        else:flat.append(v)
    walk(values)
    assert value['dtype']=='torch.int64'
    assert sha(struct.pack('<'+'q'*len(flat),*flat))==value['sha256']

try:
    spec=read(G/'launch-specification.json');assert S(G/'launch-specification.json')=='233850b6bf6ecac89fbd18452c592a5b2481eeee9f5eaf6eea8b9af23c083e8c'
    config=read(Path(spec['flash_model'])/'decision_config.json');temperature=float(config['temperature']);assert temperature>0 and math.isfinite(temperature)
    journal_before=(G/'journal.jsonl').read_bytes();jr,jhead=service_chain(G/'journal.jsonl')
    state_before=(G/'online-state.json').read_bytes();state=json.loads(state_before)
    assert state['phase']=='terminal_failure'and state['active']is None
    rows=[];cert={};file_sha_before={};totals={'actor':0,'judge':0,'observer':0,'lifecycle':0}
    for role,folder in [('primary',G/'primary/requests'),('pplx_flash',G/'pplx_flash/requests'),('lifecycle',G/'transitions')]:
        for request in sorted(folder.iterdir()):
            if not request.is_dir():continue
            seal_sha=S(request/'seal.json');mapping=manifest(request,request/'seal.json',seal_sha,True)
            original_request=(request/'request.json').read_bytes();envelope=json.loads(original_request);wire=sha(original_request)
            response_raw=(request/'response.json').read_bytes();response=json.loads(response_raw)
            assert response['external_wire_sha256']==wire
            summary={'path':str(request),'request_name':request.name,'role':role,'wire_sha256':wire,'request_seal_sha256':seal_sha,'response_file_sha256':sha(response_raw),'response_canonical_sha256':sha(canonical(response)),'sealed_files':len(mapping)}
            if role!='lifecycle':
                payload=read(request/'payload.json');assert payload==envelope['payload']and response['payload_sha256']==sha(canonical(payload))
                op='observer'if role=='pplx_flash'else payload['operation'];totals[op]+=1
                fwd=native_forward(request,payload,response,role)
                trace=read(request/'forward-trace.json')
                prefill=next(r['tensors']for r in trace if len(r.get('tensors',{}).get('input_ids',{}).get('shape',[]))==2 and r['tensors']['input_ids']['shape'][-1]>1)
                tensor_hash(prefill['input_ids'])
                if 'image_grid_thw'in prefill:tensor_hash(prefill['image_grid_thw'])
                summary.update(operation=op,decision_index=envelope['decision_index'],attempt_index=envelope['attempt_index'],payload_sha256=sha(canonical(payload)),native_forward=fwd,input_ID_tensor_raw_hash_verified=True,grid_raw_hash_verified='image_grid_thw'in prefill,pixels_shape_hash_bound_not_independently_reencoded=prefill.get('pixel_values'),generation_config=read(request/'generation.json')['generation_config']if role=='primary'else None)
                if role=='pplx_flash':
                    readout=next(r['raw_readout']for r in trace if'raw_readout'in r)
                    vals=readout['values'];bits=b''.join(struct.pack('<H',struct.unpack('<I',struct.pack('<f',v))[0]>>16)for row in vals for v in row)
                    assert sha(bits)==readout['sha256']and readout['dtype']=='torch.bfloat16'
                    expected={}
                    for i,(key,q)in enumerate(QUESTIONS.items()):
                        valid=vals[i][:len(q['criteria'])]
                        probabilities=(torch.tensor(valid,dtype=torch.float32)/temperature).softmax(-1).tolist()
                        expected[key]=answer(q,probabilities)
                    assert expected==response['answers'],('probabilities differ',request.name)
                    summary.update(raw_BF16_readout_SHA_verified=True,raw_BF16_to_native_CPU_float32_softmax_and_answer_exact=True,temperature=temperature,image_sha256=payload['image_sha256'])
            else:totals['lifecycle']+=1
            rows.append(summary)
            cert[wire]={'request_name':request.name,'role':role,'response_raw_base64':base64.b64encode(response_raw).decode(),'request_seal_raw_base64':base64.b64encode((request/'seal.json').read_bytes()).decode(),'request_sha256':wire,'native_forward_audit':summary.get('native_forward'),'payload_sha256':summary.get('payload_sha256')}
            for name,h in mapping.items():file_sha_before[str(request/name)]=h
            file_sha_before[str(request/'seal.json')]=seal_sha
    assert totals=={'actor':24,'judge':73,'observer':20,'lifecycle':2}
    assert len(rows)==119
    for p,h in file_sha_before.items():assert S(p)==h
    assert(G/'journal.jsonl').read_bytes()==journal_before and(G/'online-state.json').read_bytes()==state_before
    loaded={role:read(G/role/'loaded.json')for role in('primary','pplx_flash')}
    receipt={'status':'passed_all_actual_requests_and_forwards','group':str(G),'request_totals':totals,'request_count':len(rows),'native_primary_EOS':97,'observer_forwards':20,'all_request_seals_exhaustive_verified':True,'all_input_ID_and_grid_raw_hashes_verified':True,'all_primary_full_native_generation_messages_bound':True,'all20_observer_raw_BF16_to_CPU_native_probabilities_exact':True,'native_temperature':temperature,'pixels_are_recorded_actual_shape_hash_bindings_not_new_CPU_reencoding':True,'model_weights_loaded_or_rehashed':False,'service_journal_events':len(jr),'service_journal_head':jhead,'service_journal_file_sha256':sha(journal_before),'online_state':state,'spec_sha256':S(G/'launch-specification.json'),'runtime_config_sha256':S(G/'runtime-config.json'),'decision_config_sha256':S(Path(spec['flash_model'])/'decision_config.json'),'original_auditor_source_sha256':AUDITOR_SHA,'original_observer_source_sha256':OBSERVER_SHA,'original_protocol_source_sha256':PROTOCOL_SHA,'new_health_POST_model_GUI_scorer_calls':0,'service_exit_manifests_not_inferred':True,'original_request_files_stable_before_after':True}
    save(O/'receipt.json',receipt);save(O/'request-audits.json',rows);save(O/'request-certificates.json',cert);save(O/'loaded.json',loaded)
    (O/'service-journal.jsonl').write_bytes(journal_before);(O/'online-state.json').write_bytes(state_before)
    (O/'native-library.py').write_text(LIB_CODE,encoding='utf8')
    (O/'service_audit_remote.py').write_bytes(Path(__file__).read_bytes())
    save(O/'seal.json',{p.name:S(p)for p in O.iterdir()if p.is_file()})
    files={p.name:base64.b64encode(p.read_bytes()).decode()for p in O.iterdir()if p.is_file()}
    print(json.dumps({'root':str(O),'receipt_sha256':S(O/'receipt.json'),'seal_sha256':S(O/'seal.json'),'files':files}))
except BaseException as e:
    import traceback
    save(O/'failure.json',{'error':traceback.format_exc(),'no_model_GUI_or_health_calls':True})
    raise
