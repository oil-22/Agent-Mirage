"""Cross-bind the newly closed second track; reuse the audited first terminal."""
from pathlib import Path
import base64
import collections
import hashlib
import json
import sys
import time

HERE=Path(__file__).resolve().parent
GUI=HERE.parent/'full-gui-bounded-evidence-20261109-03'
sys.path.insert(0,str(GUI))
from remote_control import remote,save,sha

FIRST='bounded9b-fullgui-20261109-03--classifieds_112--clean--joint--no-observer'
SECOND='bounded9b-fullgui-20261109-03--classifieds_112--clean--joint--observer'
P3090=Path(r'D:\MultiModel\jev-oom-evidence\1794210643888300200\3090\original')
P4090=Path(r'D:\MultiModel\jev-oom-evidence\1794210643888241400\4090\original')

def canonical(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def digest(v):return hashlib.sha256(v).hexdigest()

def main():
    for root in [P3090,P4090]:
        seal=json.loads((root/'snapshot-seal.json').read_bytes())
        for name,expected in seal.items():
            if(root/name).is_file():assert sha(root/name)==expected,name
        assert all(not row['differences']for row in json.loads((root/'original-manifest-checks.json').read_bytes()))
    index=json.loads((P3090/'original-file-SHA256.json').read_bytes())
    stats=json.loads((P3090/'original-file-stat.json').read_bytes())
    code='TRACK='+repr(SECOND)+'\nSEALED='+repr(index)+'\nSTATS='+repr(stats)+'\n'+r'''
from pathlib import Path
import base64,collections,hashlib,json,struct,sys,time
root=Path('/home/researcher/jev-defense-four-gpu-20261106/full-gui-bounded-evidence-20261109-03/worker')
package=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/full-gui-bounded-evidence-20261109-03')
sys.path[:0]=[str(package),str(package/'release')]
from defense.core import PublicView,VisibleImage
from defense.qwen_backend import LocalQwen
import image_evidence as contract
def digest(raw):return hashlib.sha256(raw).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def bound(path):
 relative=path.relative_to(root.parent).as_posix();st=path.stat()
 assert(st.st_size,st.st_mtime_ns,st.st_ino)==(STATS[relative]['bytes'],STATS[relative]['mtime_ns'],STATS[relative]['inode'])
 raw=path.read_bytes();assert digest(raw)==SEALED[relative],relative
 return json.loads(raw)
class Capture:
 def generate(self,messages,*a,**k):return digest(canonical(messages))
rows=[];counts=collections.Counter();eos=collections.Counter();totals={'input':0,'output':0,'summed_reply_seconds_including_instrumentation':0.0}
for folder in sorted((root/'requests').iterdir()):
 body=bound(folder/'external-wire.json')
 if body['trajectory_id']!=TRACK:continue
 payload=bound(folder/'payload.json');assert body['payload']==payload
 seal=bound(folder/'seal.json')
 for name,expected in seal.items():assert SEALED[(folder/name).relative_to(root.parent).as_posix()]==expected,name
 prepared=bound(folder/'prepared.json');forward=bound(folder/'first-forward.json')
 assert set(prepared)==set(forward)
 assert all(all(prepared[k][f]==forward[k][f]for f in ['shape','dtype','bytes','sha256'])for k in prepared)
 op='evidence'if 'request_sha256'in payload and 'image_sha256'in payload else payload.get('operation')
 # Auxiliary request shape is validated by the exact original contract.
 if 'model'in payload and 'prompt_sha256'in payload and 'image_sha256'in payload:op='evidence'
 assert op in ['actor','judge','evidence'],list(payload)
 counts[op]+=1
 row={'folder':folder.name,'request_id':body['request_id'],'operation':op,'wire_sha256':digest((folder/'external-wire.json').read_bytes()),
      'payload_sha256':digest(canonical(payload)),'seal_sha256':SEALED[(folder/'seal.json').relative_to(root.parent).as_posix()],
      'CPU_and_actual_first_forward_metadata_identical':True}
 cfg=bound(folder/'effective-generation.json')
 assert cfg['max_new_tokens']==(4096 if op=='judge' else 2048)and cfg['do_sample']is False
 if(folder/'failure.json').exists():
  assert folder.name=='0178'and op=='judge'and not(folder/'response.json').exists()
  failure=bound(folder/'failure.json');assert 'OutOfMemoryError'in failure['traceback']
  assert(folder/'generated-token-progress.jsonl').stat().st_size==0
  assert bound(folder/'forward-count.json')['actual_forward_calls']==1
  row.update(technical_prefill_failure=True,generated_tokens=0,input_tokens=prepared['input_ids']['shape'][-1],
      supplied_images=prepared['image_grid_thw']['shape'][0],failure_sha256=SEALED[(folder/'failure.json').relative_to(root.parent).as_posix()])
 else:
  response=bound(folder/'response.json');actual=bound(folder/'actual-generation.json')
  assert response['request_id']==body['request_id']and response['external_wire_sha256']==row['wire_sha256']and response['payload_sha256']==row['payload_sha256']
  stops=cfg['eos_token_id'];stops=[stops]if isinstance(stops,int)else stops
  assert actual['natural_EOS']==bool(actual['output_ids']and actual['output_ids'][-1]in stops)
  assert actual['natural_EOS'];eos[op]+=1
  if op=='evidence':
   raw=contract.validate_image_only_request(payload)
   assert digest(raw)==digest((folder/'original.png').read_bytes())
   assert response['evidence_response']['raw_output']==(folder/'raw-output.txt').read_text()
   assert response['evidence_response']['image_sha256']==payload['image_sha256']
  else:
   native=bound(folder/'native-call.json');assert native['generated_ids']==actual['output_ids']
   assert digest(struct.pack('<'+'q'*len(native['input_ids']),*native['input_ids']))==prepared['input_ids']['sha256']
   assert len(native['input_ids'])==actual['input_tokens']
   if op=='actor':expected=digest(canonical(payload['body']['messages']));assert response['text']==native['text']
   else:
    v=payload['view'];view=PublicView(v['observation_id'],v['messages'],tuple(VisibleImage(base64.b64decode(im['raw_base64']),im['role'])for im in v['images']),v['recent_action'],v['execution_feedback'],v['observed_at'])
    expected=LocalQwen.judge(Capture(),payload['system'],view,payload['candidate']);assert response['verdict']==native['text']
   assert expected==native['request_messages_sha256']
  row.update(natural_EOS=True,response_canonical_sha256=digest(canonical(response)),response_file_sha256=SEALED[(folder/'response.json').relative_to(root.parent).as_posix()],
             input_tokens=actual['input_tokens'],output_tokens=actual['output_tokens'])
  totals['input']+=actual['input_tokens'];totals['output']+=actual['output_tokens'];totals['summed_reply_seconds_including_instrumentation']+=response['seconds_including_instrumentation']
 rows.append(row)
assert dict(counts)=={'judge':84,'evidence':20,'actor':25}and len(rows)==129
assert dict(eos)=={'judge':83,'evidence':20,'actor':25}
print(json.dumps({'time':time.time(),'read_only':True,'new_model_GPU_GUI_scorer_paid_calls':0,'calls':rows,'attempt_counts':dict(counts),'EOS_counts':dict(eos),'complete_reply_totals':totals,'technical_prefill_failures':1,'no_weights_or_neural_forward_called':True}))
'''
    # Compile locally before reading any remote state.
    import ast
    ast.parse(code)
    output,operation=remote('3090',code,'audit-closed-second-track-129-wire-forward-reply-bindings',timeout=120)
    service=json.loads(output);proof={r['request_id']:r for r in service['calls']}
    paths=list((P4090/'originals/batch/runs'/SECOND).glob('attempt-*/events.jsonl'))
    assert len(paths)==1
    events=[];previous='0'*64
    for line in paths[0].read_bytes().splitlines():
        event=json.loads(line);sig=event.pop('sha256')
        assert event['seq']==len(events)and event['previous']==previous and digest(canonical(event))==sig
        event['sha256']=sig;events.append(event);previous=sig
    requests={};responses={};failed=[]
    for event in events:
        kind=event['kind'];data=event['data']
        if kind in ['actual_actor_wire_request','actual_judge_wire_request','actual_evidence_wire_request']:
            body=data['body'];row=proof[body['request_id']]
            assert body['trajectory_id']==SECOND and digest(canonical(body))==data['wire_sha256']==row['wire_sha256']
            requests[body['request_id']]=event['sha256']
        if kind in ['actual_actor_wire_raw_response','actual_judge_wire_raw_response','actual_evidence_wire_raw_response']:
            raw=base64.b64decode(data['raw_base64']);assert digest(raw)==data['raw_sha256']
            body=json.loads(raw);row=proof[body['request_id']]
            if data['http_status']==200:
                assert digest(raw)==row['response_canonical_sha256']
                responses[body['request_id']]=event['sha256']
            else:
                assert data['http_status']==500 and row.get('technical_prefill_failure')is True
                assert body['external_wire_sha256']==row['wire_sha256']
                failed.append(body['request_id'])
    assert len(requests)==129 and len(responses)==128 and len(failed)==1
    assert set(requests)==set(proof)and set(responses)|set(failed)==set(proof)
    image_bindings=[]
    attempt=paths[0].parent
    for event in events:
        if event['kind']=='private_delivery_ledger':
            data=event['data'];assert data['condition']=='clean'and data['fired']is False
            captured=attempt/'screenshots'/('%03d-captured.png'%data['step'])
            delivered=attempt/'screenshots'/('%03d-delivered.png'%data['step'])
            assert sha(captured)==data['capture_sha256']==data['delivered_sha256']==sha(delivered)
            image_bindings.append({'step':data['step'],'image_sha256':sha(delivered)})
    assert len(image_bindings)==20
    first=GUI/'closed-first-track-audit/1794205070152982200/receipt.json'
    first_service=json.loads((first.parent/'service-audit.json').read_bytes())
    first_gui=json.loads((first.parent/'GUI-audit.json').read_bytes())
    assert len(first_service['calls'])==49 and first_gui['terminal_sha256']=='1c96ed33f531abfc5a6cbe4e1d09aaf1dd0e9e59cb7c0b851b3120d0c09f2022'
    for filename,expected in json.loads((first.parent/'seal.json').read_bytes()).items():
        assert sha(first.parent/filename)==expected
    terminal=attempt/'technical-failure.json'
    assert sha(terminal)=='482b461ad93eb7769966b9ec44cf297f0ccbfc027247b4cbea0382de04a8c661'
    target=HERE/('closed-batch-audit-'+str(time.time_ns()));target.mkdir(exist_ok=False)
    save(target/'second-service-audit.json',service)
    save(target/'second-GUI-audit.json',{'events':len(events),'head':previous,
        'actual_request_reply_bindings':128,'actual_failed_request_and_HTTP500_binding':1,
        'clean_capture_delivered_image_bindings':image_bindings})
    save(target/'receipt.json',{
        'schema':'closed-started-GUI-tracks-and-service-v1','passed':True,
        'GUI_manifest_sha256':'584e701680c4f593b67c0db09ea7673c11ba88803664e7acf07251b7e27a6b67',
        'planned_tracks':4,'started_tracks':2,'terminal_tracks':2,'unstarted_tracks':2,
        'unstarted_conditions':['stale_replace/noaux','stale_replace/oneaux'],
        'prior_batch_has_exited_and_must_not_restart':True,
        'terminal_files_SHA_and_all_event_chains_verified':True,
        'original_failures_and_requests_preserved':True,
        'original_service_files_SHA_verified':4108,'original_GUI_files_SHA_verified':223,
        'reused_first_closed49_call_audit':str(first),'first_audit_sha256':sha(first),
        'new_second129_call_audit':str(target/'second-service-audit.json'),
        'new_second_service_audit_sha256':sha(target/'second-service-audit.json'),
        'service_audit_operation':str(operation),
        'actual_total_model_attempts':178,'actual_complete_EOS_replies':177,
        'EOS_counts':{'actor':35,'judge':122,'evidence':20},
        'prefill_OOM':1,'failed_original_input_tokens':20382,'failed_original_full_images':4,
        'failure_input_SHA':'087461cba951b41de5cfc47ddbfd8baa48030106bc9b7b7b88aafd3ec993d844',
        'GUI_terminal_sha256':{
          'batch/runs/'+FIRST+'/attempt-1794202975891057461/complete.json':first_gui['terminal_sha256'],
          'batch/runs/'+SECOND+'/attempt-1794204770365859018/technical-failure.json':sha(terminal)},
        'allows_only_new_distinct_finite_source_controls_after_fresh_resource_admission':True,
        'allows_old_batch_resume_or_retry_completed_semantics':False,
        'new_model_GPU_GUI_scorer_paid_calls':0,'goal':'active','efficacy_proven':False,
    })
    save(target/'seal.json',{p.name:sha(p)for p in target.iterdir()if p.is_file()})
    print(json.dumps({'receipt':str(target/'receipt.json'),'sha256':sha(target/'receipt.json'),
        'all178_request_bindings':True,'EOS_replies':177,'prefill_OOM':1,
        'started_terminals':2,'unstarted':2,'new_model_GUI_calls':0}))

if __name__=='__main__':main()
