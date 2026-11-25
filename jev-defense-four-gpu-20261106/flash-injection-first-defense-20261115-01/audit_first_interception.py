"""Read-only audit of the first REAL injected-NO/fresh-YES/native-action chain."""
import hashlib
import json
import time
from pathlib import Path
from control import HERE, remote, save


def main():
    assert not (HERE / 'first-interception-current.json').exists(), 'Do not repeat a completed audit'
    pointer = json.loads((HERE / 'live-progress-current.json').read_bytes())
    progress = Path(pointer['root']); packet = json.loads((progress / 'result.json').read_bytes())
    attempt = next(a for a in packet['result']['4090']['attempts'] if a['attacks'] and a['NO_events'])
    attack = attempt['attacks'][0]
    events = attempt['events']; at = attack['seq']
    no = next(r for r in events if r['seq'] > at and r['kind'] == 'gate_decision' and r['data']['decision'] == 'NO')
    assert no['data']['image_sha256'] == attack['data']['delivered_sha256']
    yes = next(r for r in events if r['seq'] > no['seq'] and r['kind'] == 'gate_decision' and r['data']['decision'] == 'YES')
    capture = next(r for r in events if no['seq'] < r['seq'] < yes['seq'] and r['kind'] == 'capture')
    assert capture['data']['capture_id'] != no['data']['capture_id']
    assert capture['data']['image_sha256'] == yes['data']['image_sha256'] == attack['data']['captured_sha256']
    assert not any(r['kind'] in ['actual_actor_request', 'main_image_forwarded', 'native_environment_action']
                   for r in events if at < r['seq'] < yes['seq'])
    forwarded = next(r for r in events if r['seq'] > yes['seq'] and r['kind'] == 'main_image_forwarded')
    assert forwarded['data']['image_sha256'] == yes['data']['image_sha256']
    request = next(r for r in events if r['seq'] > forwarded['seq'] and r['kind'] == 'actual_actor_request')
    reply = next(r for r in events if r['seq'] > request['seq'] and r['kind'] == 'actual_actor_reply')
    action = next(r for r in events if r['seq'] > reply['seq'] and r['kind'] == 'native_environment_action')
    selected = {'attack': attack, 'no': no, 'recapture': capture, 'yes': yes, 'forwarded': forwarded,
                'request': request, 'reply': reply, 'executed_action': action,
                'run_id': attempt['run_id'], 'controller_chain': attempt['chain'],
                'progress_source': str(progress), 'progress_seal_sha256': pointer['seal_sha256']}
    code = 'SELECTED=' + repr(selected) + '\n' + r'''
import base64,hashlib,json,os,struct,time
from pathlib import Path
os.environ['CUDA_VISIBLE_DEVICES']=''
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def verify(p):
 records=json.loads((p/'seal.json').read_bytes())
 for name,h in records.items():assert sha(p/name)==h,(str(p),name)
 return {'root':str(p),'seal_sha256':sha(p/'seal.json'),'members':len(records)}
root=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/flash-injection-first-defense-20261115-01')
contract=json.loads((root/'flash/gate-contract.json').read_bytes())
import torch
torch.set_num_threads(2)
assert not torch.cuda.is_initialized()
flash=[]
for event in [SELECTED['no'],SELECTED['yes']]:
 rid=event['data']['request_id'];p=root/'flash/service/requests'/rid;proof=verify(p)
 request=json.loads((p/'wire-request.bin').read_bytes());assert set(request)=={'request_id','image_png_base64','image_sha256'}
 png=base64.b64decode(request['image_png_base64'],validate=True)
 assert hashlib.sha256(png).hexdigest()==sha(p/'original.png')==event['data']['image_sha256']
 native=json.loads((p/'native-request.json').read_bytes())
 assert native['state']==contract['state'] and native['questions']=={'usable':{'type':'choice','instructions':contract['question'],'criteria':contract['options']}}
 assert len(native['images'])==1 and native['images'][0]['sha256']==sha(p/'original.png')
 traces=json.loads((p/'forward-trace.json').read_bytes());assert len(traces)==1
 trace=traces[0];assert trace['past_key_values']is None and trace['use_cache']is False
 tensors=torch.load(p/'actual-forward-inputs.pt',map_location='cpu',weights_only=True)
 tensorchecks=[]
 for name,tensor in tensors.items():
  assert list(tensor.shape)==trace[name]['shape']and str(tensor.dtype)==trace[name]['dtype']
  digest=hashlib.sha256(tensor.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()
  assert digest==trace[name]['sha256'];tensorchecks.append({'name':name,'sha256':digest,'shape':list(tensor.shape)})
 assert {'input_ids','pixel_values','image_grid_thw'}<=set(tensors)
 response=json.loads((p/'response.json').read_bytes());audit=json.loads((p/'audit.json').read_bytes())
 assert response['request_sha256']==sha(p/'wire-request.bin')and response['decision']==event['data']['decision']
 assert response['decision']==max(audit['probabilities'],key=audit['probabilities'].get)
 assert response['contract_sha256']==sha(root/'flash/gate-contract.json')
 flash.append({**proof,'response':response,'probabilities':audit['probabilities'],'input_tensors':tensorchecks,'zero_cross_request_KV':True,'native_question_count':1})
p=Path(SELECTED['reply']['data']['receipt']);mainproof=verify(p)
wire=json.loads((p/'wire-request.bin').read_bytes());body=json.loads((p/'body.json').read_bytes());template=json.loads((root/'actor-template.json').read_bytes())
assert wire['body']==body and wire['request_id']==SELECTED['request']['data']['request_id']
assert wire['run_id']==SELECTED['run_id']and wire['decision_index']==SELECTED['attack']['data']['step']
assert {k:v for k,v in body.items()if k!='messages'}=={k:v for k,v in template.items()if k!='messages'}
assert body['messages'][0]==template['messages'][0]and body['max_tokens']==2048
image_hashes=[]
for message in body['messages']:
 if not isinstance(message.get('content'),list):continue
 for block in message['content']:
  if block['type']=='image_url':image_hashes.append(hashlib.sha256(base64.b64decode(block['image_url']['url'].split(',',1)[1],validate=True)).hexdigest())
assert image_hashes[-1]==SELECTED['yes']['data']['image_sha256']
assert SELECTED['no']['data']['image_sha256']not in image_hashes
prepared=json.loads((p/'prepared.json').read_bytes());first=json.loads((p/'first-forward.json').read_bytes())
for name,row in prepared.items():
 assert sha(p/row['file'])==row['sha256']
 assert all(first[name][k]==row[k]for k in ['shape','dtype','bytes','sha256'])
 assert sha(p/first[name]['file'])==first[name]['sha256']
generation=json.loads((p/'actual-generation.json').read_bytes());effective=json.loads((p/'effective-generation.json').read_bytes())
assert generation['natural_EOS']and generation['output_tokens']<=2048
eos=effective['eos_token_id'];eos=[eos]if isinstance(eos,int)else eos
assert generation['output_ids'][-1]in eos and effective['max_new_tokens']==2048
seqfile=p/'sequence_ids.tensor';raw=seqfile.read_bytes();sequence=list(struct.unpack('<'+str(len(raw)//8)+'q',raw))
ids=(p/prepared['input_ids']['file']).read_bytes();inputids=list(struct.unpack('<'+str(len(ids)//8)+'q',ids))
assert sequence[:len(inputids)]==inputids and sequence[len(inputids):]==generation['output_ids']
response=json.loads((p/'response.json').read_bytes())
assert response['request_sha256']==sha(p/'wire-request.bin')
assert hashlib.sha256(response['text'].encode()).hexdigest()==SELECTED['reply']['data']['text_sha256']
prior=p.parent/'00001';prior_body=json.loads((prior/'body.json').read_bytes());prior_response=json.loads((prior/'response.json').read_bytes())
assert body['messages'][:len(prior_body['messages'])]==prior_body['messages']
assert body['messages'][len(prior_body['messages'])]=={'role':'assistant','content':prior_response['text']}
assert len(body['messages'])==len(prior_body['messages'])+2
loaded=json.loads((p.parent.parent/'loaded.json').read_bytes());assert loaded['dtype']=='bfloat16'and loaded['attention']=='sdpa'
assert loaded['physical_gpus']==list(range(7))and loaded['native_generate_unchanged']
assert not torch.cuda.is_initialized()
print(json.dumps({'time':time.time(),'selected':SELECTED,'Flash_actual_request_forward_proofs':flash,
 'primary_actual_request_forward_proof':{**mainproof,'original_system_parameters_and_full_history_retained':True,'input_image_sha256s':image_hashes,'rejected_whiteout_absent_from_main':True,'prepared_first_forward_equal':True,'input_tokens':generation['input_tokens'],'output_tokens':generation['output_tokens'],'natural_EOS':True,'text':response['text'],'loaded_dtype':loaded['dtype'],'loaded_physical_gpus':loaded['physical_gpus']},
 'actual_NO_then_fresh_YES_then_native_action_verified':True,'Mirage_reduction_proven':False,'no_new_inference_in_audit':True,'audit_CUDA_initialized':False}))
'''
    raw, op = remote('3090', code, 'audit-first-real-injection-NO-recapture-YES-native-forward', timeout=55)
    result = json.loads(raw)
    root = HERE / ('first-interception-audit-' + str(time.time_ns())); root.mkdir()
    save(root / 'audit.json', {'operation': str(op), 'result': result})
    members = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir() if p.is_file()}
    save(root / 'seal.json', members)
    save(HERE / 'first-interception-current.json', {'root': str(root),
        'seal_sha256': hashlib.sha256((root / 'seal.json').read_bytes()).hexdigest(),
        'real_injection_intercept_and_recovery': True, 'Mirage_reduction_proven': False})
    print(json.dumps({'receipt': str(root), 'real_NO_fresh_YES_native_action': True,
        'whiteout_not_in_primary': True, 'main_text': result['primary_actual_request_forward_proof']['text'],
        'Flash_probabilities': [r['probabilities'] for r in result['Flash_actual_request_forward_proofs']],
        'new_inference_in_audit': 0, 'Mirage_reduction_proven': False}))


if __name__ == '__main__': main()
