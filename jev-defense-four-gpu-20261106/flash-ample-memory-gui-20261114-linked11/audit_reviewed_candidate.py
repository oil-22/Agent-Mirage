"""Join an already sealed source review to actual native tensors and execution.

Read-only, one request at a time. Never supplies private evaluation provenance to
the checker/actor and never reruns a model, screenshot, action, or old terminal.
"""
import ast
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from control import HERE, OUT, R3090, R4090, remote, save, sha
from capture_live_evidence import COMMON

packets, number, review_dir = Path(sys.argv[1]), int(sys.argv[2]), Path(sys.argv[3])
assert packets.resolve().is_relative_to(HERE.resolve()) and review_dir.resolve().is_relative_to(HERE.resolve())
for root in [packets, review_dir]:
    for name, expected in json.loads((root / 'seal.json').read_bytes()).items():
        assert sha(root / name) == expected
packet_path = packets / ('packets/p%05d.json' % number)
packet = json.loads(packet_path.read_bytes())
review = json.loads((review_dir / 'review.json').read_bytes())
label = next(row for row in review['rows'] if row.get('candidate') == number)
assert label['packet_sha256'] == sha(packet_path) and label['source_response_sha256'] == packet['source_response_sha256']
binding = next(row for row in json.loads((packets / 'PRIVATE-source-index.json').read_bytes()) if row['packet_id'] == packet['packet_id'])
assert binding['source_directory'].startswith(OUT + '/primary/requests/')
name = binding['source_directory'].rsplit('/', 1)[1]
assert re.fullmatch(r'\d{5}', name)
dest = HERE / ('reviewed-candidate-actual-audit-' + str(time.time_ns()))
dest.mkdir()
save(dest / 'review-before-join.json', {
    'review': str(review_dir), 'review_sha256': sha(review_dir / 'review.json'),
    'review_seal_sha256': sha(review_dir / 'seal.json'), 'review_row': label,
    'source_packet': str(packet_path), 'source_packet_sha256': sha(packet_path),
    'semantic_judgment_changed_by_join': False, 'time': time.time()})
code = ('ROOT=' + repr(R4090) + '\nRUN_ID=' + repr(binding['run_id']) + '\n'
        'STEP=' + repr(binding['decision_index']) + '\nREQUEST_ID=' + repr(binding['request_id']) + '\n' + COMMON + r'''
attempts=list((Path(ROOT)/'batch/runs'/RUN_ID).glob('attempt-*'));assert len(attempts)==1
a=attempts[0];proof,rows=chain(a/'controller/events.jsonl')
requests=[v['data']for v in rows if v['kind']=='actual_actor_request'];forwards=[v['data']for v in rows if v['kind']=='main_image_forwarded']
request=requests[STEP-1];frame=forwards[STEP-1];assert request['request_id']==REQUEST_ID
reply=next(v['data']for v in rows if v['kind']=='actual_actor_reply'and v['data']['request_id']==REQUEST_ID)
action=next((v['data']for v in rows if v['kind']=='native_environment_action'and v['data']['step']==STEP),None)
ledger=next(v['data']for v in rows if v['kind']=='PRIVATE_delivery_ledger'and v['data']['step']==STEP)
gate=next((v['data']for v in rows if v['kind']=='gate_decision'and v['data']['request_id']==frame['gate_request_id']),None)
print(json.dumps({'time':time.time(),'run_id':RUN_ID,'step':STEP,'attempt':str(a),'chain':proof,'request':request,'reply':reply,'forwarded_frame':frame,'actual_native_action':action,'gate':gate,'delivery_provenance_post_review_only':ledger,'new_model_GUI_calls':0}))
''')
raw, operation = remote('4090', code, 'reviewed-candidate-GUI-execution-join')
gui = json.loads(raw)
save(dest / '4090.json', {'result': gui, 'operation': str(operation)})
gate_id = gui['forwarded_frame']['gate_request_id']
if gate_id:
    assert re.fullmatch(r'[0-9a-f]{32}', gate_id)
tree = ast.parse((HERE / 'capture_live_evidence.py').read_text(encoding='utf8'))
strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
sources = [v for v in strings if v.startswith('\nimport subprocess\np=Path(PACKAGE);')]
assert len(sources) == 1
source = sources[0]
old_main = "for d in sorted((r/'primary/requests').iterdir()):"
old_flash = "for d in sorted((p/'flash/service/requests').iterdir()):"
assert source.count(old_main) == source.count(old_flash) == 1
source = source.replace(old_main, "for d in [r/'primary/requests'/REQUEST_NAME]:")
source = source.replace(old_flash, "for d in ([p/'flash/service/requests'/GATE_ID]if GATE_ID else []):")
code = ('PACKAGE=' + repr(R3090) + '\nOUTPUT=' + repr(OUT) + '\n'
        'REQUEST_NAME=' + repr(name) + '\nGATE_ID=' + repr(gate_id) + '\n' + COMMON + source)
raw, operation = remote('3090', code, 'reviewed-candidate-full-native-input-audit', timeout=55)
main = json.loads(raw)
assert len(main['sealed_main_requests']) == 1
actual = main['sealed_main_requests'][0]
assert actual['seal_sha256'] == packet['source_request_seal_sha256']
assert actual['wire_sha256'] == packet['source_wire_sha256']
assert actual['native_text'] == packet['candidate_exact_text']
assert actual['body_sha256'] == gui['request']['body_sha256']
assert actual['current_image_sha256'] == gui['forwarded_frame']['image_sha256']
assert hashlib.sha256(actual['native_text'].encode()).hexdigest() == gui['reply']['text_sha256']
if gate_id:
    assert len(main['sealed_Flash_requests']) == 1
    flash = main['sealed_Flash_requests'][0]
    assert flash['request_id'] == gate_id and flash['decision'] == 'YES'
    assert flash['image_sha256'] == actual['current_image_sha256']
    assert gui['gate']['decision'] == 'YES'
else:
    flash = None
save(dest / '3090.json', {'result': main, 'operation': str(operation)})
summary = {'source_review': str(review_dir), 'source_review_sha256': sha(review_dir / 'review.json'),
           'source_packets': str(packets), 'run_id': binding['run_id'], 'candidate': number,
           'candidate_semantic_Mirage': label['candidate_semantic_Mirage'],
           'actual_full_native_tensors_request_reply_EOS_seal_verified': True,
           'actual_Flash_independent_input_verified': flash is not None,
           'Flash_decision': flash['decision'] if flash else None,
           'same_original_PNG_forwarded': True, 'actual_native_action': gui['actual_native_action'],
           'semantic_review_sealed_before_this_join': True,
           'not_a_rate_or_efficacy_estimate': True, 'new_model_GUI_calls': 0}
save(dest / 'summary.json', summary)
save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
print(json.dumps({'audit': str(dest), **summary}))
