"""Read five sealed original checker requests; never load or call a model."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
R33 = BASE / 'remaining-full-history-gui-20261110-33'
R37 = BASE / 'remaining29-full-history-gui-20261110-37'
sys.path.insert(0, str(R37))
spec = importlib.util.spec_from_file_location('original_main_trace_transport', R37 / 'orchestrate.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
remote, save, sha = transport.remote, transport.save, transport.sha


def verify(folder, expected):
    assert sha(folder / 'seal.json') == expected
    for name, expected_sha in json.loads((folder / 'seal.json').read_bytes()).items():
        path = folder / name
        assert path.resolve().is_relative_to(folder.resolve())
        assert sha(path) == expected_sha


def main():
    assert not (HERE / 'collected.json').exists(), 'Completed read-only collector is immutable'
    wanted = {'0068', '0079', '0096', '0098', '0099'}
    targets, authorities = {}, {}
    for pp in sorted(R33.glob('mixed-receipt-audit-created-*.json')):
        pointer = json.loads(pp.read_bytes())
        root = Path(pointer['root'])
        data = json.loads((root / '3090-native-bindings.json').read_bytes())
        overlap = wanted.intersection(data['bindings'])
        if not overlap:
            continue
        verify(root, pointer['seal_sha256'])
        assert sha(root / 'receipt.json') == pointer['receipt_sha256']
        assert data['passed'] and not data['CUDA_initialized'] and not data['model_weights_loaded']
        authorities[str(root)] = pointer
        for ident in overlap:
            report = next(row for row in data['reports'] if row['request'] == ident)
            binding = data['bindings'][ident]
            assert report['operation'] == 'judge'
            assert report['native_proof']['all_prepared_first_forward_and_returned_sequence_IDs_bound']
            assert report['native_proof']['independent_native_tokenizer_decode_matches_unmodified_reply']
            if ident in targets:
                assert targets[ident]['binding'] == binding
            targets[ident] = dict(binding=binding, native_proof_reused=report['native_proof'],
                request_seal_sha256=report['request_seal_sha256'], authority=pointer)
    assert set(targets) == wanted
    out = HERE / ('original-checker-trace-' + str(time.time_ns()))
    out.mkdir()
    save(out / 'prior-native-bindings.json', dict(rows=targets, authorities=authorities,
        full_native_input_and_decode_audits_reused_not_reexecuted=True))
    expected = {ident: {key: targets[ident]['binding'][key]
        for key in ['payload_sha256', 'wire_sha256', 'request_seal_sha256']}
        for ident in sorted(wanted)}
    code = 'TARGETS=' + repr(expected) + '\n' + transport.COMMON + r'''
import base64,copy
assert os.getuid()==1033
root=Path('/data/researcher/jev-defense-four-gpu-20261106/remaining-full-history-gui-20261110-33/worker/requests')
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def project_messages(messages):
 result=copy.deepcopy(messages)
 for message in result:
  if not isinstance(message.get('content'),list):continue
  for block in message['content']:
   if block.get('type')!='image_url':continue
   value=block['image_url']['url'];prefix,encoded=value.split(',',1)
   assert prefix.startswith('data:image/')
   raw=base64.b64decode(encoded,validate=True)
   block['image_url']={'SHA256_REPLACED_DATA_URL':hashlib.sha256(raw).hexdigest(),'original_bytes':len(raw)}
 return result
rows=[]
for ident,target in sorted(TARGETS.items()):
 p=root/ident
 assert sha(p/'seal.json')==target['request_seal_sha256']
 files=json.loads((p/'seal.json').read_bytes())
 for name in ['payload.json','external-wire.json','raw-output.txt']:
  assert sha(p/name)==files[name],name
 rawpayload=(p/'payload.json').read_bytes();payload=json.loads(rawpayload)
 assert hashlib.sha256(canonical(payload)).hexdigest()==target['payload_sha256']
 assert sha(p/'external-wire.json')==target['wire_sha256']
 assert json.loads((p/'external-wire.json').read_bytes())['payload']==payload
 assert payload['operation']=='judge'
 view=payload['view'];images=[]
 for index,image in enumerate(view['images']):
  raw=base64.b64decode(image['raw_base64'],validate=True)
  images.append({'index':index,'role':image['role'],'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
 plain={k:v for k,v in view.items()if k not in ['messages','images']}
 texts=[]
 for index,message in enumerate(view['messages']):
  blocks=message['content'];blocks=[{'type':'text','text':blocks}]if isinstance(blocks,str)else blocks
  for bi,block in enumerate(blocks):
   if block.get('type')=='text':texts.append({'message_index':index,'block_index':bi,'role':message['role'],'text':block['text']})
 rows.append({'request':ident,'request_seal_sha256':target['request_seal_sha256'],
  'original_payload_file_sha256':files['payload.json'],'canonical_payload_sha256':target['payload_sha256'],
  'original_wire_sha256':target['wire_sha256'],'original_raw_output_sha256':files['raw-output.txt'],
  'actual_system':payload['system'],'actual_system_utf8_sha256':hashlib.sha256(payload['system'].encode()).hexdigest(),
  'actual_candidate':payload['candidate'],'actual_view_metadata':plain,
  'actual_public_messages_canonical_sha256':hashlib.sha256(canonical(view['messages'])).hexdigest(),
  'public_message_projection':project_messages(view['messages']),
  'complete_public_text_blocks':texts,'supplied_image_inventory':images,
  'raw_output':(p/'raw-output.txt').read_text(encoding='utf8'),
  'projection_hash_replaces_images_not_a_full_wirebody_export':True})
print(json.dumps({'time':time.time(),'UID':os.getuid(),'rows':rows,
 'read_only_original_source_export':True,'new_model_GUI_capture_action_scorer_paid_calls':0,
 'full_tensor_binaries_and_native_decode_not_rehashed_or_reexecuted':True},ensure_ascii=False))
'''
    compile(code, 'read-five-completed-checker-source-requests', 'exec')
    raw, operation = remote('3090', code, 'five-completed-checker-entailment-sources-readonly', timeout=55)
    actual = json.loads(raw)
    assert {row['request'] for row in actual['rows']} == wanted
    save(out / 'actual-original-source-projection.json', dict(actual, remote_operation=str(operation)))
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    result = dict(root=str(out), native_bindings_sha256=sha(out / 'prior-native-bindings.json'),
        actual_projection_sha256=sha(out / 'actual-original-source-projection.json'),
        seal_sha256=sha(out / 'seal.json'), original_checker_requests=5,
        new_model_GUI_capture_action_scorer_paid_calls=0)
    save(HERE / 'collected.json', result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf8')
    main()
