"""Create a four-panel figure from full-size, independently audited original captures."""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from live_common import load, sha


def render(audit, out):
    a = load(audit)
    root = Path(a['attempt'])
    assert sha(root / 'local-seal.json') == a['input_seal_sha256']
    ok = next(r for r in a['episodes'] if r['case']['arm'] == 'defense' and r.get('effective_recovery'))
    failure = next(r for r in a['episodes'] if r['case']['arm'] == 'fast' and r.get('first_ready_false_hold') and not r.get('main'))
    held = failure['first_post_capture']
    before = next(r for r in failure['truth_frames'] if r['truth'] == 'initial')
    yes = ok['delivered']
    first = ok['first_post_capture']
    n_false = len([h for h in failure['holds'] if h['truth'] == 'ready'])
    p_yes = next(p['p_yes'] for p in failure['flash'] if p['capture_id'] == held['capture_id'] and p['kind'] == 'temporal')

    face = Path('C:/Windows/Fonts/msyh.ttc')
    bold = face.with_name('msyhbd.ttc')
    regular = lambda n: ImageFont.truetype(face, n)
    strong = lambda n: ImageFont.truetype(bold, n)
    im = Image.new('RGB', (1610, 1220), '#f3f6f8')
    draw = ImageDraw.Draw(im)
    ink, muted, success, caution = '#102331', '#44606f', '#0b6352', '#904741'
    draw.text((39, 28), '双帧核验：一次闭环恢复，一次正常图误拦', font=strong(34), fill=ink)
    draw.text((40, 79), '3090 真实浏览器实验 · 由可信采集端直接取得的整图 · 按比例缩放', font=regular(21), fill=muted)

    def panel(x, y, title, subtitle, frame, color):
        w, h = 744, 418
        draw.rounded_rectangle((x-8, y-10, x+w+8, y+h+69), radius=12, fill='#ffffff', outline='#d5e0e7', width=2)
        path = Path(frame['acquisition_png'])
        assert sha(path) == frame['source_sha256']
        with Image.open(path) as p:
            assert p.size == (1280, 720)
            im.paste(p.convert('RGB').resize((w, h), Image.Resampling.LANCZOS), (x, y))
        draw.text((x+3, y+h+6), title, font=strong(25), fill=color)
        draw.text((x+3, y+h+39), subtitle, font=regular(18), fill=muted)

    panel(40, 134, 'A  真实早拍，Flash 拒绝', f"采集于动作后 {first['s_after_action']:.2f} 秒", first, success)
    panel(826, 134, 'B  同页复拍，正常图交付 27B', f"动作只执行一次；{ok['post_gate_seconds']:.2f} 秒时放行", yes, success)
    panel(40, 677, 'C  正常更新对照：操作前', '此图作为上一张已放行的截图', before, caution)
    panel(826, 677, 'D  页面已更新，Flash 仍拒绝', f"首次 P(YES) = {p_yes:.3f}；共拒绝 {n_false} 次，未交付 27B", held, caution)
    draw.text((40, 1176), f"A–B：{ok['id']}   ·   C–D：{failure['id']}", font=regular(18), fill=muted)
    with out.open('xb') as f:
        im.save(f, format='PNG')


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('audit', type=Path)
    cli.add_argument('--out', type=Path, required=True)
    args = cli.parse_args()
    render(args.audit, args.out)
