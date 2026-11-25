"""CPU transport/lifecycle controls. No model, inference, or GUI success claims."""
import hashlib
import io
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE/'source'),str(HERE)]
from PIL import Image
import image_evidence as contract
from evidence_observer import NeutralEvidenceObserver
from stateless_boundary import StatelessAuxiliaryBoundary

root=HERE/('CPU-boundaries-'+str(time.time_ns()));root.mkdir()
def image(color):
    raw=io.BytesIO();Image.new('RGB',(24,24),color).save(raw,format='PNG');return raw.getvalue()
images=[image('purple'),image('orange')]
seen=[]
reading={'schema_version':'image-evidence-v2-compact','coordinate_space':'normalized_1000',
 'frame':{'kind':'gui','summary':'Synthetic transport-only control','limitations':[]},
 'text_spans':[],'elements':[],'uncertain_regions':[]}
def backend(request):
    contract.validate_image_only_request(request);seen.append(request)
    return {'request_sha256':contract.digest(contract.canonical(request)),
        'image_sha256':request['image_sha256'],'model':request['model'],'revision':request['revision'],
        'raw_output':json.dumps(reading),'natural_eos':True}
observer=NeutralEvidenceObserver(backend,model='Qwen/Qwen3.5-9B',
 revision='c202236235762e1c871ad0ccb60c8ee5ba337b9a',enabled=True,max_calls=3)
observer.packet(images[0]);observer.packet(images[0]);observer.packet(images[1])
assert observer.calls==3 and len(seen)==3 and seen[0]==seen[1]
assert 'terminals' not in vars(observer)
budget=observer.packet(images[0]);assert budget['status']=='unavailable_budget_exhausted'and len(seen)==3
assert all(set(v)==set(seen[0])for v in seen)

class Cache:
    def __init__(self,n):self.n=n
    def get_seq_length(self):return self.n
class Handle:
    def __init__(self,model,hook):self.model,self.hook=model,hook
    def remove(self):self.model.hooks.remove(self.hook)
class Model:
    def __init__(self):self.hooks=[];self.model=SimpleNamespace(rope_deltas=None);self._cache=None
    def register_forward_pre_hook(self,hook,with_kwargs):
        assert with_kwargs;self.hooks.append(hook);return Handle(self,hook)
    def forward(self,n):
        for hook in self.hooks:hook(self,(),{'past_key_values':Cache(n)})
        self.model.rope_deltas=object()
class Processor:
    def apply_chat_template(self,messages,*args,**kwargs):return {'new_context':True}
aux,primary,processor=Model(),Model(),Processor()
for index,raw in enumerate(images):
    target=root/('independent-call-%d'%index);target.mkdir()
    with StatelessAuxiliaryBoundary(aux,processor,raw,contract.FIXED_PROMPT,target):
        processor.apply_chat_template([{'role':'user','content':[
            {'type':'image','image':Image.open(io.BytesIO(raw))},
            {'type':'text','text':contract.FIXED_PROMPT}]}],tools=None)
        aux.forward(0);aux.forward(5)
    assert aux.model.rope_deltas is None and aux._cache is None
    assert primary.model.rope_deltas is None and primary._cache is None

negative=[]
for name in ['history-message','nonempty-past-state']:
    target=root/name;target.mkdir()
    try:
        with StatelessAuxiliaryBoundary(aux,processor,images[0],contract.FIXED_PROMPT,target):
            messages=[{'role':'user','content':[{'type':'image','image':Image.open(io.BytesIO(images[0]))},
                {'type':'text','text':contract.FIXED_PROMPT}]}]
            if name=='history-message':messages.insert(0,{'role':'assistant','content':'Previous auxiliary context'})
            processor.apply_chat_template(messages,tools=None)
            aux.forward(1)
    except RuntimeError as e:
        negative.append({'case':name,'rejected':True,'reason':str(e)})
    else:raise AssertionError('Forbidden cross-call state accepted')
assert len(negative)==2
result={'passed':True,'time':time.time(),'CPU_mock_controls_only':True,
 'same_image_invocations_call_backend_separately':True,'transport_inputs_image_prompt_only':True,
 'output_memoization_removed':True,'budget_boundary_preserved':True,
 'independent_lifecycle_mock_calls':2,'negative_controls':negative,
 'main_context_untouched':True,'actual_GPU_forward_empty_cache_proof_still_pending':True,
 'new_real_model_GUI_scorer_paid_calls':0,'defense_efficacy_or_semantic_pass':False}
(root/'receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(root/'seal.json').write_text(json.dumps({p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
 for p in root.rglob('*')if p.is_file()},indent=2)+'\n',encoding='utf8')
print(json.dumps({'root':str(root),'passed':True,'backend_mock_calls':3,'lifecycle_mock_calls':2,
 'forbidden_context_rejected':2,'actual_model_GUI_calls':0}))
