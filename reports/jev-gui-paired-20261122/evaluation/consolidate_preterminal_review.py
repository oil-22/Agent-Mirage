"""Bind directly reviewed notes for the same real requests to a later public prefix."""

import argparse
import json
from pathlib import Path
import time

from collect import HERE, read, save, sha
from exact_review_reuse import load_packet, signature
from link import verify


def open_prefix(path):
    verify(path)
    binding = read(path / 'prefix.json')
    assert binding['terminal_outcome_not_read_or_linked']
    assert binding['new_model_GUI_scorer_calls'] == 0
    assert set(binding['source_receipts']) == {'GUI', 'model'}
    for proof in binding['source_receipts'].values():
        operation = Path(proof['path'])
        verify(operation)
        assert sha(operation/'seal.json') == proof['seal_sha256']
    packet = Path(binding['review_input'])
    assert packet == HERE / 'review-packets' / path.name
    public, seal = load_packet(packet)
    assert sha(packet / 'seal.json') == binding['review_input_sha256']
    assert set(binding['alias_to_source']) == set(public['packets'])
    return binding, packet, public, seal


def request_binding(binding, alias, decision):
    item = binding['alias_to_source'][alias]
    assert item['run_id'] == binding['run'] and item['terminal_sha256'] is None
    return item['private_candidates'][str(decision)]


def verify_original(packet, digest, seal):
    name = seal['original_images'][digest]
    assert name == 'images/' + digest + '.png' and sha(packet / name) == digest


def build(target, direct_partitions):
    target_binding, packet, public, seal = open_prefix(target)
    candidates, expected = {}, {}
    for alias, turns in public['packets'].items():
        for turn in turns:
            decision = turn['decision']
            wire = request_binding(target_binding, alias, decision)
            rid = wire['request_id']
            assert rid not in expected
            expected[rid] = (alias, turn, wire)
    needed_images = set(read(packet / 'image-quality-input.json')['images'])
    quality = {}
    proof_sources = []
    for directory in direct_partitions:
        verify(directory)
        notes = read(directory / 'review.json')
        assert not notes['joined_private_execution_labels']
        assert 'same_request_consolidation_proof_sha256' not in notes
        src = HERE / 'preterminal-review-private' / notes['packet_key']
        src_binding, src_packet, src_public, src_seal = open_prefix(src)
        assert notes['packet_seal_sha256'] == src_binding['review_input_sha256']
        assert all(src_binding[k] == target_binding[k] for k in ('run', 'stage'))
        for alias, items in notes['candidate_labels'].items():
            turns = {t['decision']: t for t in src_public['packets'][alias]}
            for item in items:
                assert 'exact_review_reuse_from' not in item
                decision = item['decision']
                original = turns[decision]
                wire = request_binding(src_binding, alias, decision)
                dst_alias, dst_turn, dst_wire = expected.pop(wire['request_id'])
                assert dst_wire == wire and dst_turn['decision'] == decision
                assert signature(dst_turn) == signature(original)
                assert all(item[k] == original[k] for k in ('raw_reply_sha256', 'current_image_sha256'))
                candidates.setdefault(dst_alias, []).append(item)
        for digest, label in notes['quality_labels'].items():
            assert digest in needed_images and digest not in quality
            assert digest in read(src_packet / 'image-quality-input.json')['images']
            verify_original(src_packet, digest, src_seal)
            verify_original(packet, digest, seal)
            quality[digest] = label
        proof_sources.append({'labels': str(directory.resolve()), 'label_seal': sha(directory/'seal.json'),
                              'prefix': str(src), 'prefix_seal': sha(src/'seal.json')})
    assert not expected and needed_images == quality.keys()
    return {'packet_key': packet.name, 'packet_seal_sha256': target_binding['review_input_sha256'],
            'scope_and_blinding': 'Consolidation of directly reviewed, outcome-free prefixes. Same real '
                 'request IDs, exact wire SHAs, legal histories, current originals, and replies. Original '
                 'judgments are unchanged; these are not reviews borrowed from other requests.',
            'candidate_labels': {a: sorted(v, key=lambda x: x['decision']) for a,v in candidates.items()},
            'quality_labels': quality, 'joined_private_execution_labels': False}, {
            'target': str(target.resolve()), 'target_seal': sha(target/'seal.json'),
            'source_partitions': proof_sources, 'new_model_GUI_scorer_calls': 0}


def verify_consolidation(directory, private_binding):
    verify(directory)
    record = read(directory/'review.json')
    proof_file = directory/'same-request-proof.json'
    assert record.pop('same_request_consolidation_proof_sha256') == sha(proof_file)
    proof = read(proof_file)
    assert private_binding['preterminal_source'] == {'path': proof['target'], 'seal_sha256': proof['target_seal']}
    target = Path(proof['target'])
    labels = [Path(v['labels']) for v in proof['source_partitions']]
    assert (record, proof) == build(target, labels)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target_prefix', type=lambda p: Path(p).resolve())
    parser.add_argument('direct_labels', type=lambda p: Path(p).resolve(), nargs='+')
    args = parser.parse_args()
    result, proof = build(args.target_prefix, args.direct_labels)
    out = HERE / 'labels' / str(time.time_ns())
    out.mkdir(exist_ok=False)
    save(out/'same-request-proof.json', proof)
    save(out/'review.json', {**result, 'same_request_consolidation_proof_sha256': sha(out/'same-request-proof.json')})
    save(out/'seal.json', {f: sha(out/f) for f in ('same-request-proof.json', 'review.json')})
    print(json.dumps({'labels': str(out), 'seal': sha(out/'seal.json'),
                      'direct_replies': sum(map(len,result['candidate_labels'].values())),
                      'original_image_labels': len(result['quality_labels'])}))


if __name__ == '__main__':
    main()
