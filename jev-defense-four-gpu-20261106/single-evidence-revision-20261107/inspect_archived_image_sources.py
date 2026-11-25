"""Read archive image sources for source-first selection; never read predictions."""
import base64
import hashlib
import io
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]
OUT = ROOT / 'source-discovery-01'
OUT.mkdir(exist_ok=False)
plans = [WORKSPACE / 'attention-audit-20261031/campaign/plan.json',
         WORKSPACE / 'attention-audit-20261031/source-campaign/plan.json']
records, seen = [], set()
for plan in plans:
    raw = plan.read_bytes()
    source = json.loads(raw)
    for case in source['cases']:
        if case['condition'] not in ('current_control', 'original') or case.get('history') != 'full':
            continue
        images = []
        for mi, message in enumerate(case['request']['messages']):
            content = message.get('content')
            if isinstance(content, list):
                for bi, block in enumerate(content):
                    if block.get('type') == 'image_url':
                        url = block['image_url']['url']
                        if url.startswith('data:image/') and ';base64,' in url:
                            image_raw = base64.b64decode(url.split(';base64,', 1)[1], validate=True)
                            images.append((mi, bi, image_raw))
        if not images:
            continue
        mi, bi, image_raw = images[-1]
        image_sha = hashlib.sha256(image_raw).hexdigest()
        if image_sha in seen:
            continue
        seen.add(image_sha)
        image = Image.open(io.BytesIO(image_raw)); image.load()
        image_id = f'S{len(records)+1:02d}'
        filename = image_id + '.png'
        # Original bytes retain the source encoding; extension follows archive use.
        (OUT / filename).write_bytes(image_raw)
        records.append({'id': image_id, 'image_path': filename, 'image_sha256': image_sha,
            'image_size': list(image.size), 'image_format': image.format,
            'source_plan': str(plan.relative_to(WORKSPACE)),
            'source_plan_sha256': hashlib.sha256(raw).hexdigest(),
            'source_case_id': case['id'], 'condition': case['condition'],
            'task': case['task'], 'app': case['app'], 'step': case['step'],
            'image_message_index': mi, 'image_content_block_index': bi,
            'original_source_artifact': case.get('source_archive_path', case.get('source_artifact')),
            'original_source_artifact_sha256': case.get('source_archived_json_sha256', case.get('source_artifact_sha256')),
            'history_or_prediction_used_as_visual_gold': False,
            'original_raw_artifact_locally_reverified': False})
(OUT / 'inventory.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
for start in range(0, len(records), 12):
    rows = records[start:start+12]
    sheet = Image.new('RGB', (1200, ((len(rows)+2)//3)*257), '#dddddd')
    draw = ImageDraw.Draw(sheet)
    for j, row in enumerate(rows):
        im = Image.open(OUT / row['image_path']).convert('RGB')
        im.thumbnail((396, 223))
        x, y = (j % 3)*400, (j // 3)*257
        sheet.paste(im, (x, y+30))
        draw.text((x+4, y+4), row['id'] + ' ' + row['app'] + ' ' + str(row['step']), fill='black')
    sheet.save(OUT / f'contact-{start//12+1:02d}.png')
print(json.dumps({'images':len(records), 'directory':str(OUT),
                  'original_raw_archive_verification_still_required': True}))
