"""Export and audit completed captures without model inference or action execution."""
import collections,csv,hashlib,json,pathlib,re,sys,time
import numpy as np
from PIL import Image
from transformers import AutoTokenizer
from action_audit import action_spans,audit_action
root=pathlib.Path('/home/researcher/attention-20261102');out=root/'analysis';out.mkdir(exist_ok=True)
models={'qwen27':'/opt/whz/llms/Qwen3.8-27B','qwen9':'/home/researcher/models/Qwen3.5-9B','glm':'/home/researcher/models/GLM-4.6V-Flash-411bb4d77144'}
def write(p,obj):
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(obj,ensure_ascii=False,indent=2));t.replace(p)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(8*1024*1024):h.update(b)
 return h.hexdigest()
def bytesha(a):return hashlib.sha256(a.tobytes()).hexdigest()
def canonical(req):return hashlib.sha256(json.dumps(req,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def image_urls(req):return [b['image_url']['url'] for m in req['messages'] if isinstance(m['content'],list) for b in m['content'] if b.get('type')=='image_url']
def historical_actions(req):
 return [[text[a:b] for a,b,w in action_spans(text)] for m in req['messages'] if m['role']=='assistant' for text in [m['content'] if isinstance(m['content'],str) else '\n'.join(b['text'] for b in m['content'] if b.get('type')=='text')]]
plans={};cases={};progress={};batches=[];rows=[];reviews=[];inputs={};errors=[];pairs=[];hash_cache={};tensor_cache={};query_cachepath=out/'query-cache.json';query_cache=json.loads(query_cachepath.read_text()) if query_cachepath.exists() else {}
cpupath=root/'source-campaign/cpu-input-audit.json';cpu={(x['model'],x['id']):x for x in json.loads(cpupath.read_text())} if cpupath.exists() else {}
for cohort,prefix,planfolder in [('main','','campaign'),('buttons','buttons-','button-campaign'),('source','source-','source-campaign')]:
 if not (root/planfolder/'plan.json').exists():continue
 plans[cohort]=json.loads((root/planfolder/'plan.json').read_text());cases[cohort]={c['id']:c for c in plans[cohort]['cases']}
 for mid,modelpath in models.items():
  folder=root/(prefix+mid);tokenizer=None;status=json.loads((folder/'status.json').read_text()) if (folder/'status.json').exists() else {};progress[prefix+mid]=status
  rr=json.loads((folder/'results.json').read_text()) if (folder/'results.json').exists() else [];successful=[r for r in rr if r['status']=='completed'];bad=[r for r in rr if r['status']!='completed'];localrows=[];preflights=[];truncated=[];unique_requests=set()
  for r in successful:
   try:
    case=cases[cohort][r['id']];origin=r.get('reused_from',r['id']);caseout=folder/origin;p=caseout/'attention.npz';ip=caseout/'input.json';meta=json.loads(ip.read_text());ids=np.asarray(meta['input_ids'],dtype='<i8');groups=np.asarray(meta['groups'],dtype='<i8');claim_mask=np.asarray(meta.get('source_claim_mask') or [False]*len(ids),dtype=bool)
    assert len(ids)==r['input_tokens']==len(groups)
    assert canonical(meta['request'])==r['request_sha256']==canonical(case['request'])
    st=p.stat();physical=(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)
    if physical not in hash_cache:hash_cache[physical]=sha(p)
    assert hash_cache[physical]==r['attention_sha256']
    unique_requests.add(r['request_sha256']);key=mid+':'+r['attention_sha256']
    if tokenizer is None:tokenizer=AutoTokenizer.from_pretrained(modelpath,local_files_only=True)
    eos=set(json.loads((folder/'runtime.json').read_text())['effective_generation_eos_token_ids']);outputids=r['output_ids'];assert len(outputids)==r['output_tokens'];assert not any(i in eos for i in outputids[:-1]),'post-native-EOS tokens present'
    if not r['eos_reached']:truncated.append(r['id'])
    if key not in query_cache:
     artifact=np.load(p);mass=artifact['mass'];assert mass.shape[0]==len(outputids);assert np.isfinite(mass).all();assert float(np.abs(mass.sum(-1)-1).max())<2e-4
     assert np.array_equal(artifact['input_groups'],groups)
     raw=tokenizer.decode(outputids,skip_special_tokens=False,clean_up_tokenization_spaces=False);encoded=tokenizer(raw,add_special_tokens=False,return_offsets_mapping=True);exact=encoded['input_ids']==outputids;offsets=encoded['offset_mapping'] if exact else None
     if offsets is None:
      prefixes=[tokenizer.decode(outputids[:k],skip_special_tokens=False,clean_up_tokenization_spaces=False) for k in range(len(outputids)+1)]
      if all(raw.startswith(p) for p in prefixes) and all(len(a)<=len(b) for a,b in zip(prefixes,prefixes[1:])):offsets=[(len(a),len(b)) for a,b in zip(prefixes,prefixes[1:])]
     spans=action_spans(raw);indices=[]
     if len(spans)==1 and offsets is not None:
      start,end,_=spans[0];indices=[k for k,(a,b) in enumerate(offsets) if a<end and b>start and outputids[k] not in tokenizer.all_special_ids]
     data={'query_character_offsets_exact':offsets is not None,'output_exactly_reencoded':exact,'action_query_count':len(indices),'layers':artifact['layers'].tolist(),'first_query_mass':mass[0].mean(axis=(0,1)).tolist(),'all_query_mass':mass.mean(axis=(0,1,2)).tolist(),'action_query_mass':mass[indices].mean(axis=(0,1,2)).tolist() if indices else None,'first_query_layer_mass':mass[0].mean(axis=1).tolist(),'action_query_layer_mass':mass[indices].mean(axis=(0,2)).tolist() if indices else None,'mass_conservation_max_error_verified':float(np.abs(mass.sum(-1)-1).max())}
     if 'source_mass' in artifact:
      sm=artifact['source_mass'];assert sm.shape[:3]==mass.shape[:3];data.update(source_mass=sm.mean(axis=(0,1,2)).tolist(),first_query_source_mass=sm[0].mean(axis=(0,1)).tolist(),action_query_source_mass=sm[indices].mean(axis=(0,1,2)).tolist() if indices else None,action_query_source_layer_mass=sm[indices].mean(axis=(0,2)).tolist() if indices else None)
     query_cache[key]=data;artifact.close()
    counts=np.bincount(groups,minlength=9);row={k:r[k] for k in ['id','task','app','stage','step','history','condition','input_tokens','output_tokens','eos_reached','truncated','output','history_turns']};row.update(cohort=cohort,model=mid,request_sha256=r['request_sha256'],attention_sha256=r['attention_sha256'],reused_from=r.get('reused_from'),image_tokens=int(counts[0]),reference_image_tokens=int(counts[8]),history_tokens=int(counts[3]+counts[4]),**audit_action(r['output']),**query_cache[key])
    for name,field in [('first','first_query_mass'),('action','action_query_mass'),('all','all_query_mass')]:
     mm=row[field]
     for label,value in [('image',None if mm is None else mm[0]),('history',None if mm is None else mm[3]+mm[4])]:row[name+'_'+label]=value
     row[name+'_history_nonimage']=None if mm is None else (mm[3]+mm[4])/(1-mm[0]) if mm[0]<1 else None
    if cohort=='source':
     check=cpu[mid,r['id']];actual={'input_ids_sha256':bytesha(ids),'groups_sha256':bytesha(groups),'claim_mask_sha256':bytesha(claim_mask)};assert all(actual[k]==check[k] for k in actual);row['cpu_preflight_matches_actual']=True;row['source_claim_tokens']=int(claim_mask.sum());row['source_claim']=case['source_claim'];row['trajectory']=case['trajectory'];inputs[mid,r['id']]=(meta,ids,claim_mask)
     assert np.all(groups[claim_mask]==3),'claim must be a subset of historical prose';row['source_prose_tokens']=int(np.sum((np.asarray(meta['turns'])==case['source_assistant_index']) & (groups==3)));row['history_prose_tokens']=int(counts[3])
    rows.append(row);localrows.append(row)
    if r.get('capture_validation') is not None:
     v=r['capture_validation'];assert v['output_ids_equal'] and v['max_logit_abs_diff']==0;preflights.append({'id':r['id'],**v})
    if cohort=='main' and r['condition'] in ['blank_replace','silent_drop']:reviews.append({'model':mid,'id':r['id'],'condition':r['condition'],'task':r['task'],'stage':r['stage'],'history':r['history'],'output':r['output'],'review_key':hashlib.sha256((r['condition']+'\0'+r['output']).encode()).hexdigest(),**audit_action(r['output'])})
   except Exception as e:errors.append({'cohort':cohort,'model':mid,'id':r['id'],'error':repr(e)})
  batches.append({'cohort':cohort,'model':mid,'expected':len(cases[cohort]),'logical_completed':len(localrows),'unique_requests':len(unique_requests),'reused':sum(bool(x['reused_from']) for x in localrows),'failed':bad,'truncated':truncated,'status':status,'preflights':preflights})
  write(query_cachepath,query_cache)
for (mid,cid),(meta,ids,mask) in inputs.items():
 if not cid.endswith('-original'):continue
 base=cid[:-len('-original')]
 for variant in ['source_withdrawn','meaning_preserving_sham']:
  key=(mid,base+'-'+variant)
  if key not in inputs:continue
  vm,vi,vk=inputs[key];equal=len(ids)==len(vi);changed=np.flatnonzero(ids!=vi) if equal else np.array([],int);inside=bool(equal and np.all((mask|vk)[changed]));origreq=meta['request'];variantreq=vm['request'];expected=copyreq=json.loads(json.dumps(origreq));msg=[m for m in expected['messages'] if m['role']=='assistant'][1];old=cases['source'][cid]['source_claim'];new=cases['source'][key[1]]['source_claim'];assert msg['content'].count(old)==1;msg['content']=msg['content'].replace(old,new)
  check={'model':mid,'original_id':cid,'variant_id':key[1],'equal_native_token_length':equal,'all_token_changes_inside_source_claim':inside,'only_source_assertion_text_changed':expected==variantreq,'image_order_and_bytes_unchanged':image_urls(origreq)==image_urls(variantreq),'historical_action_blocks_unchanged':historical_actions(origreq)==historical_actions(variantreq),'changed_token_count':len(changed)};pairs.append(check)
  if not all(check[k] for k in ['equal_native_token_length','all_token_changes_inside_source_claim','only_source_assertion_text_changed','image_order_and_bytes_unchanged','historical_action_blocks_unchanged']):errors.append({'source_pair_failed':check})
pixel=[]
if 'main' in plans:
 for s in plans['main']['sources']:
  assets=root/'campaign/assets';a=np.array(Image.open(next(assets.glob('*/'+s['image_sha256']+'.*'))).convert('RGB'));b=np.array(Image.open(next(assets.glob('*/'+s['previous_image_sha256']+'.*'))).convert('RGB'));same=a.shape==b.shape and np.array_equal(a,b);pixel.append({'task':s['task'],'stage':s['stage'],'pixels_identical':same,'changed_fraction':float(np.any(a!=b,axis=-1).mean()) if a.shape==b.shape else None})
write(out/'measurements.json',rows);write(out/'semantic-review.json',reviews);write(out/'pixel-audit.json',pixel);write(out/'source-pair-audit.json',pairs)
maskchecks=[]
if (root/'button-campaign/mask-audit.json').exists():
 for s in json.loads((root/'button-campaign/mask-audit.json').read_text()):
  p=next((root/'campaign/assets').glob('*/'+s['original_sha256']+'.*'));q=next((root/'button-campaign/assets').glob('*/'+s['mask_sha256']+'.*'))
  a=np.array(Image.open(p).convert('RGB'));b=np.array(Image.open(q).convert('RGB'));keep=np.zeros(a.shape[:2],bool)
  for x0,y0,x1,y1 in s['pixel_rectangles']:keep[y0:y1,x0:x1]=True
  check={'id':s['id'],'original_file_sha_verified':sha(p)==s['original_sha256'],'mask_file_sha_verified':sha(q)==s['mask_sha256'],'inside_pixels_identical':bool(np.array_equal(a[keep],b[keep])),'outside_pixels_white':bool(np.all(b[~keep]==255)),'kept_pixel_fraction':float(keep.mean()),'mask_version':s['mask_version']};maskchecks.append(check)
  if not all(check[k] for k in ['original_file_sha_verified','mask_file_sha_verified','inside_pixels_identical','outside_pixels_white']):errors.append({'mask_pixel_failed':check})
write(out/'mask-pixel-audit.json',maskchecks)
groups=collections.defaultdict(list)
for r in reviews:groups[r['review_key']].append(r)
packets=[{'group':k,'review_key':key,'condition':rr[0]['condition'],'text':rr[0]['output'],'members':[{a:r[a] for a in ['model','id','task','stage','history']} for r in rr]} for k,(key,rr) in enumerate(groups.items())];write(out/'review-packets.json',packets)
terminal={'batches':batches,'errors':errors,'logical_completed':len(rows),'unique_physical_tensors_hashed':len(hash_cache),'unique_tensor_sha256s':len(query_cache),'source_pairs_audited':len(pairs),'source_cpu_matches_actual':sum(r['cohort']=='source' and r.get('cpu_preflight_matches_actual',False) for r in rows),'all_expected_complete':len(batches)==9 and all(b['logical_completed']==b['expected'] and b['status'].get('phase')=='finished' and not b['failed'] for b in batches) and not errors,'all_replies_reached_native_eos':all(not b['truncated'] for b in batches),'truncation_policy':'A capture ending at the prespecified generation cap is complete but its reply is censored. Retain first-query metrics; exclude from complete-reply/action comparisons. Preserve and report every censored case without post-hoc cap extension.'};write(out/'terminal-audit.json',terminal)
with (out/'measurements.csv').open('w',newline='') as f:
 fields=[k for k,v in rows[0].items() if not isinstance(v,(list,dict))] if rows else [];w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
print(json.dumps({'logical_completed':len(rows),'source_pairs':len(pairs),'unique_review_outputs':len(packets),'errors':errors[:10],'complete':terminal['all_expected_complete']}))
