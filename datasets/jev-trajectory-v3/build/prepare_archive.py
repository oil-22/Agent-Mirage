"""Read selected archived OSWorld receipts, recorded clicks and original PNGs. No UI actions are run."""
import hashlib,json,re,sys
from collections import Counter,defaultdict
from pathlib import Path
HERE=Path(__file__).resolve().parents[1];BASE=HERE.parent/'jev-trajectory-v2.1'
W=HERE.parents[1]/'.tmp/jev-balanced-v3';W.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(HERE.parent/'jev-trajectory-v1'))
import archive_files as ar
from join_archive import bystep
def sha(b):return hashlib.sha256(b).hexdigest()
def can(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def js(p):return json.loads(p.read_bytes())
def dump(p,rows):p.write_bytes(b''.join(can(r)+b'\n' for r in rows))
def main():
    aliases=js(ar.WORK/'archive-logs-aliases.json');idx=ar.index()
    pngs={Path(n).stem:n for n in idx if '/_embedded-input-images/' in n and n.endswith('.png')}
    found={};clean=defaultdict(list);duplicates=0
    for f,k in sorted(aliases.items()):
        if '/OSWorld__' not in f or not f.endswith('/model_delivery.jsonl'):continue
        run=f.rsplit('/',1)[0];domain,task,episode=run.split('/')[-3:]
        if domain not in ('libreoffice_writer','libreoffice_impress','libreoffice_calc','gimp','chrome','vlc','thunderbird'):continue
        wantlogs=('model_delivery.jsonl','coordinate_mapping.jsonl','trajectory.jsonl')
        if not all(run+'/'+n in aliases for n in wantlogs):continue
        files={n:ar.BLOB/ar.content_id(aliases[run+'/'+n]) for n in wantlogs}
        ds,map_,tr=(bystep(files[n]) for n in wantlogs)
        for st,x in ds.items():
            y=ds.get(st+1,{});m=map_.get(st,{});j=tr.get(st,{})
            if not (x.get('injection_fired') is False and x.get('captured_sha256')==x.get('delivered_sha256') and
                y.get('injection_fired') in (True,False) and all(v.get('image_count')==1 and v.get('historical_screenshot_blocks')==0 and v.get('dom_or_ax_delivered') is False and v.get('request_sha256') for v in (x,y))):continue
            b=x['delivered_sha256'];e=y.get('delivered_sha256');h=y.get('captured_sha256')
            if not (b in pngs and e in pngs and h and y.get('previous_delivered_sha256')==b):continue
            act=m.get('executed_native_action')
            if not isinstance(act,str) or act!=j.get('action') or m.get('original_supplied_size')!=[1920,1080]:continue
            ma=re.fullmatch(r'pyautogui\.click\(x=(\d+),\s*y=(\d+)\)',act)
            if not ma:continue
            px,py=map(int,ma.groups())
            if not(0<px<1920 and 0<py<1080) or not any(t.get('native_point')==[px,py] for t in (m.get('mapping') or [])):continue
            a=dict(type='click',x=round(px*1000/1920,7),y=round(py*1000/1080,7))
            mode=y['condition'] if y['injection_fired'] else 'normal'
            if mode not in ('normal','blank_replace','stale_replace','buttons_only'):continue
            if mode=='normal' and (h!=e or b==e):continue
            if mode!='normal' and h==e:continue
            if mode=='stale_replace' and not (b==e and x['captured_sha256']==e):continue
            if mode=='buttons_only' and (y.get('zero_button_regions') is not False or y.get('synthetic_partial_rendering') is not True):continue
            req=[run+'/requests/'+f'{i:03}'+tail+'.json' for i in (st,st+1) for tail in ('','-response')]
            if any(n not in idx for n in req):continue
            if st+1 not in tr:continue
            key=sha(can([b,a,e]))
            if key in found:duplicates+=1;continue
            geom=run+'/intervention/geometry.json'
            if mode=='buttons_only' and geom not in aliases:continue
            r=dict(run=run,domain=domain,task=task,step=st,mode=mode,b=b,e=e,h=h,action=a,
                input_delivery=x,output_delivery=y,executed=act,pixel=[px,py],original_size=m['original_supplied_size'],
                trajectory_action=j['action'],source_log_sha={n:sha(files[n].read_bytes()) for n in wantlogs},
                request_paths=req,pair_id=key,image_members={q:pngs[q] for q in [b,e,h] if q in pngs},
                geometry=js(ar.BLOB/ar.content_id(aliases[geom])) if mode=='buttons_only' else None)
            if h not in r['image_members']:
                z=run+'/'+Path(tr[st+1].get('captured_screenshot','')).name
                if z in idx and z.endswith('.png'):r['image_members'][h]=z
            found[key]=r
            if mode=='normal':clean[domain,task].append(r)
    inject=[r for r in found.values() if r['mode']!='normal']
    # Capture checked clean contrasts across office and browser tasks, not just the injected class.
    ik={(r['b'],r['pixel'][0]//20,r['pixel'][1]//20) for r in inject}
    extra=[r for pool in clean.values() for r in sorted(pool,key=lambda r:((r['b'],r['pixel'][0]//20,r['pixel'][1]//20) not in ik,r['step']!=1,r['pair_id']))[:5]]
    rows=inject+extra;memb={n for r in rows for n in (r['request_paths']+list(r['image_members'].values()))}
    dump(W/'desktop-pending.jsonl',rows)
    print('archive shortlist:',Counter(r['mode'] for r in rows),'requests and original images:',len(memb),flush=True)
    ar.fetch(sorted(memb),idx,W/'desktop-aliases.json')
if __name__=='__main__':main()
