"""Advance sealed evaluation using the previous report's verified review partitions."""

import argparse
from pathlib import Path
import subprocess
import sys

from collect import HERE, read, sha
from link import verify


def by_seal(directory):
    result = {}
    for child in sorted(directory.iterdir()):
        seal = child / 'seal.json'
        if seal.is_file():
            result.setdefault(sha(seal), child)
    return result


def review_pairs(report):
    verify(report)
    sources = read(report / 'condition-by-version.json')['review_sources']
    bindings = by_seal(HERE / 'review-private')
    labels = by_seal(HERE / 'labels')
    return [(bindings[s['private_binding_seal']], labels[s['label_seal']]) for s in sources]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('packets', 'reuse', 'summarize'))
    parser.add_argument('source', type=Path, help='Ledger for packets/summarize; public packet for reuse.')
    parser.add_argument('--prior', type=Path, required=True, help='Previous verified summary.')
    parser.add_argument('--add', action='append', nargs=2, type=Path, default=[], metavar=('BINDING', 'LABELS'))
    args = parser.parse_args()
    prior = list(dict.fromkeys(review_pairs(args.prior) + [tuple(p.resolve() for p in pair) for pair in args.add]))
    for binding, labels in args.add:
        verify(binding)
        verify(labels)
    if args.operation == 'reuse':
        # One historical partition predates public packet keys. It stays in all
        # ledger joins, but cannot be used by the exact-equality lookup.
        supported = [label for _, label in prior if 'packet_key' in read(label / 'review.json')]
        script = 'exact_review_reuse.py'
        extra = supported
    else:
        script = args.operation + '.py'
        flag = '--previous-review' if args.operation == 'packets' else '--review'
        extra = [value for a, b in prior for value in (flag, a, b)]

    return subprocess.run([sys.executable, '-B', HERE / script, args.source, *extra], check=False).returncode


if __name__ == '__main__':
    raise SystemExit(main())
