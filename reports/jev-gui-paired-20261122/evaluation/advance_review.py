"""Collect one newly sealed suffix snapshot and prepare its independent review."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

from collect import EXPERIMENT, HERE, latest_nf4_stage, manifest_for, read, sha
from link import verify


CLOSED_COLLECTIONS = ('1795492310870313100', '1795494470418068900')
READERS = {'NF4-resume-01':'resume_frozen_suffix.py','NF4-resume-02':'resume_after_resource_stop.py'}


def call(script, *args):
    command = [sys.executable, '-B', script, *args]
    result = subprocess.run(command, cwd=EXPERIMENT, text=True, encoding='utf-8',
                            errors='replace', capture_output=True, check=False)
    if result.returncode:
        print(result.stdout, file=sys.stderr, end='')
        print(result.stderr, file=sys.stderr, end='')
        raise SystemExit(result.returncode)
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('previous_collection', type=lambda v: Path(v).resolve())
    parser.add_argument('prior_report', type=lambda v: Path(v).resolve())
    parser.add_argument('--preterminal', action='append', nargs='+', type=lambda v: Path(v).resolve(), default=[],
                        metavar='PREFIX_OR_LABELS', help='A prefix followed by one or more sealed label partitions.')
    args = parser.parse_args()
    if any(len(group) < 2 for group in args.preterminal):
        parser.error('--preterminal needs a prefix followed by at least one sealed label partition')
    for path in (args.previous_collection, args.prior_report):
        verify(path)
    active_stage = latest_nf4_stage()
    pointer, _, _ = manifest_for(active_stage)
    before = read(args.previous_collection / 'index.json').get(active_stage, {}).get('GUI_terminals', 0)
    source = EXPERIMENT / 'quantized-continuation-20261123' / READERS[active_stage]
    receipt = json.loads(call(source, 'inspect', '4090'))
    records = receipt['result']['records']
    status = records.get('batch/status.json', {})
    snapshot = {'operation': receipt['operation'], 'stage': active_stage, 'status': status,
                'actual_GUI_process': records.get('control/actual'),
                'actual_site_lease': records.get('actual_site_lease'),
                'seen_terminal_files': len(records['terminals'])}
    print(json.dumps(snapshot), flush=True)
    if len(records['terminals']) <= before:
        return

    collection_stdout = call(HERE / 'collect.py', active_stage, '--previous', args.previous_collection)
    first, counts = collection_stdout.splitlines()
    collection = Path(first.removeprefix('Evidence collection: '))
    count = json.loads(counts.split(' ', 1)[1])['GUI_terminals']
    print(json.dumps({'collection': str(collection), 'sealed_suffix_slots': count}), flush=True)
    if count <= before:
        return  # Terminal file exists but has not yet been sealed.

    parents = [HERE / 'collections' / c for c in CLOSED_COLLECTIONS]
    if 'closed_parent_collection' in pointer:
        bound = pointer['closed_parent_collection']
        prior = Path(bound['path'])
        verify(prior)
        assert sha(prior/'seal.json') == bound['seal_sha256']
        parents.append(prior)
    joined = json.loads(call(HERE / 'link.py', *parents, collection))
    print(json.dumps(joined), flush=True)
    ledger = joined['ledger']
    stage = HERE / 'review_cycle.py'
    extra = []
    for prefix, *partitions in args.preterminal:
        bound = json.loads(call(HERE / 'preterminal_review.py', 'bind', ledger, prefix, *partitions))
        print(json.dumps(bound), flush=True)
        for label_folder in bound['labels']:
            extra.extend(('--add', bound['review_private'], label_folder))
    packet = json.loads(call(stage, 'packets', ledger, '--prior', args.prior_report, *extra))
    print(json.dumps(packet), flush=True)
    if 'review_input' not in packet:
        print(call(stage, 'summarize', ledger, '--prior', args.prior_report, *extra))
        return

    exact = json.loads(call(stage, 'reuse', packet['review_input'], '--prior', args.prior_report, *extra))
    print(json.dumps(exact), flush=True)
    if (exact['manual_candidates_remaining'] or
            packet['new_independent_image_quality_candidates'] != exact.get('exact_reused_images', 0)):
        return  # No private result join before the new manual judgments are sealed.
    print(call(stage, 'summarize', ledger, '--prior', args.prior_report, *extra,
               '--add', packet['review_private'], exact['labels']))


if __name__ == '__main__':
    main()
