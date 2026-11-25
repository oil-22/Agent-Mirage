"""Portable v2 verifier: python verify.py [dataset_directory]. Requires Pillow.

Checks training files, independent source/parent relationships, decoded visual identities, split
isolation, frozen evaluations, action formatting, and construction evidence. Does not train a model.
"""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,math,re,sys
from PIL import Image
def require(v,msg):
    if not v:raise ValueError(msg)
def digest(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def data(p):return json.loads(Path(p).read_bytes())
def lines(p):
    with Path(p).open('rb') as f:return [json.loads(x) for x in f if x.strip()]
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def viewkey(row):return (row['images'][0],row['prompt'],row['images'][1])
def groups(src):
    return [(k,src[k]) for k in ('family_id','task_id','trajectory_id','event_id') if src.get(k)]+[('capture',src[k]) for k in ('capture_id','before_capture_id') if src.get(k)]
def check(folder,report=True):
    p=Path(folder).resolve();splits=('train','val','test');rs=lines(p/'manifest.jsonl')
    audit=lines(p/'audit.jsonl');by={r['sample_id']:r for r in rs};by_a={r['sample_id']:r for r in audit}
    require(len(by)==len(rs)==len(by_a)==len(audit) and by.keys()==by_a.keys(),'Duplicate/missing sample or audit ID')
    prot=data(p/'split-guards.json');held=prot['regression_png_to_visual_sha256'];blocked=set(held.values())
    proto=data(p/'protocol.json');require(proto['answer_codes']=={'A':'YES','B':'NO'},'Native answer codes')
    groupsplit={};coresplit={};hashsplit={};images={};near=defaultdict(list);keys=set();labels={};id_obs={}
    inputs=set();stats={'splits':{},'by_origin':{},'by_evidence':{},'same_rendering':{}}
    def mark(d,k,s):require(d.setdefault(k,s)==s,'Split overlap: '+str(k))
    def image(h,s):
        require(isinstance(h,str) and re.fullmatch(r'[0-9a-f]{64}',h) is not None and h not in held,'Invalid or protected digest: '+str(h))
        if h not in images:
            f=p/'images'/(h+'.png');require(digest(f)==h,'PNG bytes: '+h)
            with Image.open(f) as im:
                w,t=im.size;require(im.format=='PNG' and im.n_frames==1 and w*t<=4194304,'Invalid PNG: '+h)
                rgb=im.convert('RGB');full=sha(canon([w,t])+rgb.tobytes())
                if t>w:
                    rgb=rgb.crop((0,round(t*.04),w,round(t*.968)));core=sha(canon(list(rgb.size))+rgb.tobytes())
                else:core=full
            require(core not in blocked,'Protected decoded pixels: '+h);images[h]=(core,w,t,full)
        core,w,t,full=images[h];mark(hashsplit,h,s);mark(coresplit,core,s);mark(coresplit,full,s);return images[h]
    for s in splits:
        views=lines(p/(s+'.jsonl'));mm=[r for r in rs if r['split']==s];require(len(views)==len(mm),'File/manifest count: '+s)
        stats['splits'][s]=dict(Counter(r['label'] for r in mm))
        stats['by_origin'][s]={k:dict(Counter(r['label'] for r in mm if r['origin']==k)) for k in sorted({r['origin'] for r in mm})}
        stats['by_evidence'][s]=dict(Counter(r['evidence_kind'] for r in mm))
        if s!='train':require(digest(p/(s+'.jsonl'))==prot['frozen_v1'][s],'Frozen split changed: '+s)
        for r,v in zip(mm,views):
            i=r['sample_id'];au=by_a[i];b,e=(r[k+'_sha256'] for k in ('before','candidate'));a=r['action'];l=r['label'];origin=r['origin']
            require(i=='jev-'+sha(canon([b,a,e]))[:24] and au['origin']==origin,'ID/provenance: '+i)
            require(set(v)=={'images','prompt','label'} and v['images']==[r['before_png'],r['candidate_png']]==['images/'+h+'.png' for h in (b,e)] and l==v['label'] and l in ('YES','NO'),'Three-field native input: '+i)
            act=canon(a).decode();require('<|' not in act and '|>' not in act and v['prompt']==proto['user_text'].replace('{canonical_action_json}',act),'Native prompt: '+i)
            k=viewkey(v);require(k not in keys,'Duplicate input: '+i);keys.add(k);labels[k]=(s,l,i)
            x,w,t,_=image(b,s);y,ww,tt,_=image(e,s);inputs.update((b,e));require((w,t)==(ww,tt),'Mismatched viewports: '+i)
            pool=near[x,y,a['type']]
            for old in pool:
                eq=math.hypot((a['x']-old['x'])*w/1000,(a['y']-old['y'])*t/1000)<=6 if a['type']=='click' else old==a
                require(not eq,'Visually equivalent action and image pair: '+i)
            pool.append(a)
            for g in groups(r):mark(groupsplit,g,s)
            for h in au.get('support_images',[]):image(h,s)
            for z in [au.get('source',au.get('evidence',{}).get('source',{})),*au.get('donor_sources',[])]:
                for g in groups(z):mark(groupsplit,g,s)
            observed=origin!='constructed';require(r['pair_observed'] is observed,'Origin flag: '+i)
            if observed:require(r['receipt_valid'] is True and bool(r['capture_id']),'Observed pair lacks receipt: '+i)
            else:require(l=='NO' and s=='train' and r['receipt_valid'] is None and r['capture_id'] is None,'Constructed pair claims actual delivery: '+i)
            if origin=='observed_v1':
                require(r['source_observation_id'] in r['all_observation_ids'],'v1 source binding: '+i)
                for o in r['all_observation_ids']:
                    require(o not in id_obs,'Repeated v1 source');id_obs[o]=i
            if not observed or origin=='observed_matched':
                z=au['evidence'];parent=by[z['parent_sample_id']]
                require(parent['split']=='train' and parent['pair_observed'] and parent['label']=='YES' and parent['phase']=='settled' and parent['before_sha256']==b and parent['action']==a and parent['candidate_sha256']==z['expected_after_sha256'] and image(z['expected_after_sha256'],s)[0] not in (y,x),'Missing distinct positive control: '+i)
                d=z['donor'];require(d['hash']==e,'Donor hash mismatch: '+i)
                kind=r['evidence_kind'];ps=au['source'] if not observed else au['donor_sources'][0]
                if kind=='before_replay':require(e==b and d['sample_id']==parent['sample_id'] and d['role']=='before','Invalid replay')
                elif kind in ('earlier_same_page','earlier_unchanged_field','earlier_list_view'):
                    require(b!=e and d['source_run']==ps['source_run'] and d['step']<ps['step'] and d['route']==ps['before_route'] and d['receipt'],'Invalid earlier screenshot: '+i)
                elif kind=='different_typed_value':
                    don=by[d['sample_id']];require(don['split']=='train' and don['label']=='YES' and don['pair_observed'] and don['before_sha256']==b and don['candidate_sha256']==e and don['action']['text']!=a['text'],'Invalid contrasting typed field: '+i)
                else:raise ValueError('Unrecognized construction rule '+kind)
            if origin=='observed_injection':
                src=au['source'];h=src.get('archived_delivered_sha256') or src['probe']['delivered_sha256'];require(h==e and src.get('after_request',src.get('probe',{}).get('input_ids_sha256')),'Missing injected delivery binding: '+i)
                if r['evidence_kind']=='delivered_blank':
                    with Image.open(p/v['images'][1]) as im:require(im.convert('RGB').getextrema()==((255,255),)*3,'Blank-frame evidence: '+i)
            if s!='train':require(origin=='observed_v1','Constructed/added row in held-out split')
        stats['same_rendering'][s]=dict(Counter(r['label']+':'+('same' if images[r['before_sha256']][0]==images[r['candidate_sha256']][0] else 'different') for r in mm))
    require(sum(map(sum,(z.values() for z in stats['splits'].values())))==len(rs) and sum(stats['splits']['train'].values())>=3000,'Train minimum or split accounting')
    v1p=lines(p/'v1-provenance.jsonl');require(set(id_obs)=={z['observation_id'] for z in v1p} and len(v1p)==len(id_obs),'v1 source index coverage')
    for z in v1p:
        i=id_obs[z['observation_id']];r=by[i];s=r['split'];fam=z.get('family_key',z['family'])
        for g in groups(dict(family_id=fam,task_id=z.get('task_key',fam+':'+z['task']),trajectory_id=z['suite']+':'+z['run'],event_id=z['suite']+':'+z['event'],capture_id=z['capture_id'],before_capture_id=z['before_capture_id'])):mark(groupsplit,g,s)
        if r['source_observation_id']==z['observation_id']:require([z['before_sha256'],z['action'],z['candidate_sha256']]==[r['before_sha256'],r['action'],r['candidate_sha256']],'v1 representative: '+i)
    if (p/'train-balanced.jsonl').exists():
        bb=lines(p/'train-balanced.jsonl');counter=Counter(r['label'] for r in bb)
        require(counter.get('YES')==counter.get('NO') and len({viewkey(r) for r in bb})==len(bb) and all(labels.get(viewkey(r),())[:2]==('train',r['label']) for r in bb),'Balanced view is not a distinct train-only subset')
        stats['balanced_train']=dict(counter)
    stats.update(rows=len(rs),observed=sum(r['pair_observed'] for r in rs),constructed=sum(not r['pair_observed'] for r in rs),model_input_pngs=len(inputs),audit_only_pngs=len(set(images)-inputs),v1_observations=len(v1p),cross_split_shared_images=0,cross_split_shared_source_groups=0,duplicate_inputs=0,conflicting_exported_labels=0,regression_images_checked=len(held))
    if report:print(json.dumps({k:v for k,v in stats.items() if k not in ('by_evidence','same_rendering','by_origin')},ensure_ascii=False,indent=2))
    return rs,stats
if __name__=='__main__':check(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent)
