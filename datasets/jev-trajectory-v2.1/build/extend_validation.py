"""Rebuild from frozen v2, review decisions, and the original AndroidWorld log/PNG cache.

Run validation_sources.py first if the injection PNG cache is absent. No model is run.
"""
import base64
import hashlib
import json
import re
import shutil
import sys
from collections import Counter
from functools import lru_cache

from validation_sources import HERE, V1, V2, W, WORK, BLOB, bystep, lines, read, out, dump, sha, canon, content_id, android_action, safe
from validation_review import imagepath, apair, distance, mkclean
from matched_controls import diff
from export import prompt
from release import native_messages
from temporal_request import native_request
sys.path.insert(0,str(HERE))
from validation_extension import BASE_FIXED, BASE_PREFIX, ORIGIN, KINDS, inspect_pixels, need, receipt

ALIASES=read(WORK/'archive-logs-aliases.json')
REVIEWED=lines(HERE/'build/review-decisions.jsonl')
NORMAL={ (o['source_run'],o['step']):o for o in lines(V1/'additional-archive-observations.jsonl') if o['suite']=='archive_android' }
DELIVERY=('step','time','request_sha256','capture_sha256','delivered_sha256','image_count','native_dimensions','condition','injection_fired','stale_source_step','ax_text_or_indices_delivered')

def project(r,keys):
    return {k:r[k] for k in keys}

@lru_cache(None)
def log(run,name):
    path=BLOB/content_id(ALIASES[run+'/'+name])
    return bystep(path),sha(path.read_bytes())

def collect_event(run,step,expected,condition,is_control=False):
    ds,dh=log(run,'model_delivery.jsonl')
    ac,ah=log(run,'agent_trace.jsonl')
    x,y,ex=ds[step],ds[step+1],ac[step]
    a=android_action(ex,x['native_dimensions'])
    b,e=x['delivered_sha256'],y['delivered_sha256']
    need(safe(a) and apair(b,a,e)==expected, 'Archived PNG / native dispatch differs from reviewed input')
    log_sha={'model_delivery.jsonl':dh,'agent_trace.jsonl':ah}
    digests={'input_delivery':sha(canon(x)),'output_delivery':sha(canon(y)),'dispatch':sha(canon(ex))}
    hit=None;replay=None
    if condition=='normal':
        original=NORMAL[run,step]
        need(original['pair_id']==expected and original['raw_action']==ex['action'] and original['source_before_request']==x['request_sha256'] and original['source_after_request']==y['request_sha256'] and original['allowed_source_log_sha256']==log_sha, 'Historical Android archive join disagrees')
        need(is_control or original['label'] is None, 'Supplement must not reuse definite labelled observations')
    else:
        events,ih=log(run,'intervention/events.jsonl')
        hit=events[step+1]
        need(ac[step+1]['injection_fired'] is True and hit['condition']==condition, 'Missing actual injection evidence')
        log_sha['intervention/events.jsonl']=ih
        digests['intervention']=sha(canon(hit))
        if condition=='stale_replace':
            frame=ds[y['stale_source_step']]
            replay=project(frame,DELIVERY);digests['replay_source']=sha(canon(frame))
    fam=re.search(r'/\d{3}-([A-Z][A-Za-z0-9_]+)(?:/|$)',run)[1]
    t='archive_android:archive-'+sha(run.encode())[:24]; f='android:'+fam
    src=dict(suite='archive_android',source_run=run,step=step,action=a,condition=condition,
             family_id=f,task_id=f+':'+fam,trajectory_id=t,event_id=t+'/'+str(step),
             before_capture_id=sha(canon([run,step,b]))[:32],capture_id=sha(canon([run,step+1,e]))[:32],
             input_delivery=project(x,DELIVERY),output_delivery=project(y,DELIVERY),
             dispatch=project(ex,('step','action','execution','result','injection_fired')),
             intervention=hit,replay_source=replay,source_log_sha256=log_sha,source_record_sha256=digests)
    need(receipt(src)==(b,a,e),'Portable receipt mismatch')
    if condition=='normal':
        need(src['before_capture_id']==original['before_capture_id'] and src['capture_id']==original['capture_id'],'Historical capture identifiers')
    return src

def png(h,required=True):
    dst=HERE/'images'/(h+'.png')
    if dst.exists():return True
    try:src=imagepath(h)
    except KeyError:src=None
    if src is None or not src.is_file():
        need(not required,'Missing observed PNG: '+h);return False
    need(sha(src.read_bytes())==h,'Original screenshot hash mismatch')
    shutil.copyfile(src,dst);return True

def base_copy():
    img=HERE/'images';img.mkdir(exist_ok=True)
    for n,h in (BASE_FIXED|BASE_PREFIX).items():
        source=V2/('val.jsonl' if n=='val-v2-original.jsonl' else n)
        need(sha(source.read_bytes())==h,'Wrong base release: '+n)
        shutil.copyfile(source,HERE/n)
    for n in ('example-typed-contrast.jsonl','v1-archive-label-evidence.jsonl','spot-check.json'):
        shutil.copyfile(V2/n,HERE/n)
    shutil.copyfile(V2/'validation.json',HERE/'build/v2-validation.json')
    for f in (V2/'images').glob('*.png'):
        if not (img/f.name).exists():shutil.copyfile(f,img/f.name)

def confirm_distinct():
    # Beyond exact/pixel checks in verify.py, veto even a nearby visually similar previous
    # labelled Android observation. Include previously labelled but unexported occurrences.
    seen={o['pair_id']:mkclean(o) for o in NORMAL.values() if o['label']}
    pool=list(seen.values())
    for d in REVIEWED:
        pair=d['pair_id'];typ=KINDS[d['kind']];s=collect_event(d['source_run'],d['step'],pair,typ)
        b,a,e=receipt(s)
        for prior in pool:
            if distance(a,prior['action'])>60:continue
            fr,md=diff(b,prior['before'])
            if fr>.012 or md>1.7:continue
            fr,md=diff(e,prior['candidate'])
            need(fr>.012 or md>1.7,'Perceptual copy or ambiguous old label: '+d['review_code'])
        pool.append(dict(before=b,action=a,candidate=e))
    return len(seen)

def build():
    base_copy();known=confirm_distinct()
    model=native_messages();protocol=read(HERE/'protocol.json')
    manifests=[];audits=[];views=[];index=[];bindings=Counter()
    buffered=[]
    for d in REVIEWED:
        kind=d['kind'];s=collect_event(d['source_run'],d['step'],d['pair_id'],KINDS[kind]);b,a,e=receipt(s)
        c=d['control']
        ctrl=collect_event(c['source_run'],c['step'],c['pair_id'],'normal',is_control=True) if c else None
        support=set()
        for h in (b,e):png(h)
        if ctrl:
            u,_,v=receipt(ctrl)
            for h in (u,v):png(h)
            support.update((u,v))
        raw=s['output_delivery']['capture_sha256']
        if s['condition']!='normal' and png(raw,required=False):support.add(raw)
        buffered.append((d,s,b,a,e,ctrl,support))
    for num,(d,s,b,a,e,ctrl,support) in enumerate(buffered,1):
        kind=d['kind']; paths=['images/'+h+'.png' for h in (b,e)]
        raw=s['output_delivery']['capture_sha256'];has_raw=s['condition']!='normal' and (HERE/'images'/(raw+'.png')).is_file()
        if has_raw:support.add(raw)
        view=dict(images=paths,prompt=prompt(a),label='NO')
        # Native request and reference encoder, checked on every appended row with ordered original bytes.
        files=[(HERE/n).read_bytes() for n in paths]
        req=native_request(files[0],a,files[1])
        need([base64.b64decode(img.split(',',1)[1]) for img in req['images']]==files,'Native encoder swapped or substituted a PNG')
        msg=model.messages(dict(images=[0,1],questions=req['questions'],state=req['state']))
        need(msg[0]['content']==protocol['system_prompt'] and msg[1]['content']==[{'type':'image'},{'type':'image'},{'type':'text','text':view['prompt']}],'Native encoder text')
        sid='jev-'+d['pair_id'][:24]; oid=sha(canon([s['source_run'],s['step'],d['pair_id']]))
        groups=project(s,('family_id','task_id','trajectory_id','event_id','capture_id','before_capture_id'))
        phase='no_change' if kind in ('injected_logged_replay','normal_controlled_unchanged','normal_target_unchanged') else 'unrelated' if kind in ('normal_unrelated_destination','normal_query_unverified') else 'unknown'
        manifests.append(dict(sample_id=sid,**groups,source_suite='archive_android',source_observation_id=oid,all_observation_ids=[oid],
                              supporting_pair_ids=[d['pair_id']],before_sha256=b,before_png=paths[0],candidate_sha256=e,candidate_png=paths[1],
                              split='val',action=a,label='NO',phase=phase,evidence_kind=kind,review_code=d['review_code'],
                              reason=d['reason'],pair_observed=True,receipt_valid=True,origin=ORIGIN))
        audits.append(dict(sample_id=sid,origin=ORIGIN,source=s,donor_sources=[ctrl] if ctrl else [],support_images=sorted(support-{b,e}),
                           evidence=dict(original_unreplaced_png_in_package=has_raw,pixel_checks=inspect_pixels(HERE,kind,s,ctrl,has_raw),
                                         decision_pair_id=d['pair_id'],control_role='visual comparison only; never the candidate' if ctrl else None)))
        views.append(view)
        bindings[kind]+=1
        index.append(dict(sample_id=sid,val_line=188+num,source_run=s['source_run'],step=s['step'],kind=kind,reason=d['reason'],review_code=d['review_code']))
    for name,records in [('manifest.jsonl',manifests),('audit.jsonl',audits)]:
        with (HERE/name).open('ab') as f:
            for rec in records:f.write(canon(rec)+b'\n')
    out(HERE/'val-added-no.jsonl',views)
    (HERE/'val.jsonl').write_bytes((HERE/'val-v2-original.jsonl').read_bytes()+(HERE/'val-added-no.jsonl').read_bytes())
    out(HERE/'val-added-index.jsonl',index)
    dump(HERE/'build/extension-checks.json',dict(reviewed_input_bindings=len(views),new_native_request_and_encoder_matches=len(views),
         by_evidence=dict(bindings),distinct_existing_labeled_android_pairs_checked=known,
         extra_dedup='Native action within 60 px, or identical non-click action: veto if both median-filtered screen bodies differ on at most 1.2% of pixels and mean max-channel difference is at most 1.7/255 in each.',
         logs_reconciled=len(views)+sum(bool(d['control']) for d in REVIEWED),control_receipts=sum(bool(d['control']) for d in REVIEWED),
         archive_alias_index_sha256=sha((WORK/'archive-logs-aliases.json').read_bytes())))
    print('Appended',len(views),'observed NO records;',dict(bindings),flush=True)
if __name__=='__main__':build()
