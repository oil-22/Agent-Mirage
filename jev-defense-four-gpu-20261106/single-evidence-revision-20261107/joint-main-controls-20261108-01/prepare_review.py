"""Export unchanged frozen legal source frames and indexed text, with hashes."""
from pathlib import Path
import base64
import hashlib
import json

HERE = Path(__file__).resolve().parent
target = HERE / 'source-review-01'
target.mkdir(exist_ok=False)
(target / 'images').mkdir()
mapping = {}
for path in sorted((HERE / 'payload/inputs').glob('C*.json')):
    d = json.loads(path.read_bytes())
    item = {'candidate': d['candidate'], 'images': [], 'source_input_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    for index, im in enumerate(d['view']['images']):
        raw = base64.b64decode(im['raw_base64'])
        h = hashlib.sha256(raw).hexdigest()
        image_path = target / 'images' / (h + '.png')
        if not image_path.exists():
            image_path.write_bytes(raw)
        else:
            assert image_path.read_bytes() == raw
        item['images'].append({'index': index, 'role': im['role'], 'sha256': h, 'path': str(image_path)})
    messages = d['view']['messages']
    (target / (d['id'] + '-messages.json')).write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding='utf8')
    mapping[d['id']] = item
(target / 'index.json').write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding='utf8')
(target / 'seal.json').write_text(json.dumps({str(p.relative_to(target)): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in sorted(target.rglob('*')) if p.is_file()}, indent=2), encoding='utf8')
print(json.dumps({cid: {'images': v['images'], 'candidate': v['candidate']} for cid, v in mapping.items()}, ensure_ascii=False))
