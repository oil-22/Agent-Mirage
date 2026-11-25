"""Check the self-contained v3 export without the archive, a model or a GPU (Python + Pillow)."""
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
import argparse, hashlib, json, math, re
from PIL import Image, ImageChops
T=('blank_replace','stale_replace','buttons_only')
S=('train','val')
def need(x,what):
    if not x:raise ValueError(what)
def canon(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def js(p):return json.loads(p.read_bytes())
def lines(p):return [json.loads(x) for x in p.read_bytes().splitlines() if x.strip()]
def filehash(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def same_action(a,z,w,h):
    return a['type']==z['type'] and (math.hypot((a['x']-z['x'])*w/1000,(a['y']-z['y'])*h/1000)<=6 if a['type']=='click' else a==z)
def scenario(run):
    last=run.rstrip('/').split('/')[-1]
    return next((k for k in T if last==k or '-'+k+'-' in last),None)
def check(folder):
    p=Path(folder).resolve();rs=lines(p/'manifest.jsonl');aa=lines(p/'audit.jsonl');src=lines(p/'source-receipts.jsonl')
    by={r['sample_id']:r for r in rs};au={r['sample_id']:r for r in aa};refs={r['source_ref']:r for r in src}
    need(len(rs)==len(by)==len(au)==len(aa) and set(au)==set(by) and len(src)==len(refs),'duplicate, missing or mismatched IDs')
    tpls=js(p/'mask-templates.json');guard=js(p/'split-guards.json');test=set(guard['test_visual_ids']);prot=set(guard['regression'].values())
    indexed=js(p/'image-index.json');need(indexed==sorted(set(indexed)),'image inventory')
    proto=js(p/'protocol.json')
    need(proto['answer_codes']=={'A':'YES','B':'NO'} and proto['image_order']==['previous_accepted_full_screenshot','current_candidate_full_screenshot'],'native answer and image order')
    imgset=set(indexed);ownership={};srcsplit={};groups={};used=set();refs_used=set();masks_used=set();inputs=set();near=defaultdict(list);allkeys=set()
    stats={'splits':{},'tasks':{},'observed_vs_constructed':{},'roles':{},'matched_pairs':{},'by_task_and_origin':{},'unique_buttons_only_NO_candidates':{}}
    def mark(d,k,s):need(d.setdefault(k,s)==s,'cross-split overlap: '+str(k))
    def markgroup(k,v,s):
        if v:mark(groups,(k,v),s)
    def fp(h):
        need(h in imgset and re.fullmatch(r'[0-9a-f]{64}',h),'unknown digest '+str(h))
        return p/'images'/(h+'.png')
    @lru_cache(None)
    def read(h):
        f=fp(h);need(filehash(f)==h,'image SHA-256 '+h)
        with Image.open(f) as im:
            need(im.format=='PNG' and im.n_frames==1 and 0<im.width*im.height<=4194304,'non-native or invalid PNG '+h)
            rgb=im.convert('RGB');w,t=rgb.size;full=sha(canon([w,t])+rgb.tobytes());iswhite=rgb.getextrema()==((255,255),)*3
            core=full
            if t>w:
                rgb=rgb.crop((0,round(t*.04),w,round(t*.968)));core=sha(canon(list(rgb.size))+rgb.tobytes())
            elif (w,t)==(1920,1080):
                rgb=rgb.crop((0,28,w,t));core=sha(canon(list(rgb.size))+rgb.tobytes())
        need(h not in guard['regression'] and not ({full,core}&(test|prot)),'protected test/regression pixels '+h)
        return w,t,core,full,iswhite
    def img(h,s):
        v=read(h);used.add(h)
        for z in (h,v[2],v[3]):mark(ownership,z,s)
        return v
    @lru_cache(None)
    def pixels(h,boxes):
        with Image.open(fp(h)) as im:
            rgb=im.convert('RGB');w,t=rgb.size
            need(boxes and all(len(b)==4 and all(type(v) is int for v in b) and 0<=b[0]<b[2]<=w and 0<=b[1]<b[3]<=t for b in boxes),'unbounded rectangle '+h)
            return tuple(sha(rgb.crop(b).tobytes()) for b in boxes)
    @lru_cache(None)
    def masked(h,boxes):
        pixels(h,boxes)
        with Image.open(fp(h)) as im:
            rgb=im.convert('RGB');canvas=Image.new('RGB',rgb.size,'white')
            for b in boxes:canvas.paste(rgb.crop(b),b[:2])
            need(not ImageChops.difference(canvas,rgb).getbbox() and rgb.getextrema()!=((255,255),)*3,'empty mask or nonwhite pixels outside controls: '+h)
    def rects(boxes):return tuple(sorted(set(tuple(r) for r in boxes)))
    def source(r,s):
        i=r['source_ref'];refs_used.add(i);mark(srcsplit,i,s);k=r['source']
        if k=='v2.1':
            v=r['row'];a=r['audit'];need(v['sample_id']==a['sample_id']==i and v['split']==s and v['receipt_valid'] and v['pair_observed'],'legacy observed receipt '+i)
            z=a.get('source',a.get('evidence',{}).get('source',{}));b,act,h=v['before_sha256'],v['action'],v['candidate_sha256']
            for t in ('capture_id','before_capture_id'):markgroup('capture',v.get(t),s)
            for t in a.get('support_images',[]):img(t,s)
            if r.get('representative'):
                rv=r['representative'];need([rv['before_sha256'],rv['action'],rv['candidate_sha256']]==[b,act,h],'legacy representative '+i)
            if z.get('probe'):
                pr=z['probe'];g=pr['condition'];need(pr['delivered_sha256']==h and pr['input_ids_sha256'] and z['before']['png_sha256']==b,'legacy experimental input '+i)
            elif z.get('output_delivery'):
                d=z['output_delivery'];g=d['condition'];need(d['delivered_sha256']==h and d['injection_fired'] and d['request_sha256'] and z['input_delivery']['delivered_sha256']==b and z['action']==act,'legacy mobile delivery '+i)
            elif z.get('archived_delivered_sha256'):
                g=z['condition'];need(z['archived_delivered_sha256']==h and z['before_request'] and z['after_request'],'legacy archived delivery '+i)
            else:g=None
            for zz in [z,*a.get('donor_sources',[])]:
                for name in ('family_id','task_id','trajectory_id','event_id','source_run'):markgroup(name,zz.get(name),s)
                for name in ('capture_id','before_capture_id'):markgroup('capture',zz.get(name),s)
            label=v['label']
        elif k=='desktop':
            v=r['record'];b,act,h=v['b'],v['action'],v['e'];x,y=v['input_delivery'],v['output_delivery'];g=v['mode'] if y['injection_fired'] else None
            need(not x['injection_fired'] and v['mode']==(y['condition'] if y['injection_fired'] else 'normal') and y['previous_delivered_sha256']==b,'desktop dispatch chain '+i)
            click=re.fullmatch(r'pyautogui\.click\(x=(\d+),\s*y=(\d+)\)',v['trajectory_action'])
            need([round(v['pixel'][0]*1000/1920,7),round(v['pixel'][1]*1000/1080,7)]==[act['x'],act['y']] and click and list(map(int,click.groups()))==v['pixel'],'recorded click '+i)
            for d,u,pf in zip((x,y),(b,h),v['proof'],strict=True):
                need(d['image_count']==1 and not d['historical_screenshot_blocks'] and d['dom_or_ax_delivered'] is False and d['delivered_sha256']==pf['single_archive_image']==u and pf['original_request_hash_verified']==d['request_sha256'] and pf['http_status']==200 and pf['response_id'],'desktop request/response '+i)
            markgroup('source_run',v['run'],s);label=None
        elif k=='android':
            v=r['record'];b,act,h=v['before'],v['action'],v['candidate'];g=v['condition'];it=v['intervention']
            need(g==T[2]==it['condition'] and it['injection_fired'] and it['delivered_sha256']==h and v['before_request'] and v['after_request'] and v['source_log_sha256'],'reviewed Android receipt '+i)
            markgroup('source_run',v['run'],s);label=None
        else:raise ValueError(k)
        need(i=='jev-'+sha(canon([b,act,h]))[:24],'source truth binding '+i)
        return b,act,h,g,label
    def rule(g,b,act,h,positive,z,s):
        w,t,bc,_,wb=img(b,s);_,_,yc,_,_=img(positive,s);w1,t1,hc,_,wh=img(h,s)
        need((w,t)==(w1,t1) and hc!=yc,'ineffective or wrong-sized corruption')
        key=z['rule']
        if key=='archived_white':
            _,_,f,c,l=source(refs[z['blank_source_ref']],s)
            need(g==T[0]==c and l in ('NO',None) and f==h and wh and not wb,'white control provenance')
        elif key=='pre_action_replay':
            need(g==T[1] and h==b and bc!=yc,'replay provenance')
        elif key=='documented_earlier':
            d=z['donor'];q=z['source'];v=z['witness']
            need(g==T[1] and d['hash']==h and d['source_run']==q['source_run'] and d['step']<q['step'] and d['route']==q['before_route'] and d['receipt'] and v['earlier_step']==d['step'] and v['action_step']==q['step'],'earlier-frame evidence')
            markgroup('source_run',d['source_run'],s)
        elif key=='archived_control_rectangles':
            tk=z['template_ref'];m=tpls[tk];masks_used.add(tk);markgroup('source_run',m['run'],s)
            need(g==T[2] and tk==s+':'+h and m['frame']==h and m['split']==s and (w,t)==(m['w'],m['h']) and m['geometry_digest'],'wrong mask source')
            bx=rects(m['rects']);masked(h,bx)
            if m.get('normal'):img(m['normal'],s);need(pixels(m['normal'],bx)==pixels(h,bx),'mask template source normal')
            if m['source']=='archive_android':need(sha(canon(m['geometry_record']))==m['geometry_digest'] and m['geometry_record']['delivered_sha256']==h and m['after_request'],'template receipt')
            else:need(m['probe']['condition']==T[2] and m['probe']['delivered_sha256']==h and m['probe']['input_ids_sha256'],'template receipt')
            need(bc!=yc and pixels(b,bx)==pixels(positive,bx)==pixels(h,bx),'mask retains or invents a changed control')
            if act['type']=='click':need(not any(l-3<=act['x']*w/1000<r+3 and u-3<=act['y']*t/1000<v+3 for l,u,r,v in bx),'transferred mask contains click target')
        else:raise ValueError('unknown construction '+key)
    for s in S:
        mm=[r for r in rs if r['split']==s];vv=lines(p/(s+'.jsonl'));need(len(mm)==len(vv) and mm,'file/manifest mismatch '+s)
        cells=Counter((r['task'],r['label']) for r in mm)
        need(set(cells)=={(g,l) for g in T for l in ('YES','NO')} and len(set(cells.values()))==1,'six-cell balance '+s)
        for line,(r,v) in enumerate(zip(mm,vv,strict=True),1):
            i=r['sample_id'];b,act,h=r['before_sha256'],r['action'],r['candidate_sha256'];l,g,role=r['label'],r['task'],r['role'];z=au[i]
            acttext=canon(act).decode();pmt=proto['user_text'].replace('{canonical_action_json}',acttext)
            need(set(v)=={'images','prompt','label'} and v['images']==[r['before_png'],r['candidate_png']]==['images/'+k+'.png' for k in (b,h)] and v['prompt']==pmt and v['label']==l and '<|' not in acttext and '|>' not in acttext,'native export line '+i)
            need(r['line']==line and i=='jev-'+sha(canon([b,act,h]))[:24],'line or sample ID '+i)
            trip=(b,h,pmt);need(trip not in allkeys,'duplicate input');allkeys.add(trip)
            w,t,x,_,wb=img(b,s);wd,ht,y,_,wh=img(h,s);inputs.update((b,h));need((w,t)==(wd,ht),'viewport mismatch')
            pool=near[x,y,act['type']];need(not any(same_action(act,a,w,t) for a in pool),'equivalent actions on equal images '+i);pool.append(act)
            for name in ('family_id','task_id','trajectory_id','event_id'):markgroup(name,r[name],s)
            need(r['family_id'] not in guard['test_families'],'test family')
            ob=r['origin']=='observed';need(r['pair_observed'] is ob and r['origin'] in ('constructed','observed'),'observed status')
            if ob:
                b0,a0,h0,cond,ll=source(refs[z['source_ref']],s);need(z['source_ref']==i and (b0,a0,h0)==(b,act,h) and ll in (None,l),'wrong observed source')
                if role=='observed_injection':
                    need(cond==z['actual_condition']==g,'scenario not fired '+i)
                    if g==T[0]:need(l=='NO' and wh and not wb,'white label')
                    if g==T[1]:need(l=='NO' and r['phase']=='early','replay label')
                    if g==T[2]:masked(h,rects(z['rectangles']))
                else:need(cond is None and l=='YES' and role in ('matched_control','scenario_control','audit_matched_control'),'ordinary control role')
            else:
                need('source_ref' not in z and role=='constructed_injection' and l=='NO','false original receipt')
            mate=r['contrast_sample_id']
            if mate:
                m=by[mate];need(m['contrast_sample_id']==i and m['task']==g and m['split']==s and m['before_sha256']==b and m['action']==act and m['label']!=l and m['candidate_sha256']!=h,'invalid paired contrast '+i)
            if role=='matched_control':need(mate,'dangling YES control')
            if not ob:
                need(mate and mate==z['parent_sample_id'] and m['label']=='YES' and m['pair_observed'] and m['candidate_sha256']==z['expected_after_sha256'],'missing observed YES parent')
                rule(g,b,act,h,m['candidate_sha256'],z,s)
            if role=='audit_matched_control':
                c=z['comparison_only'];rule(g,b,act,c['candidate_sha256'],h,c,s)
            if 'scenario_witness' in z:
                sw=z['scenario_witness'];need(scenario(sw['archive_run'])==g,'mislabeled scenario control');markgroup('source_run',sw['archive_run'],s)
                if 'observation' in sw:
                    o=sw['observation'];need((o.get('source_run') or o['run'])==sw['archive_run'] and (o['before_sha256'],o['action'],o['candidate_sha256'])==(b,act,h),'wrong scenario input')
                else:need(sw['source_ref']==i and refs[i]['record']['run']==sw['archive_run'],'wrong desktop control')
            if role=='scenario_control':need('scenario_witness' in z,'unsubstantiated task assignment')
        stats['splits'][s]=dict(total=len(mm),**dict(Counter(r['label'] for r in mm)))
        stats['tasks'][s]={g:{l:cells[g,l] for l in ('YES','NO')} for g in T}
        stats['observed_vs_constructed'][s]=dict(Counter(r['origin'] for r in mm))
        stats['by_task_and_origin'][s]={g:{l:dict(Counter(r['role'] for r in mm if r['task']==g and r['label']==l)) for l in ('YES','NO')} for g in T}
        stats['roles'][s]=dict(Counter(r['role'] for r in mm))
        stats['matched_pairs'][s]=sum(bool(r['contrast_sample_id']) and r['label']=='NO' for r in mm)
        stats['unique_buttons_only_NO_candidates'][s]=len({read(r['candidate_sha256'])[2] for r in mm if r['task']==T[2] and r['label']=='NO'})
    need(len(rs)==sum(v['total'] for v in stats['splits'].values()) and stats['splits']['train']['total']>=3000,'minimum training size')
    need(refs_used==set(refs) and masks_used==set(tpls) and used==imgset,'unused or missing evidence or assets')
    stats.update(total_rows=len(rs),unique_model_input_PNGs=len(inputs),audit_only_PNGs=len(imgset-inputs),missing_images=0,
        duplicate_inputs=0,conflicting_labels=0,cross_split_decoded_images=0,cross_split_source_groups=0,
        sha256={f:filehash(p/f) for f in ('train.jsonl','val.jsonl','manifest.jsonl','audit.jsonl','source-receipts.jsonl','protocol.json','mask-templates.json','image-index.json','split-guards.json')})
    return rs,stats
if __name__=='__main__':
    pa=argparse.ArgumentParser(description=__doc__);pa.add_argument('--write-stats',action='store_true');pa.add_argument('dataset',nargs='?',type=Path,default=Path(__file__).resolve().parent)
    args=pa.parse_args();_,stats=check(args.dataset)
    if args.write_stats:(args.dataset/'stats.json').write_text(json.dumps(stats,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({k:stats[k] for k in ('splits','tasks','observed_vs_constructed','total_rows','missing_images','duplicate_inputs','cross_split_decoded_images')},indent=2))
