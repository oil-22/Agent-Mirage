"""Unchanged pinned native Decider, one question/one image/no KV per call."""
import io,json,sys,time
from pathlib import Path
from gate_core import digest
from resource_guard import admit,checkpoint
from wire_contract import native_request

def save(p,v):
    with p.open('x',encoding='utf8')as f:json.dump(v,f,ensure_ascii=False,indent=2)
class FlashRuntime:
    def __init__(self,root,config,contract):
        self.root=root;self.config=config;self.contract=contract;self.trace=[];self.copies=[];self.readout=[]
        save(root/'admission-before-load.json',admit(config,False));before=checkpoint(config,root.parent);save(root/'checkpoint-before.json',before)
        import torch,transformers
        from PIL import Image
        self.torch=torch;self.Image=Image
        torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        model=Path(config['model_dir']);sys.path.insert(0,str(model/'source/src'))
        from pplx_decider import Decider
        import pplx_decider.model as native
        if Path(native.__file__).resolve()!=model/'source/src/pplx_decider/model.py':raise RuntimeError('Wrong native Flash source import')
        t=time.monotonic();self.engine=Decider.from_pretrained(model,device='cuda:0',fast=False,cpu_threads=4);torch.cuda.synchronize();load=time.monotonic()-t
        tensors=[]
        for name,module in [('backbone',self.engine.backbone),('readout',self.engine.readout)]:
            for key,v in list(module.named_parameters())+list(module.named_buffers()):
                if v.device.type!='cuda'or v.device.index!=0:raise RuntimeError('CPU/disk/meta/other-device tensor prohibited')
                tensors.append({'name':name+'.'+key,'dtype':str(v.dtype),'device':str(v.device),'elements':v.numel(),'bytes':v.numel()*v.element_size()})
        save(root/'actual-tensors.json',tensors)
        after=checkpoint(config,root.parent)
        if before!=after:raise RuntimeError('Model identity changed during load')
        save(root/'checkpoint-after-load.json',after)
        self.engine.backbone.register_forward_pre_hook(self._pre,with_kwargs=True)
        self.engine.readout.register_forward_hook(self._post)
        self.loaded={'model':config['repository'],'revision':config['revision'],'torch':torch.__version__,'transformers':transformers.__version__,'native_decision_adapter_loaded':True,'dtype':'bfloat16','attention':'sdpa/noncausal_full_attention','fast':False,'questions':1,'single_image':True,'no_cross_request_KV':True,'load_seconds':load,'tensor_count':len(tensors),'model_tensor_bytes':sum(r['bytes']for r in tensors),'memory':self.memory()}
        save(root/'loaded.json',self.loaded);save(root/'admission-after-load.json',admit(config,True))
    def memory(self):
        t=self.torch;return {'allocated_bytes':t.cuda.memory_allocated(),'reserved_bytes':t.cuda.memory_reserved(),'peak_allocated_bytes':t.cuda.max_memory_allocated(),'peak_reserved_bytes':t.cuda.max_memory_reserved()}
    def tensor(self,v,values=False):
        c=v.detach().cpu().contiguous();r={'shape':list(c.shape),'dtype':str(c.dtype),'sha256':digest(c.view(self.torch.uint8).numpy().tobytes())}
        if values:r['values']=c.tolist()
        return c,r
    def _pre(self,module,args,kwargs):
        if kwargs.get('past_key_values')is not None or kwargs.get('use_cache')is not False:raise RuntimeError('Independent no-KV forward required')
        row={'past_key_values':None,'use_cache':False};copies={}
        for k,v in kwargs.items():
            if isinstance(v,self.torch.Tensor):
                c,r=self.tensor(v,k in ['input_ids','image_grid_thw']);row[k]=r;copies[k]=c
        if not {'input_ids','pixel_values','image_grid_thw'}<=row.keys()or row['input_ids']['shape'][0]!=1 or row['image_grid_thw']['shape'][0]!=1:raise RuntimeError('One full multimodal input required')
        self.trace.append(row);self.copies.append(copies)
    def _post(self,module,args,value):self.readout.append(self.tensor(value,True)[1])
    def decide(self,png,directory):
        image=self.Image.open(io.BytesIO(png));image.load()
        if image.format!='PNG'or image.width*image.height>4194304:raise ValueError('Original PNG exceeds native deployment source limit; never crop it')
        self.trace.clear();self.copies.clear();self.readout.clear();self.torch.cuda.reset_peak_memory_stats()
        req=native_request(self.contract,image)
        save(directory/'native-request.json',{**req,'images':[{'sha256':digest(png),'size':list(image.size)}]})
        try:
            t=time.monotonic();result=self.engine.decide(req);self.torch.cuda.synchronize();elapsed=time.monotonic()-t
            if len(self.trace)!=1 or len(self.readout)!=1 or len(self.copies)!=1:raise RuntimeError('Unexpected native forward/readout count')
            save(directory/'native-result.json',result);save(directory/'forward-trace.json',self.trace);save(directory/'raw-readout.json',self.readout)
            self.torch.save(self.copies[0],directory/'actual-forward-inputs.pt')
            text=self.engine.processor.tokenizer.decode(self.copies[0]['input_ids'][0].tolist(),skip_special_tokens=False)
            with (directory/'actual-input-text.txt').open('x',encoding='utf8')as f:f.write(text)
            answer=result['answers']['usable'];prob=answer['probabilities']
            if set(prob)!={'YES','NO'}or answer['choice']!=max(prob,key=prob.__getitem__):raise RuntimeError('Native binary choice mismatch')
            return answer['choice'],{'probabilities':prob,'native_result':result,'input_tokens':self.trace[0]['input_ids']['shape'][1],'output_tokens':0,'elapsed_seconds_with_input_capture':elapsed,'memory':self.memory(),'image_grid_thw':self.trace[0]['image_grid_thw']['values']}
        finally:
            # A failed forward still keeps every actual tensor/score captured
            # before the failure. Do not replace it by a fabricated model NO.
            for name,value in [('forward-trace.json',self.trace),('raw-readout.json',self.readout)]:
                if not (directory/name).exists():save(directory/name,value)
            if self.copies and not (directory/'actual-forward-inputs.pt').exists():self.torch.save(self.copies[0],directory/'actual-forward-inputs.pt')
            # Weights stay loaded; current input tensors/results are not a next-call context.
            self.trace.clear();self.copies.clear();self.readout.clear()
