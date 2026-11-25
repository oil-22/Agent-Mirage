"""Finalize original29 controller/native bindings only after the fresh postexit audit.

This reads sealed experimental evidence. It cannot launch a model, retry a
request, take a screenshot, execute a GUI action, or change experimental inputs.
"""
import argparse
import ast
import hashlib
import json
import re
import time
from pathlib import Path
from control import HERE, OUT, R4090, remote, save, sha
from capture_live_evidence import COMMON
from finalize_GUI_postexit_evidence import admission


GUI_READER = r'''
r=Path(ROOT);plan=json.loads((r/'plan.json').read_bytes());controllers=[]
for terminal_path in sorted((r/'batch/runs').glob('*/attempt-*/terminal.json')):
 a=terminal_path.parent;t=json.loads(terminal_path.read_bytes());seal=json.loads((a/'seal.json').read_bytes())
 assert sha(terminal_path)==seal['terminal.json']
 assert sha(a/'controller/events.jsonl')==seal['controller/events.jsonl']
 proof,events=chain(a/'controller/events.jsonl');assert not proof['ignored_partial_last_line']
 captures=[v for v in events if v['kind']=='capture']
 for event in captures:
  h=event['data']['image_sha256']
  if h is not None:assert sha(a/'controller'/(h+'.png'))==h
 ledgers=[v for v in events if v['kind']=='PRIVATE_delivery_ledger']
 for event in ledgers:
  row=event['data'];n=row['step']
  assert sha(a/('%03d-actually-captured.png'%n))==row['captured_sha256']
  assert sha(a/('%03d-initial-delivered.png'%n))==row['delivered_sha256']
 controllers.append({'attempt':str(a),'terminal':t,'terminal_sha256':sha(terminal_path),
                     'seal_sha256':sha(a/'seal.json'),'chain':proof,'events':events})
assert len(controllers)==29 and {v['terminal']['run']['run_id']for v in controllers}=={v['run_id']for v in plan['queue']}
print(json.dumps({'time':time.time(),'controllers':controllers,'new_model_GPU_GUI_calls':0}))
'''


def load(path):
    return json.loads(path.read_bytes())


def parse_original():
    source = HERE / 'package/native-parser-source.py'
    tree = ast.parse(source.read_text(encoding='utf8'))
    selected = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'parse')
    namespace = {'json': json, 're': re}
    exec(compile(ast.Module(body=[selected], type_ignores=[]), str(source) + ':parse', 'exec'), namespace)
    return namespace['parse']


def check_controller(controller, mains, flashes, terminal_binding, parse):
    terminal = controller['terminal']
    run = terminal['run']['run_id']
    assert not terminal['infrastructure_failure'] and terminal['cleanup_error'] is None
    assert controller['terminal_sha256'] == terminal_binding['terminal_sha256']
    assert controller['seal_sha256'] == terminal_binding['seal_sha256']
    assert controller['chain']['head'] == terminal_binding['event_chain_head']
    assert controller['chain']['verified_prefix_events'] == terminal_binding['event_chain_count']
    events = controller['events']
    select = lambda kind: [v for v in events if v['kind'] == kind]
    requests, replies, forwards = select('actual_actor_request'), select('actual_actor_reply'), select('main_image_forwarded')
    count = terminal['actor_calls']
    assert len(requests) == len(replies) == len(forwards) == len(terminal['actor_receipts']) == count
    assert count == terminal['decisions'] and 1 <= count <= 50
    assert len(select('native_environment_action')) == terminal['environment_actions']
    actions = {v['data']['step']: v for v in select('native_environment_action')}
    assert len(actions) == terminal['environment_actions']
    captured = {v['data']['capture_id']: v for v in select('capture')}
    assert len(captured) == len(select('capture'))
    gates = select('gate_decision')
    assert len(gates) == terminal['Flash_request_attempts'] == len(terminal['Flash_replies'])
    assert len(select('recapture_requested')) == terminal['recaptures']
    assert bool(gates) == terminal['run']['gate_enabled']
    for event, receipt in zip(gates, terminal['Flash_replies']):
        gate = event['data'];actual = flashes[gate['request_id']]
        assert gate['request_id'] == receipt['request_id']
        assert gate['decision'] == receipt['decision'] == actual['decision']
        assert gate['image_sha256'] == receipt['image_sha256'] == actual['image_sha256']
        assert captured[gate['capture_id']]['data']['image_sha256'] == gate['image_sha256']
        assert captured[gate['capture_id']]['seq'] < event['seq']
    if terminal['run']['gate_enabled']:
        accepted = select('gate_terminal')
        assert len(accepted) == count and all(v['data']['status'] == 'accepted' for v in accepted)
        assert sum(v['data']['model_calls'] for v in accepted) == len(gates)
        assert sum(v['data']['recaptures'] for v in accepted) == terminal['recaptures']
    else:
        assert not gates and not select('gate_terminal') and len(select('no_gate_control')) == count
    dispatched = select('native_proposal_dispatched')
    used_dispatches, native_ids, gate_ids, rows = set(), [], [v['data']['request_id'] for v in gates], []
    for number, (request_event, reply_event, forward_event, transport) in enumerate(
            zip(requests, replies, forwards, terminal['actor_receipts']), 1):
        request, reply, frame = request_event['data'], reply_event['data'], forward_event['data']
        rid = request['request_id'];native = mains[rid]
        assert native['run_id'] == run and native['decision'] == number
        assert native['request_id'] == reply['request_id'] == transport['request_id']
        assert native['folder'] == reply['receipt'] == transport['receipt']
        assert native['wire_sha256'] == transport['wire_sha256']
        assert request['body_sha256'] == native['body_sha256']
        assert reply['text_sha256'] == hashlib.sha256(native['native_text'].encode()).hexdigest()
        assert native['actual_tensor_files_verified'] and native['natural_EOS']
        assert native['current_image_sha256'] == frame['image_sha256']
        assert frame['extra_auxiliary_text_in_main_prompt'] is False
        capture = captured[frame['capture_id']]
        assert capture['data']['image_sha256'] == frame['image_sha256']
        assert capture['seq'] < forward_event['seq'] < request_event['seq'] < reply_event['seq']
        if terminal['run']['gate_enabled']:
            gate = next(v for v in gates if v['data']['request_id'] == frame['gate_request_id'])
            assert gate['data']['decision'] == 'YES' and gate['data']['capture_id'] == frame['capture_id']
            assert gate['seq'] < forward_event['seq']
            end = next(v for v in accepted if v['data']['last_capture_id'] == frame['capture_id'])
            assert end['data']['last_image_sha256'] == frame['image_sha256']
            assert gate['seq'] < end['seq'] < forward_event['seq']
        else:
            assert frame['gate_request_id'] is None
        next_request_seq = requests[number]['seq'] if number < count else len(events)
        matching = [v for v in dispatched if reply_event['seq'] < v['seq'] < next_request_seq]
        assert len(matching) <= 1
        action = actions.get(number)
        if matching:
            dispatch = matching[0]
            assert dispatch['data']['candidate_sha256'] == reply['text_sha256']
            assert dispatch['data']['proposal_unmodified'] is True
            assert dispatch['data']['capture_id'] == frame['capture_id']
            assert dispatch['data']['image_sha256'] == frame['image_sha256']
            payload = parse(native['native_text'])
            if payload['type'] == 'stop':
                assert action is None and number == count and terminal['outcome'] == 'model_stop'
                assert dispatch['data']['environment_action'] is False
            else:
                assert action is not None and action['data']['payload'] == payload
                assert action['data']['ok'] is True and dispatch['data']['environment_action'] is True
                assert reply_event['seq'] < action['seq'] < dispatch['seq']
            used_dispatches.add(dispatch['seq'])
        else:
            assert number == count and terminal['outcome'] == 'native_contract_failure' and action is None
            failures = [v for v in select('native_actor_or_parser_failure') if reply_event['seq'] < v['seq']]
            assert len(failures) == 1 and failures[0]['data']['executed'] is False
        native_ids.append(rid)
        rows.append({'decision': number, 'request_id': rid, 'request_seal_sha256': native['seal_sha256'],
                     'gate_request_id': frame['gate_request_id'], 'image_sha256': frame['image_sha256'],
                     'actual_native_action': action['data'] if action else None,
                     'candidate_dispatched': bool(matching)})
    assert len(used_dispatches) == len(dispatched)
    return {'run_id': run, 'terminal_sha256': controller['terminal_sha256'], 'chain': controller['chain'],
            'actor_requests': native_ids, 'Flash_requests': gate_ids,
            'official_reward': terminal['official_reward'], 'outcome': terminal['outcome'],
            'rows': rows, 'semantic_Mirage_label': None, 'semantic_labels_not_inferred_from_score_or_dispatch': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--postexit-evidence', type=Path)
    args = parser.parse_args()
    compile(COMMON + GUI_READER, '<source-bound-controller-reader>', 'exec')
    original_parse = parse_original()
    if args.prepare_only:
        assert args.postexit_evidence is None
        dest = HERE / ('controller-finalization-preparation-' + str(time.time_ns()))
        dest.mkdir()
        (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
        save(dest / 'preparation.json', {'time': time.time(), 'compiled_only': True,
             'actual_postexit_binding_audit_executed': False, 'requires_fresh_all29_postexit_raw_audit': True,
             'runtime_sources_unchanged': True, 'new_model_GPU_GUI_calls': 0,
             'original_parser_source_sha256': sha(HERE / 'package/native-parser-source.py')})
        save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
        print(json.dumps({'preparation': str(dest), 'actual_final_audit_executed': False}))
        return
    assert args.postexit_evidence is not None
    source = args.postexit_evidence.resolve()
    assert source.parent == HERE and source.name.startswith('full-postexit-evidence-')
    assert all(sha(source / n) == h for n, h in load(source / 'seal.json').items())
    summary = load(source / 'summary.json')
    assert summary['terminal_count'] == 29 and summary['original_processes_exited']
    assert not (HERE / 'postexit-controller-bindings-current.json').exists()
    current = load(HERE / 'postexit-evidence-current.json')
    assert Path(current['root']) == source and current['seal_sha256'] == sha(source / 'seal.json')
    admitted_main, admitted_gui = admission('3090'), admission('4090')
    assert admitted_main['result']['postexit_seal_sha256'] == load(source / '3090-admission.json')['result']['postexit_seal_sha256']
    assert admitted_gui['result']['postexit_seal_sha256'] == load(source / '4090-admission.json')['result']['postexit_seal_sha256']
    raw, operation = remote('4090', 'ROOT=' + repr(R4090) + '\n' + COMMON + GUI_READER,
                            'postexit-all29-controller-bindings', timeout=55)
    gui = json.loads(raw)
    native = load(source / '3090.json')
    mains = {v['request_id']: v for v in native['sealed_main_requests']}
    flashes = {v['request_id']: v for v in native['sealed_Flash_requests']}
    assert len(mains) == summary['fresh_full_main_requests']
    assert len(flashes) == summary['fresh_full_Flash_requests']
    terminals = {v['run']['run_id']: v for v in load(source / 'terminal-audit.json')['result']['terminals']}
    rows = [check_controller(v, mains, flashes, terminals[v['terminal']['run']['run_id']], original_parse)
            for v in gui['controllers']]
    ids = [rid for row in rows for rid in row['actor_requests']]
    gates = [rid for row in rows for rid in row['Flash_requests']]
    assert len(ids) == len(set(ids)) == len(mains) and set(ids) == set(mains)
    assert len(gates) == len(set(gates)) == len(flashes) and set(gates) == set(flashes)
    dest = HERE / ('postexit-controller-bindings-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'GUI-collection.json', {'result': gui, 'operation': str(operation)})
    save(dest / 'binding-review.json', {'time': time.time(), 'source_postexit_raw_audit': str(source),
         'source_raw_audit_seal_sha256': sha(source / 'seal.json'), 'trajectories': rows,
         'normal29_actual_exits_rechecked': {'3090': admitted_main, '4090': admitted_gui},
         'all_actual_requests_replies_images_Flash_actions_and_native_parser_bound': True,
         'original_terminal_files_unchanged': True, 'semantic_completion_or_effectiveness_proven': False,
         'new_model_GPU_GUI_calls': 0, 'goal': 'active'})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    save(HERE / 'postexit-controller-bindings-current.json', {'root': str(dest),
         'seal_sha256': sha(dest / 'seal.json'), 'raw_postexit_evidence': str(source),
         'semantic_completion_or_effectiveness_proven': False, 'goal': 'active', 'time': time.time()})
    print(json.dumps({'bindings': str(dest), 'GUI_terminals': 29, 'main_requests': len(ids),
                      'Flash_requests': len(gates), 'effectiveness_proven': False, 'new_model_GPU_GUI_calls': 0}))


if __name__ == '__main__':
    main()
