"""Balance BOTH labels inside EACH task without repeating a model input.

Fit disjoint observed YES rows to exact positive/negative contrasts or independently
receipt-bound control steps in the corresponding scenario. Never infer a positive
label from the scenario. No interaction, model inference or image synthesis.
"""
from collections import Counter, defaultdict
from copy import deepcopy
import os, shutil
import networkx as nx
from materials import *

def build():
    old,oa,pos,direct,refs,occ,earlier,nom,rect,templates=materials()
    options=defaultdict(list)
    for a in rows(W/'buttons-options.jsonl'):options[a['parent']].append(a['candidate'])
    guards=js(BASE/'split-guards.json')['regression_png_to_visual_sha256']
    blocked=set(guards.values());ownership={};test_families=set()
    for r in old:
        if r['split']=='test':test_families.add(r['family_id'])
        for h in (r['before_sha256'],r['candidate_sha256'],*oa[r['sample_id']].get('support_images',[])):
            x=identity(h)[0];assert ownership.setdefault(x,r['split'])==r['split']
    test_cores=sorted(k for k,v in ownership.items() if v=='test')
    incoming=defaultdict(set)
    for r in [*pos.values(),*direct]:
        for h in (r['before_sha256'],r['candidate_sha256']):incoming[identity(h)[0]].add(r['split'])
    def ok(h,s):
        x=identity(h)[0]
        # For newly recovered desktop backgrounds that become identical when the
        # panel clock is removed, assign to train; held-out copies cannot enter val.
        owner=ownership.get(x,'train' if len(incoming[x])>1 else s)
        return h not in guards and x not in blocked and owner==s
    def splitok(r):
        return all(ok(r[k],r['split']) for k in ('before_sha256','candidate_sha256')) and r['family_id'] not in test_families
    pos={i:r for i,r in pos.items() if splitok(r)}
    # Previously reviewed labels, including archived visual aliases, veto a new construction.
    known=defaultdict(list)
    def vk(b,e,t):return (identity(b)[0],identity(e)[0],t)
    def known_row(b,a,e,l):
        bucket=known[vk(b,e,a['type'])]
        if (a,l) not in bucket:bucket.append((a,l))
    for r in old:known_row(r['before_sha256'],r['action'],r['candidate_sha256'],r['label'])
    for r in rows(V1/'additional-archive-observations.jsonl'):
        if r.get('label'):known_row(r['before_sha256'],r['action'],r['candidate_sha256'],r['label'])
    for r in pos.values():known_row(r['before_sha256'],r['action'],r['candidate_sha256'],'YES')
    near=defaultdict(list)
    def reserve(b,a,e,l):
        k=vk(b,e,a['type']);_,w,h=identity(b);i=sid(b,a,e)
        if any(l!=v and close(a,z,w,h) for z,v in known[k]):return False
        for z,j in near[k]:
            if close(a,z,w,h):return i==j
        near[k].append((a,i));return True
    # Ordinary positives have already been vetted. Register them before admitting alternatives.
    pos={i:r for i,r in pos.items() if reserve(r['before_sha256'],r['action'],r['candidate_sha256'],'YES')}
    direct0={}
    for r in direct:
        b,a,e=(r[k] for k in ('before_sha256','action','candidate_sha256'))
        if not splitok(r) or not reserve(b,a,e,r['label']):continue
        if r['task']==BU and not rect.get(r['sample_id']):continue
        if r['task']==BL and (white(b) or not white(e)):continue
        direct0.setdefault(r['sample_id'],r)
    direct=list(direct0.values());blankref={}
    for r in direct:
        if r['task']==BL:
            b=r['before_sha256'];blankref.setdefault((r['split'],identity(b)[1:]),r)
    ans=[];audits={};keeprefs=set();usedmasks={};extra_images=set()
    def keep_rule(s,rule,info,h):
        if rule=='archived_white':keeprefs.add(info['blank_source_ref'])
        if rule=='archived_control_rectangles':usedmasks[info['template_ref']]=templates[s,h]
        extra_images.add(h)
    def arow(r,g,role,record=None,mate=None):
        v=dict(r,task=g,role=role,contrast_sample_id=mate,before_png=pic(r['before_sha256']),candidate_png=pic(r['candidate_sha256']))
        i=v['sample_id'];v['pair_observed']=v['origin']=='observed'
        # An explicitly replayed earlier frame is temporally earlier *content*;
        # this says nothing about the delivery time of the resulting candidate.
        if v['label']=='NO' and g==ST:v['phase']='early'
        if v['pair_observed']:
            proof=refs[i];keeprefs.add(i);record=dict(record or {},source_ref=i)
        if record is None:raise ValueError(i)
        assert i not in audits
        audits[i]=dict(sample_id=i,**record);ans.append(v);return v
    def offer(G,src,dst,record,weight):
        if not G.has_edge(src,dst) or weight<G[src][dst]['weight']:
            G.add_edge(src,dst,capacity=1,weight=weight,record=record)
    def fit(s,cap):
        sub=sorted((r for r in pos.values() if r['split']==s),key=lambda r:r['sample_id'])
        ds=[r for r in direct if r['split']==s];nn=Counter((r['task'],r['label']) for r in ds)
        direct_neg={(r['before_sha256'],can(r['action'])):[] for r in ds if r['label']=='NO'}
        for r in ds:
            if r['label']=='NO':direct_neg[r['before_sha256'],can(r['action'])].append(r)
        G=nx.DiGraph();G.add_node('start')
        for g in TASKS:
            for k in ('single','new'):G.add_node((k,g))
        for p in sub:
            i=p['sample_id'];b,a,f=(p[k] for k in ('before_sha256','action','candidate_sha256'))
            changed=identity(b)[0]!=identity(f)[0] and p['phase']=='settled'
            G.add_edge('start',i,capacity=1,weight=rank('row',i)%13)
            for g,witness in occ[i].items():
                offer(G,i,('single',g),('run',g,witness),430+rank(i,g)%35)
            for neg in direct_neg.get((b,can(a)),[]):
                j=neg['sample_id'];g=neg['task'];n=('observed',j)
                G.add_edge(n,('single',g),capacity=1,weight=0)
                offer(G,i,n,('observed_match',g,j),0 if nom[j]==f else 15)
            def option(g,h,rule,detail,cost):
                if not ok(h,s) or identity(b)[1:]!=identity(h)[1:] or identity(h)[0]==identity(f)[0]:return
                j=sid(b,a,h)
                if j in direct0 or not reserve(b,a,h,'NO'):return
                n=('variant',g,j);count=('new',g)
                witness=occ[i].get(g)
                # An independently observed negative does not always have a recovered
                # normal mate. Keep a concrete, repeatable same-before/action reference
                # for its independently selected positive even when the alternate PNG
                # is audit-only. These references are not extra training examples.
                offer(G,i,('single',g),('reference',g,h,rule,detail,witness),
                      (160 if witness else 320)+cost//3+rank(i,h)%12)
                if g==BU:
                    # Prefer a variety of full historically logged sets of controls.
                    mn=('mask',s,h);G.add_edge(n,mn,capacity=1,weight=0)
                    if not G.has_edge(mn,('tier',s,h,0)):
                        for z,lim in enumerate((10,20,40,80,160,800)):
                            tier=('tier',s,h,z);G.add_edge(mn,tier,capacity=lim,weight=z*9);G.add_edge(tier,count,capacity=lim,weight=0)
                else:G.add_edge(n,count,capacity=1,weight=0)
                offer(G,i,n,('make',g,h,rule,detail),cost+rank(i,h)%9)
            ref=blankref.get((s,identity(b)[1:]))
            if ref and not white(b):
                option(BL,ref['candidate_sha256'],'archived_white',{'blank_source_ref':ref['sample_id']},60)
            if changed and p['evidence_kind'] not in ('visible_scroll_boundary','visually_supported_noop') and 'current sort option' not in p['reason']:
                for r in earlier.get(i,[]):
                    ev=oa[r['sample_id']]['evidence']
                    option(ST,r['candidate_sha256'],'documented_earlier',{'legacy_negative_id':r['sample_id'],'source':oa[r['sample_id']]['source'],'donor':ev['donor'],'witness':ev['rule'],'legacy_evidence_kind':r['evidence_kind']},0)
                option(ST,b,'pre_action_replay',{},65)
                for h in sorted(options.get(i,[])):
                    option(BU,h,'archived_control_rectangles',{'template_ref':s+':'+h},35)
        minq=max(nn.values())
        # Every offline NO must have its original, exact before+action YES in the same split.
        # Independent YES whose paired NO was not selected must have their own scenario receipt.
        for q in range(min(cap,(len(sub)+sum(nn[g,'YES'] for g in TASKS))//3),minq-1,-1):
            total=0
            for g in TASKS:
                n=q-nn[g,'NO'];m=nn[g,'NO']-nn[g,'YES']
                assert m>=0
                for k,d in [('single',m),('new',n)]:G.nodes[k,g]['demand']=d;total+=d
            G.nodes['start']['demand']=-total
            try:_,flow=nx.network_simplex(G);break
            except nx.NetworkXUnfeasible:continue
        else:raise RuntimeError('No six-cell allocation for '+s)
        print(s,'per cell',q,'direct injections',dict(nn),flush=True)
        orig={}
        for r in ds:
            i=r['sample_id'];ar={'actual_condition':r['task']}
            if r['task']==BU:ar['rectangles']=rect[i]
            orig[i]=arow(r,r['task'],'observed_injection',ar)
        for p in sub:
            i=p['sample_id']
            if flow['start'][i]!=1:continue
            n=next(n for n,x in flow[i].items() if x);kind,g,*detail=G[i][n]['record']
            if kind=='run':
                arow(p,g,'scenario_control',{'scenario_witness':detail[0]});continue
            if kind=='observed_match':
                j=detail[0];orig[j]['contrast_sample_id']=i
                arow(p,g,'matched_control',{'match':'same ordered before image and dispatched action'},j);continue
            if kind=='reference':
                h,rule,info,witness=detail;keep_rule(s,rule,info,h)
                note=dict(comparison_only=dict(candidate_sha256=h,rule=rule,**info))
                if witness:note['scenario_witness']=witness
                arow(p,g,'audit_matched_control',note);continue
            h,rule,info=detail;j=sid(p['before_sha256'],p['action'],h)
            arow(p,g,'matched_control',{'match':'same ordered before image and dispatched action'},j)
            why={'archived_white':'A full-size, entirely white PNG removes the visible result of this action.',
                 'documented_earlier':'An earlier capture of the same trajectory still shows the old target state.',
                 'pre_action_replay':'The original pre-action screen lacks the effect established by the exact positive control.',
                 'archived_control_rectangles':'Every retained button rectangle is unchanged between the original before image and visible outcome; all other pixels are white.'}[rule]
            v=rawrow(p['before_sha256'],p['action'],h,s,'NO',rule,why,'constructed',p['source_suite'],p['family_id'],p['task_id'],p['trajectory_id'],p['event_id'])
            ar=dict(parent_sample_id=i,expected_after_sha256=p['candidate_sha256'],rule=rule,**info)
            keep_rule(s,rule,info,h)
            arow(v,g,'constructed_injection',ar,i)
    fit('train',640);fit('val',60)
    (HERE/'images').mkdir(exist_ok=True)
    counts={}
    for s in ('train','val'):
        vv=sorted((r for r in ans if r['split']==s),key=lambda r:rank('jev-v3-release',r['sample_id']))
        for j,r in enumerate(vv,1):r['line']=j
        counts[s]=len(vv)
    ans.sort(key=lambda r:(r['split']!='train',r['line']))
    proto=js(BASE/'protocol.json');shutil.copyfile(BASE/'protocol.json',HERE/'protocol.json')
    out(HERE/'manifest.jsonl',ans);out(HERE/'audit.jsonl',[audits[r['sample_id']] for r in ans])
    out(HERE/'source-receipts.jsonl',[dict(source_ref=i,**refs[i]) for i in sorted(keeprefs)])
    dump(HERE/'mask-templates.json',usedmasks)
    dump(HERE/'split-guards.json',dict(regression=guards,test_visual_ids=test_cores,test_families=sorted(test_families),
            original_test_sha256=sha((BASE/'test.jsonl').read_bytes()),base_manifest_sha256=sha((BASE/'manifest.jsonl').read_bytes())))
    for s in ('train','val'):
        out(HERE/(s+'.jsonl'),[dict(images=[r['before_png'],r['candidate_png']],prompt=proto['user_text'].replace('{canonical_action_json}',can(r['action']).decode()),label=r['label']) for r in ans if r['split']==s])
    imgs=extra_images|{r[k] for r in ans for k in ('before_sha256','candidate_sha256')}
    for t in usedmasks.values():
        if t.get('normal'):imgs.add(t['normal'])
    for i in keeprefs:
        ref=refs[i]
        if ref['source']=='v2.1':imgs.update(ref['audit'].get('support_images',[]))
    dump(HERE/'image-index.json',sorted(imgs))
    for h in sorted(imgs):
        dest=HERE/pic(h)
        if not dest.exists():shutil.copyfile(path(h),dest)
    print('exported',counts,'unique inputs/support PNGs',len(imgs),flush=True)
if __name__=='__main__':build()
