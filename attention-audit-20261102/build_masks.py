import copy,hashlib,json,math,pathlib
import numpy as np
from PIL import Image,ImageDraw
root=pathlib.Path('/data/researcher/attention-audit-20261102');source=root/'campaign';dest=root/'button-campaign';dest.mkdir(exist_ok=True);assets=dest/'assets';assets.mkdir(exist_ok=True)
ann=json.loads((root/'mask-annotations.json').read_text());plan=json.loads((source/'plan.json').read_text());cases=[];audit=[];sheets={}
for s in plan['sources']:
 original=next(c for c in plan['cases'] if c['task']==s['task'] and c['stage']==s['stage'] and c['history']=='full' and c['condition']=='current_control');tid=original['id'].split('-')[0];key=tid+'-'+s['stage']
 pp=next((source/'assets').glob('*/'+s['image_sha256']+'.*'));img=Image.open(pp).convert('RGB');w,h=img.size;arr=np.array(img);keep=np.zeros((h,w),bool)
 rects=ann['replace_base_rectangles'].get(key,ann['bases'][s['app']]+ann['additional_rectangles'].get(key,[]))
 pixelrects=[]
 for a,b,c,d in rects:
  box=[math.floor(a*w/1000),math.floor(b*h/1000),math.ceil(c*w/1000),math.ceil(d*h/1000)];x0,y0,x1,y1=box;keep[y0:y1,x0:x1]=True;pixelrects.append(box)
 masked=np.full_like(arr,255);masked[keep]=arr[keep];out=Image.fromarray(masked)
 import io
 buf=io.BytesIO();out.save(buf,format='PNG');data=buf.getvalue();sha=hashlib.sha256(data).hexdigest();target=assets/sha[:2]/(sha+'.png');target.parent.mkdir(exist_ok=True);target.write_bytes(data)
 assert np.array_equal(masked[keep],arr[keep]) and np.all(masked[~keep]==255)
 audit.append({'id':key,'task':s['task'],'stage':s['stage'],'app':s['app'],'original_sha256':s['image_sha256'],'mask_sha256':sha,'size':[w,h],'normalized_rectangles':rects,'pixel_rectangles':pixelrects,'kept_pixel_fraction':float(keep.mean()),'original_pixels_unchanged_inside_mask':True,'all_pixels_white_outside_mask':True,'mask_version':ann['version']})
 sheet=sheets.setdefault(tid,Image.new('RGB',(1800,400),'white'));idx=['early','middle','late'].index(s['stage']);thumb=out.copy();thumb.thumbnail((595,355));sheet.paste(thumb,(600*idx,40));ImageDraw.Draw(sheet).text((600*idx,5),s['app']+' '+s['stage']+' '+ann['version'],fill='black')
 for history in ['full','last2','none']:
  base=next(c for c in plan['cases'] if c['task']==s['task'] and c['stage']==s['stage'] and c['history']==history and c['condition']=='current_control');case=copy.deepcopy(base);case['id']=case['id'].replace('current_control','buttons_only');case['condition']='buttons_only';case['mask_version']=ann['version'];case['mask_sha256']=sha
  imblocks=[b for b in case['request']['messages'][-1]['content'] if b.get('type')=='image_url'];assert len(imblocks)==1;imblocks[-1]['image_url']['url']='archive-image://sha256/'+sha;cases.append(case)
previews=dest/'previews';previews.mkdir(exist_ok=True)
for tid,sheet in sheets.items():sheet.save(previews/(tid+'.png'))
result={'selection':plan['selection'],'independent_tasks':plan['independent_tasks'],'max_new_tokens':2048,'scope':'Same 10 newly added clean-prefix tasks, early/middle/late x full/last2/none, with visible-control-region mask v2. Combine only with matching new normal/blank/missing/stale cases for five-way comparisons. Do not pool these masks with archived native buttons masks without a version factor.','mask_annotation_sha256':hashlib.sha256((root/'mask-annotations.json').read_bytes()).hexdigest(),'cases':cases}
(dest/'plan.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(dest/'mask-audit.json').write_text(json.dumps(audit,indent=2));(dest/'plan.sha256').write_text(hashlib.sha256((dest/'plan.json').read_bytes()).hexdigest())
print(json.dumps({'masks':len(audit),'cases_per_model':len(cases),'independent_tasks':plan['independent_tasks'],'keep_fraction_range':[min(a['kept_pixel_fraction'] for a in audit),max(a['kept_pixel_fraction'] for a in audit)]}))
