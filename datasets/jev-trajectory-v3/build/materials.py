"""Resolve observed inputs and their receipts from the existing local experiment collections."""
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
import hashlib, json, math
from PIL import Image
from masks import BASE, V1, W, A, HERE, path, can, sha, rows, js, out, dump
from review_choices import DESKTOP, ANDROID

BL, ST, BU = 'blank_replace', 'stale_replace', 'buttons_only'
TASKS = (BL, ST, BU)
DG = {'gimp','thunderbird'}  # whole OSWorld task domains, not randomly split frames
def sid(b,a,e):return 'jev-'+sha(can([b,a,e]))[:24]
def pic(h):return 'images/'+h+'.png'
def rank(*s):return int(sha(can(s))[:12],16)
def scenario(run):
    last=(run or '').rstrip('/').split('/')[-1]
    return next((k for k in TASKS if last==k or '-'+k+'-' in last),None)
def close(a,z,w,h):
    return a['type']==z['type'] and (math.hypot((a['x']-z['x'])*w/1000,(a['y']-z['y'])*h/1000)<=6 if a['type']=='click' else a==z)
@lru_cache(None)
def ids():return js(V1/'archive-content-index.json')
@lru_cache(None)
def identity(h):
    if h in ids() and tuple(ids()[h][1:])!=(1920,1080):return tuple(ids()[h])
    with Image.open(path(h)) as im:
        w,t=im.size;rgb=im.convert('RGB')
        if t>w:rgb=rgb.crop((0,round(t*.04),w,round(t*.968)))
        elif (w,t)==(1920,1080):rgb=rgb.crop((0,28,w,t))
        return sha(can(list(rgb.size))+rgb.tobytes()),w,t
@lru_cache(None)
def white(h):
    with Image.open(path(h)) as im:return im.convert('RGB').getextrema()==((255,255),)*3
def rawrow(b,a,e,s,lab,kind,why,origin,source,fam,task,run,event,phase=None):
    return dict(sample_id=sid(b,a,e),split=s,before_sha256=b,action=a,candidate_sha256=e,label=lab,
                evidence_kind=kind,reason=why,origin=origin,source_suite=source,family_id=fam,task_id=task,
                trajectory_id=run,event_id=event,phase=phase or ('settled' if lab=='YES' else 'unrelated'))
def materials():
    old=rows(BASE/'manifest.jsonl');old_a={r['sample_id']:r for r in rows(BASE/'audit.jsonl')}
    prov={r['observation_id']:r for r in rows(BASE/'v1-provenance.jsonl')}
    pos={};direct=[];refs={};occ=defaultdict(dict);earlier=defaultdict(list);nom={};rect={}
    def legacy(r):
        i=r['sample_id'];q=old_a[i]
        refs[i]=dict(source='v2.1',row=r,audit=q,representative=prov.get(r.get('source_observation_id')))
        return rawrow(r['before_sha256'],r['action'],r['candidate_sha256'],r['split'],r['label'],r['evidence_kind'],r['reason'],
                      'observed',r['source_suite'],r['family_id'],r['task_id'],r['trajectory_id'],r['event_id'],r['phase'])
    for r in old:
        if r['split']=='test':continue
        i=r['sample_id'];k=r['evidence_kind'];s=r['split']
        if r['label']=='YES' and r['pair_observed']:
            pos[i]=legacy(r)
            for oid in sorted(r.get('all_observation_ids',[])):
                v=prov[oid];name=v.get('source_run') or v['run'];c=scenario(name)
                if c and v['before_sha256']==r['before_sha256'] and v['action']==r['action'] and v['candidate_sha256']==r['candidate_sha256']:
                    occ[i].setdefault(c,dict(archive_run=name,observation=v)); 
        elif k in ('earlier_same_page','earlier_unchanged_field','earlier_list_view'):
            z=old_a[i];earlier[z['evidence']['parent_sample_id']].append(r)
        elif k in ('delivered_blank','delivered_stale','delivered_partial','injected_blank','injected_logged_replay','injected_fragment'):
            a=old_a[i]['source'];c=(a.get('probe') or {}).get('condition') or a.get('condition')
            if c not in TASKS:continue
            v=legacy(r);v['task']=c;direct.append(v)
            e=old_a[i]['evidence'];nom[i]=e.get('normal_after_sha256') or e.get('normal_capture_sha256') or a.get('output_delivery',{}).get('capture_sha256')
            if c==BU:
                rect[i]=[b['bounds'] for b in (a.get('intervention') or {}).get('button_regions',[])]
    for r in rows(W/'desktop-bound.jsonl'):
        k=r['mode'];code=r['code'];s='train' if r['domain'] in DG else 'val'
        if code in DESKTOP:lab,why=DESKTOP[code]
        elif k==BL and s=='val':
            lab='NO';why='The archived full-size PNG is completely white; no target or response to the recorded click is visible.'
        else:continue
        if k==BL and white(r['b']):continue
        if k==ST and white(r['b']):continue
        run='osworld:'+sha(r['run'].encode())[:24];fam='osworld:'+r['domain']
        v=rawrow(r['b'],r['action'],r['e'],s,lab,'archived_desktop_'+k,why,'observed','archive_osworld',fam,fam+':'+r['task'],run,run+'/'+str(r['step']))
        i=v['sample_id'];refs[i]=dict(source='desktop',review_code=code,record={t:r[t] for t in ('run','task','domain','step','mode','b','e','h','pixel','action','trajectory_action','input_delivery','output_delivery','proof','source_log_sha','geometry')})
        if k=='normal':
            pos[i]=v;c=scenario(r['run'])
            if c:occ[i][c]=dict(archive_run=r['run'],source_ref=i)
        else:
            v['task']=k;direct.append(v);nom[i]=r['h']
            if k==BU:rect[i]=[z['bounds'] for z in r['geometry']['regions'] if 'bounds' in z]
    for r in rows(A/'review-index.jsonl'):
        code=r['review_code']
        if code not in ANDROID:continue
        assert r['condition']==BU
        lab,why=ANDROID[code];run='archive_android:archive-'+sha(r['run'].encode())[:24];fam='android:'+r['family']
        v=rawrow(r['before'],r['action'],r['candidate'],'val',lab,'archived_android_buttons_only',why,'observed','archive_android',fam,fam+':'+r['family'],run,run+'/'+str(r['step']))
        i=v['sample_id'];refs[i]=dict(source='android',review_code=code,record=r);nom[i]=r['normal'];v['task']=BU;direct.append(v)
        rect[i]=[z['bounds'] for z in r['intervention']['button_regions']]
    tpl={(t['split'],t['frame']):t for t in js(W/'templates.json')}
    for v in direct:
        i=v['sample_id']
        if v['task']==BU and not rect.get(i):
            t=tpl.get((v['split'],v['candidate_sha256']))
            if t:rect[i]=t['rects']
            else:
                # Some first-party checkpoint candidates use a full recorded geometry
                # even if its normal frame was not accepted for rectangle transfer.
                t=next((q for q in js(W/'natural-mask-references.json') if q['template']==v['candidate_sha256']),None)
                if t:rect[i]=t['rectangles']
    return old,old_a,pos,direct,refs,occ,earlier,nom,rect,tpl
