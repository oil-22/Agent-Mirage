"""Fetch public model catalog/cards only; never download weights or execute model code."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import urllib.error
import urllib.request

BASE = Path(__file__).resolve().parent


def get(url):
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Mirage-Jev-public-model-review/1.0'})
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read(5_000_001)
            assert len(raw) <= 5_000_000, 'Public metadata response exceeds this audit limit'
            return {'url': url, 'http_status': response.status, 'data': raw,
                    'sha256': hashlib.sha256(raw).hexdigest()}
    except Exception as error:
        return {'url': url, 'error': type(error).__name__ + ': ' + str(error)}


def main():
    root = BASE / 'model-research' / str(time.time_ns())
    root.mkdir(parents=True, exist_ok=False)
    urls = [
        'https://huggingface.co/api/models?search=jev&limit=100&full=true&sort=downloads&direction=-1',
        'https://huggingface.co/api/models?search=jev&limit=100&full=true&sort=lastModified&direction=-1',
        'https://huggingface.co/api/models?author=TokenRhythm&search=decision&limit=100&full=true',
    ]
    catalog = []
    receipts = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for i, row in enumerate(pool.map(get, urls)):
            raw = row.pop('data', None)
            if raw is not None:
                name = 'catalog-' + str(i) + '.json'
                (root / name).write_bytes(raw)
                row['file'] = name
                try:
                    items = json.loads(raw)
                    if isinstance(items, list):catalog.extend(items)
                except ValueError:
                    row['parse_error'] = True
            receipts.append(row)
    selected = {}
    for item in catalog:
        model_id = item.get('id', item.get('modelId', ''))
        tags = item.get('tags', [])
        if 'jev' in model_id.lower() and any(t in tags for t in
            ['decision-model', 'decision-making', 'typed-decisions', 'multimodal', 'vision']):
            selected[model_id] = item
    # Review pinned known sources even if catalog access fails.
    selected.setdefault('TokenRhythm/NeoHorse-Jev-4B', {'id': 'TokenRhythm/NeoHorse-Jev-4B', 'sha': '434cb21d3a994a953d3ae5788405fcb2c4970554'})
    selected.setdefault('chaoliangUNSW/Jev-Style-2B-Decision-v4', {'id': 'chaoliangUNSW/Jev-Style-2B-Decision-v4', 'sha': '9d3147c2ba1d793958e447b0e7e20c7436ec34b5'})
    cards = []
    # A finite metadata-only survey. Counts/popularity are discovery signals, not quality evidence.
    for model_id, item in list(selected.items())[:16]:
        revision = item.get('sha') or 'main'
        cards.append((model_id, revision, 'https://huggingface.co/' + model_id + '/raw/' + revision + '/README.md'))
    summaries = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(get, [x[2] for x in cards]))
    for (model_id, revision, url), row in zip(cards, results):
        raw = row.pop('data', None)
        if raw is not None:
            name = model_id.replace('/', '--') + '--README.md'
            (root / name).write_bytes(raw)
            row['file'] = name
        row.update(model_id=model_id, revision=revision)
        receipts.append(row)
        item = selected[model_id]
        summaries.append({k: item.get(k) for k in ['id', 'sha', 'lastModified', 'downloads', 'likes', 'tags', 'cardData']})
    (root / 'candidate-summary.json').write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding='utf-8')
    (root / 'receipt.json').write_text(json.dumps({'checked_at_UTC': datetime.now(timezone.utc).isoformat(),
        'model_calls': 0, 'weight_downloads': 0, 'remote_code_executed': False,
        'catalog_is_not_a_quality_ranking': True, 'requests': receipts}, indent=2), encoding='utf-8')
    (root / 'seal.json').write_text(json.dumps({p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.iterdir() if p.is_file()}, indent=2), encoding='utf-8')
    print(json.dumps({'root': str(root), 'models': list(selected), 'reviewed_cards': len(cards),
        'fetch_failures': [{'url': r['url'], 'error': r['error']} for r in receipts if 'error' in r]}, ensure_ascii=True))


if __name__ == '__main__':
    main()
