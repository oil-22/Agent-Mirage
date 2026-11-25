"""Look up a physically observed, visibly different result of the same action; never replace the validation candidate."""
from validation_review import *
def ft(h):
    a=tiny(h)[24:309];return cv2.resize(cv2.medianBlur(a,3),(12,24),interpolation=cv2.INTER_AREA).astype(np.float32).ravel()
@lru_cache(450)
def den(h):return cv2.medianBlur(tiny(h)[24:309],3)
def diff(h,k):
    a=cv2.absdiff(den(h),den(k)).max(2)
    return float((a>20).mean()),float(a.mean())
def controls():
    rr=lines(V1/'additional-archive-observations.jsonl');orig=sorted((o for o in rr if o['suite']=='archive_android'),key=lambda r:(r['source_run'],r['step']))
    bypair={};byloc={}
    for o in orig:
        r=mkclean(o);r['known_yes']=o['label']=='YES' and o['evidence_kind']!='visually_supported_noop';r['prior_method']=o['evidence_kind']
        bypair.setdefault(o['pair_id'],r);byloc[r['run'],r['step']]=r
    cand=lines(W/'review-index.jsonl')
    origpool=[]
    for r in bypair.values():
        if r['action']['type'] not in ('click','scroll','back','type'):continue
        if r['known_yes'] or diff(r['before'],r['candidate'])[0]>=.058:origpool.append(r)
    F=np.stack([ft(r['before']) for r in origpool]);terms=[r['action'] for r in origpool]
    groups=defaultdict(list)
    for i,r in enumerate(origpool):groups[r['action']['type']].append(i)
    occ=Counter();qs=[]
    for r in cand:
        if r['review_code'][0] not in ('K','H','R','S'):continue
        if r['condition']=='clean' and diff(r['before'],r['candidate'])[0]>.018:continue
        a=r['action'];ix=[i for i in groups[a['type']] if distance(a,terms[i])<=32]
        if not ix:continue
        b=r['before'];rank=np.abs(F[ix]-ft(b)).mean(1)
        opts=[];n=byloc.get((r['run'],r['step']+1))
        if n and n['before']==r['candidate'] and distance(a,n['action'])<=32 and (n['known_yes'] or diff(n['before'],n['candidate'])[0]>=.058):opts.append((0,n))
        for j in sorted((j for j in range(len(ix)) if rank[j]<=2.8),key=lambda j:(not origpool[ix[j]]['known_yes'],rank[j],distance(a,terms[ix[j]])))[:48]:opts.append((1,origpool[ix[j]]))
        for related,ctrl in opts:
            u=ctrl['before'];e=ctrl['candidate']
            if (r['run'],r['step'])==(ctrl['run'],ctrl['step']):continue
            fr,mad=diff(b,u)
            if fr>.01 or mad>1.8 or e==r['candidate']:continue
            if a['type']=='click':
                cx=round(144*a['x']/1000);cy=round(320*a['y']/1000)
                if not (4<cx<140 and 25<cy<307):continue
                dx=cv2.absdiff(cv2.medianBlur(tiny(b),3),cv2.medianBlur(tiny(u),3)).max(2)[cy-4:cy+5,cx-5:cx+6]
                if (dx>25).mean()>.07:continue
            if not ctrl['known_yes'] and diff(u,e)[0]<.058:continue
            r=dict(r,control=ctrl,control_evidence=dict(later_repeat_in_same_trajectory=related==0,initial_body_changed_fraction=round(fr,5),initial_body_mean_delta=round(mad,3),action_pixel_distance=round(distance(a,ctrl['action']),4)))
            qs.append(r);break
    # Suppress cosmetically different repetitions of roughly the same visible input and target.
    keep=[];sg=defaultdict(list)
    for r in sorted(qs,key=lambda r:(r['condition']=='clean',not r['control']['known_yes'],not r['control_evidence']['later_repeat_in_same_trajectory'],r['review_code'])):
        a=r['action'];pool=sg[a['type'],r['condition']]
        if any(distance(a,q['action'])<=68 and diff(r['before'],q['before'])[0]<.014 and diff(r['candidate'],q['candidate'])[0]<.014 for q in pool):continue
        pool.append(r);keep.append(r)
    for i,r in enumerate(keep):r['match_id']='M'+str(i+1).zfill(3)
    out(W/'matched.jsonl',keep);print('stronger witnesses',len(qs),'after semantic prescreen',len(keep),Counter((r['condition'],r['action']['type']) for r in keep),flush=True)
def gallery():
    vv=lines(W/'matched.jsonl');dest=W/'sheets';dest.mkdir(exist_ok=True);per=12
    for j in range(0,len(vv),per):
        batch=vv[j:j+per];cw,ch=352,298;sheet=Image.new('RGB',(4*cw,math.ceil(len(batch)/4)*ch),'#f4f5f6');dr=ImageDraw.Draw(sheet)
        for i,r in enumerate(batch):
            a=r['action'];x0=cw*(i%4);y0=ch*(i//4)
            dr.text((x0+2,y0),r['match_id']+' '+r['review_code']+'  '+short(a)+'  '+r['family'][:14],font=font(12),fill='black')
            dr.text((x0+2,y0+16),'Before             Received         Control outcome',font=font(12),fill='#234567')
            for col,h in enumerate((r['before'],r['candidate'],r['control']['candidate'])):
                im=Image.fromarray(tiny(h)[:,:,::-1]).resize((115,255),Image.Resampling.BILINEAR);x=x0+col*116;y=y0+34;sheet.paste(im,(x,y))
                if a['type']=='click' and col==0:
                    xx=x+115*a['x']/1000;yy=y+255*a['y']/1000;dr.ellipse([xx-4,yy-4,xx+4,yy+4],outline='#e10061',width=2)
        sheet.save(dest/('M'+str(j+1).zfill(3)+'.jpg'),quality=92)
if __name__=='__main__':controls();gallery()
