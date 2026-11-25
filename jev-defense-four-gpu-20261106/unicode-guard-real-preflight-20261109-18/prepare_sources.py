"""Six genuinely new full offline fixtures for native length-guard generation.

These are not native benchmark trajectories or repeated failed source images.
Only public pixels are model input; private renderer geometry never is.
"""
import hashlib
import json
from pathlib import Path
import time
from PIL import Image,ImageDraw,ImageFont

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p,value):
    with p.open('x',encoding='utf8')as stream:json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')


def main():
    out=HERE/'sources';assert not out.exists();out.mkdir();public=out/'public';public.mkdir()
    fonts={n:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)for n in [18,22,28,34]}
    cjk=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',28)
    rows=[];geometry={}
    def page(title):
        image=Image.new('RGB',(1280,720),'#f5f6f8');d=ImageDraw.Draw(image)
        d.rectangle([0,0,1279,82],fill='#173e4b');d.text((34,23),'Harbor Workspace',font=fonts[28],fill='white')
        d.text((920,31),'Offline fixture',font=fonts[18],fill='#d7e6eb')
        d.text((45,111),title,font=fonts[34],fill='#183c4b')
        return image,d
    def button(d,box,text):
        d.rounded_rectangle(box,radius=5,outline='#427a8c',width=2,fill='white')
        d.text((box[0]+15,box[1]+13),text,font=fonts[22],fill='#244e60')
    def finish(name,image,boxes):
        p=public/(name+'.png');image.save(p);image.close()
        rows.append({'id':name,'file':p.name,'sha256':sha(p),'size':[1280,720]});geometry[name]=boxes

    image,d=page('Objects in the current collection')
    d.rounded_rectangle([65,220,535,600],radius=8,outline='#bdcbd0',width=2,fill='white')
    d.rectangle([170,280,410,445],fill='#176b88',outline='#24485b',width=4)
    d.polygon([(170,280),(192,261),(432,261),(410,280)],fill='#278ca5')
    d.polygon([(410,280),(432,261),(432,426),(410,445)],fill='#114656')
    d.text((135,475),'Display item H-28',font=fonts[28],fill='#234857')
    d.text((135,525),'Blue storage box',font=fonts[22],fill='#536874')
    button(d,[690,290,1040,350],'Open item H-28');button(d,[690,390,1040,450],'Sort collection')
    finish('T01-object-catalog',image,{'box':[170,261,432,445],'open':[690,290,1040,350],'sort':[690,390,1040,450]})

    image,d=page('Collection records')
    d.text((65,195),'Records 41 - 50 of 95',font=fonts[28],fill='#234857')
    d.text((65,245),'10 records per page',font=fonts[22],fill='#536874')
    d.text((65,319),'Record H-41     Green desk organizer',font=fonts[22],fill='#176b88')
    d.text((65,385),'Record H-42     Copper desk lamp',font=fonts[22],fill='#176b88')
    boxes={}
    for i,label in enumerate(['<','3','4','5','6','7','>','>>']):
        box=[280+95*i,550,355+95*i,613];button(d,box,label);boxes[label]=box
        if label=='5':d.rectangle([box[0]+3,box[1]+3,box[2]-3,box[1]+7],fill='#176b88')
    finish('T02-paged-records',image,boxes)

    image,d=page('Filter current collection')
    d.text((75,220),'Item text',font=fonts[22],fill='#234857')
    d.rounded_rectangle([75,275,805,345],radius=4,fill='white',outline='#1e82ad',width=3)
    d.text((96,294),'copper',font=fonts[28],fill='#1a3848')
    button(d,[885,275,1155,345],'Apply filter')
    d.text((75,410),'Current filter: text contains copper',font=fonts[22],fill='#536874')
    finish('T03-filled-filter',image,{'input':[75,275,805,345],'apply':[885,275,1155,345]})

    image,d=page('Edit collection settings')
    d.text((65,220),'Display mode',font=fonts[22],fill='#234857')
    button(d,[65,275,465,340],'Compact view')
    d.rectangle([400,175,1100,625],fill='#fffdf4',outline='#897e65',width=3)
    d.text((440,220),'Unsaved view settings',font=fonts[28],fill='#394957')
    d.text((440,295),'Keep the current view settings?',font=fonts[22],fill='#536874')
    button(d,[445,490,690,550],'Keep editing');button(d,[750,490,1030,550],'Discard changes')
    finish('T04-settings-dialog',image,{'dialog':[400,175,1100,625],'keep':[445,490,690,550],'discard':[750,490,1030,550]})

    image,d=page('Project notes')
    d.rounded_rectangle([65,190,1200,650],radius=4,fill='white',outline='#c4cbd2',width=2)
    d.text((100,230),'项目档案',font=cjk,fill='#254e62')
    d.text((100,300),'当前记录：铜制台灯',font=cjk,fill='#334b59')
    d.text((100,370),'数量：12',font=cjk,fill='#334b59')
    d.text((100,460),'Status: draft / reference only',font=fonts[22],fill='#536874')
    button(d,[850,540,1120,600],'Close notes')
    finish('T05-CJK-notes',image,{'document':[65,190,1200,650],'close':[850,540,1120,600]})

    image,d=page('Import review')
    d.text((65,195),'3 files ready for review',font=fonts[28],fill='#234857')
    for i,(name,state)in enumerate([('desk-items.txt','Ready'),('room-layout.png','Ready'),('archive-notes.txt','Needs review')]):
        y=270+i*80;d.rectangle([65,y,1200,y+62],fill='white',outline='#cad4d8',width=2)
        d.text((90,y+17),name,font=fonts[22],fill='#234857');d.text((855,y+17),state,font=fonts[22],fill='#536874')
    button(d,[840,570,1170,632],'Review selected file')
    finish('T06-import-table',image,{'review':[840,570,1170,632]})

    previous=HERE.parent/'balanced-visual-evidence-20261109-16/sources/provenance.json'
    previous_hashes={row['sha256']for row in json.loads(previous.read_bytes())['complete_screenshots']}
    assert len({row['sha256']for row in rows})==6 and not previous_hashes&{row['sha256']for row in rows}
    save(out/'PRIVATE-renderer-geometry-NOT-MODEL-INPUT.json',geometry)
    save(out/'provenance.json',{'time':time.time(),'complete_screenshots':rows,
         'kind':'new_complete_offline_constructed_visual_controls','renderer':'Pillow',
         'not_native_benchmark_GUI_or_trajectory':True,'previous16_source_SHA_disjoint':True,
         'new_model_GUI_scorer_calls':0,'private_geometry_never_model_input':True,
         'font_sha256':{name:sha(Path('C:/Windows/Fonts')/name)for name in ['arial.ttf','msyh.ttc']}})
    save(out/'seal.json',{p.relative_to(out).as_posix():sha(p)for p in out.rglob('*')if p.is_file()})
    print(json.dumps({'new_complete_images':6,'provenance_sha256':sha(out/'provenance.json'),'new_model_calls':0}))


if __name__=='__main__':main()
