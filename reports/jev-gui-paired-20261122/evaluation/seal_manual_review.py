"""Seal notes against the public legal packet before joining native outcomes."""

import argparse
import time
from pathlib import Path

from collect import HERE, read, save, sha
from exact_review_reuse import load_packet, signature
from link import verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packet', type=Path)
    parser.add_argument('notes', type=Path)
    parser.add_argument('--exact-labels', type=Path)
    args = parser.parse_args()
    packet, notes = args.packet, read(args.notes)
    public, seal = load_packet(packet)
    digest = sha(packet / 'seal.json')
    assert notes['packet_key'] == packet.name
    ledger = {(alias, t['decision']): t for alias, turns in public['packets'].items() for t in turns}
    qualities = set(read(packet / 'image-quality-input.json')['images'])
    exact_source = None
    manual = set(ledger)
    if args.exact_labels:
        verify(args.exact_labels)
        exact = read(args.exact_labels / 'review.json')
        assert exact['packet_seal_sha256'] == digest and exact['joined_private_execution_labels'] is False
        for alias, labels in exact['candidate_labels'].items():
            for item in labels:
                key = alias, item['decision']
                assert 'exact_review_reuse_from' in item and key in manual
                manual.remove(key)
        assert manual == {tuple(v) for v in exact['still_requires_manual_candidate_review']}
        qualities -= exact['quality_labels'].keys()
        exact_source = sha(args.exact_labels / 'seal.json')
    assert set(notes['quality_labels']) == qualities
    assert all(sha(packet / rel) == d for d, rel in seal['original_images'].items())
    for item in notes['quality_labels'].values():
        assert item['label'] in ('coherent_usable', 'visually_incomplete', 'unresolved') and item['note'].strip()
    for alias, labels in notes['candidate_labels'].items():
        for item in labels:
            key = alias, item['decision']
            assert key in manual, key
            t = ledger[key]
            signature(t)
            assert all(t[k] == item[k] for k in ('raw_reply_sha256', 'current_image_sha256'))
            assert item['semantic_label'] in ('definite', 'no_definite_positive', 'unresolved', 'pure_native_WAIT_excluded')
            assert item['note'].strip()
            manual.remove(key)
    assert not manual, manual
    assert notes['scope_and_blinding'].strip()
    out = HERE / 'labels' / str(time.time_ns())
    out.mkdir(exist_ok=False)
    save(out / 'review.json', {**notes, 'packet_seal_sha256': digest, 'joined_private_execution_labels': False,
         'notes_sha256': sha(args.notes), 'exact_partition_seal_sha256': exact_source})
    save(out / 'seal.json', {'review.json': sha(out / 'review.json')})
    print(out)


if __name__ == '__main__':
    main()
