"""Keep the held-out views frozen. Join real labels first, then contrast only established training effects."""
from common import *
from qualify import arcsrc,ns
from collections import Counter,defaultdict
from urllib.parse import urlsplit,parse_qs
import os,shutil

def compatible_box(ax,bx):
    x,y,r,t=ax;u,v,rr,tt=bx
    return max(0,min(r,rr)-max(u,x))*max(0,min(t,tt)-max(y,v)) >= .28*min((r-x)*(t-y),(rr-u)*(tt-v))
def pagekind(u):return parse_qs(urlsplit(u or '').query).get('page',['home'])[0]
def donor_witness(p,s,d):
    """An earlier clean same-route screen that establishes the old state, beyond mere step order."""
    b=p['before_sha256'];post=p['candidate_sha256'];h=d['hash'];a=p['action'];meth=p['evidence_kind']
    if h in (b,post) or not s.get('before_route') or s['before_route']!=d.get('route'):return
    x,z,y=(small(j) for j in (b,h,post))
    if x.shape!=z.shape or x.shape!=y.shape:return
    mask=cv2.absdiff(x,z).max(2)>=20;dif=cv2.absdiff(x,y).max(2)>=24
    n=int(mask.sum());delta=int(dif.sum());height,w=mask.shape
    if n<50 or delta<90:return
    ys,xs=np.where(mask);box=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
    info=dict(earlier_step=d['step'],action_step=s['step'],same_route=d['route'],thumbnails=[w,height],earlier_changed_box=box,earlier_changed_fraction=round(float(mask.mean()),5),normal_transition_changed_fraction=round(float(dif.mean()),5))
    if meth=='rendered_navigation':
        if pagekind(s['before_route'])==pagekind(s['after_route']) and s['before_route']==s['after_route']:return
        if a['type']=='click':
            cx=int(a['x']*w/1000);cy=int(a['y']*height/1000)
            if mask[max(0,cy-5):cy+6,max(0,cx-9):cx+10].any():return
        if mask.mean()<=.03 and box[3]-box[1]<=.34*height and box[2]-box[0]<=.75*w and (dif & ~mask).sum()>=.94*delta:
            return 'earlier_same_page',dict(**info,visible_witness='Only a localized part of the old page changed; the navigation target is still in its old state and at least 94% of the normal transition footprint remains as before.')
        # Real earlier search-list scroll position vs. a recorded, distinct item destination.
        # Require spatially separated unique patches at a common translation plus exact route history.
        if pagekind(s['before_route'])=='search' and pagekind(s.get('after_route'))=='item' and a['type']=='click' and mask.mean()>.04:
            for direction in ('up','down'):
                q=scrollevidence(x,z,direction)
                if q and q['total']>=6:
                    return 'earlier_list_view',dict(**info,destination=s['after_route'],translation=q,visible_witness='The earlier image is a displaced viewport of the same search list. It is not the item detail page reached by the recorded click.')
    if meth in ('visible_typed_text','visible_focus_ring') and n<.06*mask.size and (dif & mask).sum()<=.01*delta:
        ev=s.get('target_evidence',{});roi=ev.get('box') or ev.get('focus_box')
        if not roi:return
        l,t,r,bt=roi
        if 'focus_box' in ev:r+=l;bt+=t
        xb=screen(b);xh=screen(h)
        if not np.array_equal(xb[t:bt,l:r],xh[t:bt,l:r]):return
        if box[3]-box[1]>.4*height:return
        return 'earlier_unchanged_field',dict(**info,target_box=[l,t,r,bt],target_pixels_identical_to_before=True)
def main():
    old=list(lines(V1/'manifest.jsonl'));prov={r['observation_id']:r for r in lines(V1/'provenance.jsonl')}
    arc_ev={r['pair_id']:r for r in lines(V1/'archive-label-evidence.jsonl')}
    qualified=list(lines(WORK/'qualified.jsonl'));nat=load(NAT/'extract.json')
    archived=list(lines(V1/'additional-archive-observations.jsonl'))
    occ=defaultdict(list);history=defaultdict(dict);parents_by_source=defaultdict(list);actual={};counter=Counter()
    for o in archived:
        if o['assigned_split']!='train':continue
        b=o['before_sha256'];i=o['step'];run=o['source_run']
        history[run][i]=dict(hash=b,route=o['before_url_path'],step=i,receipt=o['source_before_request'],file=o['source_delivery'],trajectory_id='archive_vwa:'+o['run'],event_id='archive_vwa:'+o['event'],capture_id=o['before_capture_id'],family_id=family(o),task_id=task(o))
        occ[o['pair_id']].append(o)
    for z in nat['events']:
        run=z['source_run'];i=z['step'];s=ns(z);b=z['before']['png_sha256']
        history[run][i]=dict(hash=b,route=z['trace']['before_route'],step=i,receipt=z['before']['input_ids_sha256'],file=run+'/'+z['before']['source_png'],capture_id=s['before_capture_id'],trajectory_id=s['trajectory_id'],event_id=s['event_id'],family_id=s['family_id'],task_id=s['task_id'])
        actual[pid(b,z['action'],z['after']['png_sha256'])]=s
    reg=heldout_images();reg_core={};idx=load(V1/'archive-content-index.json')
    for h in reg:
        try:p=path(h)
        except FileNotFoundError:p=next((ROOT/'reports/jev-temporal-gate-20261122/attempts').rglob(h+'.png'))
        assert sha(p.read_bytes())==h;reg_core[h]=identity_file(p)[0]
    guardcores=set(reg_core.values());sp={};gp={};near=defaultdict(list);rawlabels=defaultdict(list);source={};audit={};allm=[]
    def ident(h):
        if h not in idx:idx[h]=list(identity_file(path(h))[:3])
        return idx[h]
    def groups(s):
        return [(k,s[k]) for k in ('family_id','task_id','trajectory_id','event_id') if s.get(k)]+[('capture_id',s[k]) for k in ('capture_id','before_capture_id') if s.get(k)]
    def cols(o):return [o['before_sha256'],o['candidate_sha256']]
    for r in old:
        b,e=cols(r);a=r['action'];s=r['split'];i=r['sample_id'];o=prov[r['source_observation_id']];k=pid(b,a,e)
        r.update(origin='observed_v1',pair_observed=True,before_capture_id=o['before_capture_id'])
        src=arcsrc(o);src['target_evidence']=arc_ev.get(k,{}).get('evidence',{})
        source[i]=src;ev=dict(v1_representative=r['source_observation_id'],pair_id=k,archive_evidence=arc_ev.get(k),source=src)
        audit[i]=dict(sample_id=i,origin=r['origin'],evidence=ev)
        for oid_ in r['all_observation_ids']:
            v=prov[oid_]
            for g in groups(arcsrc(v)):assert gp.setdefault(g,s)==s
        for h in (b,e):
            hh=ident(h)[0];assert hh not in guardcores and sp.setdefault(hh,s)==s
        near[ident(b)[0],ident(e)[0],a['type']].append((a,r['label'],i));allm.append(r)
    # Protect independent definite labels including additional actual occurrences and visual aliases.
    for r in old:
        b,e=cols(r);rawlabels[ident(b)[0],ident(e)[0],r['action']['type']].append((r['action'],r['label']))
    for r in archived:
        if not r.get('label'):continue
        b,e=cols(r);a=r['action'];rawlabels[ident(b)[0],ident(e)[0],a['type']].append((a,r['label']))
    for q in qualified:
        b=q['before'];e=q['after'];a=q['action'];rawlabels[ident(b)[0],ident(e)[0],a['type']].append((a,q['label']))
    def allowed(h):
        if h in reg:return False
        try:v=ident(h)[0]
        except FileNotFoundError:return False
        return v not in guardcores and sp.get(v,'train')=='train'
    def add(b,a,e,label,method,reason,src,ev,origin,support=(),donors=()):
        obs=not origin.startswith('constructed');i=sid(b,a,e)
        if not all(allowed(h) for h in (b,e,*support)):counter['excluded: protected, held-out, or missing support image']+=1;return
        x,w,t=ident(b);y,w1,t1=ident(e);key=(x,y,a['type'])
        if (w,t)!=(w1,t1):counter['excluded: viewport mismatch']+=1;return
        if any(l!=label and pixel_close(other,a,w,t) for other,l in rawlabels[key]):counter['excluded: conflicts with independent definite label']+=1;return
        if any(pixel_close(other,a,w,t) for other,_,_ in near[key]):counter['merged: equivalent input']+=1;return
        if any(gp.get(g,'train')!='train' for s in (src,*donors) for g in groups(s)):counter['excluded: held-out source group']+=1;return
        for s in (src,*donors):
            for g in groups(s):gp[g]='train'
        near[key].append((a,label,i));sp[x]=sp[y]='train'
        for h in support:sp[ident(h)[0]]='train'
        m=dict(sample_id=i,split='train',before_png=pic(b),before_sha256=b,action=a,candidate_png=pic(e),candidate_sha256=e,label=label,reason=reason,evidence_kind=method,origin=origin,pair_observed=obs,receipt_valid=True if obs else None,capture_id=src['capture_id'] if obs else None,before_capture_id=src['before_capture_id'],phase='no_change' if method=='visible_scroll_boundary' else 'settled' if label=='YES' else 'early' if 'stale' in method else 'unrelated',source_suite=src['suite'],**{k:src[k] for k in ('family_id','task_id','trajectory_id','event_id')})
        allm.append(m);source[i]=dict(src);audit[i]=dict(sample_id=i,origin=origin,source=src,evidence=ev,support_images=sorted(set(support)),donor_sources=list(donors));return m
    for q in sorted(qualified,key=lambda q:(q['origin']!='observed_injection',q['method'],q['source']['source_run'],q['source']['step'])):
        s=q['source'];ev=q['evidence'];support=[ev[k] for k in ('normal_after_sha256','normal_capture_sha256','reference') if ev.get(k)]
        m=add(q['before'],q['action'],q['after'],q['label'],q['method'],q['reason'],s,ev,q['origin'],support)
        if m:source[m['sample_id']]['target_evidence']=ev
    print('observed before constructing:',dict(Counter((r['split'],r['origin'],r['label']) for r in allm)),flush=True)
    trainpos=[r for r in allm if r['split']=='train' and r['label']=='YES' and r['phase']=='settled' and ident(r['before_sha256'])[0]!=ident(r['candidate_sha256'])[0] and r['evidence_kind'] not in ('visually_supported_noop','visible_scroll_boundary') and 'current sort option' not in r['reason']]
    for r in trainpos:
        b,e=cols(r)
        if r.get('all_observation_ids'):
            for oi in r['all_observation_ids']:
                o=prov[oi]
                if o.get('assigned_split')=='train' and [o['before_sha256'],o['action'],o['candidate_sha256']]==[b,r['action'],e]:
                    parents_by_source[r['sample_id']].append(arcsrc(o))
        if source[r['sample_id']].get('step') is not None:parents_by_source[r['sample_id']].append(source[r['sample_id']])
    def counterfactual(p,s,h,kind,why,proof,donor,extra=None):
        p_id=p['sample_id'];b=p['before_sha256'];a=p['action'];e=p['candidate_sha256'];k=pid(b,a,h)
        df=dict(parent_sample_id=p_id,expected_after_sha256=e,expected_positive_reason=p['reason'],expected_evidence_kind=p['evidence_kind'],rule=proof,donor=dict(donor))
        # When an exact independently recorded triple exists, credit that real observed pair.
        # Its label still derives from this positive/contrast witness, not from a model response.
        actualsrc=arcsrc(occ[k][0]) if occ.get(k) else actual.get(k)
        supp=[e,h]+([extra] if extra else [])
        if actualsrc:
            return add(b,a,h,'NO',kind,why,actualsrc,df,'observed_matched',supp,(s,donor))
        # Parent receipt refers to its original normal candidate only. The constructed pair has no receipt.
        return add(b,a,h,'NO',kind,why,s,df,'constructed',supp,(donor,))
    def ref(p,field):
        s=source[p['sample_id']];d={k:s[k] for k in ('family_id','task_id','trajectory_id','event_id','source_run','step')};old=(field=='before');h=p['before_sha256' if old else 'candidate_sha256']
        d.update(hash=h,role=field,capture_id=s['before_capture_id' if old else 'capture_id'],sample_id=p['sample_id']);return d
    starts=defaultdict(list)
    for p in trainpos:starts[ident(p['before_sha256'])[0]].append(p)
    # Both strings really were newly rendered from the same starting field. Use at most two other values.
    for p in trainpos:
        if p['evidence_kind']!='visible_typed_text':continue
        s=source[p['sample_id']];target=norm(p['action']['text']);left=s.get('target_evidence',{}).get('box')
        if not left:continue
        b=p['before_sha256'];options=[]
        for d in starts[ident(b)[0]]:
            if d['evidence_kind']!='visible_typed_text' or d['before_sha256']!=b:continue
            v=norm(d['action']['text']);other=source[d['sample_id']].get('target_evidence',{});right=other.get('box')
            if target in v or v in target or not right or not compatible_box(left,right) or target in norm(other.get('after','')):continue
            options.append(d)
        n=0
        for d in sorted(options,key=lambda d:sha((p['sample_id']+d['sample_id']).encode())):
            dr=ref(d,'after');ev=dict(expected_ocr=s['target_evidence'],other_ocr=source[d['sample_id']]['target_evidence'],other_positive_sample_id=d['sample_id'],other_executed_text=d['action']['text'])
            if counterfactual(p,s,d['candidate_sha256'],'different_typed_value','The same input field displays a different, independently read value. The dispatched text and an explicit failure message are absent.',ev,dr):n+=1
            if n>=2:break
    # Same-run earlier captures, not randomly swapped pages. Favor useful non-identical negatives.
    for p in trainpos:
        n=0;seen=set();p_id=p['sample_id']
        if p['evidence_kind'] not in ('rendered_navigation','visible_typed_text','visible_focus_ring'):continue
        for s in parents_by_source[p_id]:
            s=dict(s,target_evidence=source[p_id].get('target_evidence',{}));i=s['step'];hh=history[s['source_run']]
            for j in sorted((j for j in hh if max(0,i-12)<=j<i),reverse=True):
                d=hh[j];h=d['hash']
                if h in seen or d.get('route')!=s.get('before_route') or not allowed(h):continue
                seen.add(h);q=donor_witness(p,s,d)
                if not q:continue
                kind,ev=q;donor=dict(d,source_run=s['source_run'],role='earlier_observed_before')
                why={'earlier_same_page':'The earlier frame still shows the originating page. Only a localized unrelated area changed, and the verified navigation result is missing.','earlier_list_view':'The candidate still shows the same search-list content at another scroll position; the clicked item detail has not appeared.','earlier_unchanged_field':'The earlier frame contains another local change, but the affected field is pixel-identical to its pre-action state.'}[kind]
                if counterfactual(p,s,h,kind,why,ev,donor):n+=1
                if n>=2:break
            if n>=2:break
    for p in trainpos:
        b,e=cols(p);s=source[p['sample_id']]
        # A positively established changed outcome is required; unchanged no-op positives never seed this.
        counterfactual(p,s,b,'before_replay','The candidate repeats the original pre-action screen. The matched positive shows a visible change for this exact action, which the replay omits.',dict(exact_pre_action_png=True),ref(p,'before'))
    print('all training',dict(Counter((r['origin'],r['label']) for r in allm if r['split']=='train')),flush=True)
    (HERE/'images').mkdir(exist_ok=True)
    for n in ('protocol.json','val.jsonl','test.jsonl'):
        shutil.copyfile(V1/n,HERE/n)
    for orig,n in [('provenance.jsonl','v1-provenance.jsonl'),('archive-label-evidence.jsonl','v1-archive-label-evidence.jsonl')]:shutil.copyfile(V1/orig,HERE/n)
    train=sorted((r for r in allm if r['split']=='train'),key=lambda r:sha(('jev-v2-mix/'+r['sample_id']).encode()))
    allm=train+[r for s in ('val','test') for r in allm if r['split']==s]
    assert len(train)>=3000,(len(train),counter)
    # Training + audit reference images (including normal control frames used to certify observed injections).
    imgs={h for r in allm for h in cols(r)}|{h for m in audit.values() for h in m.get('support_images',[])}
    for h in sorted(imgs):
        dest=HERE/pic(h)
        if not dest.exists():shutil.copyfile(path(h),dest)
    writel(HERE/'train.jsonl',(dict(images=[r['before_png'],r['candidate_png']],prompt=prompt(r['action']),label=r['label']) for r in train))
    writel(HERE/'manifest.jsonl',allm);writel(HERE/'audit.jsonl',(audit[r['sample_id']] for r in allm))
    writej(HERE/'split-guards.json',dict(regression_png_to_visual_sha256=reg_core,frozen_v1={s:sha((V1/(s+'.jsonl')).read_bytes()) for s in ('val','test')},v1_manifest_sha256=sha((V1/'manifest.jsonl').read_bytes()),v1_bundle_sha256=(V1/'bundle.sha256').read_text().split()[0]))
    writej(WORK/'selection-diagnostics.json',dict(counter))
if __name__=='__main__':main()
