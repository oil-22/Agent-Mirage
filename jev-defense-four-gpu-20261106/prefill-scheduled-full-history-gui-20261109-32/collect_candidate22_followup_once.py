"""Read candidate22's original followup frame and actual judge64 evidence."""
import base64
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'full-history-gui-development-20261109-23'))
from remote_control import remote, save, sha


def main():
    assert not (HERE / 'candidate22-followup-created.json').exists()
    joinpath = HERE / 'post-review-join-1794233314583525500/join.json'
    assert sha(joinpath) == json.loads((joinpath.parent / 'seal.json').read_bytes())['join.json']
    joined = json.loads(joinpath.read_bytes())
    assert joined['all_source_labels_sealed_before_this_join']
    assert len(joined['rows']) == 1 and joined['rows'][0]['accepted'] and joined['rows'][0]['executed']
    # Reuse the read-only original-frame exporter without changing that artifact.
    source = (HERE / 'collect_candidate21_postexecution_frame_once.py').read_text(encoding='utf8')
    scope = {'__name__': 'read_only_frame_exporter_source', '__file__': str(HERE / 'collect_candidate21_postexecution_frame_once.py')}
    exec(compile(source, 'immutable-original-frame-exporter', 'exec'), scope)
    code = scope['CODE']
    before = 'c94c66947622a0224b5f'
    assert code.count(before) == 1
    code = code.replace(before, '9da9deeee4f6ef35f3a9')
    output, operation = remote('4090', code, 'read-original-next-frame-candidate22-no-capture', timeout=55)
    frame = json.loads(output)
    picture = base64.b64decode(frame.pop('original_capture_png_base64'), validate=True)
    code = r'''
from pathlib import Path
import hashlib,json,time
root=Path('/home/researcher/jev-defense-four-gpu-20261106/prefill-scheduled-full-history-gui-20261109-32')
p=root/'worker/requests/0019'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
seal=json.loads((p/'seal.json').read_bytes())
for name in ['external-wire.json','payload.json','native-call.json','response.json','actual-generation.json']:
 assert sha(p/name)==seal[name],name
wire=json.loads((p/'external-wire.json').read_bytes());payload=wire['payload']
native=json.loads((p/'native-call.json').read_bytes());response=json.loads((p/'response.json').read_bytes())
actual=json.loads((p/'actual-generation.json').read_bytes())
assert wire['request_id']==response['request_id']
assert wire['attempt_index']==64 and wire['decision_index']==22 and payload['operation']=='judge'
assert sha(p/'external-wire.json')==response['external_wire_sha256']
assert native['text']==response['verdict'] and actual['natural_EOS']
images=[{k:v for k,v in im.items() if k in ['sha256','size','role','decoded']}for im in payload['view']['images']]
assert images[0]['sha256']=='019f34bbae1b72b0b6426ae074a68bd225ae956646151c7c635ad832e8f530d8'and images[0]['role']=='current'
print(json.dumps({'time':time.time(),'read_only':True,'request':'0019','original_judge_attempt':64,
 'decision':22,'request_id':wire['request_id'],'seal_sha256':sha(p/'seal.json'),
 'wire_sha256':sha(p/'external-wire.json'),'response_sha256':sha(p/'response.json'),
 'native_response_text':native['text'],'actual_public_image_inventory':images,
 'natural_EOS':actual['natural_EOS'],'input_tokens':actual['input_tokens'],
 'output_tokens':actual['output_tokens'],'new_model_GUI_scorer_calls':0},ensure_ascii=False))
'''
    output2, operation2 = remote('3090', code, 'bind-original-judge64-false-current-pagination-description', timeout=55)
    judge = json.loads(output2)
    out = HERE / ('candidate22-followup-' + str(time.time_ns()))
    out.mkdir()
    filename = '023-originally-captured.png'
    (out / filename).write_bytes(picture)
    assert sha(out / filename) == frame['next_observation_current_image']['sha256']
    frame.update(remote_operation=str(operation), source_sealed_execution_join=str(joinpath),
                 source_sealed_execution_join_sha256=sha(joinpath), image_requires_visual_review=True)
    judge['remote_operation'] = str(operation2)
    save(out / 'frame-receipt.json', frame)
    save(out / 'judge64-source-binding.json', judge)
    save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    pointer = {'root': str(out), 'seal_sha256': sha(out / 'seal.json'),
               'frame_receipt_sha256': sha(out / 'frame-receipt.json'),
               'judge_binding_sha256': sha(out / 'judge64-source-binding.json')}
    save(HERE / 'candidate22-followup-created.json', pointer)
    print(json.dumps(dict(pointer, next_observation=frame['next_observation_id'],
                          actual_judge_text=judge['native_response_text'], new_model_GUI_calls=0), ensure_ascii=False))


if __name__ == '__main__':
    main()
