"""Export only frozen public controls; no expected answers or outcomes."""
import base64
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
source = HERE / 'runtime-package/control-inputs'
out = HERE / ('source-image-review-' + str(time.time_ns())); out.mkdir()
rows = []
for p in sorted(source.glob('E*.json')):
    v = json.loads(p.read_bytes()); images = []
    for i, image in enumerate(v['view']['images']):
        raw = base64.b64decode(image['raw_base64'])
        target = out / (p.stem + '-' + str(i) + '.png'); target.write_bytes(raw)
        images.append({'path': str(target), 'sha256': hashlib.sha256(raw).hexdigest()})
    text_messages = []
    for m in v['view']['messages']:
        content = m['content']
        text_messages.append({'role': m['role'], 'text': content if isinstance(content, str)
                              else '\n'.join(b['text'] for b in content if b.get('type') == 'text')})
    rows.append({'id': p.stem, 'source_path': str(p),
                 'source_sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                 'candidate': v['candidate'], 'images': images, 'text_messages': text_messages,
                 'recent_action': v['view']['recent_action'],
                 'execution_feedback': v['view']['execution_feedback']})
with (out / 'sources.json').open('x', encoding='utf8') as f:
    json.dump({'new_calls': 0, 'public_sources_only': True, 'rows': rows}, f, ensure_ascii=False, indent=2)
print(json.dumps({'path': str(out), 'sources': len(rows)}, ensure_ascii=False))
