"""Portable checks for the appended, observed validation negatives. Requires Pillow."""
import hashlib
import json
import math
import re
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ORIGIN = 'observed_android_val'
KINDS = {
    'injected_blank': 'blank_replace', 'injected_fragment': 'buttons_only',
    'injected_logged_replay': 'stale_replace', 'normal_empty_surface': 'normal',
    'normal_controlled_unchanged': 'normal', 'normal_target_unchanged': 'normal',
    'normal_unrelated_destination': 'normal', 'normal_query_unverified': 'normal',
}
BASE_ROWS = 4459
BASE_VAL = 'aa02691281c1693a08806a6c128a9a0c8a1265c6ef45446d55e9dc18bb145008'
BASE_FIXED = {
    'train.jsonl': '9d4928a5d8ac9f2c6784d3c510f70f34f54db04f405b767ba779b323f60ac3b5',
    'train-balanced.jsonl': '3b0e9ef5f3d3f78086a024926617c338de334f7eb2390cb2fee12b3df88930c8',
    'test.jsonl': 'a5e9200c9af1f1072a5ec8a9382b96783c3577c1d66c1829336105d659810dc9',
    'val-v2-original.jsonl': BASE_VAL,
    'protocol.json': '83a8d7014fe7469ab99076b01ab9d58776553e09a2edf7628042627de2ba15bf',
    'split-guards.json': '7d90326fc74e01a148a5f03cc49f717c00981fdf359e41c581ff8dae0e3ab9fb',
    'v1-provenance.jsonl': '5825cc4614c5fbedbe1d8e915a4a61852c1ab70962ead67fd87f9c6f9829c4eb',
}
BASE_PREFIX = {
    'manifest.jsonl': '6610186502a995806b8e318afee739065ee4c715c0bd46bae02ed5a60cfcec7e',
    'audit.jsonl': '11503f7b3c071317af046c22fd2f71ce5a2f418029555179584f82d26bca5ac6',
}

def need(ok, why):
    if not ok:
        raise ValueError(why)

def canon(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()

def sha(b):
    return hashlib.sha256(b).hexdigest()

def jsonl(path):
    return [json.loads(b) for b in path.read_bytes().splitlines() if b.strip()]

def ishash(h):
    return isinstance(h, str) and bool(re.fullmatch('[a-f0-9]{64}', h))

def frozen(p, manifest):
    for name, hx in BASE_FIXED.items():
        need(sha((p/name).read_bytes()) == hx, 'Changed v2 file: '+name)
    for name, hx in BASE_PREFIX.items():
        with (p/name).open('rb') as f:
            need(sha(b''.join(f.readline() for _ in range(BASE_ROWS))) == hx, 'Changed original v2 rows: '+name)
    extra = manifest[BASE_ROWS:]
    need(extra and all(m['origin'] == ORIGIN and m['split']=='val' and m['label']=='NO' for m in extra), 'Unexpected appended data')
    v0 = (p/'val-v2-original.jsonl').read_bytes()
    need((p/'val.jsonl').read_bytes() == v0 + (p/'val-added-no.jsonl').read_bytes(), 'Changed validation prefix or suffix')
    ds = jsonl(p/'build/review-decisions.jsonl')
    ix = jsonl(p/'val-added-index.jsonl')
    need(len(extra)==len(ds)==len(ix) and len({d['pair_id'] for d in ds})==len(ds), 'Decision coverage')
    need(len({(d['source_run'], d['step']) for d in ds}) == len(ds), 'Duplicate delivered event')
    for j,(m,d,entry) in enumerate(zip(extra,ds,ix),1):
        pair = sha(canon([m['before_sha256'],m['action'],m['candidate_sha256']]))
        need(d['pair_id']==pair and d['reason']==m['reason'] and d['kind']==m['evidence_kind'] and d['review_code']==m['review_code'], 'Visual decision binding')
        need(entry==dict(sample_id=m['sample_id'],val_line=188+j,source_run=d['source_run'],step=d['step'],kind=d['kind'],review_code=d['review_code'],reason=d['reason']), 'Validation change index')
    return {m['sample_id']:d for m,d in zip(extra,ds)}

def pixel_action(raw, wh):
    kind=raw.get('action_type')
    if kind=='click':
        x,y=raw['x'],raw['y']
        need(all(type(v) in (int,float) and 0<v<n for v,n in zip((x,y),wh)), 'Native pointer outside viewport')
        return {'type':'click','x':round(1000*x/wh[0],7),'y':round(1000*y/wh[1],7)}
    if kind=='navigate_back': return {'type':'back'}
    if kind=='input_text' and isinstance(raw.get('text'),str): return {'type':'type','text':raw['text']}
    if kind=='scroll' and raw.get('direction') in ('up','down'): return {'type':'scroll','direction':raw['direction']}
    raise ValueError('Unsupported Android dispatch')

def receipt(src):
    run,st=src['source_run'],src['step']
    match=re.search(r'/\d{3}-([A-Z][A-Za-z0-9_]+)(?:/|$)',run)
    need(match and len(run.split('/'))>3 and run.split('/')[2].split('__')[0]=='AndroidWorld' and type(st)==int and st>=0,'Android archive source')
    family='android:'+match[1]; trajectory='archive_android:archive-'+sha(run.encode())[:24]
    x,y=src['input_delivery'],src['output_delivery']; b=x['delivered_sha256']; e=y['delivered_sha256']
    mode=src['condition']; wh=[1080,2400]
    need(src['suite']=='archive_android' and x['step']==st and y['step']==st+1 and y['time']>=x['time'], 'Nonconsecutive delivery receipts')
    for row in (x,y):
        need(all(ishash(row[k]) for k in ('capture_sha256','delivered_sha256','request_sha256')) and row['image_count']==1 and row['native_dimensions']==wh and row['ax_text_or_indices_delivered'] is False, 'Non-native or unaudited image delivery')
    for k,v in dict(family_id=family,task_id=family+':'+match[1],trajectory_id=trajectory,event_id=trajectory+'/'+str(st),
                    before_capture_id=sha(canon([run,st,b]))[:32],capture_id=sha(canon([run,st+1,e]))[:32]).items():
        need(src[k]==v, 'Wrong archive group: '+k)
    ex=src['dispatch']
    need(ex['step']==st and ex['injection_fired'] is False and ex['execution']['primitive']=='official_execute_action' and ex['result'].startswith('Action executed'), 'No evidence for actual native dispatch')
    a=pixel_action(ex['action'],wh)
    need(src['action']==a and x['injection_fired'] is False and x['capture_sha256']==b, 'Invalid before frame or native action')
    keys={'agent_trace.jsonl','model_delivery.jsonl'}
    digests={'input_delivery','output_delivery','dispatch'}
    if mode=='normal':
        need(y['injection_fired'] is False and y['capture_sha256']==e and src['intervention'] is None and src['replay_source'] is None,'Not a normal received pair')
    else:
        keys.add('intervention/events.jsonl');digests.add('intervention')
        it=src['intervention']
        need(mode in ('blank_replace','buttons_only','stale_replace') and y['injection_fired'] is True and it['injection_fired'] is True and it['step']==st+1 and it['condition']==y['condition']==mode and it['capture_sha256']==y['capture_sha256']!=e and it['delivered_sha256']==e,'Invalid intervention binding')
        if mode=='stale_replace':
            di=src['replay_source'];digests.add('replay_source')
            need(di['step']==it['stale_source_step']==y['stale_source_step']<=st and di['capture_sha256']==e and di['native_dimensions']==wh, 'Old frame origin')
        else:need(src['replay_source'] is None,'Spurious old-frame claim')
    need(set(src['source_log_sha256'])==keys and set(src['source_record_sha256'])==digests and all(ishash(v) for table in ('source_log_sha256','source_record_sha256') for v in src[table].values()), 'Unbound log evidence')
    # These are complete native receipt / intervention records. For execution records
    # the bundle keeps only dispatch fields; extend_validation.py checks those directly
    # against the archived agent_trace rather than shipping unrelated model text.
    for key in digests-{'dispatch'}:
        need(sha(canon(src[key]))==src['source_record_sha256'][key], 'Archived record digest: '+key)
    return b,a,e

@lru_cache(120)
def thumb(path):
    with Image.open(path) as im:
        return im.convert('RGB').resize((144,320),Image.Resampling.BOX).crop((0,24,144,309)).filter(ImageFilter.MedianFilter(3))

def change(p,b,e):
    x,y=(thumb(p/'images'/(h+'.png')) for h in (b,e))
    r,g,bl=ImageChops.difference(x,y).split()
    hist=ImageChops.lighter(ImageChops.lighter(r,g),bl).histogram()
    return round(sum(hist[21:])/sum(hist),6)

def inspect_pixels(p,kind,s,ctrl,raw_in_package):
    b,e=s['input_delivery']['delivered_sha256'],s['output_delivery']['delivered_sha256']
    filename=lambda h:p/'images'/(h+'.png')
    metrics={'body_changed_fraction':change(p,b,e)}
    if ctrl:
        u,v=ctrl['input_delivery']['delivered_sha256'],ctrl['output_delivery']['delivered_sha256']
        metrics.update(control_initial_difference=change(p,b,u),control_result_difference=change(p,e,v))
        need(metrics['control_initial_difference']<.035 and metrics['control_result_difference']>.012,'Control lacks comparable starting UI or different outcome')
    if kind in ('normal_target_unchanged','normal_controlled_unchanged','injected_logged_replay'):
        need(metrics['body_changed_fraction']<.035,'Claimed unchanged UI is substantially different')
    if kind in ('normal_unrelated_destination','normal_query_unverified'):
        need(metrics['body_changed_fraction']>.06,'Claimed different interface not seen')
    if kind in ('injected_blank','injected_fragment','normal_empty_surface'):
        with Image.open(filename(e)) as opened:
            rgb=opened.convert('RGB')
        if kind=='injected_blank':
            need(rgb.getextrema()==((255,255),)*3,'Not an all-white delivered frame')
        elif kind=='normal_empty_surface':
            body=rgb.crop((0,192,1080,2304))
            extremes=[]
            for color in ('black','white'):
                r,g,bl=ImageChops.difference(body,Image.new('RGB',body.size,color)).split()
                hist=ImageChops.lighter(ImageChops.lighter(r,g),bl).histogram()
                extremes.append(sum(hist[:13])/sum(hist))
            metrics['uniform_body_fraction']=round(max(extremes),6)
            need(max(extremes)>.99,'Not an empty app viewport')
        else:
            regs=s['intervention']['button_regions']
            need(regs and s['intervention']['zero_button_regions'] is False,'Missing fragment regions')
            mask=Image.new('L',rgb.size,0);draw=ImageDraw.Draw(mask)
            for reg in regs:
                l,t,r,h=reg['bounds']
                need(0<=l<r<=1080 and 0<=t<h<=2400,'Invalid fragment bounds')
                draw.rectangle((l,t,r-1,h-1),fill=255)
            white=Image.new('RGB',rgb.size,'white')
            need(Image.composite(white,rgb,mask).getextrema()==((255,255),)*3 and rgb.getextrema()!=((255,255),)*3,'Fragment pixels outside logged regions, or empty')
            metrics['retained_rectangle_fraction']=round(mask.histogram()[255]/(1080*2400),6)
            if raw_in_package:
                with Image.open(filename(s['output_delivery']['capture_sha256'])) as raw:
                    need(ImageChops.difference(Image.composite(raw.convert('RGB'),white,mask),rgb).getbbox() is None, 'Fragment differs from its actual native capture')
        need(metrics['body_changed_fraction']>.06,'Missing populated pre-action interface')
    return metrics

def verify_new(p,m,au,d):
    s=au['source']; kind=d['kind']
    need(s['source_run']==d['source_run'] and s['step']==d['step'] and KINDS[kind]==s['condition'], 'Decision is attached to another event')
    b,a,e=receipt(s)
    need(m['source_suite']=='archive_android' and m['origin']==ORIGIN and m['split']=='val' and m['label']=='NO' and m['pair_observed'] is True and m['receipt_valid'] is True, 'New validation origin')
    for field in ('family_id','task_id','trajectory_id','event_id','before_capture_id','capture_id'):
        need(m[field]==s[field],'New source grouping mismatch')
    pair=sha(canon([b,a,e]))
    need([b,a,e]==[m['before_sha256'],m['action'],m['candidate_sha256']] and pair==d['pair_id'] and m['source_observation_id']==sha(canon([s['source_run'],s['step'],pair])),'Receipt vs. model input')
    witnesses=au['donor_sources'];need(len(witnesses)==int(d['control'] is not None),'Control count')
    ctrl=witnesses[0] if witnesses else None
    need(bool(ctrl)==(kind in ('injected_logged_replay','normal_controlled_unchanged')), 'Unexpected control contract')
    support=set()
    if ctrl:
        u,v,w=receipt(ctrl);c=d['control'];wh=(1080,2400)
        need(c['pair_id']==sha(canon([u,v,w])) and (ctrl['source_run'],ctrl['step'])==(c['source_run'],c['step'])!=(s['source_run'],s['step']) and ctrl['condition']=='normal' and e!=w, 'Control identity')
        dist=math.hypot((a['x']-v['x'])*wh[0]/1000,(a['y']-v['y'])*wh[1]/1000) if a['type']==v['type']=='click' else (0 if a==v else math.inf)
        need(dist<=32 and (not c['later_repeat'] or (ctrl['source_run']==s['source_run'] and ctrl['step']==s['step']+1 and u==e)), 'Unrelated control action')
        support.update((u,w))
    raw=s['output_delivery']['capture_sha256']
    available=s['condition']!='normal' and (p/'images'/(raw+'.png')).is_file()
    need(au['evidence']['original_unreplaced_png_in_package'] is available,'Incorrect original-capture availability')
    if available:support.add(raw)
    need(au['support_images']==sorted(support-{b,e}), 'Incorrect evidence image inventory')
    need(au['evidence']['pixel_checks']==inspect_pixels(p,kind,s,ctrl,available),'Image evidence metrics')
