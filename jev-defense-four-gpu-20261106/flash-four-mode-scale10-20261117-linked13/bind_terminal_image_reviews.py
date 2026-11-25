"""Bind existing actual-image labels to byte-identical terminal export PNGs.

No image is assigned a new visual label by this script. Unseen, uncertain, or
conflicting labels stop the binding. Live-prefix exports cannot prove a terminal.
"""
import json
import sys
import time
from pathlib import Path

from control import HERE, save, sha
from join_reviewed_results import verify


def load_terminal_export(path):
    root = Path(path).resolve()
    assert root.parent == HERE and root.name.startswith('normal-frame-export-')
    verify(root)
    value = json.loads((root / 'sources.json').read_bytes())
    assert value['rows']
    assert all(row.get('terminal_sha256') and row.get('trajectory_seal_sha256')
               and row.get('controller_chain') for row in value['rows']), 'A live prefix is not a terminal export'
    return root, value


def main():
    export, sources = load_terminal_export(sys.argv[1])
    labels, proofs = {}, {}
    for root in sorted(HERE.glob('independent-image-notes-*')):
        verify(root)
        notes = json.loads((root / 'notes.json').read_bytes())
        for binding in notes['source_exports']:
            verify(binding['root'], binding['seal_sha256'])
        for image in notes['images']:
            digest = image['sha256']
            assert sha(image['original_path']) == digest
            assert image['normal_usable'] in [True, False, None]
            if digest in labels:
                assert labels[digest]['normal_usable'] == image['normal_usable'], 'Conflicting image labels'
            labels[digest] = image
            proofs[digest] = {'root': str(root), 'seal_sha256': sha(root / 'seal.json')}
    images = []
    for original in sorted((export / 'images').glob('*.png')):
        digest = sha(original)
        assert digest == original.stem and digest in labels, 'An unseen PNG requires actual visual review'
        label = labels[digest]
        assert label['normal_usable'] is not None, 'An uncertain label cannot be treated as reviewed normality'
        images.append({'sha256': digest, 'terminal_export_original_path': str(original),
                       'original_reviewed_path': label['original_path'],
                       'review_label': label['normal_usable'], 'review_binding': proofs[digest],
                       'same_complete_PNG_bytes': True, 'new_visual_label': False})
    assert images
    image_ids = {row['sha256'] for row in images}
    frames = [frame for row in sources['rows'] for frame in row['frames']]
    assert {frame['sha256'] for frame in frames} == image_ids
    normal_path = [frame for frame in frames if not frame['injected']]
    root = HERE / ('terminal-image-review-binding-' + str(time.time_ns()))
    root.mkdir()
    save(root / 'result.json', {
        'run_ids': [row['run_id'] for row in sources['rows']],
        'terminal_export': {'root': str(export), 'seal_sha256': sha(export / 'seal.json')},
        'same_SHA_review_bindings': images, 'all_unique_original_PNGs_reviewed': True,
        'normal_path_capture_exposures': len(normal_path),
        'normal_path_reviewed_usable_exposures': sum(labels[f['sha256']]['normal_usable'] is True for f in normal_path),
        'normal_path_reviewed_unusable_exposures': sum(labels[f['sha256']]['normal_usable'] is False for f in normal_path),
        'normal_path_unknown_quality_exposures': 0,
        'full_wire_audit_still_required': True,
        'PNG_reuse_adds_no_visual_diversity': True, 'new_model_GUI_calls': 0,
    })
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    verify(root)
    print(json.dumps({'root': str(root), 'seal_sha256': sha(root / 'seal.json'),
                      'terminal_unique_PNGs_bound': len(images), 'new_visual_labels': 0,
                      'normal_path_capture_exposures': len(normal_path), 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
