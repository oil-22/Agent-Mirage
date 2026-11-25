"""Audit two already-delivered calls, without a new forward or GPU allocation."""
import json
import time
from control import HERE, R3090, remote, save, sha

snapshot = HERE / 'live-evidence-1794649695787169300'
model = json.loads((snapshot / '3090.json').read_bytes())
gui = json.loads((snapshot / '4090.json').read_bytes())
forwarded = gui['controllers'][0]['forwarded_images']
assert len(forwarded) == 2 and forwarded[0]['image_sha256'] == forwarded[1]['image_sha256']
fresh_after_click = gui['controllers'][0]['environment_actions'][0]
assert fresh_after_click['payload'] == {'type': 'click', 'x': 302, 'y': 419}
assert fresh_after_click['ok'] and fresh_after_click['current_capture_sha256'] == '564e7a79f977e2d647625301b9539e73027467dad75a59a85eda7bb8f6f66848'
selected = [row['gate_request_id'] for row in forwarded]
code = 'PACKAGE=' + repr(R3090) + '\nIDS=' + repr(selected) + '\n' + r'''
import hashlib,json,time,torch
from pathlib import Path
p=Path(PACKAGE)/'flash/service/requests'
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
rows=[];tensors=[];heads=[]
for rid in IDS:
 d=p/rid;seal=json.loads((d/'seal.json').read_bytes())
 for name,expected in seal.items():assert sha(d/name)==expected,name
 trace=json.loads((d/'forward-trace.json').read_bytes())
 assert len(trace)==1 and trace[0]['past_key_values']is None and trace[0]['use_cache']is False
 tensors.append(torch.load(d/'actual-forward-inputs.pt',map_location='cpu',weights_only=True))
 head=torch.load(d/'raw-head.pt',map_location='cpu',weights_only=True);heads.append(head)
 response=json.loads((d/'response.json').read_bytes())
 rows.append({'request_id':rid,'decision':response['decision'],'image_sha256':response['image_sha256'],'seal_sha256':sha(d/'seal.json'),'native_input_ids_sha256':trace[0]['input_ids']['sha256']})
assert tensors[0].keys()==tensors[1].keys()
checks=[]
for key in tensors[0]:
 a=tensors[0][key];b=tensors[1][key]
 assert isinstance(a,torch.Tensor)and isinstance(b,torch.Tensor),key
 assert a.dtype==b.dtype and a.shape==b.shape and torch.equal(a.view(torch.uint8),b.view(torch.uint8)),key
 checks.append({'name':key,'shape':list(a.shape),'dtype':str(a.dtype),'all_bytes_equal':True})
assert heads[0].dtype==heads[1].dtype and heads[0].shape==heads[1].shape and torch.equal(heads[0].view(torch.uint8),heads[1].view(torch.uint8))
assert all(row['decision']=='YES'for row in rows)
print(json.dumps({'time':time.time(),'calls':rows,'actual_forward_tensor_comparisons':checks,'raw_native_head_bytes_equal':True,'past_key_values_none_and_use_cache_false':True,'new_forward_calls':0,'new_GPU_allocations':0}))
'''
raw, operation = remote('3090', code, 'CPU-existing-same-PNG-freshness-boundary-audit')
result = json.loads(raw)
result.update({'source_live_snapshot': str(snapshot), 'source_live_snapshot_seal_sha256': sha(snapshot / 'seal.json'),
               'actual_current_after_click_SHA': fresh_after_click['current_capture_sha256'],
               'forwarded_both_times_SHA': forwarded[0]['image_sha256'],
               'interpretation': 'The identical current screenshot can be a fresh observation before click and a stale observation after click. Single-image/context-free usability inputs and raw outputs are equal for this pair; readability YES does not certify freshness.',
               'semantic_Mirage_occurrence_from_this_audit': None,
               'overall_effect_estimate': None, 'protocol_changed': False})
receipt = HERE / ('same-PNG-freshness-boundary-' + str(time.time_ns()) + '.json')
save(receipt, {'result': result, 'operation': str(operation)})
print(json.dumps({'receipt': str(receipt), 'calls_audited': 2, 'all_forward_tensors_and_raw_heads_equal': True,
                  'both_decisions': 'YES', 'new_inference': 0, 'protocol_changed': False}))
