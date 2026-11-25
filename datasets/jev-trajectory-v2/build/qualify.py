"""Qualify new labels against independent evidence, without reading model predictions."""
from common import *
from collections import Counter,defaultdict
from join_archive import okscreen,bystep,u,surface
from archive_files import BLOB,WORK as OLDWORK,content_id

def record(b,a,e,label,method,reason,ev,src,origin='observed_normal'):
    assert label in ('YES','NO') and safe(a)
    return dict(before=b,action=a,after=e,label=label,method=method,reason=reason,evidence=ev,source=src,origin=origin)
def arcsrc(o):
    return dict(suite=o['suite'],family_id=family(o),task_id=task(o),trajectory_id=o['suite']+':'+o['run'],event_id=o['suite']+':'+o['event'],source_run=o.get('source_run',o['run']),step=o.get('step'),capture_id=o['capture_id'],before_capture_id=o['before_capture_id'],source_observation_id=oid(o),before_request=o.get('source_before_request'),after_request=o.get('source_after_request'),log_hashes=o.get('allowed_source_log_sha256'),before_route=o.get('before_url_path'),after_route=o.get('after_url_path'))
def ns(z):
    run=z['source_run'];step=z['step'];tid='natural:'+sha(run.encode())[:24]
    # A capture is the existing source path/receipt, not an invented run-time capture UUID.
    return dict(suite='natural_classifieds',family_id='classifieds',task_id='classifieds:'+z['task'],trajectory_id=tid,event_id=tid+'/'+str(step),source_run=run,step=step,capture_id=run+'/'+z['after']['source_png'],before_capture_id=run+'/'+z['before']['source_png'],before=z['before'],after=z['after'],trace=z['trace'],trace_member_sha256=z['trace_member_sha256'],before_route=z['trace']['before_route'],after_route=z['trace']['after_route'])
def main():
    facts={};eligible={};records=[];cache={};nat=load(NAT/'extract.json')
    base=list(lines(V1/'manifest.jsonl'));ae={r['pair_id']:r for r in lines(V1/'archive-label-evidence.jsonl')}
    for m in base:
        b=m['before_sha256'];e=m['candidate_sha256'];a=m['action'];p=pid(b,a,e)
        if m['split']=='train' and m['label']=='YES' and b!=e and m['phase']=='settled':
            facts[p]=(m['evidence_kind'],m['reason'],{'existing_positive_id':m['sample_id'],**ae.get(p,{}).get('evidence',{})})
    def get(b,a,e,l,r,tr=None):
        p=pid(b,a,e)
        if p in facts:return facts[p]
        key=(p,l,r,str(tr and (tr['scroll_y_before'],tr['scroll_y_after'])))
        if key not in cache:cache[key]=establish(b,a,e,l,r,tr)
        return cache[key]
    selected=set()
    for o in lines(V1/'additional-archive-observations.jsonl'):
        if o['assigned_split']!='train' or o['label'] or o['pair_id'] in selected or o['action']!={'type':'scroll','direction':'down'} or o['before_sha256']!=o['candidate_sha256']:continue
        b=o['before_sha256'];a=o['action'];ev=boundary(b,a,b)
        if ev:
            records.append(record(b,a,b,'YES','visible_scroll_boundary','Further downward scrolling leaves the complete visible page footer at the bottom of the viewport.',ev,arcsrc(o)));selected.add(o['pair_id'])
    natmap={}
    for z in nat['events']:
        b=z['before']['png_sha256'];e=z['after']['png_sha256'];a=z['action']
        if not safe(a):continue
        t=z['trace'];src=ns(z);q=get(b,a,e,t['before_route'],t['after_route'],t);natmap[z['source_run'],z['step']]=(z,q)
        if q:
            records.append(record(b,a,e,'YES',*q,src))
            if b!=e:facts[pid(b,a,e)]=q
    for d in nat['probes']:
        info=natmap.get((d['source_run'],d['step']))
        if info is None:continue
        z,q=info;b=z['before']['png_sha256'];e=z['after']['png_sha256'];a=z['action'];h=d['delivered_sha256']
        if h==e or white(b) or screen(b).shape!=screen(h).shape:continue
        src=ns(z);src.update(capture_id=z['source_run']+'/'+d['relative_file'],probe=d);mf=d['condition'];ev=dict(normal_after_sha256=e)
        if mf=='blank_replace' and white(h):
            method='delivered_blank';why='The delivered PNG is entirely white. There is no visible control, result, or failure message for the dispatched action.'
        elif q and b!=e and mf=='stale_replace' and h==b:
            method='delivered_stale';why='The delivered image is exactly the pre-action screen, whereas the verified normal frame shows a visible outcome.';ev['normal_effect']=q
        elif q and b!=e and mf=='buttons_only' and (v:=partial(b,e,h)):
            method='delivered_partial';why='The visible fragment preserves only unchanged controls. Every pixel region showing the verified normal transition is missing.';ev.update(normal_effect=q,partial=v)
        else:continue
        records.append(record(b,a,h,'NO',method,why,ev,src,'observed_injection'))
    print('natural + boundary',dict(Counter(r['method'] for r in records)),flush=True)
    aliases=load(OLDWORK/'archive-logs-aliases.json');groups=defaultdict(dict)
    for n,org in aliases.items():
        if '/VisualWebArena' in n and re.search(r'/classifieds_[0-9]+/',n):
            run,file=n.rsplit('/',1);groups[run][file]=BLOB/content_id(org)
    for run,pp in sorted(groups.items()):
        cond=run.split('/')[-1];req='model_delivery.jsonl';act='agent_visible_trace.jsonl';ex='action_execution.jsonl'
        if cond not in ('blank_replace','loading_blank','stale_replace') or not {req,act,ex}<=pp.keys():continue
        ds=bystep(pp[req]);ac=bystep(pp[act]);exs=bystep(pp[ex]);rid='archive-'+sha(run.encode())[:24]
        for i,x in sorted(ds.items()):
            y=ds.get(i+1,{});s=ac.get(i,{});a=s.get('action');exe=exs.get(i,{});aa=ac.get(i+1,{})
            if not (okscreen(x) and y.get('injection_fired') is True and y.get('current_image_blocks')==1 and y.get('dom_or_ax_delivered') is False and y.get('request_sha256') and y.get('pre_injection_request_sha256') and exe.get('success') is True and not exe.get('error') and s.get('injection_fired') is False and str(s.get('screenshot','')).endswith('-delivered.png') and aa.get('injection_fired') is True and str(aa.get('screenshot','')).endswith('-delivered.png') and safe(a)):continue
            if any(surface(o.get('captured_url'))!='classifieds' or u(o.get('captured_url')) is None for o in (x,y)):continue
            b=x['delivered_sha256'];h=y.get('delivered_sha256');e=y.get('capture_sha256')
            if not h or not e or e==h:continue
            try:path(b);path(h)
            except FileNotFoundError:continue
            if white(b) or screen(b).shape!=screen(h).shape:continue
            ev={'normal_capture_sha256':e}
            if cond in ('blank_replace','loading_blank') and white(h):
                method='delivered_blank';why='Both the delivery record and decoded pixels identify a completely white candidate: it shows no result or explicit error for the action.'
            elif cond=='stale_replace' and h==b and y.get('stale_source_step') in ds and y['stale_source_step']<=i and ds[y['stale_source_step']].get('capture_sha256')==h:
                try:path(e)
                except FileNotFoundError:continue
                q=get(b,a,e,u(x['captured_url']),u(y['captured_url']))
                if not q:continue
                method='delivered_stale';why='The delivered, logged stale source is the pre-action image. The captured normal outcome is visibly different in the relevant UI.';ev.update(normal_effect=q,stale_source_step=y['stale_source_step'])
            else:continue
            src=dict(suite='archive_vwa',family_id='classifieds',task_id='classifieds:T%03d'%int(re.search(r'/classifieds_(\d+)/',run)[1]),trajectory_id='archive_vwa:'+rid,event_id='archive_vwa:'+rid+'/'+str(i),source_run=run,step=i,before_capture_id=sha(canon([run,i,b]))[:32],capture_id=run+'/'+aa['screenshot'],condition=cond,before_route=u(x['captured_url']),after_route=u(y['captured_url']),log_hashes={k:sha(pp[k].read_bytes()) for k in (req,act,ex)},action_log=act,execution_log=ex,delivery_log=req,execution_success=True,before_request=x['request_sha256'],after_request=y['request_sha256'],archived_capture_sha256=e,archived_delivered_sha256=h)
            records.append(record(b,a,h,'NO',method,why,ev,src,'observed_injection'))
    writel(WORK/'qualified.jsonl',records)
    print('all qualified occurrences before deduplication:',dict(Counter((r['origin'],r['method']) for r in records)),flush=True)
if __name__=='__main__':main()
