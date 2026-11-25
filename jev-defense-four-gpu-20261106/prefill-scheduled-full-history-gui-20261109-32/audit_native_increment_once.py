"""Audit a new contiguous completed range using the original strict auditor."""
import argparse
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(first, last, sequence, evidence):
    pointer = 'new-replies-' + sequence + '-audit-created.json'
    assert not (HERE / pointer).exists()
    assert 1 < first <= last and evidence.parent == HERE
    for name, expected in read(evidence / 'seal.json').items():
        assert sha(evidence / name) == expected
    prior_rows, prior_authorities = [], []
    pointers = [HERE / 'prefix-audit-created.json'] + sorted(p for p in HERE.glob('new-replies-*-audit-created.json')
        if re.fullmatch(r'new-replies-\d+-audit-created\.json', p.name))
    for path in pointers:
        record = read(path)
        audit_path = Path(record['audit'])
        assert sha(audit_path) == record['audit_sha256']
        value = read(audit_path)
        assert value['passed']
        prior_rows.extend(value['requests'])
        prior_authorities.append(record)
    prior_rows.sort(key=lambda row: row['request'])
    assert [row['request'] for row in prior_rows] == [str(i).zfill(4) for i in range(1, first)]
    counts = {op: max(row['original_track_attempt_index'] for row in prior_rows if row['operation'] == op)
              for op in ['actor', 'judge']}
    selected = read(evidence / '3090.json')['sealed_requests'][first - 1:last]
    ids = [str(i).zfill(4) for i in range(first, last + 1)]
    assert [row['request'] for row in selected] == ids
    binary_authorities = []
    for row in selected:
        authority = row.get('full_SHA_verification_authority', {
            'evidence': str(evidence), 'request': row['request'], 'request_seal_sha256': row['seal_sha256']})
        origin = Path(authority['evidence'])
        for name, expected in read(origin / 'seal.json').items():
            assert sha(origin / name) == expected
        original = next(item for item in read(origin / '3090.json')['sealed_requests'] if item['request'] == row['request'])
        assert original['files_verified'] > 0
        assert authority['request_seal_sha256'] == row['seal_sha256'] == original['seal_sha256']
        binary_authorities.append(authority)
    operation = selected[0]['operation']
    assert operation in counts and all(row['operation'] in counts for row in selected)
    source = (HERE / 'audit_new_replies_02_once.py').read_text(encoding='utf8')
    changes = [
        ('new-replies-02-audit-created.json', pointer, 2),
        ('actual-evidence-1794230765210589400', evidence.name, 1),
        ("record['sealed_requests'][1:4]", "record['sealed_requests'][" + str(first - 1) + ':' + str(last) + ']', 1),
        ("len(rows)==3 and [row['request'] for row in rows] == ['0002','0003','0004']",
         "len(rows)==" + str(len(ids)) + " and [row['request'] for row in rows] == " + repr(ids), 1),
        ("counts={'actor':17,'judge':51}", 'counts=' + repr(counts), 1),
        ("assert results[0]['operation']=='judge'and results[0]['original_track_attempt_index']==52",
         "assert results[0]['operation']==" + repr(operation) + " and results[0]['original_track_attempt_index']==" + str(counts[operation] + 1), 1),
        ('prefills[1:4]', 'prefills[' + str(first - 1) + ':' + str(last) + ']', 1),
        ('linked32-only-new-replies2to4-native-tensor-prefill-audit-v1', 'linked32-only-new-replies' + str(first) + 'to' + str(last) + '-native-tensor-prefill-audit-v1', 1),
        ('audit-only-new32-replies2to4-no-repeat-original-prefix-once', 'audit-only-new32-replies' + str(first) + 'to' + str(last) + '-no-repeat-original-prefix-once', 1),
        ("'new-replies-02-audit-'", "'new-replies-" + sequence + "-audit-'", 1),
    ]
    for before, after, count in changes:
        assert source.count(before) == count, before
        source = source.replace(before, after)
    before = "assert len(item['visited_groups'])==69 and set(item['visited_groups'])==set(item['same_native_execution_device_map'])"
    assert source.count(before) == 1
    source = source.replace(before, "expected=set(item['same_native_execution_device_map'])\n if row['complete_supplied_images']==0:expected.remove('model.visual')\n assert set(item['visited_groups'])==expected and len(item['visited_groups'])==len(expected)\n row['actual_native_prefill_group_count']=len(expected)\n row['native_visual_forward_observed']='model.visual'in item['visited_groups']")
    before = "assert native['text']==response['text'if operation=='actor'else'verdict']"
    assert source.count(before) == 1
    source = source.replace(before, before + "\n if operation=='actor':\n  assert native['verifier_grammar']is None\n  assert payload['body']['chat_template_kwargs']['enable_thinking']is False\n  for field in ['force_words_ids','forced_decoder_ids','forced_bos_token_id','constraints','bad_words_ids','suppress_tokens','begin_suppress_tokens']:\n   assert cfg.get(field)in [None,[]],field")
    before = 'value = json.loads(output)'
    assert source.count(before) == 1
    source = source.replace(before, before + "\n    value['selected_binary_full_SHA_authorities']=" + repr(binary_authorities)
        + "\n    value['prior_original_budget_counts_bound_to_completed_prefix']=" + repr(counts)
        + "\n    value['prior_nonoverlapping_audit_authorities']=" + repr(prior_authorities))
    exec(compile(source, str(Path(__file__).resolve()), 'exec'), {'__name__': '__main__', '__file__': str(Path(__file__).resolve())})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--first', type=int, required=True)
    parser.add_argument('--last', type=int, required=True)
    parser.add_argument('--sequence', required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'\d{2,3}', args.sequence)
    main(args.first, args.last, args.sequence, args.evidence.resolve())
