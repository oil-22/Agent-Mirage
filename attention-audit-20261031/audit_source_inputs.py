"""Audit localized source-state interventions against saved native input IDs."""
import collections,difflib,hashlib,json,pathlib,re
import numpy as np
from action_audit import audit_action
root=pathlib.Path('/home/researcher/attention-20261031');out=root/'analysis';out.mkdir(exist_ok=True)
plan=json.loads((root/'source-campaign/plan.json').read_text());cases={c['id']:c for c in plan['cases']}
cpu={(r['model'],r['id']):r for r in json.loads((root/'source-campaign/cpu-input-audit.json').read_text()) if r['status']=='passed'}
audits=[];results=[]
def blocks(req):
    texts=[];images=[]
    for m in req['messages']:
        content=m['content'] if isinstance(m['content'],list) else [{'type':'text','text':m['content']}]
        for p in content:
            if p.get('type')=='text':texts.append((m['role'],p['text']))
            if p.get('type')=='image_url':images.append(p['image_url']['url'])
    return texts,images
for model in ['qwen9','glm']:
    folder=root/('source-'+model)
    if not (folder/'results.json').exists():continue
    rr={r['id']:r for r in json.loads((folder/'results.json').read_text()) if r['status']=='completed'}
    for cid,r in rr.items():
        saved=json.loads((folder/r.get('reused_from',cid)/'input.json').read_text())
        groups=np.asarray(saved['groups']);turns=np.asarray(saved['turns']);mask=np.asarray(saved['source_claim_mask'],dtype=bool);focus=cases[cid]['source_assistant_index']
        pre=cpu[(model,cid)]
        matches={'ids':pre['input_ids_sha256']==hashlib.sha256(np.asarray(saved['input_ids'],dtype='<i8').tobytes()).hexdigest(),'groups':pre['groups_sha256']==hashlib.sha256(np.asarray(groups,dtype='<i8').tobytes()).hexdigest(),'claim_mask':pre['source_claim_mask_sha256']==hashlib.sha256(mask.tobytes()).hexdigest()}
        assert all(matches.values()),(model,cid,matches)
        results.append(dict(model=model,id=cid,source_prose_tokens=int(((turns==focus)&(groups==3)).sum()),source_action_tokens=int(((turns==focus)&(groups==4)).sum()),source_claim_tokens=int(mask.sum()),claim_mask_all_in_source_turn=bool((turns[mask]==focus).all()),current_image_tokens=int((groups==0).sum()),reference_image_tokens=int((groups==8).sum()),cpu_preflight_matches_actual_native_inputs=matches,capture_validation=r.get('capture_validation'),eos_reached=r['eos_reached'],**audit_action(r['output'])))
    for original_id in [cid for cid in rr if cid.endswith('-original')]:
        stem=original_id[:-len('-original')];original=json.loads((folder/original_id/'input.json').read_text());oldids=original['input_ids'];oldmask=original['source_claim_mask'];oldtexts,oldimages=blocks(original['request'])
        for variant in ['state_corrected','meaning_preserving_sham']:
            cid=stem+'-'+variant
            if cid not in rr:continue
            new=json.loads((folder/cid/'input.json').read_text());newids=new['input_ids'];newmask=new['source_claim_mask'];newtexts,newimages=blocks(new['request'])
            changes=[];inside=True
            if len(oldids)==len(newids):
                positions=[i for i,(a,b) in enumerate(zip(oldids,newids)) if a!=b]
                opcodes=[('replace',i,i+1,i,i+1) for i in positions]
            else:opcodes=difflib.SequenceMatcher(a=oldids,b=newids,autojunk=False).get_opcodes()
            for tag,a,b,c,d in opcodes:
                if tag=='equal':continue
                valid_old=all(oldmask[a:b]);valid_new=all(newmask[c:d]);inside=inside and valid_old and valid_new
                changes.append({'kind':tag,'old_span':[a,b],'new_span':[c,d],'old_ids':oldids[a:b],'new_ids':newids[c:d],'inside_claim_masks':valid_old and valid_new})
            # Full request diff is recorded. No unrelated historical action is rewritten.
            text_changes=[]
            for bi,(a,b) in enumerate(zip(oldtexts,newtexts)):
                if a!=b:
                    chunks=[{'old':a[1][s:e],'new':b[1][u:v]} for tag,s,e,u,v in difflib.SequenceMatcher(a=a[1],b=b[1],autojunk=False).get_opcodes() if tag!='equal']
                    text_changes.append({'text_block':bi,'role':a[0],'changes':chunks})
            oldactions=re.findall(r'(?s)<action>.*?</action>|```.*?```', '\n'.join(t for _,t in oldtexts))
            newactions=re.findall(r'(?s)<action>.*?</action>|```.*?```', '\n'.join(t for _,t in newtexts))
            audits.append({'model':model,'original_id':original_id,'variant_id':cid,'input_token_lengths':[len(oldids),len(newids)],'equal_native_token_length':len(oldids)==len(newids),'all_token_changes_inside_source_claim':inside,'token_changes':changes,'image_order_and_bytes_unchanged':oldimages==newimages,'historical_action_blocks_unchanged':oldactions==newactions,'text_changes':text_changes})
(out/'source-input-audit.json').write_text(json.dumps(audits,ensure_ascii=False,indent=2))
(out/'source-token-counts.json').write_text(json.dumps(results,indent=2))
print(json.dumps({'source_results':len(results),'intervention_pairs':len(audits),'equal_length_pairs':sum(a['equal_native_token_length'] for a in audits),'localized_pairs':sum(a['all_token_changes_inside_source_claim'] for a in audits),'preserved_images':sum(a['image_order_and_bytes_unchanged'] for a in audits),'preserved_actions':sum(a['historical_action_blocks_unchanged'] for a in audits)}))
