"""Reconcile every reviewed reply with its actual complete visible input and review origin."""

import argparse
from collections import Counter
import json
from pathlib import Path
import time

from collect import HERE, read, save, sha
from consolidate_preterminal_review import verify_consolidation
from exact_review_reuse import load_packet, signature
from link import verify
from review_cycle import review_pairs
from summarize import load_reviews


def audit(ledger, source_pairs, labels):
    actual = {}
    visible = ledger['public_legal_messages']
    for slot in ledger['rows']:
        t = slot['evidence']
        if t:
            for step in t['steps']:
                m = step['main']
                if m and m['natural_EOS']:
                    assert step['actual_first_forward']
                    actual[slot['slot']['run_id'], step['step']] = m

    by_original = {}
    packets, packet_images, compared, keyed_labels = {}, set(), set(), {}
    origins = Counter()
    for binding_dir, label_dir in source_pairs:
        mapping = read(binding_dir / 'PRIVATE-mapping.json')
        label_set = read(label_dir / 'review.json')
        if 'same_request_consolidation_proof_sha256' in label_set:
            verify_consolidation(label_dir, mapping)
        dossier = Path(mapping['review_input'])
        if dossier not in packets:
            public, seal = load_packet(dossier)
            assert set(public) == {'packets', 'messages'}
            assert sha(dossier/'读包说明.md') == seal['读包说明.md']
            for digest, loc in seal['original_images'].items():
                assert loc == 'images/' + digest + '.png' and sha(dossier / loc) == digest
                packet_images.add(digest)
            assert all(v == visible[k] for k, v in public['messages'].items())
            packets[dossier] = {p: {t['decision']:t for t in turns} for p,turns in public['packets'].items()}
        public_rows = packets[dossier]
        for alias, candidate_labels in label_set['candidate_labels'].items():
            run = mapping['alias_to_source'][alias]['run_id']
            for item in candidate_labels:
                n = item['decision']
                joined = run, n
                assert joined not in compared and labels[joined] == item
                compared.add(joined)
                t, m = public_rows[alias][n], actual[joined]
                original = signature(t)
                assert original == (tuple(m['messages_ordered']), m['current_image_sha256'],
                                    m['reply_sha256'], m['reply_text'])
                review_key = dossier.name, alias, n
                entry = {'run': run, 'decision': n, 'label': item['semantic_label'],
                         'direction_flag': bool(item.get('native_direction_conflict')),
                         'target_flag': bool(item.get('native_target_conflict'))}
                by_original.setdefault(original, []).append(entry)
                src = item.get('exact_review_reuse_from')
                if src:
                    k = src['packets'], src['packet_id'], src['decision']
                    upstream_signature, source_label, depth = keyed_labels[k]
                    assert upstream_signature == original and k != review_key
                    omit = {'decision','exact_review_reuse_from'}
                    assert {k:v for k,v in item.items() if k not in omit} == {
                        k:v for k,v in source_label.items() if k not in omit}
                    origins[depth + 1] += 1
                    keyed_labels[review_key] = original, item, depth + 1
                else:
                    origins[0] += 1
                    keyed_labels[review_key] = original, item, 0
    assert compared == set(labels) <= set(actual)
    differences = [xs for xs in by_original.values() if len({
        (r['label'], r['direction_flag'], r['target_flag']) for r in xs}) > 1]
    return {'actual_natural_EOS_replies': len(actual), 'reviews_bound_to_full_visible_input': len(compared),
            'distinct_exact_legal_context_image_reply_combinations': len(by_original),
            'exact_combinations_seen_multiple_times': sum(len(xs) > 1 for xs in by_original.values()),
            'distinct_original_PNGs_byte_checked_in_review_packets': len(packet_images),
            'source_manual_labels': origins[0], 'transitive_exact_reuses':sum(n for d,n in origins.items() if d),
            'reuse_lineage_depth_counts': dict(sorted(origins.items())),
            'conflicts_between_equal_full_inputs_originals_and_replies': differences,
            'labels_changed':False,'new_model_GUI_or_scorer_calls':0}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('ledger', type=Path)
    p.add_argument('report', type=Path)
    a = p.parse_args()
    for folder in (a.ledger,a.report): verify(folder)
    ledger = read(a.ledger/'private-linked.json')
    report = read(a.report/'condition-by-version.json')
    assert report['ledger_seal_sha256'] == sha(a.ledger/'seal.json')
    pairs = review_pairs(a.report)
    _, labels, sources = load_reviews(ledger, pairs)
    assert sources == report['review_sources']
    result = audit(ledger,pairs,labels)
    overall = report['overall_counts_only_no_pooled_effect_estimate']
    assert result['source_manual_labels'] == overall['candidate_replies_manually_reviewed']
    assert result['transitive_exact_reuses'] == overall['candidate_replies_with_exact_review_reuse']
    out = HERE/'review-binding-audits'/str(time.time_ns())
    out.mkdir(parents=True,exist_ok=False)
    save(out/'review-binding.json',{'ledger_seal_sha256':sha(a.ledger/'seal.json'),
          'report_seal_sha256':sha(a.report/'seal.json'), **result})
    save(out/'seal.json',{'review-binding.json':sha(out/'review-binding.json')})
    print(json.dumps({'review_binding':str(out),'seal':sha(out/'seal.json'),**result}))


if __name__=='__main__':
    main()
