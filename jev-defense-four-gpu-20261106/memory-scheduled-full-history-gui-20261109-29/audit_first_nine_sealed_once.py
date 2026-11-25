"""Audit the frozen nine-reply prefix, not a new inference or semantic test."""
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from orchestrate import OUTPUT, COMMON, remote, save, sha


def main():
    assert not (HERE / 'first-nine-prefix-audit.json').exists()
    evidence = HERE / 'actual-evidence-1794227450705900700'
    record = json.loads((evidence / '3090.json').read_bytes())
    rows = record['sealed_requests']
    assert len(rows) == 9 and [row['request'] for row in rows] == ['%04d' % n for n in range(1, 10)]
    code = 'ROOT=' + repr(OUTPUT) + '\nROWS=' + repr(rows) + '\n' + COMMON + r'''
import struct
root=Path(ROOT);results=[];totals={'input_tokens':0,'output_tokens':0,'native_call_timer_seconds':0.0}
for row in ROWS:
 path=root/'worker/requests'/row['request'];assert sha(path/'seal.json')==row['seal_sha256']
 seal=json.loads((path/'seal.json').read_bytes())
 # The prior immutable evidence verifies every binary file's full hash.
 # Here compare its metadata bindings and the native returned ID lists.
 for name in ['external-wire.json','payload.json','prepared.json','first-forward.json','effective-generation.json','actual-generation.json','native-call.json','response.json']:
  assert sha(path/name)==seal[name],name
 wire=(path/'external-wire.json').read_bytes();request=json.loads(wire);payload=request['payload']
 response=json.loads((path/'response.json').read_bytes())
 assert hashlib.sha256(wire).hexdigest()==response['external_wire_sha256']and request['request_id']==response['request_id']
 assert response['payload_sha256']==sha(path/'payload.json')or response['payload_sha256']==hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
 prepared=json.loads((path/'prepared.json').read_bytes());forward=json.loads((path/'first-forward.json').read_bytes())
 assert set(prepared)==set(forward)
 for key in prepared:
  assert all(prepared[key][field]==forward[key][field]for field in ['shape','dtype','bytes','sha256']),key
  for item in [prepared[key],forward[key]]:assert seal[item['file']]==item['sha256']
 native=json.loads((path/'native-call.json').read_bytes());actual=json.loads((path/'actual-generation.json').read_bytes());cfg=json.loads((path/'effective-generation.json').read_bytes())
 assert native['generated_ids']==actual['output_ids']and len(actual['output_ids'])==actual['output_tokens']
 assert len(native['input_ids'])==actual['input_tokens']==prepared['input_ids']['shape'][1]
 assert prepared['input_ids']['dtype']=='torch.int64'
 ids=struct.pack('<'+'q'*len(native['input_ids']),*native['input_ids'])
 assert hashlib.sha256(ids).hexdigest()==prepared['input_ids']['sha256']
 assert native['generation_config']==cfg and not native['hit_output_cap']
 assert actual['natural_EOS']and actual['output_ids'][-1]in cfg['eos_token_id']
 operation=payload['operation'];assert operation in ['actor','judge']
 assert native['text']==response['text'if operation=='actor'else'verdict']
 assert cfg['max_new_tokens']==(2048 if operation=='actor'else4096)
 images=len(payload['view']['images'])if operation=='judge'else sum(block['type']=='image_url'for message in payload['body']['messages']if isinstance(message.get('content'),list)for block in message['content'])
 results.append({'request':row['request'],'operation':operation,'decision':request['decision_index'],'original_track_attempt_index':request['attempt_index'],
  'complete_supplied_images':images,'actual_input_tokens':actual['input_tokens'],'output_tokens':actual['output_tokens'],
  'actual_prepared_first_forward_tensors_and_native_input_outputIDs_bound':True,'natural_EOS':True,
  'original_effective_generation_unchanged':True,'native_call_timer_seconds':native['seconds']})
 totals['input_tokens']+=actual['input_tokens'];totals['output_tokens']+=actual['output_tokens'];totals['native_call_timer_seconds']+=native['seconds']
assert [(row['operation'],row['original_track_attempt_index'])for row in results[:3]]==[('judge',35),('actor',12),('judge',36)]
assert [row['complete_supplied_images']for row in results if row['operation']=='actor']==[12,13]
print(json.dumps({'schema':'linked29-first-nine-actual-sealed-request-native-tensor-audit-v1','passed':True,'time':time.time(),'requests':results,'totals':totals,
 'prior_all_binary_file_SHA_evidence_bound':True,'scope':'Only9completed actual27Bcalls. Native timer includes generation instrumentation; excludes preprocessing/load/failed or ongoing work and outside-holder reservation. Not walltime/currency/energy/effect or auxiliary benefit.',
 'new_auxiliary_GPU_forward_proven':False,'new_model_GUI_scorer_paid_calls':0}))
'''
    output, operation = remote('3090', code, 'audit-frozen29-first9-request-wire-native-tensors-EOS-once', timeout=55)
    value = json.loads(output)
    out = HERE / ('first-nine-prefix-audit-' + str(time.time_ns())); out.mkdir()
    value.update(source_evidence=str(evidence), source_evidence_seal_sha256=sha(evidence / 'seal.json'), remote_operation=str(operation))
    save(out / 'audit.json', value)
    save(out / 'seal.json', {'audit.json': sha(out / 'audit.json')})
    save(HERE / 'first-nine-prefix-audit.json', {'audit': str(out / 'audit.json'), 'audit_sha256': sha(out / 'audit.json')})
    print(json.dumps({'audit': str(out / 'audit.json'), 'passed': True, 'actual_completed_calls': len(value['requests']),
        'totals': value['totals'], 'new_inference_or_GUI_calls': 0}))


if __name__ == '__main__':
    main()
