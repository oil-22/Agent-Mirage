from pathlib import Path
from functools import lru_cache
import hashlib,json,math,sys,re
import cv2,numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parents[1]
ROOT=HERE.parents[1]; V1=HERE.parent/'jev-trajectory-v1'
WORK=ROOT/'.tmp/jev-trajectory-v2-review'; NAT=WORK/'natural'
sys.path.insert(0,str(V1))
from export import sha,canon,prompt,action_json,heldout_images,oid,split_groups,part,family,task
from release import native_messages
from join_archive import safe
from archive_rules import getroute,nav
from screen_evidence import scrollevidence
from field_borders import witness
from read_typed_fields import norm
cv2.setNumThreads(1)
def load(p):return json.loads(Path(p).read_bytes())
def lines(p):
    with Path(p).open('rb') as f:
        for l in f:
            if l.strip():yield json.loads(l)
def writej(p,x):Path(p).write_bytes((json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode())
def writel(p,rs):
    with Path(p).open('wb') as f:
        for r in rs:f.write(canon(r)+b'\n')
def path(h):
    for d in (V1/'images',NAT,HERE/'images'):
        p=d/(h+'.png')
        if p.is_file():return p
    raise FileNotFoundError(h)
@lru_cache(22)
def screen(h):
    raw=path(h).read_bytes();assert sha(raw)==h and raw.startswith(b'\x89PNG')
    im=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR)
    assert im is not None and im.shape[0]*im.shape[1]<=4194304
    return im
@lru_cache(160)
def small(h):
    im=screen(h);w=400;t=round(im.shape[0]/im.shape[1]*w)
    return cv2.resize(im,(w,t),interpolation=cv2.INTER_AREA)
def identity_file(p):
    with Image.open(p) as im:
        assert im.format=='PNG' and im.n_frames==1 and im.width*im.height<=4194304
        w,t=im.size;a=im.convert('RGB');full=sha(canon([w,t])+a.tobytes())
        if t>w:
            a=a.crop((0,round(t*.04),w,round(t*.968)));core=sha(canon(list(a.size))+a.tobytes())
        else:core=full
        return core,w,t,full
def pixel_close(a,b,w,h):
    return a['type']==b['type'] and (math.hypot((a['x']-b['x'])*w/1000,(a['y']-b['y'])*h/1000)<=6 if a['type']=='click' else a==b)
def pic(h):return 'images/'+h+'.png'
def pid(b,a,e):return sha(canon([b,a,e]))
def sid(b,a,e):return 'jev-'+pid(b,a,e)[:24]
FOOT='089fd797a5022a336264fd11ff2dd0a73fbb2c8d807d1ea0720994fa2296a5e6'
HEAD='28a37436ee074c6182b662c3c4f7e0f7eb779024f9c9bba8e49d04e597b51218'
def boundary(b,a,e,tr=None):
    if a['type']!='scroll' or b!=e:return
    im=screen(b)
    if im.shape[:2]!=(720,1280):return
    if a['direction']=='down':
        # Complete end-of-document teal footer incl. Contact and copyright, not its color alone.
        if np.array_equal(im[-110:],screen(FOOT)[-110:]):return dict(witness='visible_full_footer',box=[0,610,1280,720],reference=FOOT)
    if a['direction']=='up' and tr and tr.get('scroll_y_before')==tr.get('scroll_y_after')=={'n':0}:
        if np.array_equal(im[:75,120:315],screen(HEAD)[:75,120:315]):return dict(witness='visible_page_header_and_zero_offset',box=[120,0,315,75],reference=HEAD)
def layout(b,e):
    a,z=small(b),small(e);d=(cv2.absdiff(a,z).max(2)>=22).astype(np.float32)
    m=cv2.resize(d,(8,8),interpolation=cv2.INTER_AREA)>.065
    return dict(change=round(float(d.mean()),6),tiles=int(m.sum()),coverage=[int(m.any(axis=x).sum()) for x in (0,1)],edges=[round(float((cv2.Canny(x,50,130)>0).mean()),5) for x in (a,z)])
@lru_cache(1)
def ocr_engine():
    from rapidocr_onnxruntime import RapidOCR
    return RapidOCR(intra_op_num_threads=1,inter_op_num_threads=1,use_text_det=False,use_angle_cls=False)
def ocr(a):
    out,_=ocr_engine()(a)
    return (out[0][1],float(out[0][2])) if out else ('',0.)
def typed(b,a,e):
    q=norm(a['text'])
    if len(q)<2:return
    x,y=screen(b),screen(e);h,w=x.shape[:2]
    mask=(cv2.absdiff(x,y).max(2)>35).astype(np.uint8)
    cs=cv2.findContours(cv2.dilate(mask,cv2.getStructuringElement(cv2.MORPH_RECT,(17,3))),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0]
    for l,t,ww,hh in sorted((cv2.boundingRect(c) for c in cs),key=lambda b:-b[2]*b[3])[:8]:
        if not (7<=hh<=74 and 8<=ww<=min(950,.9*w)):continue
        for pad in (1,12):
            l0,t0,r,b0=max(0,l-pad),max(0,t-3),min(w,l+ww+pad),min(h,t+hh+3)
            out,conf=ocr(y[t0:b0,l0:r]);outn=norm(out)
            if q not in outn or conf<.90:continue
            pre,_=ocr(x[t0:b0,l0:r])
            if outn.count(q)>norm(pre).count(q):return dict(box=[l0,t0,r,b0],after=out,before=pre,confidence=round(conf,4))
def establish(b,a,e,burl,eurl,tr=None):
    if not safe(a) or not (burl and eurl):return
    bd=boundary(b,a,e,tr)
    if bd:return 'visible_scroll_boundary','The stationary viewport shows the boundary in the requested direction.',bd
    if b==e:return
    v=layout(b,e);k=a['type'];same=getroute(burl)==getroute(eurl)
    if nav(dict(action=a,family='classifieds',suite='archive_vwa',before_url_path=burl,after_url_path=eurl),v):
        return 'rendered_navigation','Native navigation changed the task-relevant route and visibly replaced populated page content.',dict(**v,before_route=burl,after_route=eurl)
    if not same:return
    if k=='scroll' and v['change']>.004:
        ev=scrollevidence(small(b),small(e),a['direction'])
        if ev:return 'directional_scroll','Separated distinctive landmarks moved together in the requested direction on the same page.',ev
        if tr and min(v['edges'])>.022 and v['tiles']>=16 and v['change']>=.07:
            u=tr['scroll_y_before'];w=tr['scroll_y_after']
            if isinstance(u,dict) and isinstance(w,dict) and type(u.get('n')) in (int,float) and type(w.get('n')) in (int,float):
                dy=w['n']-u['n'];s=1 if a['direction']=='down' else -1
                if dy*s>=100:return 'visible_browser_scroll','The browser measured a viewport shift in the requested direction; populated page content visibly moved or was replaced across the viewport.',dict(**v,offset_before=u['n'],offset_after=w['n'])
    if k=='click' and 0<v['change']<.045:
        t=screen(b).shape
        ev=witness(screen(b),screen(e),round(a['x']*t[1]/1000),round(a['y']*t[0]/1000))
        if ev:return 'visible_focus_ring','A new four-sided colored focus outline appeared around the clicked control.',ev
    if k=='type' and 0<v['change']<.045 and v['tiles']<15:
        ev=typed(b,a,e)
        if ev:return 'visible_typed_text','OCR reads the dispatched text newly appearing inside the changed input region.',ev
def white(h):
    a=screen(h);return bool(a.min()==255)
def partial(b,e,h):
    # For the shown controls to furnish NO, nothing information-bearing in the fragment
    # may differ from either the earlier or normal screenshot at those coordinates.
    p=screen(h);x=screen(b);y=screen(e)
    if x.shape!=p.shape or p.shape!=y.shape:return
    mask=(p.min(2)<248);n=int(mask.sum())
    if not (90<=n<=.055*mask.size):return
    if np.any(np.abs(x[mask].astype(np.int16)-p[mask].astype(np.int16))>4) or np.any(np.abs(y[mask].astype(np.int16)-p[mask].astype(np.int16))>4):return
    d=cv2.absdiff(x,y).max(2)>24
    if d.sum()<90 or (d&mask).any():return
    return dict(shown_nonwhite_pixels=n,other_pixels_white_or_near_white=int(mask.size-n),visible_outcome_change_pixels_omitted=int(d.sum()),shown_content_identical_to_before_and_normal=True)
