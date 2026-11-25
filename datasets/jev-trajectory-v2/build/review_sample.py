"""Make deterministic visual spot-check sheets from the released PNGs; QA marks never enter training."""
from common import *
from PIL import ImageDraw,ImageFont,ImageOps
from collections import defaultdict
def main():
    rr=list(lines(HERE/'manifest.jsonl'));aud={r['sample_id']:r for r in lines(HERE/'audit.jsonl')};bins=defaultdict(list)
    for r in rr:
        if r['origin']!='observed_v1':bins[r['evidence_kind']].append(r)
    sel=[]
    for kind,rows in sorted(bins.items()):
        sel+=sorted(rows,key=lambda r:sha(('v2-visual-qa/'+r['sample_id']).encode()))[:3]
    out=WORK/'spotcheck';out.mkdir(exist_ok=True);idx=[]
    for j in range(0,len(sel),5):
        batch=sel[j:j+5];sheet=Image.new('RGB',(1152,246*len(batch)),'#f0f1f4');dr=ImageDraw.Draw(sheet)
        for n,r in enumerate(batch):
            i=r['sample_id'];a=r['action'];b,e=r['before_sha256'],r['candidate_sha256'];q=aud[i];ev=q.get('evidence',{});ex=ev.get('expected_after_sha256') or ev.get('normal_after_sha256') or ev.get('normal_capture_sha256');k=r['evidence_kind']
            y=246*n;dr.text((6,y+1),f"{j+n+1:02}  {k}  {r['label']}   {str(a)}    {i}",fill='black')
            for col,h,name in [(0,b,'1: before'),(1,e,'2: candidate'),(2,ex,'observed normal outcome')]:
                if not h:continue
                try:im=Image.open(path(h)).convert('RGB')
                except FileNotFoundError:continue
                im.thumbnail((379,210));x=384*col;sheet.paste(im,(x,y+32));dr.text((x+2,y+16),name,fill='black')
                if a['type']=='click' and col==0:
                    xx=x+im.width*a['x']/1000;yy=y+32+im.height*a['y']/1000;dr.ellipse([xx-5,yy-5,xx+5,yy+5],outline='red',width=2)
            roi=ev.get('rule',{}).get('expected_ocr',{}).get('box') or ev.get('box') or ev.get('focus_box')
            if roi and k in ('different_typed_value','visible_typed_text','visible_focus_ring'):
                l,t,rrr,bb=roi
                if 'focus_box' in ev:rrr+=l;bb+=t
                for co,h in enumerate((b,e,ex)):
                    if not h:continue
                    im=Image.open(path(h)).convert('RGB');crop=im.crop((max(0,l-8),max(0,t-4),min(im.width,rrr+36),min(im.height,bb+4)));crop.thumbnail((356,55));sheet.paste(crop,(384*co+15,y+177))
            idx.append(dict(index=j+n+1,sample_id=i,method=k))
        sheet.save(out/f'sheet-{j//5+1:02}.jpg',quality=89)
    writej(WORK/'spotcheck-index.json',idx)
if __name__=='__main__':main()
