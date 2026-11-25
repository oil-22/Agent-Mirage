"""Original controller reader/checks only; no all29 finalizer import."""
import hashlib
from native_parser_reader import parse_original

GUI_READER = "\nr=Path(ROOT);plan=json.loads((r/'plan.json').read_bytes());controllers=[]\nfor terminal_path in sorted((r/'batch/runs').glob('*/attempt-*/terminal.json')):\n a=terminal_path.parent;t=json.loads(terminal_path.read_bytes());seal=json.loads((a/'seal.json').read_bytes())\n assert sha(terminal_path)==seal['terminal.json']\n assert sha(a/'controller/events.jsonl')==seal['controller/events.jsonl']\n proof,events=chain(a/'controller/events.jsonl');assert not proof['ignored_partial_last_line']\n captures=[v for v in events if v['kind']=='capture']\n for event in captures:\n  h=event['data']['image_sha256']\n  if h is not None:assert sha(a/'controller'/(h+'.png'))==h\n ledgers=[v for v in events if v['kind']=='PRIVATE_delivery_ledger']\n for event in ledgers:\n  row=event['data'];n=row['step']\n  assert sha(a/('%03d-actually-captured.png'%n))==row['captured_sha256']\n  assert sha(a/('%03d-initial-delivered.png'%n))==row['delivered_sha256']\n controllers.append({'attempt':str(a),'terminal':t,'terminal_sha256':sha(terminal_path),\n                     'seal_sha256':sha(a/'seal.json'),'chain':proof,'events':events})\nassert len(controllers)==29 and {v['terminal']['run']['run_id']for v in controllers}=={v['run_id']for v in plan['queue']}\nprint(json.dumps({'time':time.time(),'controllers':controllers,'new_model_GPU_GUI_calls':0}))\n"

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
