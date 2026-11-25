"""Read-only SDPA sidecar, fixed-snapshot history/timing probes. No GUI execution."""
import argparse,base64,collections,copy,hashlib,io,json,os,pathlib,re,time,traceback
import numpy as np
import torch
from PIL import Image
from transformers import AutoModelForImageTextToText,AutoProcessor
from transformers.modeling_utils import ALL_ATTENTION_FUNCTIONS
from action_audit import action_spans

GROUPS=['delivered_image','system','current_user','history_prose','history_action','history_metadata','template','generated_prefix','reference_image']
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        while b:=f.read(8*1024*1024):h.update(b)
    return h.hexdigest()
def atomic(p,obj):
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2));tmp.replace(p)
def textcontent(content):
    if isinstance(content,str):return content
    return '\n'.join(x.get('text','') for x in content if x.get('type')=='text')
def convert(messages,assets):
    out=[]
    for m in messages:
        content=m['content'];content=[{'type':'text','text':content}] if isinstance(content,str) else copy.deepcopy(content)
        converted=[]
        for item in content:
            if item.get('type')=='image_url':
                url=item['image_url']['url']
                if url.startswith('archive-image://sha256/'):
                    digest=url.rsplit('/',1)[1];matches=list(assets.glob('*/'+digest+'.*'))
                    if len(matches)!=1:raise FileNotFoundError(f'image {digest}: {matches}')
                    p=matches[0]
                    if sha(p)!=digest:raise ValueError('image hash mismatch')
                    img=Image.open(p).convert('RGB')
                elif url.startswith('data:image/'):
                    img=Image.open(io.BytesIO(base64.b64decode(url.split(',',1)[1]))).convert('RGB')
                else:raise ValueError('unsupported image URL '+url[:100])
                converted.append({'type':'image','image':img})
            else:converted.append(item)
        out.append({'role':m['role'],'content':converted})
    return out

def group_prompt(tokenizer,ids,config,request):
    decoded=tokenizer.decode(ids,skip_special_tokens=False,clean_up_tokenization_spaces=False)
    rec=tokenizer(decoded,add_special_tokens=False,return_offsets_mapping=True)
    if rec['input_ids']!=ids:
        raise ValueError('prompt decode/reencode is not exact; refusing approximate source labels')
    offsets=rec['offset_mapping'];groups=np.full(len(ids),6,np.int64)
    turns=np.full(len(ids),-1,np.int32)
    search_start=0;assistant_idx=0
    for mi,message in enumerate(request['messages']):
        txt=textcontent(message['content'])
        # Each text block is located once in its actual original order.
        blocks=[txt] if isinstance(message['content'],str) else [c['text'] for c in message['content'] if c.get('type')=='text']
        for block in blocks:
            if not block:continue
            role=message['role']
            candidates=[block]
            # Native templates remove/reformat archived assistant reasoning tags.
            # Label only the literal body actually retained in the native input;
            # do not rewrite the request or approximate token spans.
            if role=='assistant' and '</think>' in block:
                candidates.append(block.split('</think>')[-1].lstrip('\n'))
            candidates += [c.strip() for c in list(candidates) if c.strip()!=c]
            start=-1
            for candidate in candidates:
                if not candidate:continue
                start=decoded.find(candidate,search_start)
                if start>=0:block=candidate;break
            if start<0:raise ValueError(f'message {mi} role {role}: literal native body not found')
            end=start+len(block);search_start=end
            if role=='system':group=1
            elif role=='assistant':group=3
            elif mi==len(request['messages'])-1:group=2
            else:group=5
            selected=[i for i,(a,b) in enumerate(offsets) if a<end and b>start]
            groups[selected]=group
            if role=='assistant':
                turns[selected]=assistant_idx
                match=re.search(r'(?m)^Action:|```(?:python)?\s*\n|pyautogui\.|<action>',block)
                if match:
                    action_start=start+match.start()
                    groups[[i for i in selected if offsets[i][1]>action_start]]=4
            if role=='user':
                for hist in re.finditer(r'(?ms)^## step (\d+)\n(.*?)(?=^## step \d+\n|\Z)',block):
                    hs=start+hist.start();he=start+hist.end();turn=int(hist.group(1))
                    hi=[i for i,(a,b) in enumerate(offsets) if a<he and b>hs]
                    groups[hi]=3;turns[hi]=turn
                    for action in re.finditer(r'(?s)<action>.*?</action>',hist.group()):
                        astart=hs+action.start();aend=hs+action.end()
                        groups[[i for i in hi if offsets[i][0]<aend and offsets[i][1]>astart]]=4
        if message['role']=='assistant':assistant_idx+=1
    image_id=config.image_token_id
    image_positions=np.flatnonzero(np.asarray(ids)==image_id)
    groups[image_positions]=0
    image_count=sum(item.get('type')=='image_url' for m in request['messages'] if isinstance(m['content'],list) for item in m['content'])
    if image_count>1:
        clusters=np.split(image_positions,np.flatnonzero(np.diff(image_positions)>1)+1)
        if len(clusters)!=image_count:raise ValueError('cannot exactly distinguish current and reference image clusters')
        for cluster in clusters[:-1]:groups[cluster]=8
    return groups,turns,decoded,offsets

class Collector:
    def __init__(self):self.active=False;self.frames=collections.defaultdict(list)
    def start(self,groups,turns,prompt_tokens,focus_turn=None,claim_mask=None):
        self.groups=groups;self.turns=turns;self.prompt_tokens=prompt_tokens;self.focus_turn=focus_turn;self.claim_mask=claim_mask;self.frames=collections.defaultdict(list);self.turn_frames=collections.defaultdict(list);self.source_frames=collections.defaultdict(list);self.active=True
    def collect(self,module,q,k,mask,scale):
        layer=module._audit_layer_idx
        query=q[:,:,-1:,:].float()
        if query.shape[1]%k.shape[1]:raise ValueError('GQA head mismatch')
        keys=k.repeat_interleave(query.shape[1]//k.shape[1],dim=1).float()
        logits=(query@keys.transpose(-1,-2))*scale
        if mask is not None:
            local=mask[..., -1:, :k.shape[-2]]
            if local.dtype==torch.bool:logits=logits.masked_fill(~local,float('-inf'))
            else:logits=logits+local
        weights=torch.softmax(logits,dim=-1)[0,:,0,:]
        n=k.shape[-2]
        labels=np.concatenate([self.groups,np.full(max(0,n-len(self.groups)),7,np.int64)])[:n]
        index=torch.as_tensor(labels,device=weights.device).expand(weights.shape[0],-1)
        mass=torch.zeros(weights.shape[0],len(GROUPS),device=weights.device,dtype=torch.float32)
        mass.scatter_add_(1,index,weights)
        turn_labels=np.concatenate([self.turns,np.full(max(0,n-len(self.turns)),-1,np.int32)])[:n]
        numturns=int(self.turns.max())+1
        if numturns:
            valid=turn_labels>=0
            ti=torch.as_tensor(turn_labels[valid],device=weights.device,dtype=torch.long).expand(weights.shape[0],-1)
            tm=torch.zeros(weights.shape[0],numturns,device=weights.device)
            tm.scatter_add_(1,ti,weights[:,torch.as_tensor(valid,device=weights.device)])
            self.turn_frames[layer].append(tm.detach())
        self.frames[layer].append(mass.detach())
        if self.focus_turn is not None:
            focus=(turn_labels==self.focus_turn)
            masks=[focus & (labels==g) for g in [3,4]]
            if self.claim_mask is not None:masks.append(np.concatenate([self.claim_mask,np.full(max(0,n-len(self.claim_mask)),False)])[:n])
            source=torch.stack([weights[:,torch.as_tensor(m,device=weights.device)].sum(-1) for m in masks],dim=-1)
            self.source_frames[layer].append(source.detach())
    def save(self,path):
        layers=sorted(self.frames)
        frames=np.stack([torch.stack(self.frames[l]).cpu().numpy() for l in layers],axis=1)
        if not np.isfinite(frames).all():raise ValueError('non-finite attention')
        error=float(np.max(np.abs(frames.sum(-1)-1)))
        if error>2e-4:raise ValueError(f'attention mass error {error}')
        arrays={'mass':frames,'layers':np.array(layers),'group_names':np.array(GROUPS),'input_groups':self.groups,'input_turns':self.turns}
        if self.turn_frames:arrays['turn_mass']=np.stack([torch.stack(self.turn_frames[l]).cpu().numpy() for l in layers],axis=1)
        if self.source_frames:arrays['source_mass']=np.stack([torch.stack(self.source_frames[l]).cpu().numpy() for l in layers],axis=1)
        np.savez_compressed(path,**arrays)
        return frames,error,layers

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--model',required=True);ap.add_argument('--model-id',required=True);ap.add_argument('--plan',required=True);ap.add_argument('--assets',required=True);ap.add_argument('--out',required=True);ap.add_argument('--limit',type=int);ap.add_argument('--preflight',action='store_true');args=ap.parse_args()
    out=pathlib.Path(args.out);out.mkdir(parents=True,exist_ok=True)
    plan=json.loads(pathlib.Path(args.plan).read_text());cases=plan['cases'];cases=cases[:args.limit] if args.limit else cases
    torch.manual_seed(42);torch.set_num_threads(8)
    processor=AutoProcessor.from_pretrained(args.model,local_files_only=True)
    maxmemory={i:'21GiB' for i in range(torch.cuda.device_count())}
    model=AutoModelForImageTextToText.from_pretrained(args.model,dtype=torch.bfloat16,attn_implementation='sdpa',device_map='auto',max_memory=maxmemory,local_files_only=True).eval()
    original_eos=model.generation_config.eos_token_id
    effective_eos=[original_eos] if isinstance(original_eos,int) else list(original_eos or [])
    if processor.tokenizer.eos_token_id is not None and processor.tokenizer.eos_token_id not in effective_eos:effective_eos.append(processor.tokenizer.eos_token_id)
    model.generation_config.eos_token_id=effective_eos
    attention_modules=[]
    for name,module in model.named_modules():
        if module.__class__.__name__ in ['Qwen3_5Attention','Glm4vTextAttention']:
            module._audit_layer_idx=module.layer_idx;attention_modules.append(name)
    if not attention_modules:raise ValueError('no supported language attention modules')
    collector=Collector();original=ALL_ATTENTION_FUNCTIONS['sdpa']
    def sidecar(module,q,k,v,attention_mask,*posargs,**kwargs):
        result=original(module,q,k,v,attention_mask,*posargs,**kwargs)
        if collector.active and hasattr(module,'_audit_layer_idx'):
            collector.collect(module,q,k,attention_mask,kwargs.get('scaling',module.scaling))
        return result
    ALL_ATTENTION_FUNCTIONS.register('sdpa',sidecar)
    runtime={'model':args.model,'model_id':args.model_id,'torch':torch.__version__,'transformers':__import__('transformers').__version__,'attention_modules':attention_modules,'device_map':{k:str(v) for k,v in model.hf_device_map.items()},'config_sha256':sha(pathlib.Path(args.model)/'config.json'),'plan_sha256':sha(args.plan),'scope':'Fixed archived snapshots; no GUI actions executed; full-attention language layers only; source-position reading, not causal information attribution.'}
    runtime.update(original_generation_eos_token_ids=original_eos,effective_generation_eos_token_ids=effective_eos,tokenizer_eos_token_id=processor.tokenizer.eos_token_id,collector_transfer='Identical per-query FP32 reductions retained on GPU until reply ends; CPU transfer deferred only',runner_sha256=sha(__file__))
    atomic(out/'runtime.json',runtime)
    results=[];request_cache={}
    for ci,case in enumerate(cases):
        caseout=out/case['id'];caseout.mkdir(exist_ok=True)
        if (caseout/'result.json').exists():
            prev=json.loads((caseout/'result.json').read_text())
            if prev.get('status')=='completed':
                results.append(prev)
                if 'request_sha256' in prev:request_cache[prev['request_sha256']]=prev
                continue
        start=time.time();atomic(out/'status.json',{'phase':'running','case':case['id'],'index':ci,'total':len(cases),'completed':sum(r['status']=='completed' for r in results),'pid':os.getpid()})
        try:
            request=case['request']
            request_sha=hashlib.sha256(json.dumps(request,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
            if request_sha in request_cache:
                prior=request_cache[request_sha];result=copy.deepcopy(prior)
                result.update({k:case[k] for k in ['id','task','app','stage','step','history','condition']})
                result.update(reused_from=prior['id'],seconds=round(time.time()-start,2))
                if not (caseout/'attention.npz').exists():os.link(out/prior['id']/'attention.npz',caseout/'attention.npz')
                atomic(caseout/'input-reference.json',{'same_complete_request_sha256':request_sha,'reused_case':prior['id'],'case':{k:v for k,v in case.items() if k!='request'}})
                (caseout/'output.txt').write_text(result['output']);atomic(caseout/'result.json',result);results.append(result)
                atomic(out/'results.json',results)
                continue
            messages=convert(request['messages'],pathlib.Path(args.assets))
            batch=processor.apply_chat_template(messages,add_generation_prompt=True,tokenize=True,return_dict=True,return_tensors='pt',enable_thinking=False)
            device=model.get_input_embeddings().weight.device;batch=batch.to(device)
            ids=batch['input_ids'][0].tolist()
            groups,turns,prompt,offsets=group_prompt(processor.tokenizer,ids,model.config,request)
            claim_mask=None
            if 'source_claim' in case:
                claim_mask=np.full(len(ids),False)
                for hit in re.finditer(re.escape(case['source_claim']),prompt):
                    for i,(a,b) in enumerate(offsets):
                        if a<hit.end() and b>hit.start() and turns[i]==case['source_assistant_index']:claim_mask[i]=True
                if not claim_mask.any():raise ValueError('source claim could not be located exactly in its original source turn')
            atomic(caseout/'input.json',{'case':{k:v for k,v in case.items() if k!='request'},'input_ids':ids,'groups':groups.tolist(),'turns':turns.tolist(),'source_claim_mask':claim_mask.tolist() if claim_mask is not None else None,'request':request})
            kwargs={'max_new_tokens':int(plan.get('max_new_tokens',512)),'do_sample':False,'use_cache':True,'return_dict_in_generate':True,'output_logits':args.preflight}
            baseline=None
            if args.preflight:
                collector.active=False
                with torch.inference_mode():baseline=model.generate(**batch,**kwargs)
            collector.start(groups,turns,len(ids),case.get('source_assistant_index'),claim_mask)
            with torch.inference_mode():generated=model.generate(**batch,**kwargs)
            collector.active=False
            output_ids=generated.sequences[0,len(ids):].tolist()
            frames,error,layers=collector.save(caseout/'attention.npz')
            if len(frames)!=len(output_ids):raise ValueError('query/output count mismatch')
            equality=None
            if baseline is not None:
                equality={'output_ids_equal':torch.equal(baseline.sequences,generated.sequences),'logits_steps':len(generated.logits),'max_logit_abs_diff':max(float((a-b).abs().max()) for a,b in zip(baseline.logits,generated.logits))}
                if not equality['output_ids_equal'] or equality['max_logit_abs_diff']!=0:raise ValueError('read-only collection changed baseline')
            eos=model.generation_config.eos_token_id
            eos=[eos] if isinstance(eos,int) else eos
            eos_reached=bool(output_ids and output_ids[-1] in (eos or []))
            output=processor.tokenizer.decode(output_ids,skip_special_tokens=True,clean_up_tokenization_spaces=False)
            (caseout/'output.txt').write_text(output)
            result={'id':case['id'],'status':'completed','model_id':args.model_id,'task':case['task'],'app':case['app'],'stage':case['stage'],'step':case['step'],'history':case['history'],'condition':case['condition'],'input_tokens':len(ids),'history_turns':int(turns.max())+1,'output_tokens':len(output_ids),'output_ids':output_ids,'eos_reached':eos_reached,'truncated':not eos_reached,'output':output,'mass':frames.mean(axis=(0,1,2)).tolist(),'first_query_mass':frames[0].mean(axis=(0,1)).tolist(),'mass_conservation_max_error':error,'capture_validation':equality,'attention_sha256':sha(caseout/'attention.npz'),'seconds':round(time.time()-start,2),'semantic_label':'unreviewed','groups':GROUPS}
            result['request_sha256']=request_sha
            if collector.source_frames:
                source_frames=np.stack([torch.stack(collector.source_frames[l]).cpu().numpy() for l in layers],axis=1)
                result['source_assistant_index']=case['source_assistant_index']
                result['source_mass']=source_frames.mean(axis=(0,1,2)).tolist()
                result['first_query_source_mass']=source_frames[0].mean(axis=(0,1)).tolist()
                raw_output=processor.tokenizer.decode(output_ids,skip_special_tokens=False,clean_up_tokenization_spaces=False)
                parsed=processor.tokenizer(raw_output,add_special_tokens=False,return_offsets_mapping=True)
                spans=action_spans(raw_output)
                if parsed['input_ids']==output_ids and len(spans)==1:
                    astart,aend,_=spans[0]
                    query_indices=[i for i,(a,b) in enumerate(parsed['offset_mapping']) if a<aend and b>astart]
                    result['action_query_source_mass']=source_frames[query_indices].mean(axis=(0,1,2)).tolist()
                    result['action_query_count']=len(query_indices)
                else:result['action_query_source_mass']=None
            atomic(caseout/'result.json',result);results.append(result);request_cache[request_sha]=result
            del generated,baseline,batch
        except Exception as exc:
            collector.active=False
            error={'id':case['id'],'status':'failed','error':repr(exc),'traceback':traceback.format_exc(),'seconds':round(time.time()-start,2)}
            atomic(caseout/'failure.json',error);results.append(error)
            print(error['traceback'],flush=True)
            torch.cuda.empty_cache()
        atomic(out/'results.json',results)
        print(json.dumps({'id':case['id'],'status':results[-1]['status'],'seconds':round(time.time()-start,2)}),flush=True)
        if args.preflight and results[-1]['status']=='failed':break
    atomic(out/'status.json',{'phase':'finished','total':len(cases),'completed':sum(r['status']=='completed' for r in results),'failed':sum(r['status']=='failed' for r in results),'pid':os.getpid()})
if __name__=='__main__':main()
