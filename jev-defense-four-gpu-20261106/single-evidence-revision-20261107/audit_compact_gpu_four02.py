"""Independent root postexit audit of the first immutable auxiliary terminal."""
import base64,hashlib,json,struct
from pathlib import Path
R=Path(__file__).resolve().parent
T=R/'gpu-compact-four-terminal-collection-02/original'
C=R/'native-auxiliary-admission-compact02/cpu-native-compact-four-02/collected/admission-01'
O=R/'compact-four-root-technical-audit-02';O.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def write(p,v):
    with p.open('x',encoding='utf8')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
manifest=read(T/'terminal-manifest.json')
assert all(sha(T/n)==h for n,h in manifest.items())
wm=read(T/'worker/input-manifest.original.json')
api=read(R/'model-capability-review/native-small-metadata-linked02-1794046900308884400/qwen-fixed-api.json')
assert api['sha']==wm['base_model']['revision']
official={r['rfilename']:r['lfs']for r in api['siblings']if r['rfilename'].endswith('.safetensors')}
identity=read(T/'worker/current-weight-identity.json')
assert len(identity['complete_current_shards'])==4
for row in identity['complete_current_shards']:
    assert row['reused_full_sha256']==row['sha256']==official[row['filename']]['sha256']
    assert row['bytes']==official[row['filename']]['size']
loaded=read(T/'worker/loaded.json')
assert loaded['model_class']=='Qwen3_5ForConditionalGeneration'
assert set(loaded['actual_attention_backends'].values())=={'sdpa'}
for tensor in loaded['actual_cuda_tensors']:
    assert tensor['device']=='cuda:0'
    if tensor['kind']=='parameter':assert tensor['dtype']=='torch.bfloat16'
assert len(loaded['actual_cuda_tensors'])==763
assert wm['generation']['max_new_tokens']==2048 and wm['generation']['eos_token_id']==[248044,248046]
rows=[]
for i,binding in enumerate(wm['requests']):
    d=T/'worker'/('r%03d'%i);cpu=read(C/('r%03d'%i)/'admission.json')
    req=read(d/'request.original.json');result=read(d/'result.json')
    assert sha(d/'request.original.json')==binding['sha256']==cpu['request_sha256']
    image=base64.b64decode(req['image_base64'],validate=True)
    assert hashlib.sha256(image).hexdigest()==binding['image_sha256']==cpu['image_sha256']==sha(d/'received-original.image')
    assert set(req)=={'policy','model','revision','image_base64','image_sha256','original_size','prompt','prompt_sha256'}
    assert req['prompt_sha256']==hashlib.sha256(req['prompt'].encode()).hexdigest()
    forward=read(d/'actual-first-forward.json')
    assert set(forward)==set(cpu['tensor_artifacts'])
    for name,record in forward.items():
        expected=cpu['tensor_artifacts'][name]
        assert all(record[k]==expected[k]for k in ['shape','dtype','bytes','sha256'])
        assert sha(d/record['file'])==record['sha256']
        assert sha(d/('prepared_'+name+'.tensor'))==record['sha256']
    original=(d/'actual_forward_input_ids.tensor').read_bytes()
    sequence=(d/'sequence_ids.tensor').read_bytes();generated=(d/'generated_ids.tensor').read_bytes()
    assert sequence==original+generated
    ids=read(d/'generated_ids.json')[0]
    assert generated==struct.pack('<'+'q'*len(ids),*ids)
    assert len(ids)==result['output_tokens'] and cpu['input_tokens']==result['input_tokens']
    assert result['natural_eos']==bool(ids[-1]in [248044,248046])
    assert sha(d/'raw-output.txt')==result['raw_output_sha256']
    assert result['contract_valid']==(d/'evidence-packet.json').exists()
    if result['contract_valid']:
        packet=read(d/'evidence-packet.json')
        assert packet['raw_output_sha256']==result['raw_output_sha256']
        assert packet['image_sha256']==result['image_sha256']
        assert packet['inventory_is_exhaustive']is False and packet['automatic_allow_or_block']is False
        assert packet['semantic_correctness_established']is False and result['natural_eos']is True
    traces=(d/'actual-forward-calls.jsonl').read_bytes().splitlines()
    assert len(traces)==result['actual_forward_calls']
    if not result['contract_valid']:assert read(d/'contract-failure.json')==result['contract_error']
    rows.append(result)
chains={}
for name in ['journal.jsonl','worker/journal.jsonl']:
    previous='0'*64;count=0
    for line in(T/name).read_bytes().splitlines():
        event=json.loads(line);given=event.pop('sha256')
        assert event.get('seq',event.get('index'))==count
        assert event.get('previous',event.get('previous_sha256'))==previous
        raw=json.dumps(event,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        assert hashlib.sha256(raw).hexdigest()==given
        previous=given;count+=1
    chains[name]={'events':count,'head':previous}
exit=read(T/'exit.json')
assert exit['worker_exit_code']==exit['launcher_exit_code']==0
assert abs((exit['ended_unix']-exit['started_unix'])*4-exit['four_GPU_reserved_seconds_during_launcher'])<1e-6
receipt={'status':'actual_native_input_generation_and_terminal_audited',
    'original_files':len(manifest),'original_manifest_sha256':sha(T/'terminal-manifest.json'),
    'requests':rows,'chains':chains,'current_identity_sha256':sha(T/'worker/current-weight-identity.json'),
    'full_current_four_shards_official_pin_bound':True,'current_identity_uses_sealed_prior_full_hash_and_current_stat_not_rehash':True,'actual_cuda_tensors':763,
    'all_actual_first_forward_inputs_equal_original_CPU_bytes':True,
    'input_tokens':sum(x['input_tokens']for x in rows),'output_tokens':sum(x['output_tokens']for x in rows),
    'generation_seconds_sum':sum(x['generation_seconds']for x in rows),
    'natural_EOS':sum(x['natural_eos']for x in rows),'nonEOS_caps':sum(not x['natural_eos']for x in rows),
    'usable_evidence_packets':sum(x['contract_valid']for x in rows),'semantic_success_or_Mirage_reduction_established':False,
    'exit':exit,'postexit_actual_absence_proof':str(R/'gpu-compact-four-terminal-collection-02/remote-audit.json'),
    'new_model_GUI_scorer_calls_by_auditor':0,
    'cost_limit':'Load and summed generation seconds, plus four-card reservation during this launcher only; holder remains active.'}
write(O/'receipt.json',receipt)
with(O/'audit_source').open('xb')as f:f.write(Path(__file__).read_bytes())
write(O/'seal.json',{'receipt.json':sha(O/'receipt.json'),'audit_source':sha(O/'audit_source')})
print(json.dumps({k:receipt[k]for k in ['status','input_tokens','output_tokens','generation_seconds_sum','natural_EOS','nonEOS_caps','usable_evidence_packets']}))
