"""Read-only binding of original candidate11 to its first linked execution."""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
R37 = BASE / 'remaining29-full-history-gui-20261110-37'
sys.path.insert(0, str(R37))
spec = importlib.util.spec_from_file_location('companion_readonly_transport', R37 / 'orchestrate.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
remote, save, sha = transport.remote, transport.save, transport.sha


def verify_seal(folder, expected=None):
    if expected is not None:
        assert sha(folder / 'seal.json') == expected
    for name, digest in json.loads((folder / 'seal.json').read_bytes()).items():
        path = folder / name
        assert path.resolve().is_relative_to(folder.resolve())
        assert sha(path) == digest, str(path)


def main():
    assert not (HERE / 'pending11-collected.json').exists()
    ledger_root = BASE / 'prefill-scheduled-full-history-gui-20261109-32'
    pointer = json.loads((ledger_root / 'first38-consolidated-source-ledger-created.json').read_bytes())
    folder = Path(pointer['root'])
    verify_seal(folder, pointer['seal_sha256'])
    assert sha(folder / 'ledger.json') == pointer['ledger_sha256']
    ledger = json.loads((folder / 'ledger.json').read_bytes())
    source = ledger['rows'][10]
    assert source['original_unique_actor_candidate_ordinal'] == 11
    assert source['candidate_id'] == '72c626fc0b56c87d5e21a967e453d54d7579ffc62f6b97f5de838f59b3700369'
    authority = source['review_authority']
    reviewpath = Path(authority['path'])
    verify_seal(reviewpath.parent, authority['seal_sha256'])
    assert sha(reviewpath) == authority['sha256']
    packetpath = Path(source['source_packet_path'])
    assert sha(packetpath) == source['source_packet_sha256']
    packet = json.loads(packetpath.read_bytes())
    assert packet['candidate_event_sha256'] == source['candidate_id']
    text = packet['candidate']
    assert text == '<action>{"type":"scroll","direction":"down"}</action>'
    canonical = lambda v: json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    assert hashlib.sha256(canonical(packet['actual_actor_request'])).hexdigest() == source['source_actual_actor_body_sha256']
    targets = dict(source_attempt=source['source_attempt'], source_candidate_seq=source['source_candidate_event_seq'],
        source_event_sha256=source['candidate_id'], source_body_sha256=source['source_actual_actor_body_sha256'],
        text=text, text_sha256=source['source_candidate_text_sha256'])
    code = 'TARGET=' + repr(targets) + '\n' + transport.COMMON + r'''
import base64
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def chain(path):
 raw=path.read_bytes();assert raw.endswith(b'\n')
 events=[];previous='0'*64
 for line in raw.splitlines():
  row=json.loads(line);value=dict(row);signature=value.pop('sha256')
  assert value['seq']==len(events)and value['previous']==previous
  assert hashlib.sha256(canonical(value)).hexdigest()==signature
  events.append(row);previous=signature
 return events,{'path':str(path),'events':len(events),'head':previous,'full_file_sha256':hashlib.sha256(raw).hexdigest()}
assert os.getuid()==1015
original=Path(TARGET['source_attempt']);old,oldchain=chain(original/'events.jsonl')
candidate=old[TARGET['source_candidate_seq']]
assert candidate['kind']=='candidate'and candidate['sha256']==TARGET['source_event_sha256']
assert candidate['data']['text']==TARGET['text']
base=Path('/data/researcher/jev-defense-four-gpu-20261106')
linked=base/'memory-scheduled-full-history-gui-20261109-29'
attempts=sorted((linked/'batch/runs/fullhistory23-T000-clean-noaux').glob('attempt-*'));assert len(attempts)==1
attempt=attempts[0];events,linkedchain=chain(attempt/'events.jsonl')
package=linked
checkpoint=package/'carryover/checkpoint/0043/payload.json'
if not checkpoint.exists():
 package=Path('/data/researcher/jev-defense-four-gpu-20261106/memory-scheduled-full-history-gui-20261109-29')
 checkpoint=package/'carryover/checkpoint/0043/payload.json'
payload=json.loads(checkpoint.read_bytes())
body=payload['body'];assert hashlib.sha256(canonical(body)).hexdigest()==TARGET['source_body_sha256']
reply=json.loads((package/'carryover/checkpoint/0043/response.json').read_bytes());assert reply['text']==TARGET['text']
state=json.loads((package/'carryover/state.json').read_bytes())
assert state['pending_candidate_event_sha256']==TARGET['source_event_sha256']
cached=[e for e in events if e['kind']=='carryover_replay_candidate'and e['data']['text']==TARGET['text']]
accepted=[e for e in events if e['kind']in['decision_accepted','carryover_replay_decision_accepted']and e['data'].get('candidate')==TARGET['text']and e['data']['observation_id']=='011-obs011']
assert len(cached)==len(accepted)==1
verdict=accepted[0];assert verdict['data']['proposal']['payload']=={'type':'scroll','direction':'down'}
executed=[e for e in events if e['kind']=='action_executed'and e['data']['observation_id']==verdict['data']['observation_id']]
assert len(executed)==1 and executed[0]['data']['proposal']==verdict['data']['proposal']
feedback=json.loads(executed[0]['data']['feedback']);assert feedback['execution_returned']and not feedback['error']
bindings=[e for e in events if e['kind']=='cached_pending_decision_source_binding'];assert len(bindings)==1
assert bindings[0]['data']['original_candidate_event_sha256']==TARGET['source_event_sha256']
returned=[e for e in events if e['kind']=='cached_pending_decision_accepted_for_first_execution'];assert len(returned)==1
assert returned[0]['data']['actor_total_spent']==11 and returned[0]['data']['judge_total_spent_including_original_OOM']==34
assert returned[0]['data']['new_model_calls']==0 and returned[0]['data']['pending_action_executed']is False
retained=[e for e in events if e['kind']=='accepted_actor_history_retained'and e['data']['accepted_observation_id']=='011-obs011'];assert len(retained)==1
assert retained[0]['data']['actual_actor_body_sha256']==TARGET['source_body_sha256']
assert cached[0]['seq']<verdict['seq']<retained[0]['seq']<executed[0]['seq']
restoration=json.loads((attempt/'native-restoration-receipt.json').read_bytes());assert restoration['pixel_identity_passed']
assert restoration['pending_action_executed']is False and restoration['original_ten_actor_actions_reexecuted']is False
capture=attempt/'screenshots/012-captured.png';assert capture.is_file()
print(json.dumps({'time':time.time(),'source_candidate_event':candidate,'source_chain':oldchain,
 'linked_chain':linkedchain,'linked_attempt':str(attempt),'cached_event':cached[0],'source_binding_event':bindings[0],
 'accepted_event':verdict,'retained_event':retained[0],'execution_event':executed[0],'returned_event':returned[0],
 'cached_body_sha256':TARGET['source_body_sha256'],'cached_body_file_sha256':sha(checkpoint),
 'restoration':restoration,'restoration_receipt_sha256':sha(attempt/'native-restoration-receipt.json'),
 'next_capture_sha256':sha(capture),'next_capture_base64':base64.b64encode(capture.read_bytes()).decode(),
 'remote_read_only':True,'new_model_GUI_capture_action_scorer_paid_calls':0},ensure_ascii=False))
'''
    compile(code, 'companion-pending11-readonly', 'exec')
    output, operation = remote('4090', code, 'companion-bind-original11-first-linked-execution-readonly', timeout=55)
    data = json.loads(output)
    out = HERE / ('pending11-first-execution-' + str(time.time_ns()))
    out.mkdir()
    raw = base64.b64decode(data.pop('next_capture_base64'), validate=True)
    (out / '012-original-after-execution.png').write_bytes(raw)
    assert sha(out / '012-original-after-execution.png') == data['next_capture_sha256']
    save(out / 'execution-evidence.json', dict(data, operation=str(operation)))
    save(out / 'join.json', dict(schema='original11-first-linked-execution-downstream-join-v1',
        time=time.time(), candidate_event_sha256=source['candidate_id'], original_ordinal=11,
        source_review=str(reviewpath), source_review_sha256=sha(reviewpath), source_label=source['original_label'],
        source_packet=str(packetpath), source_packet_sha256=sha(packetpath),
        exact_original_full_actor_body_sha256=source['source_actual_actor_body_sha256'],
        accepted=True, executed=True, accepted_event_sha256=data['accepted_event']['sha256'],
        execution_event_sha256=data['execution_event']['sha256'],
        original_label_unchanged=True, same_original_candidate_not_a_new_model_sample=True,
        old_original23_not_executed_first_executed_in_linked29=True,
        execution_evidence_sha256=sha(out / 'execution-evidence.json'),
        new_model_GUI_capture_action_scorer_paid_calls=0, efficacy_established=False))
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    pointer = dict(root=str(out), join_sha256=sha(out / 'join.json'), seal_sha256=sha(out / 'seal.json'))
    save(HERE / 'pending11-collected.json', pointer)
    print(json.dumps(pointer))


if __name__ == '__main__':
    main()
