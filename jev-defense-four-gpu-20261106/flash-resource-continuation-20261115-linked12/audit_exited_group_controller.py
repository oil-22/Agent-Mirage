"""Finalize one exited group's GUI/native bindings after its fresh full raw audit.

The technical parent remains technical. Its undelivered397th generation has a
separate branch and cannot become a public actor reply or executed action.
No all29 completion, semantic label or efficacy is inferred by this reader.
"""
import argparse
import json
import time
from pathlib import Path
from control import HERE, remote, save, sha
from capture_live_evidence import COMMON
from controller_audit_reader import GUI_READER, check_controller, parse_original
from audit_exited_group_raw import ADMISSION


def load(path):
    return json.loads(Path(path).read_bytes())


def verify(root):
    seal = load(root / 'seal.json')
    assert seal and all(sha(root / n) == h for n, h in seal.items())


def make_reader():
    original = "assert len(controllers)==29 and {v['terminal']['run']['run_id']for v in controllers}=={v['run_id']for v in plan['queue']}"
    assert GUI_READER.count(original) == 1
    source = GUI_READER.replace(original,
        "assert len(controllers)==len(EXPECTED_RUN_IDS)and{v['terminal']['run']['run_id']for v in controllers}==set(EXPECTED_RUN_IDS)")
    boundary = " a=terminal_path.parent;t=json.loads(terminal_path.read_bytes());seal=json.loads((a/'seal.json').read_bytes())"
    assert source.count(boundary) == 1
    source = source.replace(boundary, boundary + "\n for name,h in seal.items():assert sha(a/name)==h,name\n assert{str(f.relative_to(a))for f in a.rglob('*')if f.is_file()and f.name!='seal.json'}==set(seal)")
    prefix = r'''
r=Path(ROOT);assert os.getuid()==1015
assert sha(r/'manifest.json')==MANIFEST_SHA
for name,h in json.loads((r/'manifest.json').read_bytes())['files'].items():assert sha(r/name)==h,name
status=json.loads((r/'batch/status.json').read_bytes())
if GROUP=='parent':
 assert status['phase']=='technical_failure'and status['completed']==16 and status['processed']==17 and status['expected']==29
else:
 assert status['phase']=='completed'and status['completed']==status['processed']==status['expected']==13
assert json.loads((r/'control/exit.json').read_bytes())['child_exit']==0
processes=[]
for name in ['control/process.json','control/runner-process.json']:
 saved=json.loads((r/name).read_bytes());proc=Path('/proc',str(saved['pid']));actual=identity(saved['pid'])if proc.exists()else None
 same=actual is not None and actual['state']not in ['Z','X']and all(actual[k]==saved[k]for k in ['uid','command','start_ticks'])
 assert not same,'Group GUI is still live'
 processes.append({'saved':saved,'actual_if_PID_exists':actual,'same_live_process':False})
control_seal=json.loads((r/'control/postexit-seal.json').read_bytes())
assert{str(f.relative_to(r/'control'))for f in(r/'control').rglob('*')if f.is_file()and f.name!='postexit-seal.json'}==set(control_seal)
for name,h in control_seal.items():assert sha(r/'control'/name)==h,name
if GROUP=='parent':assert sha(r/'control/postexit-seal.json')==PARENT_CONTROL_SHA
'''
    source = source.replace("print(json.dumps({'time':time.time(),'controllers':controllers,'new_model_GPU_GUI_calls':0}))",
        "print(json.dumps({'time':time.time(),'controllers':controllers,'new_model_GPU_GUI_calls':0,'actual_GUI_processes_exited':processes,'control_postexit_seal_sha256':sha(r/'control/postexit-seal.json')}))")
    compile(COMMON + prefix + source, '<complete-exited-group-controller>', 'exec')
    return prefix + source


def check_technical(controller, mains, flashes, failed, parse):
    t = controller['terminal']
    run = t['run']['run_id']
    assert run == 'flash14-T089-stale_replace-gate'
    assert t['infrastructure_failure'] and t['outcome'] == 'technical_failure' and t['cleanup_error'] is None
    assert t['official_reward'] is None and t['scoring_status'] == 'not_run_technical_or_manual_stop'
    assert t['decisions'] == t['actor_calls'] == t['Flash_request_attempts'] == 28
    assert t['environment_actions'] == len(t['actor_receipts']) == 27 and t['recaptures'] == 0
    events = controller['events']
    select = lambda kind: [v for v in events if v['kind'] == kind]
    requests, replies, forwards = select('actual_actor_request'), select('actual_actor_reply'), select('main_image_forwarded')
    gates, accepted = select('gate_decision'), select('gate_terminal')
    actions, dispatched = select('native_environment_action'), select('native_proposal_dispatched')
    assert len(requests) == len(forwards) == len(gates) == len(accepted) == len(t['Flash_replies']) == 28
    assert len(replies) == len(actions) == len(dispatched) == 27
    captures = {v['data']['capture_id']: v for v in select('capture')}
    rows, success_ids, gate_ids = [], [], []
    for number, (request_event, frame_event, gate_event, end_event) in enumerate(zip(requests, forwards, gates, accepted), 1):
        request, frame, gate, end = (v['data'] for v in [request_event, frame_event, gate_event, end_event])
        online = flashes[gate['request_id']]
        assert gate['request_id'] == frame['gate_request_id'] == t['Flash_replies'][number - 1]['request_id']
        assert online['decision'] == gate['decision'] == 'YES'
        image = online['image_sha256']
        assert image == gate['image_sha256'] == frame['image_sha256'] == end['last_image_sha256']
        assert end['status'] == 'accepted' and end['model_calls'] == 1 and end['recaptures'] == 0
        assert gate['capture_id'] == frame['capture_id'] == end['last_capture_id']
        capture = captures[frame['capture_id']]
        assert capture['data']['image_sha256'] == image
        assert capture['seq'] < gate_event['seq'] < end_event['seq'] < frame_event['seq'] < request_event['seq']
        assert frame['extra_auxiliary_text_in_main_prompt'] is False
        rid = request['request_id']
        gate_ids.append(gate['request_id'])
        if number == 28:
            assert rid == failed['request_id'] and rid not in mains
            assert request['body_sha256'] == failed['body_sha256'] and image == failed['current_image_sha256']
            assert failed['public_success_response_exists'] is False and failed['action_execution_permitted'] is False
            assert failed['decision'] == number and failed['full_raw_input_first_forward_and_sequence_files_verified']
            assert all(v['data']['request_id'] != rid for v in replies)
            assert not any(v['data']['step'] == number for v in actions)
            assert not any(v['seq'] > request_event['seq'] for v in dispatched)
            failures = select('native_actor_or_parser_failure')
            assert len(failures) == 1 and failures[0]['seq'] > request_event['seq'] and failures[0]['data']['executed'] is False
            rows.append({'decision': number, 'request_id': rid, 'gate_request_id': gate['request_id'],
                         'image_sha256': image, 'public_actor_reply': False, 'actual_action': None,
                         'technical_generation_not_semantic_zero': True})
            continue
        native = mains[rid]
        reply, action, dispatch = replies[number - 1], actions[number - 1], dispatched[number - 1]
        transport = t['actor_receipts'][number - 1]
        assert native['run_id'] == run and native['decision'] == number
        assert native['natural_EOS'] and native['actual_tensor_files_verified']
        assert native['body_sha256'] == request['body_sha256'] and native['current_image_sha256'] == image
        assert native['request_id'] == reply['data']['request_id'] == transport['request_id']
        assert native['folder'] == reply['data']['receipt'] == transport['receipt']
        assert native['wire_sha256'] == transport['wire_sha256']
        assert reply['data']['text_sha256'] == __import__('hashlib').sha256(native['native_text'].encode()).hexdigest()
        payload = parse(native['native_text'])
        assert payload['type'] != 'stop' and action['data']['step'] == number
        assert action['data']['payload'] == payload and action['data']['ok'] is True
        assert dispatch['data']['candidate_sha256'] == reply['data']['text_sha256']
        assert dispatch['data']['proposal_unmodified'] is True and dispatch['data']['environment_action'] is True
        assert dispatch['data']['capture_id'] == frame['capture_id'] and dispatch['data']['image_sha256'] == image
        assert request_event['seq'] < reply['seq'] < action['seq'] < dispatch['seq'] < requests[number]['seq']
        success_ids.append(rid)
        rows.append({'decision': number, 'request_id': rid, 'gate_request_id': gate['request_id'],
                     'image_sha256': image, 'public_actor_reply': True, 'actual_action': action['data'],
                     'semantic_label_not_inferred_from_dispatch': True})
    return {'run_id': run, 'technical_attempt_preserved': True, 'actor_requests': success_ids,
            'failed_requests': [failed['request_id']], 'Flash_requests': gate_ids, 'rows': rows,
            'old_source_occurrences_and_costs_preserved': True, 'semantic_Mirage_label': None,
            'failed_generation_not_promoted_to_public_reply': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--group', choices=['parent', 'continuation'], required=True)
    parser.add_argument('--raw', type=Path)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    reader = make_reader()
    parse = parse_original()
    b = load(HERE / 'package/parent-bindings.json')
    contract = load(HERE / 'package/technical-continuation-contract.json')
    parent = args.group == 'parent'
    expected_ids = contract['normal_completed_run_ids'] + [contract['failed_attempt_preserved']['run_id']] if parent else [v['run_id'] for v in contract['remaining_queue']]
    package = b['package3090'] if parent else '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/' + HERE.name
    output = b['output3090'] if parent else '/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name
    manifest = b['manifest_sha256'] if parent else sha(HERE / 'package/manifest.json')
    native_prefix = ('PACKAGE=' + repr(package) + '\nOUTPUT=' + repr(output) + '\nGROUP=' + repr(args.group)
                     + '\nEXPECTED_MANIFEST=' + repr(manifest) + '\nEXPECTED_POSTEXIT=' + repr(b['postexit_seal_sha256']) + '\n' + COMMON)
    if args.prepare_only:
        dest = HERE / ('exited-controller-reader-preparation-' + args.group + '-' + str(time.time_ns()))
        dest.mkdir()
        (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
        (dest / 'remote-reader.py').write_text(reader, encoding='utf8')
        save(dest / 'preparation.json', {'time': time.time(), 'group': args.group,
             'readers_compiled_only_not_executed': True,
             'normal_original_controller_checks_unchanged': True,
             'technical28th_request_separate_no_reply_no_action_branch': True,
             'requires_group_fresh_full_raw_final_seal_and_actual_all_group_exits': True,
             'new_model_GPU_GUI_calls': 0, 'all29_completion_claimed': False})
        save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
        print(json.dumps({'preparation': str(dest), 'actual_controller_audit_executed': False}))
        return
    assert args.raw is not None
    raw_root = args.raw.resolve()
    assert raw_root.parent == HERE
    verify(raw_root)
    summary = load(raw_root / 'summary.json')
    assert summary['group'] == args.group and summary['actual_original_group_process_exits_verified']
    assert summary['request_and_nonrequest_files_complete_under_original_global_seal']
    pointer = HERE / ('exited-' + args.group + '-controller-current.json')
    assert not pointer.exists(), 'Use the completed immutable controller audit'
    raw, op = remote('3090', native_prefix + ADMISSION, 'exited-' + args.group + '-controller-native-exit-and-seal-recheck')
    fresh_native = json.loads(raw)
    assert fresh_native['postexit_seal_sha256'] == load(raw_root / 'admission.json')['result']['postexit_seal_sha256']
    code = ('ROOT=' + repr(output) + '\nGROUP=' + repr(args.group) + '\nMANIFEST_SHA=' + repr(manifest)
            + '\nPARENT_CONTROL_SHA=' + repr(b['GUI_control_postexit_seal_sha256'])
            + '\nEXPECTED_RUN_IDS=' + repr(expected_ids) + '\n' + COMMON + reader)
    text, gui_op = remote('4090', code, 'fresh-exited-' + args.group + '-all-GUI-files-chains-and-bindings', timeout=55)
    collection = json.loads(text)
    native = load(raw_root / '3090.json')
    mains = {v['request_id']: v for v in native['sealed_main_requests']}
    flashes = {v['request_id']: v for v in native['sealed_Flash_requests']}
    failed = native['failed_requests']
    result = []
    for controller in collection['controllers']:
        t = controller['terminal']
        if t['infrastructure_failure']:
            assert parent and len(failed) == 1
            old = contract['failed_attempt_preserved']
            assert controller['terminal_sha256'] == old['terminal_sha256'] and controller['seal_sha256'] == old['seal_sha256']
            assert controller['chain']['head'] == old['chain']['head']
            result.append(check_technical(controller, mains, flashes, failed[0], parse))
        else:
            bound = {'terminal_sha256': controller['terminal_sha256'], 'seal_sha256': controller['seal_sha256'],
                     'event_chain_head': controller['chain']['head'], 'event_chain_count': controller['chain']['verified_prefix_events']}
            result.append(check_controller(controller, mains, flashes, bound, parse))
    ids = [rid for row in result for rid in row['actor_requests']]
    gates = [rid for row in result for rid in row['Flash_requests']]
    rejects = [rid for row in result for rid in row.get('failed_requests', [])]
    assert len(ids) == len(set(ids)) == len(mains) and set(ids) == set(mains)
    assert len(gates) == len(set(gates)) == len(flashes) and set(gates) == set(flashes)
    assert set(rejects) == {v['request_id'] for v in failed} and len(rejects) == (1 if parent else 0)
    dest = HERE / ('fresh-exited-' + args.group + '-controller-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'native-identity-recheck.json', {'result': fresh_native, 'operation': str(op)})
    save(dest / 'GUI-collection.json', {'result': collection, 'operation': str(gui_op)})
    save(dest / 'bindings.json', {'time': time.time(), 'group': args.group,
         'source_full_raw_audit': str(raw_root), 'source_full_raw_seal_sha256': sha(raw_root / 'seal.json'),
         'trajectories': result, 'actor_successful_replies_bound': len(ids), 'Flash_replies_bound': len(gates),
         'failed_undelivered_generations_preserved': len(rejects),
         'all_actual_requests_replies_PNGs_Flash_and_native_actions_bound': True,
         'technical_attempt_not_relabelled_success': True, 'new_model_GPU_GUI_calls': 0,
         'all29_completion_claimed': False, 'semantic_completion_or_effectiveness_proven': False})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    save(pointer, {'root': str(dest), 'seal_sha256': sha(dest / 'seal.json'), 'group': args.group,
         'all29_completion_claimed': False, 'effectiveness_proven': False, 'time': time.time()})
    print(json.dumps({'controller_audit': str(dest), 'group': args.group,
         'successful_main': len(ids), 'Flash': len(gates), 'separate_failed_generation': len(rejects),
         'new_model_GPU_GUI_calls': 0, 'effectiveness_proven': False}))


if __name__ == '__main__':
    main()
