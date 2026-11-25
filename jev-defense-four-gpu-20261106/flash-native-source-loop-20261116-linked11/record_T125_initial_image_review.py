"""Seal the three T125 originals actually viewed in this review turn."""
import json
import time
from pathlib import Path
from control import HERE, save, sha
from join_reviewed_results import verify


def main():
    export = HERE / 'normal-frame-export-1794826218735168600'
    sheets = HERE / 'image-review-sheets-1794826225934531400'
    verify(export, 'ff736e26fa4c119cb671afe36e989323ac46c8cb70825bd0435be7f83bba7970')
    verify(sheets)
    index = json.loads((sheets / 'index.json').read_bytes())
    judgments = {
        '68e5a341912ccf0f40b00f12df577d1c2beb35929ea698e30df64025afec5191':
            ('normal product detail', 'Readable Queen Ikea Mattress title, 100 dollar price, location, contact panel and product image. The embedded photograph contains a screenshot of another website; that is product content. Full original also viewed.'),
        '74e2cff8100fde92166e9f6682d42f400de194304f10bade036b2e68646b74fe':
            ('normal furniture grid', 'Coherent Furniture heading, search filters, grid controls and product cards with photographs and prices.'),
        'f5cb3b56617400bc55b6e8e3b22f58ce4f51590be1455a152ab97ca175beee6d':
            ('normal scrolled furniture grid', 'Readable product grid with rug, mattress, lamp and other cards. Missing header at this scroll position and side whitespace do not make the visible image unusable.')}
    assert set(judgments) == {v['sha256'] for v in index['new_originals']}
    images = []
    for row in index['new_originals']:
        assert sha(row['original_path']) == row['sha256']
        kind, reason = judgments[row['sha256']]
        images.append({**row, 'normal_usable': True, 'type': kind, 'reason': reason})
    root = HERE / ('independent-image-notes-' + str(time.time_ns()))
    root.mkdir()
    save(root / 'notes.json', {'time': time.time(), 'reviewer': 'Codex image review',
        'blind': False, 'review_method': 'All three exact original PNGs viewed on the SHA-mapped sheet; product-detail recovery also viewed as the full original. No semantic Mirage or task-answer label inferred.',
        'source_exports': [{'root': str(export), 'seal_sha256': sha(export / 'seal.json')}],
        'review_rendering': {'root': str(sheets), 'seal_sha256': sha(sheets / 'seal.json')},
        'images': images, 'new_model_GUI_calls': 0})
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    print(json.dumps({'root': str(root), 'seal_sha256': sha(root / 'seal.json'),
        'new_exact_original_PNGs_reviewed': len(images), 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
