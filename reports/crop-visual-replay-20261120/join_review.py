"""Join sealed blind labels to verified arms and summarize paired outcomes."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('attempt', type=Path)
    a = ap.parse_args().attempt
    seal = load(a / 'blind-review-seal.json')
    labels_path = a / 'blind-review.tsv'
    assert seal['blind-review.tsv'] == sha(labels_path)
    assert seal['SOURCE_REVIEW.md'] == sha(a / 'SOURCE_REVIEW.md')
    audit = load(a / 'postexit-audit.json')
    map_file = a / 'private-blind-map.json'
    assert audit['blind_map_sha256'] == sha(map_file)
    mapping = load(map_file)
    labels = list(csv.DictReader(labels_path.open(encoding='utf-8', newline=''), delimiter='\t'))
    assert len(labels) == len(mapping) == audit['completed'] and {r['opaque_id'] for r in labels} == set(mapping)
    by_case = defaultdict(dict)
    metrics = {(r['case'], r['arm']): r for r in audit['rows']}
    assert len(metrics) == len(mapping)
    for row in labels:
        oid, c = row['opaque_id'], row['case']
        position = mapping[oid]
        assert position['case'] == c
        arm = position['arm']
        p = a / 'blind-final' / (oid + '.json')
        assert audit['proofs']['public/blind/' + p.name] == sha(p) == seal['candidates'][oid]
        raw = load(p)
        assert raw['case'] == c and raw['natural_EOS'] == metrics[c, arm]['natural_EOS']
        by_case[c][arm] = {**row, 'candidate': raw['candidate'], 'natural_EOS': raw['natural_EOS'],
                           'metrics': metrics[c, arm]}
    plan = load(a / 'plan.json')
    arms = plan['arms']
    complete = [c for c, x in by_case.items() if set(x) == set(arms) and all(y['natural_EOS'] for y in x.values())]
    effects = {}

    def definite_visual(r):
        return r['visual_label'].startswith('definite_')

    def usable(r):
        return r['native_action_label'] == 'reasonable'

    def clean(r):
        return usable(r) and r['visual_label'] == 'none'

    for ctrl in ('original', 'append_duplicate'):
        diff = {}
        for name, predicate in [('definite_visual_error', definite_visual), ('reasonable_action', usable), ('both_grounded_and_reasonable', clean)]:
            gained, lost, same = [], [], []
            for c in sorted(complete):
                prior, current = predicate(by_case[c][ctrl]), predicate(by_case[c]['append_zoom'])
                (gained if current and not prior else lost if prior and not current else same).append(c)
            diff[name] = {'false_to_true': gained, 'true_to_false': lost, 'no_change': same}
        effects[ctrl] = diff
    totals, elapsed = {}, {}
    for arm in arms:
        panel = [by_case[c][arm] for c in complete]
        all_arm = [r for r in audit['rows'] if r['arm'] == arm]
        totals[arm] = {'complete_case_count': len(complete),
                       'definite_visual_errors': sum(definite_visual(r) for r in panel),
                       'visual_uncertain': sum(r['visual_label'].startswith('uncertain_') for r in panel),
                       'native_action_counts': dict(Counter(r['native_action_label'] for r in panel)),
                       'both_grounded_and_reasonable': sum(clean(r) for r in panel),
                       'ocr_errors': sum(r['ocr_error'] == 'yes' for r in panel),
                       'total_calls_with_reply': len(all_arm), 'natural_EOS': sum(r['natural_EOS'] for r in all_arm),
                       'archive_exact_output_ids': sum(r['generation_ids_equal_original_archive'] for r in all_arm),
                       'total_input_tokens': sum(r['input_tokens'] for r in all_arm),
                       'total_output_tokens': sum(r['output_tokens'] for r in all_arm),
                       'summed_call_wall_seconds': sum(r['seconds'] for r in all_arm)}
        elapsed[arm] = {'peak_reserved_gib_by_logical_gpu': [max((r['peak_reserved_bytes'][i] / 1024**3 for r in all_arm), default=None) for i in range(4)]}
    report = {'paired_complete_cases': sorted(complete), 'paired_virtual_decisions': len(complete),
              'distinct_tasks_in_complete_cases': len({c.split('-')[0] for c in complete}),
              'source_labels_before_mapping_sha256': sha(a / 'blind-review-seal.json'),
              'remote_postexit_audit_sha256': sha(a / 'postexit-audit.json'), 'totals': totals, 'paired_effects': effects,
              'per_case': by_case, 'runtime': elapsed}
    with (a / 'joined-review.json').open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in report.items() if k != 'per_case'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
