"""Collect unchanged sealed replies after image/history source review, no inference."""
import base64
import hashlib
import json
from pathlib import Path
import time

from orchestrate import COMMON, HERE, OUTPUT, remote, save, sha


def verified(folder):
    for name, expected in json.loads((folder / 'seal.json').read_bytes()).items():
        assert sha(folder / name) == expected, str(folder / name)


def main():
    pointer = HERE / 'pagination-rejection-outputs-created.json'
    assert not pointer.exists()
    image_review_pointer = json.loads((HERE / 'source-review-21-created.json').read_bytes())
    image_review_root = Path(image_review_pointer['review'])
    verified(image_review_root)
    manual = json.loads((image_review_root / 'manual-review-input.json').read_bytes())
    assert len(manual['original_history_images_actually_viewed']) == 37
    seen = {row['sha256'] for row in manual['original_history_images_actually_viewed']}
    sources = []
    for key in ['pagination37-main', 'pagination38-main']:
        source_pointer = json.loads((HERE / (key + '-source-created.json')).read_bytes())
        folder = Path(source_pointer['root'])
        verified(folder)
        receipt = json.loads((folder / 'receipt.json').read_bytes())
        assert {image['sha256'] for image in receipt['images']} == seen
        assert receipt['images'][0]['role'] == 'current'
        assert receipt['images'][0]['sha256'] == manual['current_image_sha256']
        payload = json.loads((folder / 'payload.json').read_bytes())
        assert payload['candidate'] == receipt['candidate'] and payload['operation'] == 'judge'
        assert len(payload['view']['images']) == 37
        sources.append({'request': receipt['request'], 'attempt_index': receipt['attempt_index'],
                        'decision_index': receipt['decision_index'],
                        'request_seal_sha256': receipt['request_seal_sha256'],
                        'payload_sha256': sha(folder / 'payload.json'),
                        'external_wire_sha256': sha(folder / 'external-wire.json'),
                        'input_source_root': str(folder),
                        'input_source_seal_sha256': sha(folder / 'seal.json')})
    code = 'ROOT=' + repr(OUTPUT) + '\nSOURCES=' + repr(sources) + '\n' + COMMON + r'''
import base64
rows=[]
for source in SOURCES:
 p=Path(ROOT)/'worker/requests'/source['request']
 assert os.getuid()==1033 and sha(p/'seal.json')==source['request_seal_sha256']
 seal=json.loads((p/'seal.json').read_bytes())
 assert sha(p/'external-wire.json')==source['external_wire_sha256']==seal['external-wire.json']
 assert sha(p/'payload.json')==source['payload_sha256']==seal['payload.json']
 wire=json.loads((p/'external-wire.json').read_bytes())
 assert wire['attempt_index']==source['attempt_index'] and wire['decision_index']==source['decision_index']==37
 files={}
 for name in ['seal.json','native-call.json','response.json','actual-generation.json','effective-generation.json']:
  raw=(p/name).read_bytes()
  if name!='seal.json':assert hashlib.sha256(raw).hexdigest()==seal[name]
  files[name]=base64.b64encode(raw).decode()
 native=json.loads((p/'native-call.json').read_bytes())
 response=json.loads((p/'response.json').read_bytes())
 actual=json.loads((p/'actual-generation.json').read_bytes())
 assert response['request_id']==wire['request_id'] and response['operation']=='judge'
 assert response['external_wire_sha256']==source['external_wire_sha256']
 assert native['text']==response['verdict'] and actual['natural_EOS'] is True
 rows.append({'source':source,'files_base64':files,'original_SHA_bindings':{
 name:sha(p/name) for name in files},'natural_EOS':True})
print(json.dumps({'read_only':True,'rows':rows,'new_model_GUI_scorer_calls':0}))
'''
    output, operation = remote('3090', code, 'collect-original-pagination37and38-judge100and102-after-source-seal', timeout=55)
    value = json.loads(output)
    out = HERE / ('pagination-rejection-outputs-' + str(time.time_ns()))
    out.mkdir()
    for row in value['rows']:
        folder = out / row['source']['request']
        folder.mkdir()
        for name, encoded in row.pop('files_base64').items():
            raw = base64.b64decode(encoded, validate=True)
            assert hashlib.sha256(raw).hexdigest() == row['original_SHA_bindings'][name]
            (folder / name).write_bytes(raw)
        native = json.loads((folder / 'native-call.json').read_bytes())
        with (folder / 'raw-output.txt').open('x', encoding='utf8', newline='\n') as stream:
            stream.write(native['text'])
        row['raw_output_file_sha256'] = sha(folder / 'raw-output.txt')
    value.update(time=time.time(), remote_operation=str(operation), image_history_review=image_review_pointer,
                 all_original_input_images_already_directly_viewed=True,
                 current_candidate_source_labels_not_changed_by_reply_review=True,
                 source_selected_nonblind_development_not_new_semantic_controls=True)
    save(out / 'receipt.json', value)
    save(out / 'seal.json', {p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()})
    result = {'root':str(out),'receipt_sha256':sha(out/'receipt.json'),'seal_sha256':sha(out/'seal.json')}
    save(pointer, result)
    print(json.dumps(dict(result, requests=[r['source']['request'] for r in value['rows']], new_calls=0)))


if __name__ == '__main__':
    main()
