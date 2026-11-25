"""Fill mechanical packet identifiers for independently written review notes."""

import argparse
import json
from pathlib import Path
import sys

from collect import HERE, read, save
from exact_review_reuse import load_packet, signature


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packet', type=Path)
    parser.add_argument('notes', help='JSON file with review judgments, or - for stdin.')
    args = parser.parse_args()
    notes = json.load(sys.stdin) if args.notes == '-' else read(Path(args.notes))
    assert set(notes) == {'scope_and_blinding', 'quality_labels', 'candidate_labels'}
    packet, _ = load_packet(args.packet)
    images = read(args.packet / 'image-quality-input.json')['images']
    quality = {}
    for prefix, label in notes['quality_labels'].items():
        digest, = (d for d in images if d.startswith(prefix))
        assert len(prefix) >= 8 and digest not in quality
        quality[digest] = label
    candidates = notes['candidate_labels']
    for alias, labels in candidates.items():
        by_decision = {r['decision']: r for r in packet['packets'][alias]}
        assert len({r['decision'] for r in labels}) == len(labels)
        for label in labels:
            t = by_decision[label['decision']]
            signature(t)
            for field in ('raw_reply_sha256', 'current_image_sha256'):
                assert field not in label
                label[field] = t[field]
    out = HERE / 'review-notes' / (args.packet.name + '.json')
    save(out, {'packet_key': args.packet.name, **notes, 'quality_labels': quality})
    print(out)


if __name__ == '__main__':
    main()
