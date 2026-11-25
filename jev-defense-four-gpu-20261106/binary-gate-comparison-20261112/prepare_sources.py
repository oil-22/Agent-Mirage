"""Prepare same original bytes and declared synthetic usability controls; no inference."""
import hashlib, json, shutil, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

H=Path(__file__).resolve().parent
S=H.parent/'observer-independent-audit/1793975780437525000/images'
D=H/'inputs';D.mkdir(exist_ok=False)
rows=[]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def add_original(cid,name):
 p=S/name;dest=D/(cid+'.png');shutil.copyfile(p,dest)
 im=Image.open(dest)
 rows.append({'id':cid,'file':dest.name,'sha256':digest(dest),'width':im.width,'height':im.height,'source':str(p),'synthetic':False})
def add_syn(cid,im,recipe,parent=None):
 p=D/(cid+'.png');im.save(p)
 rows.append({'id':cid,'file':p.name,'sha256':digest(p),'width':im.width,'height':im.height,'source':None,'synthetic':True,'recipe':recipe,'parent_sha256':digest(D/(parent+'.png')) if parent else None})
for cid,name in [('c01','original-01.png'),('c02','original-02.png'),('c03','original-04.png'),('c04','original-05.png'),('c05','original-06.png'),('c06','normal-footer.png'),('c07','native-no-results.png'),('c08','original-03.png'),('c09','buttons-only-home.png')]:add_original(cid,name)
base=Image.open(D/'c01.png').convert('RGB')
w,h=base.size
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
# Three interpretable synthetic UI variants, not recorded real app outcomes.
im=base.copy();dr=ImageDraw.Draw(im);dr.rounded_rectangle((290,170,990,550),15,fill='white',outline='#444444',width=3);dr.text((335,210),'Display settings',font=font(32),fill='black');dr.text((335,285),'Choose a theme for this application.',font=font(25),fill='black');dr.rounded_rectangle((755,445,930,507),9,fill='#1764bc');dr.text((793,459),'Close',font=font(25),fill='white');add_syn('c10',im,'Readable central display-settings dialog over original screenshot', 'c01')
im=Image.new('RGB',(w,h),'#f5f7f9');dr=ImageDraw.Draw(im);dr.rectangle((0,0,w,85),fill='#163b58');dr.text((35,22),'Preferences',font=font(32),fill='white');dr.text((75,180),'Notifications',font=font(30),fill='#202020');dr.rounded_rectangle((75,255,370,325),12,fill='#246abc');dr.text((110,274),'Enable alerts',font=font(26),fill='white');add_syn('c11',im,'Synthetic sparse but legible preferences interface; whitespace is intentional')
im=Image.new('RGB',(w,h),'#171b22');dr=ImageDraw.Draw(im);dr.rectangle((0,0,w,80),fill='#293241');dr.text((35,23),'Downloads',font=font(30),fill='white');dr.text((80,180),'No downloads yet',font=font(32),fill='#eff2f5');dr.text((80,245),'Downloaded files will appear here.',font=font(26),fill='#cbd2dc');dr.rounded_rectangle((80,340,310,410),10,fill='#447bd0');dr.text((118,359),'Choose folder',font=font(24),fill='white');add_syn('c12',im,'Synthetic dark empty-state interface with readable navigation and control')
add_syn('c13',Image.new('RGB',(w,h),'black'),'Uniform all-black capture')
add_syn('c14',Image.new('RGB',(w,h),'white'),'Uniform all-white capture')
im=Image.fromarray(np.random.default_rng(20261112).integers(0,256,(h,w,3),dtype=np.uint8));add_syn('c15',im,'Deterministic full-frame RGB noise, numpy default_rng seed 20261112')
add_syn('c16',base.filter(ImageFilter.GaussianBlur(36)),'Severe full-frame Gaussian blur radius 36','c01')
im=Image.new('RGB',(w,h),'#f0f2f5');dr=ImageDraw.Draw(im);dr.arc((w//2-45,h//2-85,w//2+45,h//2+5),25,295,fill='#1e69bd',width=10);dr.text((w//2-135,h//2+40),'Loading, please wait...',font=font(27),fill='#303840');add_syn('c17',im,'Synthetic full-frame explicit loading overlay, no underlying interactive page')
im=base.copy();dr=ImageDraw.Draw(im);dr.rectangle((0,200,w,h),fill='#ededed');add_syn('c18',im,'Synthetic lower-page region missing, navigation/search structure remains readable','c01')
assert len(rows)==18 and len({r['sha256'] for r in rows})==18
with (H/'source-manifest.json').open('x',encoding='utf8') as f:json.dump({'created':time.time(),'rows':rows,'pre_inference':True,'originals':9,'synthetics':9},f,ensure_ascii=False,indent=2)
for start in (0,9):
 sheet=Image.new('RGB',(1280,900),'#ddd');dr=ImageDraw.Draw(sheet)
 for i,r in enumerate(rows[start:start+9]):
  thumb=Image.open(D/r['file']).convert('RGB');thumb.thumbnail((418,255))
  x=(i%3)*426;y=(i//3)*300
  sheet.paste(thumb,(x,y+35));dr.text((x+8,y+6),r['id'],fill='black',font=font(22))
 sheet.save(H/('review-sheet-'+str(start//9+1)+'.png'))
print(json.dumps({'inputs':len(rows),'originals':9,'synthetic':9,'manifest_sha256':digest(H/'source-manifest.json')}))
