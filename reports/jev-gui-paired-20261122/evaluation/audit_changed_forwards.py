"""Rehash the actual forward bytes at late injection and recapture decisions."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import time

from audit_nf4_forward_bytes import AUDIT
from collect import HERE, control, manifest_for, read, save, sha
from link import verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ledger', type=Path)
    parser.add_argument('--previous', type=Path, help='Last cumulative late-forward byte audit.')
    args = parser.parse_args()
    verify(args.ledger)
    ledger = read(args.ledger / 'private-linked.json')
    remaining = defaultdict(list)
    by_id = {}
    covered, during_collection, all_relevant = {}, 0, 0
    if args.previous:
        verify(args.previous)
        previous = read(args.previous / 'index.json')
        covered = previous['verified_late_forward_by_request']
    for arm in ledger['rows']:
        tape = arm['evidence']
        if not tape:
            continue
        stage = arm['stage_id']
        run = arm['slot']['run_id']
        for step in tape['steps']:
            off = step['known_injected_dose_at_first_forward']
            on = step['recapture_at_actual_forward_needs_visual_review']
            if not (off or on):
                continue
            assert not (off and on) and step['actual_first_forward']
            all_relevant += 1
            record = step['main']
            if record['tensor_raw_bytes_fully_audited']:
                during_collection += 1
                continue
            rid = step['request']['request_id']
            request = {'run': run, 'step': step['step'], 'request_id': rid,
                       'terminal_sha256': tape['terminal_sha256'], 'natural_EOS': record['natural_EOS'],
                       'wire_sha256': record['wire_sha256'], 'seal_sha256': record['seal_sha256'],
                       'request_directory': record['runtime_request_directory']}
            assert rid not in by_id and tape['model_run_end_bound']
            binding = {'stage': stage, 'role': 'altered_delivery' if off else 'recapture', **request}
            by_id[rid] = binding
            if rid in covered:
                assert binding == covered[rid]['input']
            else:
                remaining[stage].append(request)
    assert covered.keys() <= by_id.keys()
    if not remaining:
        print(json.dumps({'all_decisive_forwards': all_relevant,
                          'audited_in_collection': during_collection, 'audited_late': len(covered),
                          'new_reads': 0}))
        return

    out = HERE / 'forward-byte-audits' / str(time.time_ns())
    out.mkdir(exist_ok=False)
    control.ROOT = out
    receipts, added_bytes = [], 0
    extractor = (HERE / 'extract_on_host.py').read_text(encoding='utf-8')
    for stage, pending in remaining.items():
        ptr, manifest, slots = manifest_for(stage)
        assert {r['run'] for r in pending} <= {r['run_id'] for r in slots}
        prefix = (f"ROOT={manifest['package3090']!r}\nOUTPUT={manifest['output3090']!r}\n"
                  f"EXPECTED={ptr['manifest_sha256']!r}\nREQUESTS={pending!r}\n__name__='evidence_library'\n")
        response = control.remote('3090', prefix + extractor + '\n' + AUDIT,
                                  'verify-late-effect-forward-bytes', timeout=150)
        receipt = Path(response['operation'])
        verify(receipt)
        result = response['result']
        proof = {r['request_id']: r for r in result['requests']}
        assert proof.keys() == {r['request_id'] for r in pending}
        receipts.append({'stage': stage, 'operation': str(receipt), 'seal': sha(receipt / 'seal.json')})
        added_bytes += result['tensor_bytes_rehashed']
        for rid, forward in proof.items():
            assert forward['request_seal_sha256'] == by_id[rid]['seal_sha256']
            covered[rid] = {'input': by_id[rid], 'actual_forward': forward}

    assert len(covered) + during_collection == all_relevant
    save(out / 'index.json', {'ledger_seal_sha256': sha(args.ledger / 'seal.json'),
         'previous_audit': {'path': str(args.previous.resolve()), 'seal': sha(args.previous / 'seal.json')}
                           if args.previous else None,
         'operations': receipts, 'verified_late_forward_by_request': covered,
         'all_decisive_forwards': all_relevant, 'already_byte_checked_in_collection': during_collection,
         'new_tensor_bytes_rehashed': added_bytes, 'actual_model_browser_or_scorer_calls': 0})
    save(out / 'seal.json', {'index.json': sha(out / 'index.json')})
    print(json.dumps({'audit': str(out), 'all_decisive_forwards': all_relevant,
                      'audited_in_collection': during_collection, 'audited_late': len(covered),
                      'new_tensor_bytes_rehashed': added_bytes}))


if __name__ == '__main__':
    main()
