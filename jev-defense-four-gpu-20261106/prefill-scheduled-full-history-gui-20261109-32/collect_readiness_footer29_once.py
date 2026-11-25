"""Collect one completed readiness reply after sealing its source image review."""
import json
from pathlib import Path
import time

from orchestrate import COMMON, HERE, OUTPUT, remote, save, sha


def main():
    pointer = HERE / 'readiness-footer29-actual-collection-created.json'
    assert not pointer.exists()
    review = json.loads((HERE / 'readiness-footer29-source-review-created.json').read_bytes())
    folder = Path(review['review'])
    for name, expected in json.loads((folder / 'seal.json').read_bytes()).items():
        assert sha(folder / name) == expected
    label = json.loads((folder / 'review.json').read_bytes())
    assert label['current_readiness_reply_or_verdict_not_read_before_seal']
    evidence = HERE / 'actual-evidence-1794237179067199200'
    for name, expected in json.loads((evidence / 'seal.json').read_bytes()).items():
        assert sha(evidence / name) == expected
    record = json.loads((evidence / '3090.json').read_bytes())
    row = next(item for item in record['sealed_requests'] if item['request'] == '0040')
    assert row['operation'] == 'judge' and row['files_verified'] > 0
    code = ('ROOT=' + repr(OUTPUT) + '\nROW=' + repr(row) + '\nSOURCE=' + repr(label) + '\n'
            + COMMON + r'''
import base64
path=Path(ROOT)/'worker/requests'/ROW['request']
assert sha(path/'seal.json')==ROW['seal_sha256']
seal=json.loads((path/'seal.json').read_bytes())
names=['external-wire.json','payload.json','native-call.json','response.json','actual-generation.json','effective-generation.json','prepared.json','first-forward.json']
for name in names:assert sha(path/name)==seal[name],name
wire=(path/'external-wire.json').read_bytes();external=json.loads(wire)
payload=json.loads((path/'payload.json').read_bytes());response=json.loads((path/'response.json').read_bytes())
assert payload==external['payload'] and payload['operation']=='judge'
assert response['external_wire_sha256']==hashlib.sha256(wire).hexdigest()
view=payload['view'];assert view['observation_id']==SOURCE['observation_id']
images=[]
for item in view['images']:
 raw=base64.b64decode(item['raw_base64'])
 images.append({'role':item['role'],'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
assert len(images)==1 and images[0]['role']=='current'and images[0]['sha256']==SOURCE['image_sha256']
native=json.loads((path/'native-call.json').read_bytes());actual=json.loads((path/'actual-generation.json').read_bytes())
assert native['text']==response['verdict'] and native['generated_ids']==actual['output_ids']
assert actual['natural_EOS']
print(json.dumps({'request':ROW['request'],'operation':'judge',
 'trajectory_id':external['trajectory_id'],'decision_index':external['decision_index'],
 'attempt_index':external['attempt_index'],'request_seal_sha256':sha(path/'seal.json'),
 'source_image_and_observation_bound':True,'source_review_sealed_before_collection':True,
 'images':images,'candidate':payload['candidate'],'system':payload['system'],
 'raw_native_reply':native['text'],'actual_input_tokens':actual['input_tokens'],
 'output_tokens':actual['output_tokens'],'natural_EOS':actual['natural_EOS'],
 'immutable_file_SHA_bindings':{name:seal[name]for name in names},
 'semantic_verdict_requires_manual_review':True,'new_model_GUI_scorer_calls':0}))
''')
    output, operation = remote('3090', code, 'collect-sealed-footer29-readiness-after-source-review', timeout=55)
    value = json.loads(output)
    out = HERE / ('readiness-footer29-actual-' + str(time.time_ns()))
    out.mkdir()
    value.update(source_review=review, source_evidence=str(evidence),
                 source_evidence_seal_sha256=sha(evidence / 'seal.json'),
                 remote_operation=str(operation))
    save(out / 'receipt.json', value)
    save(out / 'seal.json', {'receipt.json': sha(out / 'receipt.json')})
    save(pointer, {'root':str(out),'receipt_sha256':sha(out/'receipt.json'),'seal_sha256':sha(out/'seal.json')})
    print(json.dumps({'root':str(out),'native_reply':value['raw_native_reply'],
        'image_bound':value['source_image_and_observation_bound'],'new_model_GUI_scorer_calls':0},ensure_ascii=False))


if __name__ == '__main__':
    main()
