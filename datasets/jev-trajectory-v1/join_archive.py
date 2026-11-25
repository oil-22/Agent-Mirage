"""Join the original action receipt and two consecutive, actually delivered PNG digests."""
from pathlib import Path
from collections import Counter,defaultdict
import ast, hashlib,json,math,re,sys
from urllib.parse import urlsplit
from archive_files import HERE,WORK,BLOB,content_id,index
from export import action_json,canon,sha,write_json

def safe(a):
    # Exclude unconstrained scripting, secrets, URLs and text too long for reliable
    # review. Only native, unambiguous read/input actions enter this benchmark.
    if not isinstance(a,dict) or a.get('type') not in ('click','scroll','type','press','back'):return False
    if a['type']=='type':
        s=a.get('text','')
        if not isinstance(s,str) or not 1<=len(s)<=96 or not re.fullmatch(r"[\w \-,.'’!?\(\)]{1,96}",s) or re.search(r'password|token|passwd|secret|sudo|powershell',s,re.I):return False
    if a['type']=='press' and a.get('key') not in ('Enter','Return','Home','End','Backspace','Delete','Escape','Tab','ArrowDown','ArrowUp','ArrowLeft','ArrowRight','Control+a','Control+A','Ctrl+a','PageDown','PageUp','Space','space','Down','Up'):return False
    try:action_json(a);return True
    except (ValueError,TypeError):return False
def bystep(p):
    if p is None:return {}
    result={}
    for l in p.read_bytes().splitlines():
        if not l.strip():continue
        r=json.loads(l);st=r.get('step')
        if type(st)!=int or st<0:continue
        if st in result and r!=result[st]:return {}
        result[st]=r
    return result
def okscreen(r):
    if r.get('injection_fired') is not False:return False
    h=r.get('capture_sha256') or r.get('captured_sha256')
    return bool(h) and h==r.get('delivered_sha256') and bool(r.get('request_sha256',r.get('pre_injection_request_sha256'))) and (r.get('delivered_current_image') is True or r.get('image_count')==1)
def u(s):
    o=urlsplit(s or '')
    if o.scheme not in ('http','https') or o.hostname not in ('192.0.2.10','localhost','127.0.0.1'):return None
    return o.path + (('?'+o.query) if o.query else '')
def surface(s):
    port=urlsplit(s or '').port
    return {980:'classifieds',999:'reddit'}.get(port%1000 if port else None,'other')
def native_click(x,y,wh):
    if type(x) not in (float,int) or type(y) not in (float,int):return {}
    return {'type':'click','x':round(1000*x/wh[0],7),'y':round(1000*y/wh[1],7)}
def android_action(r,wh):
    a=r.get('action',{});k=a.get('action_type'); pr=r.get('execution') or {}
    if pr.get('primitive')!='official_execute_action' or not r.get('result','').startswith('Action executed'):return {}
    if k=='click':return native_click(a.get('x'),a.get('y'),wh)
    if k=='navigate_back':return {'type':'back'}
    if k=='input_text':return {'type':'type','text':a.get('text')}
    if k=='scroll':return {'type':'scroll','direction':a.get('direction')}
    return {}
def main():
    aliases=json.loads((WORK/'archive-logs-aliases.json').read_bytes());groups=defaultdict(dict)
    for n,org in aliases.items():
        ds=n.split('/')[2].split('__')[0]
        if ds in ('VisualWebArena','AndroidWorld'):
            p=BLOB/content_id(org)
            if not p.is_file():raise ValueError('Logs not completely transferred: '+org)
            run,k=n.rsplit('/',1);groups[run][k]=p
    idx=index(); image_alias={n.rsplit('/',1)[-1][:-4]:n for n in idx if n.startswith('mirage-trace/_shared/input-images/_embedded-input-images/') and n.endswith('.png')}
    used=set();g=defaultdict(list);counts=Counter();filehash={}; allruns=set()
    for run,paths in sorted(groups.items()):
        ds=run.split('/')[2].split('__')[0]; web=ds=='VisualWebArena'
        if web:
            m=re.search(r'/(classifieds|reddit|shopping)_(\d+)(?:/|$)',run)
            if not m:continue
            family=m[1];task='T%03d'%int(m[2])
        else:
            m=re.search(r'/(\d{3})-([A-Z][A-Za-z0-9_]+)(?:/|$)',run)
            if not m:continue
            family='android:'+m[2];task=m[2]
        delkey='model_delivery.jsonl';actkey='agent_visible_trace.jsonl' if web else 'agent_trace.jsonl';exkey='action_execution.jsonl' if web else actkey
        if not {delkey,actkey,exkey}<=paths.keys():continue
        d=bystep(paths[delkey]);a=bystep(paths[actkey]);e=bystep(paths[exkey]) if web else a
        th=sha(run.encode())
        for st,x in sorted(d.items()):
            if st+1 not in d or st not in a or st not in e:continue
            y=d[st+1];ac=a[st];ex=e[st]
            if not (okscreen(x) and okscreen(y)):continue
            if web:
                if ex.get('success') is not True or ex.get('error') or ac.get('injection_fired') is True or not str(ac.get('screenshot','')).endswith('-delivered.png'):continue
                if u(x.get('captured_url')) is None or u(y.get('captured_url')) is None:continue
                action=ac.get('action'); wh=None; raw=action
            else:
                wh=x['native_dimensions']
                if wh!=y['native_dimensions'] or len(wh)!=2:continue
                action=android_action(ac,wh);raw=ac.get('action')
            if not safe(action):continue
            h=x['capture_sha256'];h2=y['capture_sha256']
            if not all(z in image_alias for z in (h,h2)):counts[ds+': missing archived PNG']+=1;continue
            # Storing an integer vs a float is significant to the native text encoder.
            pair=sha(canon([h,action,h2]));allruns.add(run)
            for k in (exkey,delkey,actkey):
                p=paths[k]
                if p not in filehash:filehash[p]=sha(p.read_bytes())
            g[pair].append(dict(suite='archive_vwa' if web else 'archive_android',family=family,task=task,run='archive-'+th[:24],event='archive-'+th[:24]+'/'+str(st),
                capture_id=sha(canon([run,st+1,h2]))[:32],before_capture_id=sha(canon([run,st,h]))[:32],before_sha256=h,candidate_sha256=h2,action=action,pair_id=pair,raw_action=raw,step=st,
                source_run=run,source_action=run+'/'+actkey,source_audit=run+'/'+exkey,source_delivery=run+'/'+delkey,
                allowed_source_log_sha256={k:filehash[paths[k]] for k in (actkey,delkey,exkey)},source_before_request=x['request_sha256'],source_after_request=y['request_sha256'],
                before_url_path=u(x.get('captured_url')),after_url_path=u(y.get('captured_url')),
                actual_surfaces=[surface(x.get('captured_url')),surface(y.get('captured_url'))] if web else ['android','android'],native_dimensions=wh))
            used.update((h,h2))
    (WORK/'archive-joined.jsonl').write_bytes(b''.join(canon(r)+b'\n' for k in sorted(g) for r in g[k]))
    (WORK/'archive-pair-reps.jsonl').write_bytes(b''.join(canon(g[k][0])+b'\n' for k in sorted(g)))
    (WORK/'wanted-archive-images.json').write_text(json.dumps(sorted(image_alias[h] for h in used)),encoding='utf8')
    stats=dict(archive='4090:/data/researcher/Agent-Mirage-Archive-20261029/Agent-Mirage-20261029.tar.gz',index_sha256=sha((WORK/'archive-members.jsonl.gz').read_bytes()),available_runs=len(allruns),candidate_occurrences=sum(map(len,g.values())),distinct_candidates=len(g),distinct_original_images=len(used),candidates_by_suite_action=dict(Counter(r[0]['suite']+':'+r[0]['action']['type'] for r in g.values())),excluded=dict(counts))
    write_json('archive-join-counts.json',stats);print(stats,flush=True)
if __name__=='__main__':main()
