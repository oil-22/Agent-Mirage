"""Evaluation-only exact-SHA reuse of previously viewed original PNG labels."""
import json
import time
from remote_util import HERE, save, sha


def main():
    exports = sorted(HERE.glob('image-source-review-*'))
    old = HERE.parent / 'flash-four-injection-defense-20261115-04'
    known = {}
    for root in sorted(old.glob('independent-image-notes-*')):
        for name, expected in json.loads((root / 'seal.json').read_bytes()).items():
            assert sha(root / name) == expected
        for row in json.loads((root / 'notes.json').read_bytes())['images']:
            known[row['sha256']] = (root, row)
    already = set()
    for root in HERE.glob('independent-image-notes-*'):
        already.update(v['sha256'] for v in json.loads((root / 'notes.json').read_bytes())['images'])
    labels = {}
    for export in exports:
        for name, expected in json.loads((export / 'seal.json').read_bytes()).items():
            assert sha(export / name) == expected
        for image in (export / 'images').glob('*.png'):
            expected = image.stem
            assert sha(image) == expected
            if expected not in already and expected in known:
                source, row = known[expected]
                labels[expected] = {**row, 'source_export': str(export), 'source_export_seal_sha256': sha(export / 'seal.json'),
                                    'prior_review_root': str(source), 'prior_review_seal_sha256': sha(source / 'seal.json'),
                                    'exact_image_SHA_label_reuse': True, 'new_independent_visual_pattern': False,
                                    'normality_is_not_currentness': True}
    if not labels:
        print(json.dumps({'new_exact_SHA_labels': 0}))
        return
    root = HERE / ('independent-image-notes-' + str(time.time_ns()))
    root.mkdir()
    save(root / 'notes.json', {'images': list(labels.values()), 'reviewer_saw_gate_outcomes': True,
                              'not_blind': True, 'evaluation_only_not_verifier_input': True,
                              'not_semantic_Mirage_or_task_success_labels': True})
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    print(json.dumps({'root': str(root), 'new_exact_SHA_labels': len(labels), 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
