"""Build a local review-only contact sheet; never used as model input."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw

parser = argparse.ArgumentParser()
parser.add_argument('directory', type=Path)
parser.add_argument('--first', type=int, default=1)
parser.add_argument('--last', type=int, required=True)
args = parser.parse_args()
files = [p for p in sorted(args.directory.glob('*-delivered.png'))
         if args.first <= int(p.name[:3]) <= args.last]
if not files:
    raise ValueError('No original delivered frames selected')
width, height, columns = 640, 385, 3
canvas = Image.new('RGB', (width * columns, height * ((len(files) + columns - 1) // columns)), 'white')
draw = ImageDraw.Draw(canvas)
for index, path in enumerate(files):
    x, y = index % columns * width, index // columns * height
    with Image.open(path) as original:
        thumb = original.convert('RGB')
        thumb.thumbnail((640, 360))
        canvas.paste(thumb, (x, y + 25))
    draw.text((x + 8, y + 7), path.name, fill='black')
output = args.directory / f'offline-contact-{args.first:03}-{args.last:03}.jpg'
canvas.save(output, quality=95)
manifest = {'purpose': 'local nonblind review only; never model input',
            'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
output.with_suffix('.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(json.dumps({'output': str(output.resolve()), 'frames': len(files)}))
