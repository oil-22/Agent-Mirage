"""Reuse sealed native audits; copy small immutable metadata for all31 reads."""
from collections import defaultdict
import base64
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
spec = importlib.util.spec_from_file_location('auxiliary_stability_readonly_transport', R37 / 'orchestrate.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
remote, save, sha = transport.remote, transport.save, transport.sha


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def verify_seal(folder, expected=None):
    if expected is not None:
        assert sha(folder / 'seal.json') == expected
    for name, expected_sha in json.loads((folder / 'seal.json').read_bytes()).items():
        path = folder / name
        assert path.resolve().is_relative_to(folder.resolve())
        assert sha(path) == expected_sha, str(path)


def main():
    assert not (HERE / 'collected.json').exists()
    panelroot = BASE / 'four-terminal-companion-audit-20261110-41/companion-panel-1794309959999151600'
    verify_seal(panelroot, '8891b39238dd037ddb31e30e40a7431128850f5cf7b2f71a8d001550f7b66a66')
    panel = json.loads((panelroot / 'panel.json').read_bytes())
    bindings, reports, insertions, locations = {}, {}, {}, {}
    authorities = {}
    for pointerpath in sorted(R33.glob('mixed-receipt-audit-created-*.json')):
        pointer = json.loads(pointerpath.read_bytes())
        folder = Path(pointer['root'])
        receipt = json.loads((folder / 'receipt.json').read_bytes())
        if not receipt['passed']:
            continue
        verify_seal(folder, pointer['seal_sha256'])
        assert sha(folder / 'receipt.json') == pointer['receipt_sha256']
        native = json.loads((folder / '3090-native-bindings.json').read_bytes())
        gui = json.loads((folder / '4090-GUI-bindings.json').read_bytes())
        assert native['passed'] and gui['passed']
        assert not native['CUDA_initialized'] and not native['model_weights_loaded'] and not native['runtime_modified']
        authorities[str(folder)] = dict(receipt_sha256=pointer['receipt_sha256'], seal_sha256=pointer['seal_sha256'])
        bindings.update(native['bindings'])
        for report in native['reports']:
            if report['request'] in reports:
                assert report['request_seal_sha256'] == reports[report['request']]['request_seal_sha256']
            reports[report['request']] = report
            locations[report['request']] = str(folder)
        for insertion in gui['actor_insertions']:
            insertions[insertion['request']] = insertion
    assert len([r for r in reports.values() if r['operation'] == 'evidence']) == 31
    sources = []
    used = set()
    for row in panel['candidate_rows']:
        if not row['run_id'].endswith('-aux'):
            continue
        packetpath = Path(row['source_packet'])
        assert sha(packetpath) == row['source_packet_sha256']
        packet = json.loads(packetpath.read_bytes())
        body = packet['actual_actor_request']
        assert hashlib.sha256(canonical(body)).hexdigest() == row['actor_request_body_sha256']
        payloadsha = hashlib.sha256(canonical(dict(operation='actor', body=body))).hexdigest()
        actorids = [ident for ident, value in bindings.items() if value['payload_sha256'] == payloadsha]
        assert len(actorids) == 1
        actorid = actorids[0]
        assert bindings[actorid]['response']['text'] == row['candidate_text']
        insertion = insertions[actorid]
        assert insertion['auxiliary_actual_HTTP_linked'] and insertion['all_original_messages_images_trailing_corrections_and_body_parameters_retained']
        auxid = insertion['preceding_auxiliary_request']
        assert auxid not in used
        used.add(auxid)
        assert reports[auxid]['operation'] == 'evidence'
        proof = reports[auxid]['native_proof']
        assert proof['single_complete_image_and_fixed_prompt_bound']
        assert proof['all_prepared_first_forward_tensors_and_actual_native_IDs_bound']
        assert proof['actual_first_cache_length'] == 0 and proof['all_observed_cache_objects_released']
        message = next(m for m in reversed(body['messages']) if m.get('role') == 'user' and
            isinstance(m.get('content'), list) and any(b.get('type') == 'image_url' for b in m['content']))
        textblocks = [b['text'] for b in message['content'] if b.get('type') == 'text' and
                      b['text'].startswith('IMAGE-ONLY EVIDENCE PACKET')]
        assert len(textblocks) == 1
        observer = json.loads(textblocks[0][textblocks[0].index('{"policy":'):])
        response = bindings[auxid]['response']['evidence_response']
        assert hashlib.sha256(response['raw_output'].encode()).hexdigest() == observer['raw_output_sha256']
        assert observer['status'] == 'available_fallible_reading' and not observer['automatic_allow_or_block']
        assert proof['image_sha256'] == observer['image_sha256'] == packet['current_and_reference_image_inventory'][0]['sha256']
        assert proof['request_sha256'] == bindings[auxid]['payload_sha256']
        sources.append(dict(candidate_event_sha256=row['candidate_event_sha256'], candidate_id=row['candidate_id'],
            run_id=row['run_id'], candidate_text=row['candidate_text'], original_primary_semantic_label=row['primary_semantic_label'],
            original_label_unchanged=True, accepted=row['accepted'], environment_executed=row['environment_executed'],
            source_packet=str(packetpath), source_packet_sha256=sha(packetpath),
            actor_request=actorid, auxiliary_request=auxid, observer_packet=observer,
            expected_auxiliary_seal_sha256=reports[auxid]['request_seal_sha256'],
            actual_native_proof_reused=proof, native_proof_authority=locations[auxid],
            actual_Controller_actor_insertion_reused=insertion, actual_HTTP_binding_reused=bindings[auxid]))
    assert len(sources) == len(used) == 31
    out = HERE / ('delivery-identity-' + str(time.time_ns()))
    out.mkdir()
    save(out / 'sealed-source-and-native-index.json', dict(time=time.time(), rows=sources,
        native_audit_authorities=authorities, original_primary_labels_unchanged=True,
        no_new_semantic_labels_or_calls=True, full_tensor_hash_and_native_decode_proofs_reused_not_rerun=True))
    targets = [dict(request=r['auxiliary_request'], seal_sha256=r['expected_auxiliary_seal_sha256'],
                   payload_sha256=r['actual_native_proof_reused']['request_sha256'],
                   raw_output_sha256=r['observer_packet']['raw_output_sha256']) for r in sources]
    code = 'TARGETS=' + repr(targets) + '\n' + transport.COMMON + r'''
import base64,struct
assert os.getuid()==1033
root=Path('/data/researcher/jev-defense-four-gpu-20261106/remaining-full-history-gui-20261110-33/worker/requests')
names=['prepared.json','first-forward.json','effective-generation.json','actual-generation.json',
 'stateless-input-boundary.json','stateless-context-discarded.json','unicode-length-guard.json','raw-UTF8-validation.json']
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
rows=[]
for target in TARGETS:
 p=root/target['request'];assert sha(p/'seal.json')==target['seal_sha256'];files=json.loads((p/'seal.json').read_bytes())
 for name in names+['payload.json','raw-output.txt','sequence_ids.json','original.png']:
  assert sha(p/name)==files[name],name
 payload=json.loads((p/'payload.json').read_bytes())
 assert set(payload)=={'policy','model','revision','image_base64','image_sha256','original_size','prompt','prompt_sha256'}
 assert hashlib.sha256(canonical(payload)).hexdigest()==target['payload_sha256']
 rawimage=(p/'original.png').read_bytes();assert base64.b64decode(payload['image_base64'],validate=True)==rawimage
 assert hashlib.sha256(rawimage).hexdigest()==payload['image_sha256']
 assert hashlib.sha256(payload['prompt'].encode()).hexdigest()==payload['prompt_sha256']
 values={name:json.loads((p/name).read_bytes())for name in names}
 prepared=values['prepared.json'];first=values['first-forward.json'];actual=values['actual-generation.json']
 assert set(prepared)==set(first)and{'input_ids','pixel_values','image_grid_thw'}<=set(prepared)
 for key in prepared:assert all(prepared[key][field]==first[key][field]for field in['shape','dtype','bytes','sha256'])
 seq=json.loads((p/'sequence_ids.json').read_bytes());assert len(seq)==1
 prefix=seq[0][:actual['input_tokens']];output=seq[0][actual['input_tokens']:]
 assert hashlib.sha256(struct.pack('<'+'q'*len(prefix),*prefix)).hexdigest()==first['input_ids']['sha256']
 assert output==actual['output_ids']and len(output)==actual['output_tokens']
 text=(p/'raw-output.txt').read_text(encoding='utf8');assert hashlib.sha256(text.encode()).hexdigest()==target['raw_output_sha256']
 boundary=values['stateless-input-boundary.json'];discarded=values['stateless-context-discarded.json']
 assert boundary['call_id']==discarded['call_id']and boundary['message_count']==1
 assert boundary['task_history_candidate_previous_auxiliary_content_supplied']is False
 assert discarded['actual_first_forward_cache_length']==0 and discarded['all_observed_cache_objects_released']
 assert boundary['complete_image_sha256']==payload['image_sha256']and boundary['fixed_prompt_sha256']==payload['prompt_sha256']
 rows.append({'request':target['request'],'request_seal_sha256':target['seal_sha256'],
  'model':payload['model'],'revision':payload['revision'],'image_sha256':payload['image_sha256'],
  'prompt_sha256':payload['prompt_sha256'],'payload_sha256':target['payload_sha256'],
  'raw_output':text,'raw_output_sha256':target['raw_output_sha256'],'metadata':values,
  'native_input_IDs_SHA_from_actual_returned_sequence':first['input_ids']['sha256'],
  'native_output_IDs_SHA':hashlib.sha256(struct.pack('<'+'q'*len(output),*output)).hexdigest(),
  'metadata_original_file_SHA_bound':{name:files[name]for name in names+['raw-output.txt','sequence_ids.json','payload.json','original.png']},
  'original_full_tensor_binary_audit_reused_not_freshly_rehashed':True,
  'no_current_GPU_tensor_or_unmasked_probability_verification_claim':True})
print(json.dumps({'time':time.time(),'uid':os.getuid(),'rows':rows,'remote_read_only':True,
 'new_model_GUI_capture_action_scorer_paid_calls':0,'no_tensor_binary_weight_hash_or_generation_repeated':True},ensure_ascii=False))
'''
    compile(code, 'read31-small-original-auxiliary-metadata-only', 'exec')
    output, operation = remote('3090', code, 'auxiliary31-fixed-input-stability-original-metadata-readonly', timeout=55)
    value = json.loads(output)
    assert len(value['rows']) == 31
    save(out / 'actual-original-metadata.json', dict(value, operation=str(operation)))
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    result = dict(root=str(out), source_index_sha256=sha(out / 'sealed-source-and-native-index.json'),
        actual_metadata_sha256=sha(out / 'actual-original-metadata.json'), seal_sha256=sha(out / 'seal.json'),
        actual_original_calls=31, new_model_GUI_calls=0)
    save(HERE / 'collected.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
