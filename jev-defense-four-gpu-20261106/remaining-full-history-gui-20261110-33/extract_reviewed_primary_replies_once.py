"""Export audited replies after sealing their actual source-input review.

Observer only: no model, GUI, scoring, prompt or validator changes.
Both canonical message identities and original file-byte identities are checked.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import time

from orchestrate import HERE, save, sha
from join_source_reviews import verify_seal


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':')).encode('utf8')


def main(review_pointer, audit, requests, key):
    assert review_pointer.parent == HERE and audit.parent == HERE
    assert re.fullmatch(r'[a-z][a-z0-9-]+', key)
    assert requests and len(requests) == len(set(requests))
    assert all(re.fullmatch(r'\d{4}', ident) for ident in requests)
    pointer = HERE / (key + '-created.json')
    assert not pointer.exists(), 'Inspect a completed extraction; never repeat it'
    authority = json.loads(review_pointer.read_bytes())
    reviewed = Path(authority['root'])
    assert reviewed.parent == HERE
    assert verify_seal(reviewed) == authority['seal_sha256']
    assert sha(reviewed / 'review.json') == authority['review_sha256']
    inputs = {row['request']: row for row in
              json.loads((reviewed / 'review.json').read_bytes())['rows']}
    audit_seal = verify_seal(audit)
    assert json.loads((audit / 'receipt.json').read_bytes())['passed']
    bindings = json.loads((audit / '3090-native-bindings.json').read_bytes())['bindings']
    records, replies = [], {}
    for ident in requests:
        row = inputs[ident]
        source = Path(row['source_input'])
        assert source.parent == HERE
        assert verify_seal(source) == row['source_input_seal_sha256']
        wire = json.loads((source / 'external-wire.json').read_bytes())
        payload = json.loads((source / 'payload.json').read_bytes())
        binding = bindings[ident]
        assert wire['payload'] == payload
        assert binding['wire_sha256'] == sha(source / 'external-wire.json')
        assert binding['payload_sha256'] == hashlib.sha256(canonical(payload)).hexdigest()
        assert binding['request_id'] == wire['request_id']
        response = binding['response']
        assert hashlib.sha256(canonical(response)).hexdigest() == binding['response_raw_sha256']
        raw = response['verdict']
        assert isinstance(raw, str), 'Preserve the original native reply field type'
        replies[ident] = raw
        records.append(dict(request=ident, source_input=str(source),
            source_input_review=authority, original_native_audit=str(audit),
            original_native_audit_seal_sha256=audit_seal,
            request_seal_sha256=binding['request_seal_sha256'],
            canonical_payload_sha256=binding['payload_sha256'],
            serialized_payload_file_sha256=sha(source / 'payload.json'),
            canonical_response_sha256=binding['response_raw_sha256'],
            raw_reply_utf8_sha256=hashlib.sha256(raw.encode('utf8')).hexdigest()))
    out = HERE / (key + '-' + str(time.time_ns()))
    out.mkdir()
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    for ident, raw in replies.items():
        (out / (ident + '-raw.txt')).write_bytes(raw.encode('utf8'))
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as error:
            save(out / (ident + '-decode.json'), dict(passed=False, error=str(error)))
        else:
            save(out / (ident + '-decoded.json'), decoded)
    save(out / 'receipt.json', dict(records=records,
        source_input_review_authority_verified=True,
        prior_reply_visibility_is_reported_in_source_review=True,
        original_native_receipts_retained_remotely=True,
        source_labels_and_original_replies_unchanged=True,
        new_model_GUI_scorer_calls=0))
    save(out / 'seal.json', {path.name: sha(path) for path in out.iterdir() if path.is_file()})
    result = dict(root=str(out), receipt_sha256=sha(out / 'receipt.json'),
                  seal_sha256=sha(out / 'seal.json'), requests=requests,
                  new_model_GUI_scorer_calls=0)
    save(pointer, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--review-pointer', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--request', action='append', required=True)
    parser.add_argument('--key', required=True)
    args = parser.parse_args()
    main(args.review_pointer.resolve(), args.audit.resolve(), args.request, args.key)
