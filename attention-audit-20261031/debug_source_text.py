import json,pathlib
import torch
from transformers import AutoProcessor
from run_attention_source import convert
torch.set_num_threads(8)
root=pathlib.Path('/home/researcher/attention-20261031/source-campaign');case=next(c for c in json.loads((root/'plan.json').read_text())['cases'] if c['id']=='VWA-11-original')
for model,path in [('qwen9','/home/researcher/models/Qwen3.5-9B'),('glm','/home/researcher/models/GLM-4.6V-Flash-411bb4d77144')]:
    p=AutoProcessor.from_pretrained(path,local_files_only=True);batch=p.apply_chat_template(convert(case['request']['messages'],root/'assets'),add_generation_prompt=True,tokenize=True,return_dict=True,return_tensors='pt',enable_thinking=False);text=p.tokenizer.decode(batch['input_ids'][0],skip_special_tokens=False,clean_up_tokenization_spaces=False);pos=0
    for mi,m in enumerate(case['request']['messages']):
        blocks=[m['content']] if isinstance(m['content'],str) else [x['text'] for x in m['content'] if x.get('type')=='text']
        for block in blocks:
            found=text.find(block,pos)
            if found<0:
                body=block.split('</think>')[-1].lstrip('\n');where=text.find(body,pos)
                print(json.dumps({'model':model,'message':mi,'role':m['role'],'block':repr(block[:250]),'block_length':len(block),'body_present_after_native_think_removal':where>=0,'native_neighborhood':repr(text[pos:pos+350]),'body_neighborhood':repr(text[max(0,where-50):where+200]) if where>=0 else None}));break
            pos=found+len(block)
        else:continue
        break
