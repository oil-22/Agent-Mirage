import collections,copy,gzip,hashlib,io,json,pathlib,shutil
from PIL import Image
r=pathlib.Path('/data/researcher/attention-audit-20261031');base=pathlib.Path('/data/researcher/attention-audit-20261102');meta=base/'native-button-metadata/mirage-trace/Qwen3.5-9B/VisualWebArena__buttons_only';dest=base/'four-injection-campaign';dest.mkdir(exist_ok=True);outassets=dest/'assets';outassets.mkdir(exist_ok=True)
assets=r/'inputs/mirage-trace/_shared/input-images/_embedded-input-images'
links={pathlib.PurePosixPath(n).stem:l for n,s,t,l in (json.loads(x) for x in gzip.open(r/'members.jsonl.gz','rt')) if '/_embedded-input-images/' in n and t=='1'}
def storedata(data,suffix):
 h=hashlib.sha256(data).hexdigest();target=outassets/h[:2]/(h+suffix);target.parent.mkdir(exist_ok=True)
 if not target.exists():target.write_bytes(data)
 return 'archive-image://sha256/'+h
def store(h):
 pp=list(assets.glob('*/'+h+'.*'))
 if not pp and h in links and (r/'inputs'/links[h]).is_file():pp=[r/'inputs'/links[h]]
 if not pp:raise FileNotFoundError(h)
 p=pp[0];b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==h
 return storedata(b,p.suffix)
options=collections.defaultdict(list);rejected=[]
for p in sorted(meta.glob('**/model_delivery.jsonl')):
 ledger=[json.loads(l) for l in p.read_text().splitlines() if l.strip()]
 task=p.parent.parent.name
 for row in ledger:
  if not row.get('injection_fired') or not row.get('synthetic_partial_rendering') or row.get('capture_sha256')==row.get('delivered_sha256'):continue
  requestpath=r/'inputs'/p.parent.relative_to(base/'native-button-metadata')/'requests'/f"{row['step']:03d}.json"
  if requestpath.exists():options[task].append((str(p),row,ledger,requestpath))
  break
cases=[];selected=[]
for ti,(task,opts) in enumerate(sorted(options.items())):
 for p,row,ledger,rp in opts:
  try:
   req=json.loads(rp.read_text());images=[(mi,bi,b['image_url']['url']) for mi,m in enumerate(req['messages']) if isinstance(m['content'],list) for bi,b in enumerate(m['content']) if b.get('type')=='image_url'];assert images
   mi,bi,url=images[-1];assert url.rsplit('/',1)[-1]==row['delivered_sha256']
   normal=store(row['capture_sha256']);masked=store(row['delivered_sha256']);prev=next(x for x in ledger if x['step']==row['step']-1);stale=store(prev['capture_sha256'])
   imgpath=next(outassets.glob('*/'+row['capture_sha256']+'.*'));image=Image.open(imgpath);buf=io.BytesIO();Image.new('RGB',image.size,'white').save(buf,format='PNG');blank=storedata(buf.getvalue(),'.png')
   for m in req['messages']:
    if isinstance(m['content'],list):
     for b in m['content']:
      if b.get('type')=='image_url':b['image_url']['url']=store(b['image_url']['url'].rsplit('/',1)[-1])
   old=req['messages'][1:-1];assert all(m['role']==('user' if k%2==0 else 'assistant') for k,m in enumerate(old))
   assert mi==len(req['messages'])-1
   for hist in ['full','last2','none']:
    request=copy.deepcopy(req);kept=old if hist=='full' else old[-4:] if hist=='last2' else [];request['messages']=[req['messages'][0]]+copy.deepcopy(kept)+[copy.deepcopy(req['messages'][-1])]
    for condition,delivery in [('current_control',normal),('blank_replace',blank),('silent_drop',None),('stale_replace',stale),('buttons_only',masked)]:
     modified=copy.deepcopy(request);content=modified['messages'][-1]['content']
     if delivery:content[bi]['image_url']['url']=delivery
     else:content.pop(bi)
     cases.append({'id':f'F{ti:02d}-{hist}-{condition}','task':task,'app':'VisualWebArena','stage':'archived_injection','step':row['step'],'history':hist,'condition':condition,'request':modified,'source_archive_path':str(rp.relative_to(r/'inputs')),'source_archived_json_sha256':hashlib.sha256(rp.read_bytes()).hexdigest(),'current_image_sha256':row['capture_sha256'],'native_mask_sha256':row['delivered_sha256'],'previous_image_sha256':prev['capture_sha256'],'original_history_turns':len(old)//2,'kept_history_turns':len(kept)//2})
   selected.append({'task':task,'step':row['step'],'source':str(rp.relative_to(r/'inputs')),'ledger':row,'history_turns':len(old)//2});break
  except Exception as e:rejected.append({'task':task,'source':p,'error':repr(e)})
plan={'selection':'All distinct VWA tasks with restorable archived native buttons-only injection and captured original, sorted by task and source path before any new outputs. One prefix per task. No new mask algorithm, no mismatch between captured frame and mask.','scope':'Paired fixed-snapshot five conditions, three textual history windows. Reference image bytes and all non-current-image text held fixed within window. Native qwen9 trajectories are shared prefixes, not native trajectories for other models. Timing stages are not inferred from these injection-selected snapshots.','independent_tasks':len(selected),'max_new_tokens':2048,'sources':selected,'rejected_candidates':rejected,'cases':cases}
(dest/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2));(dest/'plan.sha256').write_text(hashlib.sha256((dest/'plan.json').read_bytes()).hexdigest())
print(json.dumps({'independent_tasks':len(selected),'cases_per_model':len(cases),'rejected_candidates':len(rejected),'first_rejections':rejected[:3],'steps':collections.Counter(x['step'] for x in selected)}))
