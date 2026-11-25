"""CPU-only real-reply replay into unchanged actor insertion, never actor inference."""
import base64,copy,hashlib,importlib.util,json,sys
from pathlib import Path
from dataclasses import dataclass
R=Path(__file__).resolve().parent;O=R/'compact-real-reply-actor-wiring-02';O.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    with p.open('x',encoding='utf8')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
for name,source in [('image_evidence.py',R/'compact-evidence-02/image_evidence.py'),('evidence_observer.py',R/'evidence-contract/evidence_observer.py')]:
    with(O/name).open('xb')as f:f.write(source.read_bytes())
sys.path.insert(0,str(O))
from image_evidence import canonical,digest
from evidence_observer import NeutralEvidenceObserver
@dataclass
class CurrentImage:
    raw:bytes
    role:str='current'
@dataclass
class ExportView:
    messages:list
    images:tuple
    def data(self):return {'messages':self.messages,'images':[{'sha256':digest(i.raw),'role':i.role}for i in self.images]}
source=R/'source-discovery-linked03';terminal=R/'gpu-compact-four-terminal-collection-02/original/worker'
expected={};records=[];events=[];backend_calls=[]
for i,sid in enumerate(['S04','S10','S16','S19']):
    d=terminal/('r%03d'%i);q=json.loads((d/'request.original.json').read_bytes())
    expected[digest(canonical(q))]=(sid,q,(d/'raw-output.txt').read_text(encoding='utf8'),json.loads((d/'result.json').read_bytes()))
def replay_backend(request):
    key=digest(canonical(request));sid,frozen,raw,result=expected[key]
    assert request==frozen
    backend_calls.append({'id':sid,'canonical_request_sha256':key,'actual_preflight_request_raw_SHA':result['request_sha256'],'actual_preflight_raw_output_SHA':result['raw_output_sha256']})
    return {'request_sha256':key,'image_sha256':request['image_sha256'],'model':request['model'],'revision':request['revision'],'raw_output':raw,'natural_eos':result['natural_eos']}
observer=NeutralEvidenceObserver(replay_backend,model='Qwen/Qwen3.5-9B',revision='c202236235762e1c871ad0ccb60c8ee5ba337b9a',enabled=True,max_calls=4,emit=lambda k,v:events.append({'kind':k,'data':copy.deepcopy(v)}))
for i,sid in enumerate(['S04','S10','S16','S19']):
    raw=(source/(sid+'.png')).read_bytes();export=json.loads((source/(sid+'-source.json')).read_bytes());body=copy.deepcopy(export)
    # This export has archive image references. Explicitly reconstruct ONLY its
    # selected current image transport, without claiming historical wire recovery.
    selected=body['messages'][-1]['content'];blocks=[b for b in selected if b.get('type')=='image_url']
    assert len(blocks)==1 and blocks[0]['image_url']['url'].startswith('archive-image://sha256/'+digest(raw))
    blocks[0]['image_url']['url']='data:image/png;base64,'+base64.b64encode(raw).decode()
    before=copy.deepcopy(body);view=ExportView(copy.deepcopy(body['messages']),(CurrentImage(raw),))
    augmented=observer.augment(body,view)
    assert body==before and augmented['messages'][:-1]==body['messages'][:-1]
    assert augmented['messages'][-1]['content'][:-1]==body['messages'][-1]['content']
    assert {k:v for k,v in augmented.items()if k!='messages'}=={k:v for k,v in body.items()if k!='messages'}
    packet=observer.terminals[digest(canonical(expected[backend_calls[-1]['canonical_request_sha256']][1]))]
    actual=json.loads((terminal/('r%03d'%i)/'evidence-packet.json').read_bytes())
    assert {k:v for k,v in packet.items()if k!='exact_input_reuse'}==actual
    write(O/(sid+'-supplied-export-reconstruction.json'),body);write(O/(sid+'-augmented-actor-body.json'),augmented)
    records.append({'id':sid,'actual_packet_raw_SHA':actual['raw_output_sha256'],'reading_unchanged':True,
        'supplied_export_messages_preserved':True,'full_original_historical_wire_established':False,
        'actor_max_tokens':body['max_tokens'],'auxiliary_only_image_and_fixed_prompt':True})
assert len(backend_calls)==observer.calls==4
write(O/'journal.json',events)
write(O/'receipt.json',{'status':'CPU_actual_reply_actor_insertion_replay_completed','cases':records,
    'observer_source_identical_to_prior_CPU_wiring':sha(O/'evidence_observer.py')==sha(R/'evidence-contract/evidence_observer.py'),
    'compact_contract_sha256':sha(O/'image_evidence.py'),'backend_replay_calls':backend_calls,
    'canonical_request_SHA_distinct_from_pretty_preflight_file_SHA_explicitly_bound':True,
    'new_model_actor_judge_GUI_scorer_calls':0,'live_Controller_integration_proven':False,
    'full_export_not_claimed_full_original_wire':True,'formal_GUI_ready':False})
with(O/'replay_source.py').open('xb')as f:f.write(Path(__file__).read_bytes())
write(O/'seal.json',{p.name:sha(p)for p in O.iterdir()if p.is_file()})
print(json.dumps({'cases':len(records),'new_model_calls':0,'receipt_sha256':sha(O/'receipt.json'),'seal_sha256':sha(O/'seal.json')}))
