"""CPU-only audit of the four new real wire/forward/reply bindings."""
import base64,hashlib,json,os,sys,time,urllib.error,urllib.request
from pathlib import Path
os.environ['CUDA_VISIBLE_DEVICES']=''
import torch
from gate_core import canonical,digest
from resource_guard import sha,identity,LEASE
from flash_runtime import save
from wire_contract import decode_request,REVISION

def chain(path):
    head='0'*64;count=0;kinds={};rows=[]
    for raw in path.read_bytes().splitlines():
        v=json.loads(raw);h=v.pop('sha256');assert v['seq']==count and v['previous']==head and digest(canonical(v))==h
        head=h;count+=1;kinds[v['kind']]=kinds.get(v['kind'],0)+1;rows.append(v)
    return {'head':head,'events':count,'kinds':kinds},rows

def main(root):
    out=root/'audits'/str(time.time_ns());out.mkdir(parents=True)
    config=json.loads((root/'service-config.json').read_bytes());contract=json.loads((root/'gate-contract.json').read_bytes());service=root/'service'
    for name,h in json.loads((root/'package-manifest.json').read_bytes()).items():assert sha(root/name)==h
    proc=json.loads((service/'process.json').read_bytes());actual=identity(proc['pid'])
    assert all(actual[k]==proc[k]for k in ['uid','command','start_ticks'])and actual['state']not in['Z','X']and proc['visible_devices']=='7'
    lease=json.loads(LEASE.read_bytes());holder=lease['holder'];holder_actual=identity(holder['pid']);assert all(holder_actual[k]==holder[k]for k in ['uid','command','start_ticks'])
    locks=[]
    for row in lease['lock_records']:
        p=Path('/proc',str(proc['pid']));fd=p/'fd'/str(row['fd'])
        assert os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']and 'WRITE '+str(holder['pid'])in(p/'fdinfo'/str(row['fd'])).read_text();locks.append(row)
    token=(service/'token').read_text().strip()
    def request(path,body=None):
        r=urllib.request.Request('http://127.0.0.1:18341'+path,data=body,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        with urllib.request.urlopen(r,timeout=45)as response:return json.load(response)
    health=request('/health');assert health['complete_replies']==health['attempted_calls']==4 and health['retained_context_entries']==0
    decisions=json.loads((root/'integration-preflight/decisions.json').read_bytes());assert len(decisions)==4
    rows=[];temp=json.loads((Path(config['model_dir'])/'decision_config.json').read_bytes())['temperature']
    for decision in decisions:
        rid=decision['request_id'];d=service/'requests'/rid;seal=json.loads((d/'seal.json').read_bytes());assert all(sha(d/k)==h for k,h in seal.items())
        wire=(d/'wire-request.bin').read_bytes();req,png=decode_request(wire);response=json.loads((d/'response.json').read_bytes())
        assert png==(d/'original.png').read_bytes()and sha(d/'original.png')==decision['image_sha256']
        assert response['request_id']==req['request_id']==rid and response['request_sha256']==digest(wire)and response['image_sha256']==req['image_sha256']
        assert response['contract_sha256']==sha(root/'gate-contract.json')and response['revision']==REVISION and response['decision']==decision['value']
        native=json.loads((d/'native-request.json').read_bytes());assert native['state']==contract['state']and len(native['images'])==1 and native['images'][0]['sha256']==digest(png)
        assert native['questions']=={'usable':{'type':'choice','instructions':contract['question'],'criteria':contract['options']}}
        trace=json.loads((d/'forward-trace.json').read_bytes());assert len(trace)==1 and trace[0]['past_key_values']is None and trace[0]['use_cache']is False
        inputs=torch.load(d/'actual-forward-inputs.pt',map_location='cpu',weights_only=True)
        for k,v in inputs.items():
            record=trace[0][k];v=v.contiguous()
            assert list(v.shape)==record['shape']and str(v.dtype)==record['dtype']and digest(v.view(torch.uint8).numpy().tobytes())==record['sha256']
            if 'values'in record:assert v.tolist()==record['values']
        assert inputs['input_ids'].shape[0]==1 and inputs['image_grid_thw'].shape[0]==1
        text=(d/'actual-input-text.txt').read_text();assert 'All main history retained'not in text and 'Original current task sentinel'not in text and contract['question']in text
        raw=json.loads((d/'raw-readout.json').read_bytes());assert len(raw)==1
        # Rebuild the complete unmasked native head output, verify its byte
        # digest, then apply publisher temperature once to the two valid slots.
        head=torch.tensor(raw[0]['values'],dtype=getattr(torch,raw[0]['dtype'].split('.')[-1]))
        assert list(head.shape)==raw[0]['shape']and digest(head.contiguous().view(torch.uint8).numpy().tobytes())==raw[0]['sha256']
        probs=(head[0,:2].float()/float(temp)).softmax(-1).tolist();native_result=json.loads((d/'native-result.json').read_bytes());answer=native_result['answers']['usable'];audit=json.loads((d/'audit.json').read_bytes())
        assert all(abs(answer['probabilities'][k]-probs[i])<2e-6 for i,k in enumerate(contract['options']))and answer['probabilities']==audit['probabilities']
        assert answer['choice']==response['decision']==max(answer['probabilities'],key=answer['probabilities'].__getitem__)
        for name in ['admission-before.json','admission-after.json']:
            admission=json.loads((d/name).read_bytes());uuid=admission['gpu']['7']['uuid'];pids={r['pid']for r in admission['compute']if r['uuid']==uuid};assert pids=={proc['pid']}
        rows.append({'request_id':rid,'decision':response['decision'],'image_sha256':digest(png),'input_tokens':inputs['input_ids'].shape[1],'grid':inputs['image_grid_thw'].tolist(),'probabilities_audit_only':answer['probabilities'],'elapsed_seconds_with_capture':audit['elapsed_seconds_with_input_capture'],'peak_allocated_bytes':audit['memory']['peak_allocated_bytes'],'actual_runtime_tensor_bytes_verified':True,'raw_scores_verified':True,'seal_sha256':sha(d/'seal.json')})
    journal,journal_rows=chain(service/'journal/events.jsonl');assert journal['events']==health['journal_events']and journal['head']==health['journal_head']
    assert journal['kinds']=={'loaded':1,'request_received':4,'request_sealed':4}
    for row in journal_rows:
        if row['kind']=='request_sealed':assert row['data']['seal_sha256']==sha(service/'requests'/row['data']['request_id']/'seal.json')
    for case in ['forward-fixture','cancellation-fixture']:
        c,_=chain(root/'integration-preflight'/case/'events.jsonl');save(out/(case+'-journal.json'),c)
    fixture=root/'integration-preflight';assert all(sha(fixture/n)==h for n,h in json.loads((fixture/'seal.json').read_bytes()).items())
    terminal=json.loads((fixture/'terminal.json').read_bytes());assert terminal['status']=='passed'
    # HTTP negative controls cannot execute the model or use old reply cache.
    wire=(service/'requests'/decisions[0]['request_id']/'wire-request.bin').read_bytes();invalid=json.loads(wire);invalid['history']='forbidden main history'
    rejections=[]
    for body,expected in [(json.dumps(invalid).encode(),400),(wire,409)]:
        try:request('/decision',body);raise AssertionError('Illegal or duplicate request accepted')
        except urllib.error.HTTPError as e:assert e.code==expected;rejections.append({'status':e.code,'body':json.load(e),'new_model_call':False})
    after=request('/health');assert after['complete_replies']==after['attempted_calls']==4 and after['journal_head']==health['journal_head']
    tensors=json.loads((service/'actual-tensors.json').read_bytes());assert all(t['device']=='cuda:0'for t in tensors)
    result={'status':'passed','time':time.time(),'service_actual_identity':actual,'holder_actual_identity':holder_actual,'inherited_held_locks':len(locks),'physical_gpu':7,'revision':REVISION,'contract_sha256':sha(root/'gate-contract.json'),'new_Flash_calls_verified':4,'requests':rows,'journal':journal,'HTTP_rejections_no_new_inference':rejections,'health':after,'actual_dtype_elements':{dtype:sum(t['elements']for t in tensors if t['dtype']==dtype)for dtype in sorted({t['dtype']for t in tensors})},'main_model_calls':0,'environment_actions':0,'Mirage_reduction':None,'new_model_calls_by_auditor':0,'GPU_allocations_by_auditor':0}
    assert not torch.cuda.is_initialized()
    save(out/'audit.json',result);save(out/'seal.json',{p.name:sha(p)for p in out.iterdir()if p.is_file()})
    print(json.dumps({'status':'passed','audit_root':str(out),'verified_calls':4,'journal':journal}))
if __name__=='__main__':main(Path(sys.argv[1]))
