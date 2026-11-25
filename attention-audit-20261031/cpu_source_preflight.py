import hashlib,json,pathlib,re,traceback
import numpy as np
import torch
from transformers import AutoConfig,AutoProcessor
from run_attention_source import convert,group_prompt
torch.set_num_threads(8)
root=pathlib.Path('/home/researcher/attention-20261031/source-campaign');plan=json.loads((root/'plan.json').read_text());rows=[]
models={'qwen9':'/home/researcher/models/Qwen3.5-9B','glm':'/home/researcher/models/GLM-4.6V-Flash-411bb4d77144'}
for model,path in models.items():
    processor=AutoProcessor.from_pretrained(path,local_files_only=True);config=AutoConfig.from_pretrained(path,local_files_only=True)
    for case in plan['cases']:
        try:
            batch=processor.apply_chat_template(convert(case['request']['messages'],root/'assets'),add_generation_prompt=True,tokenize=True,return_dict=True,return_tensors='pt',enable_thinking=False)
            ids=batch['input_ids'][0].tolist();groups,turns,prompt,offsets=group_prompt(processor.tokenizer,ids,config,case['request'])
            mask=np.zeros(len(ids),bool)
            for hit in re.finditer(re.escape(case['source_claim']),prompt):
                for i,(a,b) in enumerate(offsets):
                    if a<hit.end() and b>hit.start() and turns[i]==case['source_assistant_index']:mask[i]=True
            assert mask.any()
            rows.append({'model':model,'id':case['id'],'status':'passed','input_tokens':len(ids),'input_ids_sha256':hashlib.sha256(np.asarray(ids,dtype='<i8').tobytes()).hexdigest(),'groups_sha256':hashlib.sha256(np.asarray(groups,dtype='<i8').tobytes()).hexdigest(),'source_claim_tokens':int(mask.sum()),'source_claim_mask_sha256':hashlib.sha256(mask.tobytes()).hexdigest(),'image_tokens':int((groups==0).sum()),'reference_image_tokens':int((groups==8).sum())})
            del batch
        except Exception:rows.append({'model':model,'id':case['id'],'status':'failed','error':traceback.format_exc()})
        temp=root/'cpu-input-audit.json.tmp';temp.write_text(json.dumps(rows,indent=2));temp.replace(root/'cpu-input-audit.json')
print(json.dumps({'total':len(rows),'passed':sum(r['status']=='passed' for r in rows),'failed':[r for r in rows if r['status']=='failed']}))
