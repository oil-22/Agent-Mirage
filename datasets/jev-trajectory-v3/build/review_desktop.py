"""Rehydrate both archived requests to their original logged hashes and inspect received images."""
import base64,collections,copy,json,math,re,shutil,sys
from functools import lru_cache
from PIL import Image,ImageDraw,ImageFont,ImageChops
from prepare_archive import W,ar,sha,can,js,dump
P=W/'desktop-images';P.mkdir(exist_ok=True)
G=W/'desktop-gallery';G.mkdir(exist_ok=True)
def file_of(aliases,n):return ar.BLOB/ar.content_id(aliases[n])
def full(h):
    with Image.open(P/(h+'.png')) as im:return im.convert('RGB')
@lru_cache(50)
def coded(h):return base64.b64encode((P/(h+'.png')).read_bytes()).decode()
def request(aliases,name,reply,delivery):
    blob=file_of(aliases,name).read_bytes();rh=delivery['delivered_sha256'];q=json.loads(blob);refs=[]
    for m in q.get('messages',[]):
        for item in m.get('content',[]) if isinstance(m.get('content'),list) else []:
            if item.get('type')=='image_url':
                u=item['image_url']['url'];refs.append(u);item['image_url']['url']='data:image/png;base64,'+coded(rh)
    if refs!=['archive-image://sha256/'+rh]:return
    def same(): # Most logged requests use sorted keys with default separators.
        for sort,asc,sep in ((True,False,None),(True,True,None),(True,False,(',',':')),(True,True,(',',':')),(False,False,None),(False,True,None)):
            if sha(json.dumps(q,sort_keys=sort,ensure_ascii=asc,separators=sep).encode())==delivery['request_sha256']:return [sort,asc,sep]
    fmt=same()
    if not fmt:return
    raw=file_of(aliases,reply).read_bytes();z=json.loads(raw)
    if not isinstance(z,dict) or z.get('status')!=200:return
    b=z['body'];b=json.loads(b) if isinstance(b,str) else b
    choice=(b.get('choices') or [{}])[0];msg=choice.get('message') or {}
    if not b.get('id') or msg.get('role')!='assistant' or not (msg.get('content') or msg.get('tool_calls') or msg.get('reasoning_content')):return
    return dict(request_file=name,archive_request_file_sha256=sha(blob),original_request_hash_verified=delivery['request_sha256'],format=fmt,
                single_archive_image=rh,response_file=reply,response_file_sha256=sha(raw),http_status=200,response_id=b['id'])
def prepare():
    al=js(W/'desktop-aliases.json');src=[json.loads(l) for l in (W/'desktop-pending.jsonl').read_bytes().splitlines()]
    ok=[];bad=collections.Counter()
    for r in src:
        for h,f in list(r['image_members'].items()):
            raw=file_of(al,f).read_bytes()
            if sha(raw)!=h:
                if h in (r['b'],r['e']):raise ValueError('Incorrect archived model input')
                continue
            out=P/(h+'.png')
            if not out.exists():out.write_bytes(raw)
        q=r['request_paths'];x=request(al,q[0],q[1],r['input_delivery']);y=request(al,q[2],q[3],r['output_delivery'])
        if not x or not y:bad['request/response']+=1;continue
        if any(full(h).size!=(1920,1080) for h in set((r['b'],r['e']))):bad['viewport']+=1;continue
        if r['mode']=='blank_replace' and full(r['e']).getextrema()!=((255,255),)*3:bad['not white']+=1;continue
        r['proof']=[x,y];r['normal_png_recovered']=(P/(r['h']+'.png')).is_file()
        if r['mode']=='buttons_only':
            rgb=full(r['e']);canvas=Image.new('RGB',rgb.size,'white')
            regs=r['geometry'].get('regions',[])
            boxes=[v['bounds'] for v in regs if isinstance(v.get('bounds'),list) and len(v['bounds'])==4]
            if not boxes:bad['no mask']+=1;continue
            outside=rgb.copy();dr=ImageDraw.Draw(outside)
            for l,t,u,v in boxes:
                if 0<=l<u<=rgb.width and 0<=t<v<=rgb.height:dr.rectangle((l,t,u-1,v-1),fill='white')
            if outside.getextrema()!=((255,255),)*3 or rgb.getextrema()==((255,255),)*3:bad['not a real nonempty rectangular mask']+=1;continue
        ok.append(r)
    for mode,pfx in [('normal','Y'),('buttons_only','P'),('stale_replace','S'),('blank_replace','B')]:
        pool=sorted((r for r in ok if r['mode']==mode),key=lambda r:(r['domain'],r['task'],r['pair_id']))
        for i,r in enumerate(pool,1):r['code']=f'{pfx}{i:03}'
    dump(W/'desktop-bound.jsonl',ok)
    print('Fully reconciled native requests, successful responses, and PNGs:',collections.Counter(r['mode'] for r in ok),'excluded:',bad,flush=True)
def sheets():
    ff=ImageFont.truetype('arial.ttf',13)
    rows=[json.loads(l) for l in (W/'desktop-bound.jsonl').read_bytes().splitlines()]
    for mode in 'YPSB':
        rr=sorted((r for r in rows if r['code'].startswith(mode)),key=lambda r:r['code'])
        for j in range(0,len(rr),10):
            bb=rr[j:j+10];cw,ch=625,138;sheet=Image.new('RGB',(2*cw,math.ceil(len(bb)/2)*ch),'#f1f3f5');dr=ImageDraw.Draw(sheet)
            for i,r in enumerate(bb):
                x=(i%2)*cw;y=i//2*ch;px,py=r['pixel'];dr.text((x+1,y),f"{r['code']}  {r['domain']}   click {px},{py}   {r['task'][:7]}",fill='black',font=ff)
                b=full(r['b']);out=full(r['e'])
                x0=max(0,min(1920-430,px-215));y0=max(0,min(1080-175,py-87))
                for k,img in enumerate((b,out)):
                    xx=x+197*k;yy=y+22
                    sheet.paste(img.resize((193,109),Image.Resampling.LANCZOS),(xx,yy))
                    zx=x+396;zy=y+17+58*k
                    sheet.paste(img.crop((x0,y0,x0+430,y0+175)).resize((140,57),Image.Resampling.LANCZOS),(zx,zy))
                    if k==0:
                        for u,v in ((xx+px*193/1920,yy+py*109/1080),(zx+(px-x0)*140/430,zy+(py-y0)*57/175)):dr.ellipse((u-4,v-4,u+4,v+4),outline='#ed145e',width=2)
                if r['normal_png_recovered'] and r['mode'] not in ('normal','blank_replace'):
                    sheet.paste(full(r['h']).resize((84,48),Image.Resampling.LANCZOS),(x+539,y+44));dr.text((x+539,y+25),'Raw',font=ff,fill='black')
            sheet.save(G/f'{mode}{j+1:03}.jpg',quality=95)
if __name__=='__main__':
    prepare();sheets()
