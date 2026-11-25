"""Local review rendering only; original exported PNGs remain unchanged."""
import json
import sys
import time
from pathlib import Path
from PIL import Image, ImageDraw
from remote_util import HERE, save, sha


def main():
    export = Path(sys.argv[1]).resolve()
    assert export.parent == HERE and export.name.startswith('normal-frame-export-')
    seal = json.loads((export / 'seal.json').read_bytes())
    for name, expected in seal.items():
        assert sha(export / name) == expected
    reviewed = set()
    for notes in HERE.glob('independent-image-notes-*/notes.json'):
        reviewed.update(v['sha256'] for v in json.loads(notes.read_bytes())['images'])
    originals = [p for p in sorted((export / 'images').glob('*.png')) if p.stem not in reviewed]
    root = HERE / ('image-review-sheets-' + str(time.time_ns()))
    root.mkdir()
    rows = []
    for start in range(0, len(originals), 6):
        page = Image.new('RGB', (1280, 1164), 'white')
        draw = ImageDraw.Draw(page)
        for i, path in enumerate(originals[start:start + 6]):
            digest = sha(path)
            assert digest == path.stem
            image = Image.open(path)
            assert image.size == (1280, 720)
            x, y = (i % 2) * 640, (i // 2) * 388
            page.paste(image.resize((640, 360), Image.Resampling.LANCZOS), (x, y + 24))
            draw.text((x + 6, y + 5), '%03d %s' % (start + i + 1, digest[:20]), fill='black')
            rows.append({'index': start + i + 1, 'sha256': digest, 'original_path': str(path),
                         'sheet': 'sheet-%03d.png' % (start // 6 + 1), 'position': i + 1})
        page.save(root / ('sheet-%03d.png' % (start // 6 + 1)))
    save(root / 'index.json', {'export': str(export), 'export_seal_sha256': sha(export / 'seal.json'),
          'previously_reviewed_exact_SHA_count': len(reviewed), 'new_originals': rows,
          'rendered_review_only_not_experimental_inputs': True, 'new_model_GUI_calls': 0})
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    print(json.dumps({'root': str(root), 'new_originals': len(rows),
                      'sheets': [str(p) for p in sorted(root.glob('sheet-*.png'))]}))


if __name__ == '__main__':
    main()
