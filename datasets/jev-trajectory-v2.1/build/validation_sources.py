"""Bind historical AndroidWorld delivery and execution logs; retrieve original PNGs only."""
from pathlib import Path
from collections import defaultdict,Counter
import json,re,sys,hashlib
HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parents[1];V2=HERE.parent/'jev-trajectory-v2';V1=HERE.parent/'jev-trajectory-v1'
W=ROOT/'.tmp/jev-val-v21';W.mkdir(exist_ok=True)
sys.path.insert(0,str(V1))
from archive_files import WORK,BLOB,content_id,index,fetch
from join_archive import okscreen,bystep,android_action,safe
from export import canon,sha
def read(p):return json.loads(Path(p).read_bytes())
def lines(p):
    with Path(p).open('rb') as f:return [json.loads(l) for l in f if l.strip()]
def dump(p,obj):Path(p).write_bytes((json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode())
def out(p,rs):
    with Path(p).open('wb') as f:
        for r in rs:f.write(canon(r)+b'\n')
def collect():
    aliases=read(WORK/'archive-logs-aliases.json');runs=defaultdict(dict);fs={}
    for n,p in aliases.items():
        if '/AndroidWorld' not in n:continue
        for k in ('/model_delivery.jsonl','/agent_trace.jsonl','/intervention/events.jsonl'):
            if n.endswith(k):runs[n[:-len(k)]][k[1:]]=BLOB/content_id(p);break
    dest=[];cf=Counter()
    for run,pp in sorted(runs.items()):
        mat=re.search(r'/(\d{3})-([A-Z][A-Za-z0-9_]+)(?:/|$)',run)
        if not mat or len(pp)!=3:continue
        ds,acs,ins=(bystep(pp[k]) for k in ('model_delivery.jsonl','agent_trace.jsonl','intervention/events.jsonl'))
        for st,x in ds.items():
            y=ds.get(st+1,{});a=acs.get(st,{});curr=acs.get(st+1,{});it=ins.get(st+1,{});mode=y.get('condition')
            if mode not in ('stale_replace','blank_replace','buttons_only') or y.get('injection_fired') is not True:continue
            wh=x.get('native_dimensions');b=x.get('delivered_sha256');h=y.get('delivered_sha256');normal=y.get('capture_sha256');act=android_action(a,wh)
            if not (safe(act) and okscreen(x) and x.get('image_count')==1 and y.get('image_count')==1 and a.get('injection_fired') is False and curr.get('injection_fired') is True and wh==y.get('native_dimensions') and wh==[1080,2400] and x.get('ax_text_or_indices_delivered') is False and y.get('ax_text_or_indices_delivered') is False and y.get('request_sha256')):continue
            if not (all(isinstance(k,str) and re.fullmatch('[0-9a-f]{64}',k) for k in (b,h,normal)) and y['time']>=x['time'] and it.get('condition')==mode and it.get('injection_fired') is True and it.get('capture_sha256')==normal and it.get('delivered_sha256')==h):continue
            if mode=='stale_replace':
                j=y.get('stale_source_step')
                if type(j)!=int or j>st or j not in ds or ds[j].get('capture_sha256')!=h or it.get('stale_source_step')!=j:continue
            if normal==h:continue
            for f in pp.values():
                if f not in fs:fs[f]=sha(f.read_bytes())
            r=dict(run=run,family=mat[2],step=st,condition=mode,before=b,candidate=h,normal=normal,action=act,native_action=a['action'],dimensions=wh,execution=a.get('execution'),execution_result=a['result'],before_request=x['request_sha256'],after_request=y['request_sha256'],source_log_sha256={k:fs[f] for k,f in pp.items()},intervention=it,stale_source_step=y.get('stale_source_step'))
            dest.append(r);cf[mode]+=1
    out(W/'injected-events.jsonl',dest)
    print('receipt-bound candidates',cf,flush=True)
    idx=index();via={n.rsplit('/',1)[-1][:-4]:n for n in idx if n.startswith('mirage-trace/_shared/input-images/_embedded-input-images/') and n.endswith('.png')}
    wanted={r[k] for r in dest for k in ('before','candidate','normal')}
    status=Counter();needed=[]
    for h in sorted(wanted):
        if (V1/'images'/(h+'.png')).exists():status['already locally verified in v1']+=1
        elif h in via:needed.append(via[h]);status['indexed original PNG']+=1
        else:status['no embedded source for hash']+=1
    print('images',status,flush=True)
    fetch(needed,idx,W/'fetched-aliases.json')
    paths={h:str(V1/'images'/(h+'.png')) for h in wanted if (V1/'images'/(h+'.png')).is_file()}
    for n,orig in read(W/'fetched-aliases.json').items():paths[Path(n).stem]=str(BLOB/content_id(orig))
    for h,p in paths.items():assert sha(Path(p).read_bytes())==h
    dump(W/'image-paths.json',paths)
    print('Bound before/candidate:',Counter(r['condition'] for r in dest if r['before'] in paths and r['candidate'] in paths),'all three:',Counter(r['condition'] for r in dest if all(r[k] in paths for k in ('before','candidate','normal'))),flush=True)
if __name__=='__main__':collect()
