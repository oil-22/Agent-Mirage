import copy,hashlib,json,pathlib,re
from transformers import AutoTokenizer
root=pathlib.Path('/home/researcher/attention-20261031/source-campaign')
tokenizer=AutoTokenizer.from_pretrained('/opt/whz/llms/Qwen3.8-27B',local_files_only=True)
raw=json.loads((root/'raw.json').read_text());cases=[];provenance=[]
for item in raw:
    if item['source_kind']=='native_prompt_reconstruction':
        meta=item['metadata'];ids=meta['input_ids'];decoded=tokenizer.decode(ids,skip_special_tokens=False,clean_up_tokenization_spaces=False)
        assert tokenizer.encode(decoded,add_special_tokens=False)==ids,'old prompt cannot be reconstructed exactly'
        rolematches=list(re.finditer(r'<\|im_start\|>(system|user|assistant)\n(.*?)<\|im_end\|>',decoded,re.S))
        messages=[];images=iter(meta['images']);source_index=None;asst=0
        annotation=next(c for c in meta['claim_annotations'] if c['step']==10)
        claim_char=len(tokenizer.decode(ids[:min(annotation['positions'])],skip_special_tokens=False,clean_up_tokenization_spaces=False))
        for match in rolematches:
            role,text=match.group(1),match.group(2)
            if role=='assistant':
                if match.start(2)<=claim_char<match.end(2):source_index=asst
                asst+=1
            parts=[];pos=0
            for vision in re.finditer(r'<\|vision_start\|>(?:<\|image_pad\|>)+<\|vision_end\|>',text):
                if vision.start()>pos:parts.append({'type':'text','text':text[pos:vision.start()]})
                img=next(images);parts.append({'type':'image_url','image_url':{'url':'archive-image://sha256/'+img['sha256']}});pos=vision.end()
            if pos<len(text):parts.append({'type':'text','text':text[pos:]})
            messages.append({'role':role,'content':parts})
        assert next(images,None) is None
        assert source_index is not None
        request={'messages':messages,'max_tokens':2048,'temperature':0}
        item['source_assistant_index']=source_index
        source_message=[m for m in messages if m['role']=='assistant'][source_index]
        assert 'The dropdown is open' in ''.join(p['text'] for p in source_message['content'])
        provenance.append({'id':item['id'],'original_input_ids_exactly_reencoded':True,'source_assistant_index':source_index,'source_claim_text':annotation['text'],'source_artifact_sha256':item['source_artifact_sha256']})
    else:request=item['request']
    for variant in ['original','state_corrected','meaning_preserving_sham']:
        req=copy.deepcopy(request)
        if item['app']=='WebMall':
            for msg in req['messages']:
                blocks=msg['content'] if isinstance(msg['content'],list) else [{'type':'text','text':msg['content']}]
                for block in blocks:
                    if block.get('type')!='text':continue
                    text=block['text'];pattern=r'(?ms)(^## step 9\n)(.*?)(?=^## step 10\n|\Z)'
                    matches=list(re.finditer(pattern,text))
                    if not matches:continue
                    assert len(matches)==1
                    def edit(m):
                        body=m.group(2)
                        assert 'CamelCases search returned no results (blank page).' in body
                        if variant=='state_corrected':body=body.replace('CamelCases search returned no results (blank page).','CamelCases search returned unknown results (blank page).')
                        elif variant=='meaning_preserving_sham':body=body.replace('(blank page)','(white page)')
                        return m.group(1)+body
                    block['text']=re.sub(pattern,edit,text)
                if isinstance(msg['content'],str):msg['content']=blocks[0]['text']
        else:
            source_message=[m for m in req['messages'] if m['role']=='assistant'][item['source_assistant_index']]
            for block in source_message['content']:
                if block.get('type')=='text':
                    text=block['text']
                    if variant=='state_corrected':text=text.replace('The dropdown is open','The dropdown is closed')
                    elif variant=='meaning_preserving_sham':text=text.replace('The dropdown is open','This dropdown is open')
                    block['text']=text
        case={k:v for k,v in item.items() if k not in ['metadata','request']}
        case.update(id=item['id']+'-'+variant,condition=variant,request=req)
        if item['app']=='WebMall':case['source_claim']='CamelCases search returned '+('unknown' if variant=='state_corrected' else 'no')+' results ('+('white' if variant=='meaning_preserving_sham' else 'blank')+' page).'
        else:case['source_claim']=('This' if variant=='meaning_preserving_sham' else 'The')+' dropdown is '+('closed' if variant=='state_corrected' else 'open')
        cases.append(case)
plan={'selection':'Two previously reviewed source episodes, chosen before new runs. Qwen27 original propagation already measured and reused; new models see shared archived prefixes.','max_new_tokens':2048,'scope':'Offline fixed-snapshot cross-model source reading and source-state text intervention. Source episodes belong to original Qwen27 trajectories, not native GLM/Qwen9 rollouts. Only original source state is edited; all historical action strings and later observations remain fixed.','source_state_edits':{'WebMall':'no results -> unknown results, only in step 9 block; duplicated copies within that record are both edited','VisualWebArena':'open -> closed, only in source step 10 assistant turn'},'sham':'Meaning-preserving wording change in the same source record. Actual native token-length equality must be checked from input artifacts, not assumed.','cases':cases}
(root/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2));(root/'reconstruction-audit.json').write_text(json.dumps(provenance,indent=2))
(root/'plan.sha256').write_text(hashlib.sha256((root/'plan.json').read_bytes()).hexdigest())
print('source cases per new model',len(cases))
