"""Display copies of original evidence; never change model input images."""
import json
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from control import HERE, save, sha
from record_source_checkpoint import checked


def main():
    pointer = HERE/'frame-loop-visuals-current.json'
    assert not pointer.exists()
    evidence, root = checked(HERE/'frame-loop-source-evidence-current.json')
    cases = json.loads((root/'evidence.json').read_bytes())['cases']
    assert len(cases) == 4
    font_path = Path('C:/Windows/Fonts/msyh.ttc')
    font = ImageFont.truetype(str(font_path),25)
    small = ImageFont.truetype(str(font_path),19)
    width, row_h, top = 1380, 435, 100
    canvas = Image.new('RGB',(width,top+row_h*len(cases)+45),'#eef2f5')
    draw = ImageDraw.Draw(canvas)
    draw.text((25,18),'Flash 拦截 → 持续真实复拍 → 正常图入主模型',fill='#10253c',font=font)
    draw.text((25,58),'4 个实际闭环；每例连续 3 NO / 3 次复拍；图片仅在展示副本中缩放',fill='#394e62',font=small)
    original_bindings = []
    for index, case in enumerate(cases):
        y = top+index*row_h
        task = case['run_id'].split('-')[1]
        condition = '白屏' if case['condition'] == 'late_white3' else '模糊'
        bad = case['deliveries'][0]['delivered_sha256']
        good = case['deliveries'][-1]['delivered_sha256']
        draw.text((25,y),f'{task} / {condition} / 决策 {case["trigger_step"]}',fill='#10253c',font=small)
        for x, image_hash, caption, color in [
            (25,bad,'注入后：NO（连续 3 次）','#9e2525'),
            (715,good,'真实复拍恢复：YES → 原图入主','#126b40')]:
            original = root/'images'/(image_hash+'.png')
            assert sha(original) == image_hash
            image = Image.open(original).convert('RGB')
            assert image.size == (1280,720)
            canvas.paste(image.resize((640,360),Image.Resampling.LANCZOS),(x,y+64))
            draw.text((x,y+32),caption,fill=color,font=small)
            original_bindings.append({'run_id':case['run_id'],'original':str(original),
                'original_sha256':image_hash,'display_resize_only':True})
    draw.text((25,top+len(cases)*row_h+7),'原图与请求/首次 forward/回复/真实动作及 SHA 链已核验；正常图文字误读不计本轮失败。',fill='#394e62',font=small)
    out = HERE/('frame-loop-visuals-'+str(time.time_ns()))
    out.mkdir()
    (out/'source.py').write_bytes(Path(__file__).read_bytes())
    image_file = out/'Flash拦截与复拍闭环实例.png'
    canvas.save(image_file)
    save(out/'bindings.json',{'source_evidence':evidence,'originals':original_bindings,
        'display_does_not_change_any_model_input':True,'new_model_GUI_calls':0})
    save(out/'seal.json',{q.name:sha(q) for q in out.iterdir() if q.is_file()})
    save(pointer,{'root':str(out),'seal_sha256':sha(out/'seal.json')})
    print(json.dumps({'visual':str(image_file),'cases':4,'new_model_GUI_calls':0}))


if __name__ == '__main__':
    main()
