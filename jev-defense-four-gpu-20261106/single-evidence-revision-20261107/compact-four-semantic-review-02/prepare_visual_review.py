"""Derived visual review artifacts only; no original bytes modified."""
import hashlib
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
INPUT = ROOT / 'compact-semantic-review-source-02'
EXPECTED_SEAL = '26b2e61134bf34754e1412b22a4d0b4202e5372a73fdf3ed0ae52caa9c45760d'
ART = OUT / 'visual-artifacts'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    assert sha((INPUT / 'seal.json').read_bytes()) == EXPECTED_SEAL
    seal = json.loads((INPUT / 'seal.json').read_text(encoding='utf-8'))
    for path, expected in seal.items():
        assert sha((INPUT / path).read_bytes()) == expected
    notes = json.loads((ROOT / 'source-first-compact-four-peer-notes-02' / 'source-first-notes.json').read_text(encoding='utf-8'))
    sources = {row['source_id']: row for row in notes['source_images']}
    ART.mkdir(exist_ok=False)
    bindings = []
    for index, sid in enumerate(('S04', 'S10', 'S16', 'S19')):
        rd = INPUT / 'worker' / ('r%03d' % index)
        raw_bytes = (rd / 'raw-output.txt').read_bytes()
        raw = raw_bytes.decode('utf-8')
        packet_bytes = (rd / 'evidence-packet.json').read_bytes()
        packet = json.loads(packet_bytes)
        tr = packet['native_transport']
        assert sha(raw_bytes) == packet['raw_output_sha256'] == tr['raw_output_sha256']
        start, end = tr['body_codepoint_range']
        a, b = tr['body_utf8_byte_range']
        body = raw[start:end]
        assert body.encode('utf-8') == raw_bytes[a:b]
        assert sha(body.encode('utf-8')) == tr['body_utf8_sha256']
        assert json.loads(body) == packet['reading']
        path = ROOT / 'source-discovery-linked03' / (sid + '.png')
        image_bytes = path.read_bytes()
        assert sha(image_bytes) == packet['image_sha256'] == sources[sid]['sha256']
        image = Image.open(path).convert('RGB')
        width, height = image.size
        row = {'source_id': sid, 'source_image_sha256': sha(image_bytes), 'raw_output_sha256': sha(raw_bytes), 'packet_sha256': sha(packet_bytes), 'dimensions': [width, height], 'boxes': []}
        for group, color in [('text_spans', '#d10000'), ('elements', '#0059d1')]:
            overlay = image.copy()
            draw = ImageDraw.Draw(overlay)
            for item in packet['reading'][group]:
                box = item['box_xyxy']
                px = [box[0]*width/1000, box[1]*height/1000, box[2]*width/1000, box[3]*height/1000]
                draw.rectangle(px, outline=color, width=2)
                draw.text((px[0]+2, max(0, px[1]-12)), item['id'], fill=color, stroke_width=1, stroke_fill='white')
                row['boxes'].append({'group': group, 'id': item['id'], 'normalized_1000': box, 'pixel_float_xyxy': px})
            overlay.save(ART / (sid + '-' + group + '-overlay.png'))
        # Source crops include context, and retain the predicted box as a review overlay.
        crops = {'S04': [('headings', (490, 820, 1430, 880)), ('notification', (740, 20, 1255, 112))],
                 'S10': [('zoom', (1810, 1040, 1920, 1080)), ('cryptography', (800, 645, 1485, 780))],
                 'S16': [('namebox', (70, 165, 255, 250)), ('donate', (1695, 240, 1860, 286))],
                 'S19': [('occluded-title', (430, 325, 1140, 455)), ('tools-menu', (445, 60, 775, 530))]}
        for name, crop in crops[sid]:
            image.crop(crop).resize(((crop[2]-crop[0])*2, (crop[3]-crop[1])*2), Image.Resampling.NEAREST).save(ART/(sid+'-'+name+'-original-crop-2x.png'))
        bindings.append(row)
    with (OUT/'semantic-input-bindings.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump({'semantic_source_seal_sha256': EXPECTED_SEAL, 'source_first_notes_sha256': sha((ROOT/'source-first-compact-four-peer-notes-02/source-first-notes.json').read_bytes()), 'raw_and_packet_reading_match_exactly': True, 'original_images_unchanged': True, 'prediction_analysis_started_after_source_first_seal': True, 'items': bindings}, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'inputs_verified': 4, 'output_artifacts': len(list(ART.iterdir())), 'prediction_metrics_or_other_reviewer_labels_joined': False}))


if __name__ == '__main__':
    main()
