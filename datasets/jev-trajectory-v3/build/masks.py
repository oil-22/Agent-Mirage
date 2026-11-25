"""Find recorded, nonempty control-only frames compatible with both sides of a vetted action.

Transfer the full observed set of control rectangles only when their pixels are unchanged. This
never treats an empty mask as buttons-only, and never claims delivery for a new pairing.
"""
from pathlib import Path
from collections import Counter,defaultdict
from functools import lru_cache
import json,hashlib
from PIL import Image, ImageChops
HERE=Path(__file__).resolve().parents[1];BASE=HERE.parent/'jev-trajectory-v2.1';V1=HERE.parent/'jev-trajectory-v1';ROOT=HERE.parents[1]
W=ROOT/'.tmp/jev-balanced-v3';N=ROOT/'.tmp/jev-trajectory-v2-review/natural';A=ROOT/'.tmp/jev-val-v21'
def can(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def js(p):return json.loads(p.read_bytes())
def rows(p):return [json.loads(s) for s in p.read_bytes().splitlines() if s.strip()]
def out(p,rs):p.write_bytes(b''.join(can(r)+b'\n' for r in rs))
def dump(p,x):p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
@lru_cache(1)
def extra():return js(A/'image-paths.json')
@lru_cache(20000)
def path(h):
    for d in (BASE/'images',V1/'images',N,W/'desktop-images'):
        p=d/(h+'.png')
        if p.is_file():return p
    if h in extra():return Path(extra()[h])
    raise FileNotFoundError(h)
def templates():
    refs=[]
    for r in js(W/'natural-mask-references.json'):
        refs.append(dict(split='train',source='natural_classifieds',frame=r['template'],normal=r['normal'],rects=r['rectangles'],run=r['run'],step=r['step'],geometry_digest=r['geometry_file_sha256'],geometry_file=r['geometry_file'],probe=r['source_probe']))
    for r in rows(A/'injected-events.jsonl'):
        if r['condition']!='buttons_only':continue
        it=r['intervention'];rects=sorted({tuple(s['bounds']) for s in it['button_regions']})
        if not rects:continue
        try:path(r['normal']);normal=r['normal']
        except FileNotFoundError:normal=None
        refs.append(dict(split='val',source='archive_android',frame=r['candidate'],normal=normal,rects=rects,run=r['run'],step=r['step'],
                         geometry_digest=sha(can(it)),geometry_record=it,before_request=r['before_request'],after_request=r['after_request'],source_log_sha256=r['source_log_sha256']))
    seen=set();result=[]
    for r in refs:
        name=r['frame']
        if name in seen:continue
        with Image.open(path(name)) as img:
            rgb=img.convert('RGB')
            other=Image.new('RGB',rgb.size,'white')
            for box in r['rects']:other.paste(rgb.crop(box),box[:2])
            if ImageChops.difference(rgb,other).getbbox() is not None:continue
            # Skip effectively white masks or unmappable blocks. Pixels in the normal recovered
            # source must match the photographed control rectangles exactly when available.
            r1,g,b=rgb.split();h=ImageChops.darker(ImageChops.darker(r1,g),b).histogram()
            n=sum(h[:248])
            if not 90<=n<=rgb.width*rgb.height*.34:continue
            if r['normal']:
                with Image.open(path(r['normal'])) as nrm:
                    mask=Image.new('RGB',rgb.size,'white')
                    for bx in r['rects']:mask.paste(nrm.convert('RGB').crop(bx),bx[:2])
                if ImageChops.difference(mask,rgb).getbbox() is not None:continue
            r.update(w=rgb.width,h=rgb.height,nonwhite=n)
        seen.add(name);result.append(r)
    return result
def main():
    ref=templates();dump(W/'templates.json',ref)
    pos=[m for m in rows(BASE/'manifest.jsonl') if m['split'] in ('train','val') and m['label']=='YES' and m['phase']=='settled' and m['before_sha256']!=m['candidate_sha256']]
    dims=defaultdict(set)
    for r in ref:dims[r['w'],r['h']].update(map(tuple,r['rects']))
    @lru_cache(10000)
    def sig(h):
        with Image.open(path(h)) as img:
            rgb=img.convert('RGB');return {b:sha(rgb.crop(b).tobytes()) for b in dims[rgb.size]}
    outrows=[];per=Counter()
    for m in pos:
        b,e=m['before_sha256'],m['candidate_sha256'];x,y=sig(b),sig(e);a=m['action']
        for r in ref:
            if r['split']!=m['split']:continue
            boxes=list(map(tuple,r['rects']))
            if a['type']=='click' and any(l-3<=a['x']*r['w']/1000<u+3 and t-3<=a['y']*r['h']/1000<v+3 for l,t,u,v in boxes):continue
            signature=sig(r['frame'])
            if all(k in x and x[k]==y[k]==signature[k] for k in boxes):
                outrows.append(dict(parent=m['sample_id'],candidate=r['frame'],split=m['split']));per[r['frame']]+=1
    out(W/'buttons-options.jsonl',outrows)
    print('eligible normal control parents',Counter({s:len({v['parent'] for v in outrows if v['split']==s}) for s in ('train','val')}),'observed template hashes with matches',len(per),'eligible by template',sorted(per.values(),reverse=True),flush=True)
if __name__=='__main__':main()
