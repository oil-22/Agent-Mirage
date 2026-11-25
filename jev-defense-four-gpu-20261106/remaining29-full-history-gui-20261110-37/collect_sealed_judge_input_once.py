"""Export exact judge inputs only, after the actor source review is sealed."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import time

from PIL import Image
from orchestrate import COMMON, HERE, OUTPUT, remote, save, sha


def main(request_id, evidence, key, review_pointer):
    assert re.fullmatch(r'\d{4}', request_id)
    assert re.fullmatch(r'[a-z][a-z0-9-]+', key)
    pointer = HERE / (key + '-source-created.json')
    assert not pointer.exists() and evidence.parent == HERE
    for name, expected in json.loads((evidence / 'seal.json').read_bytes()).items():
        assert sha(evidence / name) == expected
    review = json.loads((HERE / review_pointer).read_bytes())
    review_root = Path(review['review'])
    for name, expected in json.loads((review_root / 'seal.json').read_bytes()).items():
        assert sha(review_root / name) == expected
    row = next(v for v in json.loads((evidence / '3090.json').read_bytes())['sealed_requests']
               if v['request'] == request_id)
    assert row['operation'] == 'judge'
    code = 'ROOT=' + repr(OUTPUT) + '\nROW=' + repr(row) + '\n' + COMMON + r'''
import base64
p=Path(ROOT)/'worker/requests'/ROW['request']
assert sha(p/'seal.json')==ROW['seal_sha256']
seal=json.loads((p/'seal.json').read_bytes())
files={}
for name in ['external-wire.json','payload.json','prepared.json','first-forward.json']:
 assert sha(p/name)==seal[name],name
 files[name]=base64.b64encode((p/name).read_bytes()).decode()
print(json.dumps({'files_base64':files,'original_SHA_bindings':{name:seal[name]for name in files},
 'request_seal_sha256':sha(p/'seal.json'),'actual_reply_verdict_and_execution_excluded':True,
 'new_model_GUI_scorer_calls':0}))
'''
    output, operation = remote('3090', code, 'export-sealed-judge-input-only-' + key, timeout=55)
    value = json.loads(output)
    out = HERE / (key + '-source-input-' + str(time.time_ns()))
    out.mkdir()
    for name, encoded in value.pop('files_base64').items():
        raw = base64.b64decode(encoded)
        assert hashlib.sha256(raw).hexdigest() == value['original_SHA_bindings'][name]
        (out / name).write_bytes(raw)
    payload = json.loads((out / 'payload.json').read_bytes())
    wire = json.loads((out / 'external-wire.json').read_bytes())
    assert payload == wire['payload'] and payload['operation'] == 'judge'
    inventory = []
    for index, image in enumerate(payload['view']['images']):
        raw = base64.b64decode(image['raw_base64'])
        target = out / ('image-' + str(index).zfill(2) + '.png')
        target.write_bytes(raw)
        with Image.open(target) as original:
            size = list(original.size)
        inventory.append({'file':target.name,'role':image['role'],
                          'size':size,'sha256':sha(target)})
    value.update(remote_operation=str(operation), request=request_id,
                 trajectory_id=wire['trajectory_id'], decision_index=wire['decision_index'],
                 attempt_index=wire['attempt_index'], candidate=payload['candidate'],
                 observation_id=payload['view']['observation_id'], images=inventory,
                 actor_source_review=review, evidence=str(evidence),
                 source_evidence_seal_sha256=sha(evidence/'seal.json'),
                 evaluation_only_never_checker_input=True,
                 images_and_legal_request_require_source_review_before_reply_collection=True)
    save(out / 'receipt.json', value)
    save(out / 'seal.json', {p.name:sha(p) for p in out.iterdir() if p.is_file()})
    save(pointer, {'root':str(out),'receipt_sha256':sha(out/'receipt.json'),
                   'seal_sha256':sha(out/'seal.json')})
    print(json.dumps({'root':str(out),'candidate':payload['candidate'],
        'images':inventory,'request':request_id,'reply_excluded':True,'new_calls':0},ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--key', required=True)
    parser.add_argument('--review-pointer', required=True)
    args = parser.parse_args()
    main(args.request, args.evidence.resolve(), args.key, args.review_pointer)
