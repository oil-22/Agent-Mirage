"""Copy an actual sealed auxiliary input/output; never claims actor insertion."""
import argparse
import base64
import json
from pathlib import Path
import time

from orchestrate import HERE, PACKAGE, OUTPUT, REMOTE_PACKAGE, COMMON, remote, save, sha


def main(evidence, ident):
    assert evidence.parent == HERE and evidence.name.startswith('actual-evidence-')
    for name, expected in json.loads((evidence / 'seal.json').read_bytes()).items():
        assert sha(evidence / name) == expected
    row = next(row for row in json.loads((evidence / '3090.json').read_bytes())['sealed_requests'] if row['request'] == ident)
    assert row['operation'] == 'evidence'
    pointer = HERE / ('auxiliary-source-' + ident + '-collected.json')
    assert not pointer.exists(), 'Never repeat a completed auxiliary source export'
    out = HERE / ('auxiliary-source-' + ident + '-' + str(time.time_ns()));out.mkdir()
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    code = ('ROOT=' + repr(OUTPUT) + '\nPACKAGE=' + repr(REMOTE_PACKAGE) + '\nIDENT=' + repr(ident)
            + '\nEXPECTED=' + repr(row['seal_sha256']) + '\n' + COMMON + r'''
import base64
p=Path(ROOT)/'worker/requests'/IDENT;package=Path(PACKAGE)
assert os.getuid()==1033 and sha(p/'seal.json')==EXPECTED
files=json.loads((p/'seal.json').read_bytes())
for name,expected in files.items():assert Path(name).name==name and sha(p/name)==expected,name
wire=json.loads((p/'external-wire.json').read_bytes());request=wire['payload'];raw=(p/'original.png').read_bytes()
assert request==json.loads((p/'payload.json').read_bytes())
assert request['prompt']==(package/'fixed-prompt.txt').read_text()
assert request['image_sha256']==hashlib.sha256(raw).hexdigest()
assert set(request)=={'policy','model','revision','image_base64','image_sha256','original_size','prompt','prompt_sha256'}
assert base64.b64decode(request['image_base64'],validate=True)==raw
names=['original.png','raw-output.txt','response.json','stateless-input-boundary.json','stateless-context-discarded.json',
 'actual-generation.json','prepared.json','first-forward.json','raw-UTF8-validation.json','effective-generation.json','generated-raw-utf8.bin']
names+=[name for name in ['evidence-packet.json','contract-failure.json']if name in files]
exports={name:base64.b64encode((p/name).read_bytes()).decode()for name in names}
print(json.dumps({'request':request,'external_request_id':wire['request_id'],'trajectory_id':wire['trajectory_id'],
 'decision_index':wire['decision_index'],'attempt_index':wire['attempt_index'],'files':files,'request_seal_sha256':sha(p/'seal.json'),
 'exports':exports,'actual_actor_insertion_not_proven_by_this_collection':True,'new_model_GUI_scorer_calls':0}))
''')
    output, operation = remote('3090', code, 'actual-single-image-auxiliary-source-export-' + ident, timeout=55)
    value = json.loads(output)
    for name, encoded in value.pop('exports').items():
        raw = base64.b64decode(encoded, validate=True)
        (out / name).write_bytes(raw)
        assert sha(out / name) == value['files'][name]
    save(out / 'request.json', value['request'])
    (out / 'prompt.txt').write_text(value['request']['prompt'], encoding='utf8')
    save(out / 'receipt.json', dict(time=time.time(), source=value, operation=str(operation),
        inspected_seal_authority=str(evidence), native_tensor_binaries_retained_at_original_remote_paths=True,
        semantic_correctness_not_inferred=True, complete_actor_insertion_not_established=True,
        new_model_GUI_scorer_calls=0))
    save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    record = dict(root=str(out), receipt_sha256=sha(out / 'receipt.json'), seal_sha256=sha(out / 'seal.json'))
    save(pointer, record)
    print(json.dumps(record))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--request', required=True)
    args = parser.parse_args()
    assert args.request.isdigit() and len(args.request) >= 4
    main(args.evidence.resolve(), args.request)
