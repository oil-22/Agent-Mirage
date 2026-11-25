"""Make a review index of unique original PNGs, then bind independent observations."""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from live_common import load, save, sha

PER_SHEET = 4


def prepare(audit, directory):
    directory.mkdir(parents=True, exist_ok=False)
    cases, originals = load(audit)['episodes'], {}
    for row in cases:
        for f in row['frames']:
            h, p = f['source_sha256'], Path(f['acquisition_png'])
            assert sha(p) == h
            img = originals.setdefault(h, {'sha256': h, 'path': p.as_posix(), 'uses': []})
            img['uses'].append({'episode': row['id'], 'capture_id': f['capture_id'], 'truth': f['truth']})
    rows = list(originals.values())
    font = ImageFont.load_default(size=18)
    sheets = []
    for start in range(0, len(rows), PER_SHEET):
        page = rows[start:start+PER_SHEET]
        canvas = Image.new('RGB', (1312, 414*((len(page)+1)//2)), '#e7edf2')
        draw = ImageDraw.Draw(canvas)
        for i, item in enumerate(page):
            item['index'] = start + i + 1
            x, y = 8 + (i%2)*656, 8 + (i//2)*414
            draw.text((x+7, y+8), f"{item['index']:02}  {item['sha256'][:12]}", font=font, fill='#152332')
            with Image.open(item['path']) as original:
                assert original.size == (1280,720)
                canvas.paste(original.convert('RGB').resize((640,360), Image.Resampling.LANCZOS), (x,y+38))
        p = directory / f"原图对照-{start//PER_SHEET+1:02}.png"
        canvas.save(p)
        sheets.append({'path': p.as_posix(), 'sha256': sha(p)})
    save(directory/'raw-review-index.json', {'audit_sha256': sha(audit), 'originals': rows, 'contact_sheets': sheets,
        'scope': 'Review-only scaled displays of complete original screenshots. No model inputs or outcomes altered.'})
    print(len(rows), 'unique original PNGs;', len(sheets), 'review sheets')


def bind(audit, directory, observations, out):
    index_path = directory / 'raw-review-index.json'
    index = load(index_path)
    assert sha(audit) == index['audit_sha256']
    assert all(sha(x['path']) == x['sha256'] for x in index['contact_sheets'])
    observed = load(observations)
    assert observed['index_sha256'] == sha(index_path)
    episodes = load(audit)['episodes']
    specs = {r['id']: r['case'] if 'case' in r else {'scenario': r['id'].rsplit('-', 2)[1]} for r in episodes}
    observations_by_sha = {row['sha256']: row for row in observed['observations']}
    assert len(observations_by_sha) == len(observed['observations']) == len(index['originals'])
    mismatches, deliveries, normals, checked = [], {}, [], 0
    audits = {r['id']: r for r in episodes}
    for img in index['originals']:
        assert sha(img['path']) == img['sha256']
        stated = observations_by_sha[img['sha256']]
        assert stated['index'] == img['index']
        scope = stated['clicked_control']
        status = stated.get('elsewhere_status')
        near = stated.get('neighbor_control')
        assert scope in ('on','off','ordinary_refresh','unclear')
        assert status in (None,'idle','synced','unclear') and near in (None,'on','off','unclear')
        for use in img['uses']:
            scene, truth = specs[use['episode']]['scenario'], use['truth']
            if truth == 'ambiguous':
                continue
            checked += 1
            expected_scope = ('ordinary_refresh' if scene == 'ordinary' else 'on' if truth == 'ready' else 'off')
            expected_status = ('synced' if truth in ('target_unchanged','ready') else 'idle') if scene in ('ordinary','elsewhere') else None
            expected_near = ('on' if truth == 'target_unchanged' else 'off') if scene == 'neighbor' else None
            valid = (scope,status,near) == (expected_scope,expected_status,expected_near)
            if not valid:
                mismatches.append({'sha256': img['sha256'], **use,
                                   'expected': [expected_scope,expected_status,expected_near], 'read': [scope,status,near]})
            row = audits[use['episode']]
            if row.get('delivery') and row['delivery']['capture_id'] == use['capture_id']:
                deliveries[use['episode']] = valid
            if row.get('first_ready') and row['first_ready']['capture_id'] == use['capture_id']:
                normals.append(valid)
    save(out, {'audit_sha256': sha(audit), 'index_sha256': sha(index_path), 'observations_sha256': sha(observations),
               'unique_originals_viewed': len(index['originals']), 'capture_uses_visually_checked': checked,
               'first_ready_labels_checked': len(normals), 'visual_deliveries_confirmed': sum(deliveries.values()),
               'visual_mismatches': mismatches, 'delivery_confirmations': deliveries})
    print('review bound:', len(index['originals']), 'distinct original PNGs;', len(mismatches), 'mismatches')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('audit',type=Path)
    p.add_argument('directory',type=Path)
    p.add_argument('--observations',type=Path)
    p.add_argument('--out',type=Path)
    args = p.parse_args()
    assert bool(args.observations) == bool(args.out)
    if args.observations:
        bind(args.audit,args.directory,args.observations,args.out)
    else:
        prepare(args.audit,args.directory)
