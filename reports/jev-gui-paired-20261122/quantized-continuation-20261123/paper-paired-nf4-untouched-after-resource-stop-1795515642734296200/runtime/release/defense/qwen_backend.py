"""Unquantized BF16/SDPA local27B. Original images and complete text retained."""
import base64,copy,io,json,time
from pathlib import Path
from PIL import Image
from .core import digest,canonical
from .schema import judge_schema
from .prompts import VERIFY
from .prompts import HISTORY_REPORT

class TokenReceipt:
    """Append partial verifier token chunks even if a generation later fails."""
    def __init__(self,path):
        self.file=Path(path).open('x');self.first=True;self.pending=[];self.count=0
    def put(self,value):
        if self.first:self.first=False;return
        ids=value.reshape(-1).tolist();self.pending.extend(ids);self.count+=len(ids)
        if len(self.pending)>=32:self.flush()
    def flush(self):
        if self.pending:
            self.file.write(json.dumps({'time':time.time(),'generated_count':self.count,'token_ids':self.pending})+'\n');self.file.flush();self.pending=[]
    def end(self):self.flush()
    def close(self):self.flush();self.file.close()

class LocalQwen:
    def __init__(self,model_path,runtime_path,max_memory_gib=20,placement='auto'):
        import torch,transformers
        from transformers import AutoModelForImageTextToText,AutoProcessor
        self.torch=torch
        self.processor=AutoProcessor.from_pretrained(model_path,local_files_only=True,trust_remote_code=True)
        self.model=AutoModelForImageTextToText.from_pretrained(model_path,dtype=torch.bfloat16,
            attn_implementation='sdpa',device_map=placement,
            max_memory={i:f'{max_memory_gib}GiB'for i in range(torch.cuda.device_count())},
            local_files_only=True,trust_remote_code=True).eval()
        if any(str(x)in {'cpu','disk'}for x in self.model.hf_device_map.values()):raise RuntimeError('CPU/disk offload is not the frozen27B configuration')
        assert self.model.config.text_config.num_hidden_layers==64
        assert str(self.model.dtype)=='torch.bfloat16'
        self.runtime={'model_path':str(model_path),'class':type(self.model).__name__,'dtype':str(self.model.dtype),
            'backend':'sdpa','device_map':{k:str(v)for k,v in self.model.hf_device_map.items()},
            'placement':placement,'max_memory_gib':max_memory_gib,
            'torch':torch.__version__,'transformers':transformers.__version__,
            'metadata_sha256':{n:digest((Path(model_path)/n).read_bytes())for n in ['config.json','model.safetensors.index.json','preprocessor_config.json','generation_config.json']},
            'history_truncation':False,'image_preprocessing_changes':False}
        Path(runtime_path).write_text(json.dumps(self.runtime,indent=2),encoding='utf-8')
    def generate(self,messages,max_tokens,receipt,seed=42,original_body=None,json_schema=None):
        if original_body is not None and json_schema is not None:raise ValueError('Actor generation cannot be grammar constrained')
        converted=[]
        for m in messages:
            parts=m['content']if isinstance(m['content'],list)else[{'type':'text','text':m['content']}]
            blocks=[]
            for b in parts:
                if b['type']=='text':blocks.append(copy.deepcopy(b))
                elif b['type']=='image_url':
                    url=b['image_url'];url=url['url']if isinstance(url,dict)else url
                    if not url.startswith('data:image/'):raise ValueError('Only actually delivered embedded images accepted')
                    blocks.append({'type':'image','image':Image.open(io.BytesIO(base64.b64decode(url.split(',',1)[1]))).convert('RGB')})
                else:raise ValueError('Unexpected content block')
            converted.append({'role':m['role'],'content':blocks})
        kwargs={'enable_thinking':False}if original_body is None else original_body.get('chat_template_kwargs',{})
        inputs=self.processor.apply_chat_template(converted,add_generation_prompt=True,tokenize=True,
            return_dict=True,return_tensors='pt',tools=None if original_body is None else original_body.get('tools'),**kwargs)
        cfg=copy.deepcopy(self.model.generation_config)
        cfg.do_sample=False;cfg.max_new_tokens=max_tokens
        if original_body is None:
            cfg.temperature=1.0;cfg.top_p=1.0;cfg.top_k=0
        else:
            assert original_body['temperature']==0
            assert original_body.get('chat_template_kwargs',{}).get('enable_thinking')is False
            assert not set(original_body)-{'model','temperature','max_tokens','chat_template_kwargs','messages','tools'},'Unbound generation option'
            cfg.temperature=0.0
        constrained={}
        if json_schema is not None:
            if original_body is not None:raise ValueError('Actor generation cannot be grammar constrained')
            from lmformatenforcer import JsonSchemaParser
            from lmformatenforcer.integrations.transformers import build_transformers_prefix_allowed_tokens_fn,build_token_enforcer_tokenizer_data
            if not hasattr(self,'enforcer_tokenizer_data'):
                self.enforcer_tokenizer_data=build_token_enforcer_tokenizer_data(self.processor.tokenizer)
            constrained['prefix_allowed_tokens_fn']=build_transformers_prefix_allowed_tokens_fn(self.enforcer_tokenizer_data,JsonSchemaParser(json_schema))
        stream=TokenReceipt(Path(receipt).with_name('generated-token-progress.jsonl'))if json_schema is not None else None
        if stream is not None:constrained['streamer']=stream
        self.torch.manual_seed(seed);started=time.time()
        try:
            with self.torch.inference_mode():seq=self.model.generate(**inputs.to(self.model.device),generation_config=cfg,**constrained)
        finally:
            if stream is not None:stream.close()
        ids=seq[0,inputs['input_ids'].shape[-1]:].tolist()
        text=self.processor.tokenizer.decode(ids,skip_special_tokens=True).strip()
        record={'text':text,'generated_ids':ids,'input_ids':inputs['input_ids'][0].tolist(),
            'request_messages_sha256':digest(canonical(messages)),'generation_config':cfg.to_dict(),
            'hit_output_cap':len(ids)>=max_tokens,'seconds':time.time()-started,'environment_actions_executed':False,
            'verifier_grammar':None if json_schema is None else {'engine':'lm-format-enforcer','version':'0.11.3','schema':json_schema,'schema_sha256':digest(canonical(json_schema))}}
        Path(receipt).write_text(json.dumps(record,ensure_ascii=False),encoding='utf-8')
        if record['hit_output_cap']:raise RuntimeError('Output cap hit; preserve incomplete attempt')
        return text
    def judge(self,system,view,candidate=None,receipt=None):
        # Preserve every text character and actual image; do not duplicate base64 as text.
        public=view.data();index=0
        for message in public['messages']:
            if not isinstance(message['content'],list):continue
            parts=[]
            for block in message['content']:
                if block['type']=='image_url':
                    raw=base64.b64decode((block['image_url']['url']if isinstance(block['image_url'],dict)else block['image_url']).split(',',1)[1])
                    matches=[i for i,im in enumerate(view.images)if digest(im.raw)==digest(raw)]
                    if not matches:raise ValueError('Message image missing from public image list')
                    parts.append({'type':'image_reference','image_index':matches[0]});index+=1
                else:parts.append(block)
            message['content']=parts
        blocks=[{'type':'text','text':json.dumps({'public':public,'candidate':candidate},ensure_ascii=False)}]
        for i,im in enumerate(view.images):
            blocks.append({'type':'text','text':f'Image index {i}, role {im.role}, original pixels:'})
            blocks.append({'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(im.raw).decode()}})
        phase='history_report'if system.startswith(HISTORY_REPORT)else'exact_source_reference'if system.startswith(VERIFY)else None
        text=self.generate([{'role':'system','content':system},{'role':'user','content':blocks}],4096,receipt,json_schema=judge_schema(view,candidate,phase=phase))
        # Raw reply is preserved. Controller owns bounded, explicitly logged format retries.
        return text
