"""Create new complete, offline source fixtures; no model or benchmark session.

The portrait is Matplotlib's bundled public-domain photograph.  Rendering it
inside a constructed page is not an original benchmark screenshot or a task.
Private drawing geometry is evaluation provenance and is never model input.
"""
from pathlib import Path
import hashlib
import json
import shutil
import time

from PIL import Image, ImageDraw, ImageFont
import matplotlib

HERE = Path(__file__).resolve().parent
OUT = HERE / 'sources'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, value):
    with p.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    assert not OUT.exists()
    OUT.mkdir()
    public = OUT / 'public'
    public.mkdir()
    assets = OUT / 'source-assets'
    assets.mkdir()
    photo = Path(matplotlib.get_data_path()) / 'sample_data/grace_hopper.jpg'
    shutil.copyfile(photo, assets / photo.name)
    font_path = Path('C:/Windows/Fonts/arial.ttf')
    bold_path = Path('C:/Windows/Fonts/arialbd.ttf')
    assert font_path.is_file() and bold_path.is_file()
    fonts = {size: ImageFont.truetype(str(font_path), size) for size in [17, 20, 23, 28, 34]}
    bold = ImageFont.truetype(str(bold_path), 28)
    rows = []
    geometry = {}

    def page():
        image = Image.new('RGB', (1280, 720), 'white')
        draw = ImageDraw.Draw(image)
        draw.rectangle([0, 0, 1279, 85], fill='#edf3f4')
        draw.text((38, 23), 'Beacon Archive', font=bold, fill='#184e61')
        draw.text((865, 32), 'Offline visual source fixture', font=fonts[17], fill='#536975')
        return image, draw

    def button(draw, box, label, selected=False):
        draw.rounded_rectangle(box, radius=5, fill='#1c6175' if selected else '#f6fafb',
                               outline='#49889b', width=2)
        bb = draw.textbbox((0, 0), label, font=fonts[20])
        x = (box[0] + box[2] - bb[2]) / 2
        y = (box[1] + box[3] - bb[3]) / 2 - 1
        draw.text((x, y), label, font=fonts[20], fill='white' if selected else '#184e61')

    def finish(name, image, boxes):
        path = public / (name + '.png')
        image.save(path)
        rows.append({'id': name, 'file': path.name, 'sha256': sha(path), 'size': [1280, 720]})
        geometry[name] = boxes

    image, draw = page()
    draw.text((42, 113), 'Archive records', font=fonts[34], fill='#173c4d')
    draw.text((42, 171), 'Browse the current collection', font=fonts[20], fill='#536975')
    sort = [900, 111, 1230, 167]
    button(draw, sort, 'Sort: newest first')
    # Preserve the entire photograph; resize proportionally, never crop.
    portrait = Image.open(assets / photo.name).convert('RGB')
    portrait.thumbnail((360, 430), Image.Resampling.LANCZOS)
    draw.rectangle([55, 226, 424, 669], fill='#e8edf0')
    origin = (int(240 - portrait.width / 2), int(447 - portrait.height / 2))
    image.paste(portrait, origin)
    draw.text((476, 257), 'Archive record A-17', font=fonts[28], fill='#0879a3')
    draw.text((476, 315), '$24.00', font=fonts[28], fill='#172b37')
    draw.text((476, 368), 'Portrait photograph', font=fonts[23], fill='#536975')
    draw.text((476, 414), 'Record details are available below.', font=fonts[20], fill='#536975')
    open_record = [476, 487, 724, 547]
    button(draw, open_record, 'Open record')
    finish('S01-portrait', image, {'sort': sort, 'open_record': open_record,
           'entire_photo': [origin[0], origin[1], origin[0]+portrait.width, origin[1]+portrait.height]})
    portrait.close()

    image, draw = page()
    draw.text((65, 119), 'Records 25 - 36 of 72', font=fonts[28], fill='#173c4d')
    draw.text((65, 166), '12 records per page', font=fonts[20], fill='#536975')
    draw.text((65, 222), 'Record A-25     Blue document case     $18.00', font=fonts[23], fill='#0879a3')
    draw.text((65, 295), 'Record A-26     Brass desk lamp          $32.00', font=fonts[23], fill='#0879a3')
    draw.line([60, 273, 1205, 273], fill='#c5d5db', width=2)
    draw.line([60, 346, 1205, 346], fill='#c5d5db', width=2)
    page_boxes = {}
    for i, label in enumerate(['1', '2', '3', '4', '>', '>>']):
        box = [486 + 80*i, 528, 550 + 80*i, 588]
        button(draw, box, label, selected=label == '3')
        page_boxes[label] = box
    finish('S02-pagination', image, page_boxes)

    image, draw = page()
    draw.text((110, 171), 'Search the archive', font=fonts[34], fill='#173c4d')
    draw.text((110, 248), 'Keyword', font=fonts[23], fill='#173c4d')
    keyword = [110, 294, 826, 364]
    draw.rounded_rectangle(keyword, radius=4, outline='#1688ce', width=4, fill='white')
    draw.text((132, 314), 'Enter a keyword', font=fonts[23], fill='#88939b')
    search = [882, 294, 1140, 364]
    button(draw, search, 'Search')
    draw.text((110, 411), 'Search by record name or number.', font=fonts[20], fill='#536975')
    finish('S03-form', image, {'keyword': keyword, 'search': search})

    image, draw = page()
    draw.text((60, 126), 'Archive information', font=fonts[28], fill='#173c4d')
    draw.text((60, 186), 'Browse more records using the navigation above.', font=fonts[20], fill='#536975')
    draw.rectangle([0, 352, 1279, 719], fill='#e0edf0')
    draw.text((62, 398), 'Contact       Accessibility       Terms', font=fonts[23], fill='#184e61')
    draw.text((62, 460), 'Beacon Archive - collection information', font=fonts[20], fill='#536975')
    top = [910, 571, 1210, 636]
    button(draw, top, 'Back to top')
    finish('S04-footer', image, {'back_to_top': top})

    image, draw = page()
    draw.arc([593, 265, 659, 331], 20, 300, fill='#1688ce', width=7)
    draw.text((442, 366), 'Loading archive records...', font=fonts[28], fill='#173c4d')
    draw.text((558, 421), 'Please wait', font=fonts[20], fill='#536975')
    finish('S05-loading', image, {'loading_cue': [432, 255, 860, 455]})

    finish('S06-blank', Image.new('RGB', (1280, 720), 'white'), {})
    image, draw = page()
    draw.text((83, 194), '0 results', font=fonts[34], fill='#173c4d')
    draw.text((83, 267), 'No archive records match this search.', font=fonts[23], fill='#536975')
    clear = [83, 351, 355, 415]
    button(draw, clear, 'Clear search')
    finish('S07-no-results', image, {'clear_search': clear})

    save(OUT / 'PRIVATE-drawing-geometry-NOT-MODEL-INPUT.json', geometry)
    save(OUT / 'provenance.json', {'time': time.time(), 'kind': 'new_offline_constructed_full_page_controls',
         'renderer': 'Pillow', 'renderer_version': __import__('PIL').__version__,
         'portrait_origin': str(photo), 'portrait_sha256': sha(assets/photo.name),
         'portrait_provenance': 'Matplotlib bundled grace_hopper.jpg; public-domain US Navy photograph',
         'portrait_rendering': 'whole photograph proportionally resized inside a new constructed page, not a benchmark image edit',
         'font_sha256': {str(p): sha(p) for p in [font_path, bold_path]},
         'complete_screenshots': rows, 'native_GUI_task_or_scorer_actions': 0, 'model_calls': 0,
         'private_geometry_is_not_a_checker_input': True, 'heldout_evaluation_tasks_untouched': True,
         'not_a_natural_benchmark_trajectory_or_efficacy_result': True})
    save(OUT / 'seal.json', {p.relative_to(OUT).as_posix(): sha(p) for p in sorted(OUT.rglob('*')) if p.is_file()})
    print(json.dumps({'source_root': str(OUT), 'complete_new_images': len(rows), 'provenance_sha256': sha(OUT/'provenance.json'),
                      'model_GUI_calls': 0}, ensure_ascii=False))


if __name__ == '__main__':
    main()
