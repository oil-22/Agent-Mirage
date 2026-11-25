"""Select eligible *observed* Android pairs for independent image review. No inference/model output is used."""
from validation_sources import *
from collections import defaultdict,Counter
from functools import lru_cache
import cv2,numpy as np,math
from PIL import Image,ImageDraw,ImageFont
cv2.setNumThreads(1)
P=read(W/'image-paths.json')
def imagepath(h):
    p=V1/'images'/(h+'.png')
    return p if p.is_file() else Path(P[h])
@lru_cache(125)
def tiny(h):
    cache=WORK/'thumbs'/(h+'.png')
    if cache.exists():
        im=cv2.imread(str(cache));return cv2.resize(im,(144,320),interpolation=cv2.INTER_AREA)
    with Image.open(imagepath(h)) as im:return np.asarray(im.convert('RGB').resize((144,320),Image.Resampling.BOX))[:,:,::-1].copy()
@lru_cache(125)
def whole(h):
    with Image.open(imagepath(h)) as im:return im.convert('RGB')
@lru_cache(10000)
def content(h):
    idx=readcontent()
    if h in idx:return idx[h][0]
    with Image.open(imagepath(h)) as im:
        w,t=im.size;a=im.convert('RGB').crop((0,round(t*.04),w,round(t*.968)))
        return sha(canon(list(a.size))+a.tobytes())
@lru_cache(1)
def readcontent():return read(V1/'archive-content-index.json')
def distance(a,b):
    if a['type']!=b['type']:return 1e9
    if a['type']=='click':return math.hypot((a['x']-b['x'])*1.08,(a['y']-b['y'])*2.4)
    return 0 if a==b else 1e9
def apair(b,a,e):return sha(canon([b,a,e]))
def mkclean(o):
    return dict(run=o['source_run'],family=o['family'].removeprefix('android:'),step=o['step'],condition='clean',before=o['before_sha256'],candidate=o['candidate_sha256'],action=o['action'],native_action=o['raw_action'],dimensions=o['native_dimensions'],before_request=o['source_before_request'],after_request=o['source_after_request'],source_log_sha256=o['allowed_source_log_sha256'],v1_pair_id=o['pair_id'],v1_capture_id=o['capture_id'],v1_before_capture_id=o['before_capture_id'])
def nearby(b,e):
    x=tiny(b)[15:308];y=tiny(e)[15:308];m=cv2.absdiff(x,y).max(2)
    return (round(float((m>22).mean()),6),round(float(m.mean()),4))
def candidates():
    rr=lines(V1/'additional-archive-observations.jsonl');obs=sorted((o for o in rr if o['suite']=='archive_android'),key=lambda z:(z['source_run'],z['step']))
    old=[m for m in lines(V2/'manifest.jsonl') if m['split']=='val'];prev=defaultdict(list);seen=defaultdict(list);items=defaultdict(list);sk=Counter()
    for m in old:
        b=m['before_sha256'];e=m['candidate_sha256'];prev[content(b),content(e)].append(m['action'])
    # Even a non-exported definite YES from an independently reviewed visual alias is a veto.
    for o in obs:
        if o.get('label'):prev[content(o['before_sha256']),content(o['candidate_sha256'])].append(o['action'])
    stepmap={(o['source_run'],o['step']):o for o in obs};reps={}
    for o in obs:
        if not o['label']:reps.setdefault(o['pair_id'],mkclean(o))
    inject=lines(W/'injected-events.jsonl')
    for r in sorted(inject+list(reps.values()),key=lambda r:(r['condition']=='clean',r['run'],r['step'])):
        b=r['before'];e=r['candidate'];a=r['action'];cond=r['condition'];t=a['type']
        if cond!='clean' and (b not in P or e not in P):continue
        x,y=content(b),content(e)
        if any(distance(a,act)<=22 for act in prev[x,y]):sk['previous definite or close equivalent']+=1;continue
        if any(distance(a,act)<=60 for act in seen[x,y]):sk['same rendered pair & nearby target']+=1;continue
        seen[x,y].append(a)
        r['pair_id']=apair(b,a,e);r['body_equal']=x==y
        if cond!='clean':group={'stale_replace':'S','blank_replace':'B','buttons_only':'P'}[cond]
        else:
            frac,mad=nearby(b,e);r['changed_fraction_thumbnail']=frac;r['mean_delta_thumbnail']=mad
            if t=='type':group='T'
            elif t=='click' and (r['body_equal'] or frac<.028):group='K'
            elif t=='back' and (r['body_equal'] or frac<.028):group='R'
            elif t=='scroll' and frac<.02:group='H'
            elif t=='scroll':group='J'
            elif t=='click':group='C'
            else:group='A'
            nxt=stepmap.get((r['run'],r['step']+1))
            if nxt and r['candidate']==nxt['before_sha256'] and distance(r['action'],nxt['action'])<65 and content(nxt['candidate_sha256'])!=y and group in ('K','R','H'):
                r['next_same_action']=dict(pair_id=nxt['pair_id'],image=nxt['candidate_sha256'],step=nxt['step'],action=nxt['action'])
        items[group].append(r)
    # At the front of each sheet put one sample per trace before taking additional rows from that trace.
    for g,v in items.items():
        fam=defaultdict(list);occ=Counter()
        for r in sorted(v,key=lambda r:(not bool(r.get('next_same_action')),sha(('val-neg-review-v1/'+r['pair_id']).encode()))):
            i=occ[r['run']];occ[r['run']]+=1;fam[r['family']].append((i,r))
        order=[]
        for f,vs in sorted(fam.items()):
            vs.sort(key=lambda z:(z[0],sha(('val-neg-fam/'+z[1]['pair_id']).encode())))
            order.extend((i,sha(('val-neg-view/'+r['pair_id']).encode()),r) for i,(_,r) in enumerate(vs))
        items[g]=[dict(r,review_code=g+str(i+1).zfill(3)) for i,(_,__,r) in enumerate(sorted(order))]
    out(W/'review-index.jsonl',[r for g in sorted(items) for r in items[g]])
    print('candidate screen groups',dict((g,len(v)) for g,v in items.items()),sk,flush=True)
def font(n):return ImageFont.truetype('arial.ttf',n)
def short(a):
    return {'click':'tap %s %s'%(round(a.get('x',0)),round(a.get('y',0))),'type':'type: '+str(a.get('text','')),'back':'Back','scroll':'scroll '+str(a.get('direction',''))}.get(a['type'],a['type'])
def sheets(g,start,end):
    vv=[r for r in lines(W/'review-index.jsonl') if r['review_code'].startswith(g)];dest=W/'sheets';dest.mkdir(exist_ok=True)
    tw=137;th=304;cw=470;ch=343;per=9
    for j in range(start-1,min(end,len(vv)),per):
        batch=vv[j:j+per];sheet=Image.new('RGB',(cw*3,ch*math.ceil(len(batch)/3)),'#f4f5f6');sd=ImageDraw.Draw(sheet)
        for i,r in enumerate(batch):
            x0=i%3*cw;y0=i//3*ch;a=r['action'];b,e=r['before'],r['candidate'];s=r.get('normal');nxt=r.get('next_same_action',{}).get('image')
            sd.text((x0+4,y0+1),r['review_code']+' '+short(a)[:37]+' '+r['family'][:16],font=font(14),fill='black')
            sd.text((x0+4,y0+18),'Before               Received              '+('Raw capture' if s in P else 'Next same action' if nxt else 'Target detail' if a['type']=='click' else ''),font=font(12),fill='#314453')
            for col,h in enumerate((b,e,s if s in P else nxt)):
                xx=x0+col*152;yy=y0+34
                if not h:continue
                im=Image.fromarray(tiny(h)[:,:,::-1]).resize((tw,th),Image.Resampling.BILINEAR);sheet.paste(im,(xx,yy))
                if col==0 and a['type']=='click':
                    cx=xx+tw*a['x']/1000;cy=yy+th*a['y']/1000;sd.ellipse([cx-5,cy-5,cx+5,cy+5],outline='#ed1164',width=2)
            if a['type']=='click' and not nxt and s not in P:
                px=int(a['x']*1.08);py=int(a['y']*2.4);l=min(max(0,px-246),1080-492);t0=min(max(0,py-151),2400-302)
                for z,h in enumerate((b,e)):
                    crop=whole(h).crop((l,t0,l+492,t0+302)).resize((151,93),Image.Resampling.LANCZOS);sheet.paste(crop,(x0+304,y0+65+z*119))
                    if z==0:
                        cx=x0+304+(px-l)*151/492;cy=y0+65+(py-t0)*93/302;sd.ellipse([cx-4,cy-4,cx+4,cy+4],outline='#ed1164',width=1)
        sheet.save(dest/(g+str(j+1).zfill(3)+'.jpg'),quality=92)
if __name__=='__main__':
    if len(sys.argv)==1:candidates()
    else:
        for arg in sys.argv[1:]:
            g,lo,hi=arg.split(':');sheets(g,int(lo),int(hi))
