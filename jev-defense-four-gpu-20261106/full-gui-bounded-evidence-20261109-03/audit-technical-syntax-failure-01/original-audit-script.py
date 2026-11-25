"""Audit the closed first track while later finite tracks keep running."""
import json
import time
from remote_control import HERE, ROOT3090, ROOT4090, remote, save, sha

TRACK='bounded9b-fullgui-20261109-03--classifieds_112--clean--joint--no-observer'

SERVICE='ROOT='+repr(ROOT3090)+'\nTRACK='+repr(TRACK)+'\n'+r'''
from pathlib import Path
import base64,collections,hashlib,json,struct,sys,time
root=Path(ROOT);r=root/'worker';package=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/full-gui-bounded-evidence-20261109-03')
sys.path[:0]=[str(package),str(package/'release')]
from defense.core import PublicView,VisibleImage
from defense.qwen_backend import QwenBackend

def digest(raw):return hashlib.sha256(raw).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()

class Capture:
 def generate(self,messages,*args,**kwargs):return digest(canonical(messages))

calls=[];counts=collections.Counter();tokens=collections.defaultdict(lambda:{'input':0,'output':0,'seconds_including_instrumentation':0.0})
for folder in sorted((r/'requests').iterdir()):
 if not(folder/'external-wire.json').exists():continue
 raw=(folder/'external-wire.json').read_bytes();body=json.loads(raw)
 if body['trajectory_id']!=TRACK:continue
 assert(folder/'seal.json').exists()and not(folder/'failure.json').exists()
 seal=json.loads((folder/'seal.json').read_bytes())
 for name,expected in seal.items():assert sha(folder/name)==expected,(folder,name)
 payload=json.loads((folder/'payload.json').read_bytes());response=json.loads((folder/'response.json').read_bytes())
 assert payload==body['payload']and response['request_id']==body['request_id']
 assert response['external_wire_sha256']==digest(raw)and response['payload_sha256']==digest(canonical(payload))
 op=response['operation'];assert op in {'actor','judge'}
 prepared=json.loads((folder/'prepared.json').read_bytes());forward=json.loads((folder/'first-forward.json').read_bytes());assert set(prepared)==set(forward)
 for name in prepared:
  assert all(prepared[name][key]==forward[name][key]for key in ['shape','dtype','bytes','sha256']),name
 actual=json.loads((folder/'actual-generation.json').read_bytes());native=json.loads((folder/'native-call.json').read_bytes())
 assert native['generated_ids']==actual['output_ids']and len(native['input_ids'])==actual['input_tokens']
 assert prepared['input_ids']['dtype']=='torch.int64'
 assert digest(struct.pack('<'+'q'*len(native['input_ids']),*native['input_ids']))==prepared['input_ids']['sha256']
 cfg=native['generation_config'];eos=cfg['eos_token_id'];eos=[eos]if isinstance(eos,int)else eos
 assert actual['natural_EOS']==bool(actual['output_ids']and actual['output_ids'][-1]in eos)
 assert actual['natural_EOS']and not native['hit_output_cap']
 assert cfg['max_new_tokens']==(2048 if op=='actor'else4096)and cfg['do_sample']is False
 if op=='actor':
  expected_messages=digest(canonical(payload['body']['messages']))
  assert native['verifier_grammar']is None and response['text']==native['text']
 else:
  v=payload['view'];view=PublicView(v['observation_id'],v['messages'],tuple(VisibleImage(base64.b64decode(x['raw_base64']),x['role'])for x in v['images']),v['recent_action'],v['execution_feedback'],v['observed_at'])
  expected_messages=QwenBackend.judge(Capture(),payload['system'],view,payload['candidate'])
  assert native['verifier_grammar']is not None and response['verdict']==native['text']
 assert native['request_messages_sha256']==expected_messages
 counts[op]+=1;tokens[op]['input']+=actual['input_tokens'];tokens[op]['output']+=actual['output_tokens'];tokens[op]['seconds_including_instrumentation']+=response['seconds_including_instrumentation']
 calls.append({'request_id':body['request_id'],'operation':op,'folder':folder.name,'wire_sha256':digest(raw),'payload_sha256':response['payload_sha256'],
  'response_sha256':sha(folder/'response.json'),'seal_sha256':sha(folder/'seal.json'),'sealed_original_files':len(seal),'natural_EOS':actual['natural_EOS'],
  'actual_CPU_first_forward_metadata_identical':True,'native_input_generated_IDs_and_original_messages_SHA_verified':True})
assert dict(counts)=={'judge':39,'actor':10}and len(calls)==49
print(json.dumps({'time':time.time(),'read_only':True,'new_model_HTTP_GUI_calls':0,'track':TRACK,'calls':calls,'counts':dict(counts),'tokens':dict(tokens),
 'sealed_original_request_files_verified':sum(c['sealed_original_files']for c in calls),'raw_tensor_bytes_remain_remote':True,'all49_requests_EOS':True,'no_model_constructor_or_generate_called_by_this_audit':True}))
'''

GUI='ROOT='+repr(ROOT4090)+'\nTRACK='+repr(TRACK)+'\nPROOF='+repr({})+'\n'

def main():
    out,service_operation=remote('3090',SERVICE,'audit-closed-first-track-49-actual-inputs-and-seals',timeout=55)
    service=json.loads(out)
    proof={row['request_id']:row for row in service['calls']}
    code='ROOT='+repr(ROOT4090)+'\nTRACK='+repr(TRACK)+'\nPROOF='+repr(proof)+'\n'+r'''
from pathlib import Path
import base64,hashlib,json,time
r=Path(ROOT);run=r/'batch/runs'/TRACK;pointer=json.loads((run/'complete.json').read_bytes());a=Path(pointer['attempt']);assert a.parent==run
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(a/'complete.json')==pointer['sha256'];terminal=json.loads((a/'complete.json').read_bytes());terminal.pop('calls',None)
raw=(a/'events.jsonl').read_bytes();assert raw.endswith(b'\n');previous='0'*64;events=[]
for line in raw.splitlines():
 v=json.loads(line);sig=v.pop('sha256');assert v['seq']==len(events)and v['previous']==previous
 assert hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==sig
 v['sha256']=sig;events.append(v);previous=sig
assert events[-1]['kind']=='online_run_end_response'
requests={};responses={};raw_response=None
for e in events:
 if e['kind']in {'actual_actor_wire_request','actual_judge_wire_request'}:
  d=e['data'];body=d['body'];expected=PROOF[body['request_id']];assert body['trajectory_id']==TRACK
  assert d['wire_sha256']==expected['wire_sha256']and hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==d['wire_sha256']
  requests[body['request_id']]=e['sha256']
 if e['kind']in {'actual_actor_wire_raw_response','actual_judge_wire_raw_response'}:
  raw_response=base64.b64decode(e['data']['raw_base64']);assert hashlib.sha256(raw_response).hexdigest()==e['data']['raw_sha256']and e['data']['http_status']==200
 if e['kind']in {'actual_actor_wire_response','actual_judge_wire_response'}:
  body=e['data']['body'];expected=PROOF[body['request_id']]
  assert json.loads(raw_response)==body and hashlib.sha256(raw_response).hexdigest()==expected['response_sha256']
  assert body['external_wire_sha256']==expected['wire_sha256']and body['payload_sha256']==expected['payload_sha256']
  responses[body['request_id']]=e['sha256']
assert set(requests)==set(responses)==set(PROOF)
for e in events:
 if e['kind']=='private_delivery_ledger':
  d=e['data'];assert d['condition']=='clean'and d['fired']is False
  assert sha(a/'screenshots'/('%03d-captured.png'%d['step']))==d['capture_sha256']==d['delivered_sha256']==sha(a/'screenshots'/('%03d-delivered.png'%d['step']))
hashes={p.relative_to(a).as_posix():sha(p)for p in a.rglob('*')if p.is_file()}
assert sha(a/'events.jsonl')==hashes['events.jsonl']and sha(a/'complete.json')==pointer['sha256']
print(json.dumps({'time':time.time(),'read_only':True,'new_model_HTTP_GUI_calls':0,'terminal':terminal,'terminal_sha256':pointer['sha256'],
 'chain':{'events':len(events),'head':previous},'all49_Controller_service_actual_wires_and_raw_replies_bound':True,
 'closed_track_file_SHA_snapshot':hashes,'closed_track_file_count':len(hashes),'raw_private_trajectory_and_browser_trace_retained_remote':True,
 'no_current_or_later_track_mutation':True}))
'''
    out,gui_operation=remote('4090',code,'audit-closed-first-track-controller-service-bindings',timeout=55)
    gui=json.loads(out);target=HERE/'closed-first-track-audit'/str(time.time_ns());target.mkdir(parents=True,exist_ok=False)
    save(target/'service-audit.json',service);save(target/'GUI-audit.json',gui)
    save(target/'receipt.json',{'time':time.time(),'service_operation':str(service_operation),'GUI_operation':str(gui_operation),
        'service_audit_sha256':sha(target/'service-audit.json'),'GUI_audit_sha256':sha(target/'GUI-audit.json'),
        'goal':'active','efficacy_established':False,'reviewed_candidates_so_far':9,'candidate10_semantics_unreviewed_at_this_join':True,'models_HTTP_GUI_calls':0})
    save(target/'seal.json',{p.name:sha(p)for p in target.iterdir()if p.is_file()})
    print(json.dumps({'root':str(target),'counts':service['counts'],'tokens':service['tokens'],'request_original_files_SHA_verified':service['sealed_original_request_files_verified'],
        'GUI_terminal':gui['terminal'],'GUI_chain':gui['chain'],'GUI_closed_files_SHA_snapshot':gui['closed_track_file_count'],'all49_wire_reply_bindings_verified':True},ensure_ascii=False))

if __name__=='__main__':main()
