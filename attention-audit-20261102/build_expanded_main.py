import base64,collections,copy,gzip,hashlib,io,json,pathlib,re,shutil,time
from PIL import Image
root=pathlib.Path('/data/researcher/attention-audit-20261031')
inputs=root/'inputs'
assets=inputs/'mirage-trace/_shared/input-images/_embedded-input-images'
image_links={}
for line in gzip.open(root/'members.jsonl.gz','rt'):
    n,size,typ,link=json.loads(line)
    if '/_embedded-input-images/' in n and typ=='1':image_links[pathlib.PurePosixPath(n).stem]=link
dest=pathlib.Path('/data/researcher/attention-audit-20261102/campaign');dest.mkdir(parents=True,exist_ok=True)
campaign_assets=dest/'assets';campaign_assets.mkdir(exist_ok=True)
trajectories=json.loads((root/'trajectories.json').read_text())
candidates=collections.defaultdict(list)
for row in trajectories:
    p=row['trajectory']
    if p.endswith('/control') and '/OSWorld__' in p and row['requests']>=15:
        app=p.split('/runs/',1)[1].split('/')[0]
        task=p.split('/')[-2]
        priority=5 if 'results-action-v5/' in p else 4 if 'results-grounding-v3/' in p else 3 if 'results-action-v4/' in p else 2
        candidates[app].append((task,-priority,p,row))
old=json.loads((root/'campaign/plan.json').read_text());previous={r['task'] for r in old['sources']}
selected=[]
for app,options in sorted(candidates.items()):
    seen=set()
    for task,_,p,row in sorted(options):
        if task in seen or task in previous:continue
        seen.add(task);selected.append((app,task,row))

assert len(selected)>=8,len(selected)
def digest(data):return hashlib.sha256(data).hexdigest()
def getimage(req):
    msg=req['messages'][-1]
    items=msg['content']
    assert isinstance(items,list)
    images=[(i,x['image_url']['url']) for i,x in enumerate(items) if x.get('type')=='image_url']
    assert images
    return images[-1]
def loadimage(url):
    if url.startswith('archive-image://sha256/'):
        h=url.rsplit('/',1)[1];matches=list(assets.glob('*/'+h+'.*'))
        if not matches and h in image_links and (inputs/image_links[h]).is_file():matches=[inputs/image_links[h]]
        assert len(matches)==1,(h,matches,image_links.get(h))
        data=matches[0].read_bytes();assert digest(data)==h
        return data,matches[0].suffix
    if url.startswith('data:image/'):
        return base64.b64decode(url.split(',',1)[1]),'.png'
    raise ValueError(url)
def storeimage(data,suffix):
    h=digest(data);p=campaign_assets/h[:2]/(h+suffix);p.parent.mkdir(exist_ok=True)
    if not p.exists():p.write_bytes(data)
    return 'archive-image://sha256/'+h
cases=[];sources=[];future=[]
for ti,(app,task,row) in enumerate(selected):
    path=inputs/row['trajectory']/'requests';steps=row['steps']
    stage_steps={stage:steps[round((len(steps)-1)*q)] for stage,q in [('early',.1),('middle',.5),('late',.9)]}
    for stage,step in stage_steps.items():
        source=path/f'{step:03d}.json';req=json.loads(source.read_text());originalsha=digest(source.read_bytes())
        image_idx,url=getimage(req);data,suffix=loadimage(url);current=storeimage(data,suffix)
        for m in req['messages']:
            if isinstance(m['content'],list):
                for item in m['content']:
                    if item.get('type')=='image_url':
                        b,s=loadimage(item['image_url']['url']);item['image_url']['url']=storeimage(b,s)
        image=Image.open(io.BytesIO(data));blank=Image.new('RGB',image.size,'white');buffer=io.BytesIO();blank.save(buffer,format='PNG');blankurl=storeimage(buffer.getvalue(),'.png')
        prevstep=max(s for s in steps if s<step);prev=json.loads((path/f'{prevstep:03d}.json').read_text());_,prevurl=getimage(prev);pb,ps=loadimage(prevurl);staleurl=storeimage(pb,ps)
        for history in ['full','last2','none']:
            base=copy.deepcopy(req)
            original_messages=base['messages'];history_messages=original_messages[1:-1]
            assert sum(m['role']=='assistant' for m in history_messages)==(len(history_messages)//2)
            assert all(history_messages[i]['role']==('user' if i%2==0 else 'assistant') for i in range(len(history_messages)))
            kept=history_messages if history=='full' else history_messages[-4:] if history=='last2' else []
            base['messages']=[original_messages[0]]+kept+[original_messages[-1]]
            for condition in ['current_control','blank_replace','silent_drop','stale_replace']:
                modified=copy.deepcopy(base)
                content=modified['messages'][-1]['content']
                if condition=='silent_drop':content.pop(image_idx)
                elif condition=='blank_replace':content[image_idx]['image_url']['url']=blankurl
                elif condition=='stale_replace':content[image_idx]['image_url']['url']=staleurl
                cid=f'T{ti:02d}-{stage}-{history}-{condition}'
                cases.append({'id':cid,'task':task,'app':app,'stage':stage,'step':step,'history':history,'condition':condition,'source_archive_path':str(source.relative_to(inputs)),'source_archived_json_sha256':originalsha,'current_image_sha256':digest(data),'previous_image_sha256':digest(pb),'stale_pixels_identical':data==pb,'original_history_turns':len(history_messages)//2,'kept_history_turns':len(kept)//2,'request':modified})
        sources.append({'task':task,'app':app,'stage':stage,'step':step,'trajectory_length':len(steps),'source':str(source.relative_to(inputs)),'sha256':originalsha,'image_sha256':digest(data),'image_size':image.size,'previous_image_sha256':digest(pb)})
    # Save actual later clean snapshots for source-round reading, without claiming a rollout.
    middle=stage_steps['middle']
    for gap in [1,3,5]:
        target=middle+gap
        if target not in steps:continue
        req=json.loads((path/f'{target:03d}.json').read_text())
        try:
            for m in req['messages']:
                if isinstance(m['content'],list):
                    for item in m['content']:
                        if item.get('type')=='image_url':
                            b,s=loadimage(item['image_url']['url']);item['image_url']['url']=storeimage(b,s)
            future.append({'task_index':ti,'task':task,'app':app,'source_step':middle,'target_step':target,'gap':gap,'request':req})
        except AssertionError:
            print('Future snapshot image restoration still pending',task,target,flush=True)
plan={'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'selection':'All additional distinct task UUIDs not in the 20261031 nine-task campaign, lexicographically per available OSWorld app among never-injected archived control trajectories with >=15 decisions; latest archived protocol preferred. No selection by new outputs or attention.','stage_definition':'Archived decision index quantiles 0.1,0.5,0.9, rounded before model execution; stage is trajectory time, not semantic task completion.','history_levels':['none','last2','full'],'conditions':['current_control','blank_replace','silent_drop','stale_replace'],'max_new_tokens':2048,'scope':'Shared clean archived prefixes from Qwen27, evaluated with each model native template. Offline single-decision intervention; no GUI execution, no claim of native GLM or Qwen9 trajectories. Buttons-only mode is already covered by the archived 39-task experiment; no new timing generalization for that mode.','independent_tasks':len(selected),'sources':sources,'cases':cases}
(dest/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
(dest/'future-snapshots.json').write_text(json.dumps(future,ensure_ascii=False))
(dest/'plan.sha256').write_text(digest((dest/'plan.json').read_bytes()))
print(json.dumps({'tasks':len(selected),'snapshots':len(sources),'cases_per_model':len(cases),'assets':len(list(campaign_assets.glob('*/*'))),'future_snapshots':len(future),'plan_sha256':digest((dest/'plan.json').read_bytes())},indent=2))
