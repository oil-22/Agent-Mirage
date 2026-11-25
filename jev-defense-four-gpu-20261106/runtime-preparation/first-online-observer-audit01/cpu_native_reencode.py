"""One completed input: native CPU encoder and numeric answer only, no model load."""
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.nice(10)
import hashlib,json,sys
from pathlib import Path
import torch

root=Path(sys.argv[1]);config=json.loads((root/'runtime-config.json').read_bytes())
checkpoint=Path(config['flash_model']);sys.path.insert(0,str(checkpoint/'source/src'))
from transformers import AutoProcessor
from pplx_decider.protocol import Encoder,left_pad,answer
import pplx_decider.protocol as protocol
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
torch.set_num_threads(1)
assert not torch.cuda.is_initialized()
identity=json.loads(Path(config['flash_stable_identity_receipt']).read_bytes())
assert sha(config['flash_stable_identity_receipt'])==config['flash_stable_identity_receipt_sha256']
sources=[]
for row in identity['files']:
    if row['file'].startswith('source/')or row['file']=='decision_config.json':
        assert sha(checkpoint/row['file'])==row['sha256'];sources.append({'file':row['file'],'sha256':row['sha256']})
assert Path(protocol.__file__).resolve()==(checkpoint/'source/src/pplx_decider/protocol.py').resolve()
processor=AutoProcessor.from_pretrained(str(checkpoint),local_files_only=True);processor.tokenizer.padding_side='left'
decision=json.loads((checkpoint/'decision_config.json').read_bytes())
processor.image_processor.size={'shortest_edge':65536,'longest_edge':decision['max_pixels']}
encoder=Encoder(processor,decision['codes'])
request=root/'observer-request';native=json.loads((request/'native-request.json').read_bytes())
trace=json.loads((request/'forward-trace.json').read_bytes())
assert native['images_sha256']==[sha(request/'original.image')]
plans=encoder.plan({'state':native['state'],'questions':native['questions'],'images':[str(request/'original.image')]},262144)
assert len(plans)==1
chunk=plans[0];inputs=left_pad([chunk],encoder.pad_id)
prefill=next(row['tensors']for row in trace if'input_ids'in row.get('tensors',{}));records={}
for key,value in inputs.items():
    raw=value.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()
    record={'shape':list(value.shape),'dtype':str(value.dtype),'sha256':hashlib.sha256(raw).hexdigest()}
    assert all(record[k]==prefill[key][k]for k in('shape','dtype','sha256')),(key,record,prefill[key])
    if'values'in prefill[key]:assert value.tolist()==prefill[key]['values']
    records[key]=record
recorded=next(row['raw_readout']for row in trace if'raw_readout'in row)
assert recorded['shape']==[3,255]and recorded['dtype']=='torch.bfloat16'
readout=torch.tensor(recorded['values'],dtype=torch.bfloat16)
assert hashlib.sha256(readout.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()==recorded['sha256']
answers={}
for i,(key,question)in enumerate(native['questions'].items()):
    probabilities=(readout[i,:len(question['criteria'])].float()/decision['temperature']).softmax(-1).tolist()
    answers[key]=answer(question,probabilities)
result=json.loads((request/'native-result.json').read_bytes())
assert answers==result['answers']and result['usage']=={'input_tokens':chunk.length,'output_tokens':0,'sequences':1}
assert not torch.cuda.is_initialized()
proof={'status':'passed','input_tokens':chunk.length,'full_native_inputs_exact_forward':True,
    'input_IDs_pixels_grid_and_other_tensors':records,'native_marker_positions':chunk.markers.tolist(),
    'question_keys':list(chunk.keys),'option_counts':list(chunk.counts),'image_grid_thw':chunk.image_grid_thw.tolist(),
    'raw_BF16_readout_bytes_verified':True,'native_temperature_softmax_answers_exact':True,
    'decision_temperature':decision['temperature'],'source_bindings':sources,'CPU_threads':1,'nice':10,
    'model_weights_loaded':False,'model_forward_calls':0,'GPU_allocations':0,'health_GUI_POST_calls':0,
    'probabilities_are_not_semantic_labels':True}
with(root/'CPU-native-input-probability-audit.json').open('x')as f:json.dump(proof,f,indent=2)
print(json.dumps(proof))
